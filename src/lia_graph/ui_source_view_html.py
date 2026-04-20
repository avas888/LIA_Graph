"""HTML rendering for the source-view window.

Extracted from `ui_source_view_processors.py` during granularize-v2
(2026-04-20). This is the final presentation layer that takes the
processed source content and produces the HTML the user sees at
`/source-view?doc_id=…` — a self-contained page with embedded CSS,
meta chips, download actions, and the rendered article body.

Contract:

  * `_build_source_view_href(doc_id, view, question_context, citation_context, full)`
    — build the `/source-view?...` URL with sanitized query params.
  * `_build_source_view_html(…)` — assemble the full HTML document
    string (title, `<head>` with inline CSS, meta card, action buttons,
    rendered content).
  * `_render_source_view_markdown_html(text)` — block-level markdown →
    HTML (headings, lists, blockquotes, code fences, horizontal rules,
    paragraphs).
  * `_render_source_view_inline_markdown(text)` — inline markdown
    (links, code spans, bold, italic) with HTML escaping and `<a
    target="_blank" rel="noopener noreferrer">` for external links.
  * `_sanitize_source_view_href(value)` — href whitelist (http/https/
    root-relative/mailto/tel only).

Dependencies:

  * stdlib `html` + `re` (pure) and `urllib.parse.urlencode`
  * `_ui()._sanitize_question_context` — resolved via the ui_server
    lazy registry (currently points at `ui_chunk_relevance`).

Consumers (external): `ui_server.py` imports `_build_source_view_href`,
`_build_source_view_html`, `_render_source_view_markdown_html` directly
as part of its controller wiring. Those imports continue to work
because `ui_source_view_processors.py` re-imports all five names from
this module.
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlencode


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _sanitize_source_view_href(value: str) -> str:
    href = str(value or "").strip()
    if not href:
        return ""
    if href.startswith("/"):
        return href
    if re.match(r"^https?://", href, re.IGNORECASE):
        return href
    if re.match(r"^(mailto|tel):", href, re.IGNORECASE):
        return href
    return ""


def _render_source_view_inline_markdown(text: str) -> str:
    source = str(text or "")
    placeholders: dict[str, str] = {}

    def reserve(rendered: str) -> str:
        token = f"@@MDTOKEN{len(placeholders)}@@"
        placeholders[token] = rendered
        return token

    def replace_code(match: re.Match[str]) -> str:
        return reserve(f"<code>{html.escape(match.group(1))}</code>")

    source = re.sub(r"`([^`\n]+)`", replace_code, source)

    def replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "").strip()
        href = _sanitize_source_view_href(match.group(2))
        if not href:
            return reserve(html.escape(label))
        rel = " target='_blank' rel='noopener noreferrer'" if href.startswith(("http://", "https://")) else ""
        return reserve(f"<a href='{html.escape(href)}'{rel}>{html.escape(label)}</a>")

    source = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", replace_link, source)

    rendered = html.escape(source)
    rendered = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", rendered)
    rendered = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<em>\1</em>", rendered)
    for token, replacement in placeholders.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def _render_source_view_markdown_html(text: str) -> str:
    source = str(text or "").replace("\r\n", "\n").strip()
    if not source:
        return ""

    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    list_tag: str | None = None
    quote_lines: list[str] = []
    code_lines: list[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text_value = " ".join(line.strip() for line in paragraph_lines if line.strip())
        if text_value:
            blocks.append(f"<p>{_render_source_view_inline_markdown(text_value)}</p>")
        paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_items, list_tag
        if not list_items or not list_tag:
            list_items = []
            list_tag = None
            return
        items_html = "".join(f"<li>{_render_source_view_inline_markdown(item)}</li>" for item in list_items)
        blocks.append(f"<{list_tag}>{items_html}</{list_tag}>")
        list_items = []
        list_tag = None

    def flush_quote() -> None:
        nonlocal quote_lines
        if not quote_lines:
            return
        text_value = " ".join(line.strip() for line in quote_lines if line.strip())
        if text_value:
            blocks.append(f"<blockquote><p>{_render_source_view_inline_markdown(text_value)}</p></blockquote>")
        quote_lines = []

    def flush_code() -> None:
        nonlocal code_lines
        if not code_lines:
            return
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
        code_lines = []

    for raw_line in source.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code_block:
                flush_code()
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = min(len(heading_match.group(1)), 6)
            content = _render_source_view_inline_markdown(heading_match.group(2).strip())
            blocks.append(f"<h{level}>{content}</h{level}>")
            continue

        if re.match(r"^([-*_])\1{2,}$", stripped):
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append("<hr>")
            continue

        quote_match = re.match(r"^>\s?(.*)$", stripped)
        if quote_match:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote_match.group(1))
            continue

        list_match = re.match(r"^([-*]|\d+\.)\s+(.+)$", stripped)
        if list_match:
            flush_paragraph()
            flush_quote()
            current_tag = "ol" if list_match.group(1).endswith(".") and list_match.group(1)[0].isdigit() else "ul"
            if list_tag and list_tag != current_tag:
                flush_list()
            list_tag = current_tag
            list_items.append(list_match.group(2).strip())
            continue

        flush_list()
        flush_quote()
        paragraph_lines.append(stripped)

    if in_code_block:
        flush_code()
    else:
        flush_paragraph()
        flush_list()
        flush_quote()

    return "".join(blocks)


def _build_source_view_html(
    *,
    title: str,
    doc_id_html: str,
    tier_label_html: str,
    provider_label_html: str,
    reference_link_html: str,
    artifact_label: str,
    download_href: str,
    switch_view_html: str,
    official_link_html: str,
    rendered_content_html: str,
    raw_fallback_html: str,
    show_meta_card: bool = True,
    viewer_note: str = "Visor de cliente final: muestra resumen estructurado y enlaces de soporte.",
) -> str:
    """Return a user-facing HTML page for citation support content."""
    heading = "Contenido de Apoyo Proveido por Loggro"
    meta_card_html = ""
    if show_meta_card:
        meta_card_html = (
            "<section class='meta-card'>"
            "<div class='chip-row'>"
            f"<span class='chip'>Fuente: {tier_label_html}</span>"
            f"<span class='chip'>Proveedor: {provider_label_html}</span>"
            f"<span class='chip'>Documento: {artifact_label}</span>"
            "</div>"
            f"<p class='meta-link'>{reference_link_html}</p>"
            f"<p class='viewer-note'>{html.escape(viewer_note)}</p>"
            "</section>"
        )
    download_md_href = download_href.replace("&format=pdf", "&format=md")
    actions_html = (
        "<div class='actions'>"
        f"<a class='btn primary' href='{html.escape(download_href)}'>Descargar PDF</a>"
        f"<a class='btn' href='{html.escape(download_md_href)}'>Descargar Markdown</a>"
        f"{switch_view_html}"
        f"{official_link_html}"
        "</div>"
    )
    if "view=original" in download_href:
        normalized_md_href = (
            download_href.replace("view=original", "view=normalized").replace("&format=original", "&format=md")
        )
        actions_html = (
            "<div class='actions'>"
            f"<a class='btn primary' href='{html.escape(download_href)}'>Descargar original</a>"
            f"<a class='btn' href='{html.escape(normalized_md_href)}'>Descargar Markdown</a>"
            f"{switch_view_html}"
            f"{official_link_html}"
            "</div>"
        )

    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<style>"
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}"
        "body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;background:#f3f0eb;color:#1a1a1a;}"
        ".page-wrapper{max-width:900px;margin:0 auto;padding:20px 16px 28px;}"
        ".support-title{font-size:1.32rem;font-weight:700;color:#143f32;margin:0 0 14px;}"
        ".page{background:#fff;border:1px solid #d4cfc8;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,.04);padding:26px 24px;min-height:520px;"
        "line-height:1.75;font-size:.95rem;color:#2a2520;}"
        ".meta-card{border:1px solid #d8d2ca;background:#f8f5f0;padding:12px 14px;border-radius:8px;margin-bottom:12px;}"
        ".chip-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;}"
        ".chip{display:inline-flex;border:1px solid #c8d3cd;background:#edf4f1;color:#184437;border-radius:999px;padding:3px 10px;font-size:.78rem;font-weight:600;}"
        ".meta-link{font-size:.84rem;color:#595349;}"
        ".viewer-note{font-size:.8rem;color:#6a645b;}"
        ".actions{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px;}"
        ".btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid #b8c9c2;border-radius:8px;padding:7px 12px;font-size:.82rem;font-weight:700;color:#15513f;background:#f4faf7;text-decoration:none;}"
        ".btn.primary{background:#0f5a47;color:#fff;border-color:#0f5a47;}"
        ".page h1{font-size:1.55rem;font-weight:700;color:#1a1714;margin:0 0 18px;"
        "padding-bottom:10px;border-bottom:2px solid #e8e3db;}"
        ".page h2{font-size:1.25rem;font-weight:700;color:#2c2620;margin:28px 0 12px;"
        "padding-bottom:6px;border-bottom:1px solid #ede8e0;}"
        ".page h3{font-size:1.08rem;font-weight:600;color:#3a3228;margin:22px 0 8px;}"
        ".page h4{font-size:.96rem;font-weight:600;color:#4a4238;margin:18px 0 6px;}"
        ".page p{margin:0 0 14px;}"
        ".page ul,.page ol{margin:0 0 14px;padding-left:26px;}"
        ".page li{margin:0 0 6px;}"
        ".page li>ul,.page li>ol{margin:4px 0 4px;}"
        ".page strong{font-weight:700;color:#1a1714;}"
        ".page em{font-style:italic;}"
        ".page code{font-family:'SF Mono','Fira Code',Consolas,monospace;"
        "font-size:.86em;background:#f5f2ed;border:1px solid #e5e0d8;"
        "border-radius:4px;padding:1px 5px;color:#8b4513;}"
        ".page pre{background:#faf8f5;border:1px solid #e5e0d8;border-radius:8px;"
        "padding:14px 18px;overflow-x:auto;margin:0 0 14px;}"
        ".page pre code{background:none;border:none;padding:0;font-size:.84rem;"
        "line-height:1.5;}"
        ".page blockquote{border-left:3px solid #d4cfc8;margin:0 0 14px;"
        "padding:8px 16px;color:#5a534b;background:#faf9f7;border-radius:0 6px 6px 0;}"
        ".page hr{border:none;border-top:1px solid #e5e0d8;margin:24px 0;}"
        ".page table{border-collapse:collapse;width:100%;margin:0 0 14px;"
        "font-size:.88rem;}"
        ".page th,.page td{border:1px solid #e0dbd3;padding:8px 12px;text-align:left;}"
        ".page th{background:#f5f2ed;font-weight:600;color:#2c2620;}"
        ".page a{color:#4a6cf7;text-decoration:none;}"
        ".page a:hover{text-decoration:underline;}"
        ".page-raw{white-space:pre-wrap;word-wrap:break-word;"
        "font-family:'SF Mono','Fira Code',Consolas,monospace;"
        "font-size:.86rem;line-height:1.55;}"
        "@media(max-width:700px){.page-wrapper{padding:16px 10px 20px;}.page{padding:18px 14px;}}"
        "</style>"
        "</head><body>"
        "<div class='page-wrapper'>"
        f"<h1 class='support-title'>{html.escape(heading)}</h1>"
        f"<p class='meta-link' style='margin:0 0 8px'>doc_id: {doc_id_html}</p>"
        "<div class='page' id='doc-content'>"
        f"{meta_card_html}"
        f"{actions_html}"
        f"<div id='rendered-content'>{rendered_content_html}</div>"
        f"{raw_fallback_html}"
        "</div>"
        "</div>"
        "</body></html>"
    )


def _build_source_view_href(
    *,
    doc_id: str,
    view: str = "normalized",
    question_context: str = "",
    citation_context: str = "",
    full: bool = False,
) -> str:
    params: dict[str, str] = {"doc_id": str(doc_id or "").strip()}
    normalized_view = str(view or "normalized").strip().lower() or "normalized"
    if normalized_view == "original":
        params["view"] = "original"
    q_clean = _ui()._sanitize_question_context(question_context)
    if q_clean:
        params["q"] = q_clean
    cq_clean = _ui()._sanitize_question_context(citation_context, max_chars=240)
    if cq_clean:
        params["cq"] = cq_clean
    if full:
        params["full"] = "1"
    return f"/source-view?{urlencode(params)}"
