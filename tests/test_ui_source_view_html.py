"""Unit tests for `lia_graph.ui_source_view_html`.

Locks in the contract the `/source-view?doc_id=…` endpoint depends on:
href sanitization (XSS defense), inline + block-level markdown rendering,
and the download-URL builder. These tests replaced no-op coverage — the
rendering cluster previously lived inside the 1600-LOC
`ui_source_view_processors.py` module with no direct tests.
"""

from __future__ import annotations

from lia_graph.ui_source_view_html import (
    _build_source_view_href,
    _build_source_view_html,
    _render_source_view_inline_markdown,
    _render_source_view_markdown_html,
    _sanitize_source_view_href,
)


def test_sanitize_href_allows_http_and_https() -> None:
    assert _sanitize_source_view_href("https://dian.gov.co/x") == "https://dian.gov.co/x"
    assert _sanitize_source_view_href("http://example.com") == "http://example.com"


def test_sanitize_href_allows_root_relative() -> None:
    assert _sanitize_source_view_href("/source-view?doc_id=x") == "/source-view?doc_id=x"


def test_sanitize_href_allows_mailto_and_tel() -> None:
    assert _sanitize_source_view_href("mailto:user@example.com") == "mailto:user@example.com"
    assert _sanitize_source_view_href("tel:+123") == "tel:+123"


def test_sanitize_href_blocks_unsafe_schemes() -> None:
    assert _sanitize_source_view_href("javascript:alert(1)") == ""
    assert _sanitize_source_view_href("data:text/html,xss") == ""
    assert _sanitize_source_view_href("file:///etc/passwd") == ""
    assert _sanitize_source_view_href("") == ""


def test_inline_markdown_renders_link_with_blank_target() -> None:
    out = _render_source_view_inline_markdown("See [DIAN](https://dian.gov.co)")
    assert "<a href='https://dian.gov.co'" in out
    assert "target='_blank'" in out
    assert "rel='noopener noreferrer'" in out
    assert ">DIAN</a>" in out


def test_inline_markdown_strips_unsafe_link_but_keeps_label() -> None:
    out = _render_source_view_inline_markdown("[click](javascript:alert(1))")
    assert "<a " not in out
    assert "click" in out


def test_inline_markdown_renders_bold_italic_and_code() -> None:
    out = _render_source_view_inline_markdown("This is **bold** and *italic* and `code`")
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out


def test_inline_markdown_escapes_raw_html() -> None:
    out = _render_source_view_inline_markdown("Text with <script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_block_markdown_renders_headings_and_paragraphs() -> None:
    out = _render_source_view_markdown_html("# Title\n\n## Subtitle\n\nParagraph text.")
    assert "<h1>Title</h1>" in out
    assert "<h2>Subtitle</h2>" in out
    assert "<p>Paragraph text.</p>" in out


def test_block_markdown_renders_ordered_and_unordered_lists() -> None:
    out = _render_source_view_markdown_html("- Apple\n- Banana\n\n1. First\n2. Second")
    assert "<ul>" in out and "<li>Apple</li>" in out and "<li>Banana</li>" in out
    assert "<ol>" in out and "<li>First</li>" in out and "<li>Second</li>" in out


def test_block_markdown_renders_blockquote_and_hr() -> None:
    out = _render_source_view_markdown_html("> Quoted text\n\n---\n\nAfter hr")
    assert "<blockquote>" in out and "Quoted text" in out
    assert "<hr>" in out


def test_block_markdown_preserves_code_block_content() -> None:
    source = "```\nline1\nline2\n```"
    out = _render_source_view_markdown_html(source)
    assert "<pre><code>" in out
    assert "line1" in out and "line2" in out


def test_block_markdown_empty_input() -> None:
    assert _render_source_view_markdown_html("") == ""
    assert _render_source_view_markdown_html("   \n   \n") == ""


def test_build_source_view_href_basic(monkeypatch) -> None:
    import lia_graph.ui_source_view_html as mod

    class _StubUi:
        @staticmethod
        def _sanitize_question_context(text: str, max_chars: int = 320) -> str:
            return str(text or "").strip()

    monkeypatch.setattr(mod, "_ui", lambda: _StubUi())

    href = _build_source_view_href(doc_id="renta_corpus_a_et_art_290")
    assert href.startswith("/source-view?")
    assert "doc_id=renta_corpus_a_et_art_290" in href


def test_build_source_view_href_adds_view_and_contexts(monkeypatch) -> None:
    import lia_graph.ui_source_view_html as mod

    class _StubUi:
        @staticmethod
        def _sanitize_question_context(text: str, max_chars: int = 320) -> str:
            return str(text or "").strip()

    monkeypatch.setattr(mod, "_ui", lambda: _StubUi())

    href = _build_source_view_href(
        doc_id="doc_x",
        view="original",
        question_context="question",
        citation_context="cite",
        full=True,
    )
    assert "view=original" in href
    assert "q=question" in href
    assert "cq=cite" in href
    assert "full=1" in href


def test_build_source_view_html_includes_required_sections() -> None:
    out = _build_source_view_html(
        title="Mi Documento",
        doc_id_html="doc_123",
        tier_label_html="Normativo",
        provider_label_html="DIAN",
        reference_link_html="<a href='/x'>Ref</a>",
        artifact_label="Decreto",
        download_href="/download?doc_id=doc_123&format=pdf",
        switch_view_html="",
        official_link_html="",
        rendered_content_html="<p>Body</p>",
        raw_fallback_html="",
    )
    assert "<!doctype html>" in out
    assert "<title>Mi Documento</title>" in out
    assert "doc_id: doc_123" in out
    assert "<p>Body</p>" in out
    assert "Descargar PDF" in out
    assert "Descargar Markdown" in out


def test_build_source_view_html_skips_meta_card_when_disabled() -> None:
    out = _build_source_view_html(
        title="X",
        doc_id_html="d",
        tier_label_html="",
        provider_label_html="",
        reference_link_html="",
        artifact_label="",
        download_href="/d",
        switch_view_html="",
        official_link_html="",
        rendered_content_html="",
        raw_fallback_html="",
        show_meta_card=False,
    )
    assert "class='meta-card'" not in out


def test_build_source_view_html_switches_action_labels_for_original_view() -> None:
    out = _build_source_view_html(
        title="X",
        doc_id_html="d",
        tier_label_html="",
        provider_label_html="",
        reference_link_html="",
        artifact_label="",
        download_href="/download?view=original&format=original",
        switch_view_html="",
        official_link_html="",
        rendered_content_html="",
        raw_fallback_html="",
        show_meta_card=False,
    )
    assert "Descargar original" in out
    # Markdown variant swaps view + format back to normalized/md.
    assert "view=normalized" in out
    assert "format=md" in out


def test_reexport_from_host_module_has_same_identity() -> None:
    from lia_graph.ui_source_view_processors import (
        _build_source_view_html as host_html,
        _render_source_view_markdown_html as host_md,
    )
    assert host_html is _build_source_view_html
    assert host_md is _render_source_view_markdown_html
