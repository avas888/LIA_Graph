"""SUIN-Juriscol HTML → structured `SuinDocument` parser.

Handles the DOM conventions documented in `docs/next/ingestion_suin.md` Phase A:

- `<a name="ver_<id>">` anchors mark article boundaries.
- `<div class="articulo_normal">` carries the article body.
- `<li class="referencia">` items sit inside `<ul id="NotasDestino*">` (legislative
  outbound), `<ul id="NotasDestinoJurisp*">` (jurisprudence outbound), or
  `<ul id="NotasOrigen*">` (reciprocal, on the sentencia side). The container's
  id prefix tells us the edge's kind.
- Each `<li>` has a `<span>` with the raw verb ("modificado", "declara_exequible", …),
  an optional parenthetical scope, and an `<a href="/viewDocument.asp?id=<n>#ver_<m>">`
  pointing at the target.

The parser routes by container-id prefix, normalizes the Spanish verb onto a
closed canonical vocabulary, and fails loud on unknown verbs (never a silent
fallback — extending vocabulary is a code edit, by design).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
import re
import unicodedata
from typing import Optional
from urllib.parse import parse_qs, urlparse

import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# SUIN HTML documents start with `<?xml version="1.0"?>` — BeautifulSoup's
# `lxml` HTML parser emits `XMLParsedAsHTMLWarning` on every parse because the
# preamble looks like XML, even though the body is HTML. We want the HTML
# parser (not `features="xml"`) because the DOM is genuinely HTML; just
# silence the false-positive warning so live harvests log cleanly.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class UnknownVerb(ValueError):
    """Raised when a `<span>` verb cannot be mapped onto the canonical set.

    Carries the raw token so the operator can extend `_VERB_ALIASES` in one
    place. Silent fallback is deliberately disallowed — we prefer a loud run
    failure over a corpus of mis-typed edges.
    """

    def __init__(self, raw: str, *, hint: str | None = None) -> None:
        self.raw = raw
        self.hint = hint
        message = f"Unknown SUIN verb: {raw!r}"
        if hint:
            message = f"{message} ({hint})"
        super().__init__(message)


CANONICAL_VERBS: frozenset[str] = frozenset(
    {
        "modifica",
        "adiciona",
        "deroga",
        "reglamenta",
        "suspende",
        "anula",
        "declara_exequible",
        "declara_inexequible",
        "inhibida",
        "estarse_a_lo_resuelto",
        "nota_editorial",
    }
)


_CONTAINER_KINDS = {
    "NotasDestino": "NotasDestino",
    "NotasDestinoJurisp": "NotasDestinoJurisp",
    "NotasOrigen": "NotasOrigen",
    "NotasOrigenJurisp": "NotasOrigen",
    "leg_ant": "leg_ant",
}


# Raw SUIN verb tokens (lowercased, accent-stripped, whitespace-collapsed) ->
# canonical vocab. Extending this is a code change. That is the point.
_VERB_ALIASES: dict[str, str] = {
    # modifies family
    "modificado": "modifica",
    "modificado parcialmente": "modifica",
    "modifica": "modifica",
    "modifica parcialmente": "modifica",
    "sustituido": "modifica",
    "sustituye": "modifica",
    "modificado y adicionado": "modifica",
    "modifica y adiciona": "modifica",
    "subrogado": "modifica",
    "subroga": "modifica",
    # adds
    "adicionado": "adiciona",
    "adiciona": "adiciona",
    "adicionado parcialmente": "adiciona",
    # repeals
    "derogado": "deroga",
    "deroga": "deroga",
    "derogado parcialmente": "deroga",
    "deroga parcialmente": "deroga",
    # regulates
    "reglamentado": "reglamenta",
    "reglamenta": "reglamenta",
    "reglamentado parcialmente": "reglamenta",
    # suspends
    "suspendido": "suspende",
    "suspende": "suspende",
    # annuls
    "anula": "anula",
    "anulado": "anula",
    "nulidad": "anula",
    # constitutional
    "declara exequible": "declara_exequible",
    "declarado exequible": "declara_exequible",
    "exequible": "declara_exequible",
    "declara inexequible": "declara_inexequible",
    "declarado inexequible": "declara_inexequible",
    "inexequible": "declara_inexequible",
    "inhibida": "inhibida",
    "inhibida para emitir pronunciamiento": "inhibida",
    "inhibida para emitir pronunciamiento de fondo": "inhibida",
    "declarada inhibida": "inhibida",
    "declarada inhibida para emitir pronunciamiento": "inhibida",
    "declarada inhibida para emitir pronunciamiento de fondo": "inhibida",
    "declarado inhibido": "inhibida",
    "declarado inhibido para emitir pronunciamiento": "inhibida",
    "declarado inhibido para emitir pronunciamiento de fondo": "inhibida",
    "estarse a lo resuelto": "estarse_a_lo_resuelto",
    # editorial annotations (kept for metadata; bridge drops the edge)
    "nota editorial": "nota_editorial",
    "nota": "nota_editorial",
    "observacion": "nota_editorial",
}


_FRAGMENT_ID_RE = re.compile(r"ver_(\d+)")
_SCOPE_PAREN_RE = re.compile(r"\s*\(([^)]+)\)\s*")
# Article-heading capture. Allows DUR-style multi-segment numbers ("1.1.1",
# "1.6.1.1.10") which the original `(?:[-.]\d+)?` form truncated to "1.1".
# Order of the inner alternation matters: match all dotted/dashed numeric
# extensions BEFORE the optional "bis" suffix, so "Artículo 364-4" still
# captures "364-4" and "Artículo 1 bis" still captures "1 bis".
_ARTICLE_HEADING_RE = re.compile(
    r"(?i)\bart(?:[ií]culo)?\s+(?P<number>\d+(?:[-.]\d+)*(?:\s*[Bb][Ii][Ss])?)"
)
# Strip every non-ASCII-alnum sequence; keep `-` as the only separator so
# keys survive sanitize passes in the Supabase sink (`[^A-Za-z0-9_.-]+`).
# Spanish characters (ñ/á/é/í/ó/ú/ü), NBSPs, and assorted whitespace are all
# folded by NFKD + regex replace.
_KEY_NON_SAFE_RE = re.compile(r"[^A-Za-z0-9]+")


def _ascii_fold(raw: str) -> str:
    """NFKD-normalize then drop combining marks so ñ→n, á→a, ü→u, etc."""
    text = unicodedata.normalize("NFKD", raw or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _normalize_token(raw: str) -> str:
    """Verb-token normalizer: lower, accent-fold, collapse whitespace, trim punct."""
    text = _ascii_fold(raw)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".:,;")
    return text


def normalize_article_key(raw: str) -> str:
    """Canonicalize a SUIN article number so the sink/graph sees a stable key.

    - NFKD + accent-strip (Á→A, ñ→n) so Spanish characters do not leak into keys.
    - Replace every non-[A-Za-z0-9] run with a single `-` (NBSP, regular space,
      `_`, punctuation all collapse to one separator).
    - Lowercase for case-stable comparisons.
    - Trim leading/trailing separators.

    Examples:

        >>> normalize_article_key("135")
        '135'
        >>> normalize_article_key("135 bis")
        '135-bis'
        >>> normalize_article_key("Art. 364-4")
        'art-364-4'
        >>> normalize_article_key("Artículo  1º")
        'articulo-1'
    """
    text = _ascii_fold(raw or "").lower()
    text = _KEY_NON_SAFE_RE.sub("-", text)
    return text.strip("-")


def normalize_doc_id(raw: str) -> str:
    """Canonicalize a SUIN ruta/doc_id.

    Kept case-sensitive (to preserve `Decretos` / `Leyes` folder semantics) but
    accent-folded and whitespace-collapsed to ASCII so the downstream sanitizer
    in `supabase_sink._sanitize_doc_id` receives only `[A-Za-z0-9_.-]`-friendly
    input. `/` is preserved so the relative_path still reads as a path.
    """
    text = _ascii_fold(raw or "")
    text = re.sub(r"\s+", "_", text.strip())
    # Keep alnum + _ . - /; collapse everything else (NBSP, punctuation, etc.)
    text = re.sub(r"[^A-Za-z0-9_./-]+", "_", text)
    return text.strip("_/")


def normalize_verb(raw: str) -> str:
    """Return canonical verb for `raw` or raise `UnknownVerb`.

    SUIN emits long-tail phrasings for the same canonical action
    ("Declarado exequible bajo el entendido ...", "Modificado por el
    artículo X...", "Declarada inhibida para emitir pronunciamiento de
    fondo"). We try (1) exact alias, (2) underscore-collapsed alias,
    (3) ordered stem match on the closed-vocab family. Only (3) lets
    conditional/qualified phrasings resolve without a manual alias edit.
    """
    key = _normalize_token(raw)
    if not key:
        raise UnknownVerb(raw, hint="empty token")
    # Direct alias
    canonical = _VERB_ALIASES.get(key)
    if canonical is not None:
        return canonical
    # Collapsed underscores (some DOM tokens use underscores): "declara_exequible"
    collapsed = key.replace("_", " ")
    canonical = _VERB_ALIASES.get(collapsed)
    if canonical is not None:
        return canonical
    # Stem fallback — order matters; more specific stems first so
    # "inexequible" beats "exequible", "modificad" beats "modifica", etc.
    for stem, canonical_stem in _VERB_STEM_PATTERNS:
        if stem in key:
            return canonical_stem
    raise UnknownVerb(raw, hint=f"normalized={key!r}")


# Stem-based fallback matching for SUIN's long-tail phrasings. Only used when
# both exact-alias and underscore-collapsed lookups miss. Order is significant:
# `inexequible` must come before `exequible` so "declarado inexequible" does
# not false-match as `declara_exequible`.
_VERB_STEM_PATTERNS: list[tuple[str, str]] = [
    ("inexequible", "declara_inexequible"),
    ("exequible", "declara_exequible"),
    ("estarse a lo resuelto", "estarse_a_lo_resuelto"),
    ("inhibi", "inhibida"),        # inhibida / inhibido / declarada inhibida …
    ("denegad", "estarse_a_lo_resuelto"),  # "Denegadas las pretensiones" / "Denegada la pretensión"
    ("niega", "estarse_a_lo_resuelto"),     # "Niega la pretensión"
    ("decret", "estarse_a_lo_resuelto"),    # "Decreta" / "decretó" — procedural
    ("rechazad", "estarse_a_lo_resuelto"), # "Rechazada la demanda por cosa juzgada"
    ("cosa juzgad", "estarse_a_lo_resuelto"),
    ("estarse a lo decidido", "estarse_a_lo_resuelto"),
    ("nulidad", "anula"),
    ("anulad", "anula"),
    ("anula", "anula"),            # "Anula la parte …" (bare inflection)
    ("declara nulo", "anula"),      # "Declara nulo" — contencioso administrativo annulment
    ("declara probad", "estarse_a_lo_resuelto"),  # "Declara probada la excepción"
    ("excepcion", "estarse_a_lo_resuelto"),        # fallback — any verb about "excepción"
    ("inaplica", "declara_inexequible"),           # excepción de inconstitucionalidad
    ("no accede", "estarse_a_lo_resuelto"),         # "No accede" — denies request
    ("repone", "estarse_a_lo_resuelto"),             # "No repone" / "No se repone el auto"
    ("estarse a lo dispuesto", "estarse_a_lo_resuelto"),
    ("declara la legalidad", "estarse_a_lo_resuelto"),
    ("declara ajustad", "estarse_a_lo_resuelto"),   # "Declara ajustado al ordenamiento jurídico"
    ("declara la conformidad", "estarse_a_lo_resuelto"),
    ("abstenerse", "estarse_a_lo_resuelto"),        # court refuses to rule
    ("rechaza", "estarse_a_lo_resuelto"),           # "Rechaza el recurso" / "Rechaza la demanda"
    ("constitucional", "declara_exequible"),        # bare "Constitucional" verb (implicit exequible)
    ("decaimiento", "deroga"),                      # "Declara el decaimiento" — norm lapses
    ("decrara ajustad", "estarse_a_lo_resuelto"),   # typo variant of "declara ajustado"
    ("subrog", "modifica"),
    ("sustitu", "modifica"),
    ("modificad", "modifica"),
    ("modifica", "modifica"),
    ("adicionad", "adiciona"),
    ("adicion", "adiciona"),
    ("agreg", "adiciona"),          # "Agrega" / "Agregado"
    ("incluid", "adiciona"),        # "Incluido"
    ("incorporad", "adiciona"),     # "Incorporado"
    ("reglamentad", "reglamenta"),
    ("reglamenta", "reglamenta"),
    ("desarroll", "reglamenta"),   # "desarrollado por" — reglamentary development
    ("derog", "deroga"),
    ("suprim", "deroga"),          # "suprimido" — article removed; semantic derogation
    ("elimin", "deroga"),           # "eliminado" — same
    ("reemplaz", "modifica"),       # "reemplazado por"
    ("reform", "modifica"),         # "reformado por"
    ("cambiad", "modifica"),
    ("transfer", "modifica"),
    ("renombrad", "modifica"),
    ("fusionad", "modifica"),
    ("reducid", "modifica"),
    ("ampliad", "adiciona"),
    ("agregad", "adiciona"),
    ("regulad", "reglamenta"),
    ("fijad", "reglamenta"),        # value established by reglamentary norm
    ("prorrog", "reglamenta"),      # "prorrogado" — extended
    ("condicionad", "declara_exequible"),  # conditional constitutionality variant
    ("interpretad", "estarse_a_lo_resuelto"),  # "interpretado" — procedural reference
    ("confirm", "estarse_a_lo_resuelto"),       # "confirmado"
    ("suspen", "suspende"),
    ("observ", "nota_editorial"),
    ("nota", "nota_editorial"),
    ("correg", "nota_editorial"),   # "corregido yerro" / "corregido por" — fe de erratas
    ("yerro", "nota_editorial"),
    ("fe de erratas", "nota_editorial"),
    ("aclarad", "nota_editorial"),
    ("rectificad", "nota_editorial"),
    # Jurisprudence-light references — unification, interpretation, no structural change
    ("unificad", "estarse_a_lo_resuelto"),
]


@dataclass(frozen=True)
class SuinEdge:
    verb: str  # canonical
    raw_verb: str
    scope: str | None
    target_doc_id: str | None
    target_fragment_id: str | None
    target_citation: str
    container_kind: str  # one of _CONTAINER_KINDS.values()

    def to_dict(self) -> dict[str, object]:
        return {
            "verb": self.verb,
            "raw_verb": self.raw_verb,
            "scope": self.scope,
            "target_doc_id": self.target_doc_id,
            "target_fragment_id": self.target_fragment_id,
            "target_citation": self.target_citation,
            "container_kind": self.container_kind,
        }


@dataclass(frozen=True)
class SuinArticle:
    article_number: str
    article_fragment_id: str  # `ver_<id>` without the prefix
    heading: str
    body_html: str
    body_text: str
    outbound_edges: tuple[SuinEdge, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "article_number": self.article_number,
            "article_fragment_id": self.article_fragment_id,
            "heading": self.heading,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "outbound_edges": [e.to_dict() for e in self.outbound_edges],
        }


@dataclass(frozen=True)
class SuinDocument:
    doc_id: str
    ruta: str
    title: str
    emitter: str
    diario_oficial: str
    fecha_publicacion: str
    rama: str
    materia: str
    vigencia: str  # "vigente" | "derogada" | "suspendida" | "desconocida"
    articles: tuple[SuinArticle, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "ruta": self.ruta,
            "title": self.title,
            "emitter": self.emitter,
            "diario_oficial": self.diario_oficial,
            "fecha_publicacion": self.fecha_publicacion,
            "rama": self.rama,
            "materia": self.materia,
            "vigencia": self.vigencia,
            "articles": [a.to_dict() for a in self.articles],
        }


def parse_document(
    html: str,
    *,
    doc_id: str,
    ruta: str = "",
    strict_verbs: bool = True,
    verb_failures: list[dict[str, str]] | None = None,
) -> SuinDocument:
    """Parse a single SUIN document HTML blob into a `SuinDocument`.

    Set `strict_verbs=False` only for regression fuzzing — production runs must
    keep `strict_verbs=True` so unknown tokens fail loud (see `UnknownVerb`).

    When `strict_verbs=False`, pass a `verb_failures` list to collect every
    per-edge `UnknownVerb` so callers can audit the long tail of SUIN
    phrasings that need a canonical alias.
    """
    soup = BeautifulSoup(html or "", "lxml")
    metadata = _extract_metadata(soup)

    anchors = soup.find_all("a", attrs={"name": re.compile(r"^ver_\d+$")})
    articles: list[SuinArticle] = []
    for anchor in anchors:
        article = _extract_article(
            anchor, strict_verbs=strict_verbs, verb_failures=verb_failures
        )
        if article is not None:
            articles.append(article)

    return SuinDocument(
        doc_id=str(doc_id),
        ruta=str(ruta or ""),
        title=metadata.get("title", ""),
        emitter=metadata.get("emitter", ""),
        diario_oficial=metadata.get("diario_oficial", ""),
        fecha_publicacion=metadata.get("fecha_publicacion", ""),
        rama=metadata.get("rama", ""),
        materia=metadata.get("materia", ""),
        vigencia=metadata.get("vigencia", "desconocida"),
        articles=tuple(articles),
    )


def _extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Pull header metadata from SUIN's standard `<meta>` and `<div class="ficha*">` blocks.

    Falls back gracefully — all fields default to empty strings rather than
    failing, because SUIN ficha completeness varies by document.
    """
    meta: dict[str, str] = {}
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        meta["title"] = title_tag.string.strip()

    def _row(label: str) -> str | None:
        node = soup.find(
            "span", string=re.compile(rf"^\s*{re.escape(label)}\s*:", re.IGNORECASE)
        )
        if node is None:
            return None
        sibling = node.next_sibling
        if sibling is None:
            parent = node.parent
            if parent is not None:
                text = parent.get_text(" ", strip=True)
                _, _, right = text.partition(":")
                return right.strip() or None
            return None
        return str(sibling).strip() or None

    for dom_label, key in (
        ("Emitter", "emitter"),
        ("Emisor", "emitter"),
        ("Diario Oficial", "diario_oficial"),
        ("Fecha Publicacion", "fecha_publicacion"),
        ("Fecha de Publicación", "fecha_publicacion"),
        ("Rama", "rama"),
        ("Materia", "materia"),
        ("Vigencia", "vigencia"),
    ):
        if key in meta and meta[key]:
            continue
        value = _row(dom_label)
        if value:
            meta[key] = value
    if "vigencia" in meta:
        meta["vigencia"] = _normalize_vigencia(meta["vigencia"])
    return meta


def _normalize_vigencia(raw: str) -> str:
    token = _normalize_token(raw)
    if "deroga" in token:
        return "derogada"
    if "suspend" in token:
        return "suspendida"
    if "vigente" in token:
        return "vigente"
    return "desconocida"


def _extract_article(
    anchor,
    *,
    strict_verbs: bool,
    verb_failures: list[dict[str, str]] | None = None,
) -> Optional[SuinArticle]:
    fragment_match = _FRAGMENT_ID_RE.match(anchor.get("name") or "")
    if fragment_match is None:
        return None
    fragment_id = fragment_match.group(1)

    container = _locate_article_container(anchor)
    if container is None:
        return None
    heading_text = container.get_text(" ", strip=True)
    heading_match = _ARTICLE_HEADING_RE.search(heading_text)
    raw_article_number = (
        heading_match.group("number").strip() if heading_match else fragment_id
    )
    # Normalize so accented / NBSP / casing variants collapse to one stable key.
    article_number = normalize_article_key(raw_article_number) or normalize_article_key(
        fragment_id
    )

    edges: list[SuinEdge] = []
    seen_ref_signatures: set[tuple[str | None, str | None, str]] = set()
    for ul in container.find_all("ul", recursive=True):
        container_kind = _container_kind_from_id(ul.get("id")) or _container_kind_from_class(
            ul.get("class")
        )
        if container_kind is None:
            continue
        # Find all `li.referencia` descendants (old DOM nested them directly;
        # new DOM wraps them in extra `<ul class="resumenvigencias"><li>…`
        # layers, so use a recursive descendant search filtered by class).
        for li in ul.find_all("li", class_="referencia", recursive=True):
            try:
                edge = _extract_edge(
                    li,
                    container_kind,
                    strict_verbs=strict_verbs,
                    verb_failures=verb_failures,
                )
            except UnknownVerb:
                raise
            if edge is None:
                continue
            signature = (
                edge.target_doc_id,
                edge.target_fragment_id,
                edge.raw_verb,
            )
            if signature in seen_ref_signatures:
                continue
            seen_ref_signatures.add(signature)
            edges.append(edge)

    body_html = str(container)
    body_text = container.get_text("\n", strip=True)
    return SuinArticle(
        article_number=article_number,
        article_fragment_id=fragment_id,
        heading=_first_heading_line(heading_text, article_number),
        body_html=body_html,
        body_text=body_text,
        outbound_edges=tuple(edges),
    )


def _locate_article_container(anchor) -> Optional[object]:
    for sibling in anchor.find_all_next():
        classes = sibling.get("class") or []
        if "articulo_normal" in classes or "articulo" in classes:
            return sibling
        # also accept <section> / <div> that contains a known article heading
        if sibling.name in {"section", "div"}:
            heading = sibling.find(string=_ARTICLE_HEADING_RE)
            if heading is not None:
                return sibling
        # don't cross the next article anchor
        if sibling.name == "a" and _FRAGMENT_ID_RE.match(sibling.get("name") or ""):
            break
    return None


def _container_kind_from_id(raw_id: str | None) -> str | None:
    if not raw_id:
        return None
    # Match longest prefix first so `NotasDestinoJurisp` wins over `NotasDestino`.
    for prefix, kind in sorted(_CONTAINER_KINDS.items(), key=lambda item: -len(item[0])):
        if raw_id.startswith(prefix):
            return kind
    return None


def _container_kind_from_class(raw_class: list[str] | None) -> str | None:
    """Post-2025 SUIN DOM uses `<ul class="resumenvigencias">` in place of the
    old `<ul id="NotasDestino*">` containers. The class alone doesn't split
    Destino vs Jurisp — we route every resumenvigencias ref through
    `NotasDestino` and let the verb (declara_exequible → jurisprudence,
    modifica/adiciona/… → legislative) drive downstream edge typing.
    """
    if not raw_class:
        return None
    classes = set(raw_class)
    if "resumenvigencias" in classes or "resumen-vigencias" in classes:
        return "NotasDestino"
    return None


def _extract_edge(
    li,
    container_kind: str,
    *,
    strict_verbs: bool,
    verb_failures: list[dict[str, str]] | None = None,
) -> Optional[SuinEdge]:
    span = li.find("span")
    if span is None:
        return None
    raw_verb_text = span.get_text(" ", strip=True)
    if not raw_verb_text:
        return None
    try:
        canonical = normalize_verb(raw_verb_text)
    except UnknownVerb as exc:
        if strict_verbs:
            raise
        if verb_failures is not None:
            verb_failures.append({"raw_verb": exc.raw, "hint": exc.hint or ""})
        return None

    # Scope — parenthetical inside the <li> but outside the <a>.
    after_span_text = _text_after(span).strip()
    scope_match = _SCOPE_PAREN_RE.search(after_span_text)
    scope = scope_match.group(1).strip() if scope_match else None

    anchor = li.find("a", href=True)
    target_doc_id: str | None = None
    target_fragment_id: str | None = None
    target_citation = ""
    if anchor is not None:
        href = anchor.get("href", "")
        target_doc_id, target_fragment_id = _parse_href(href)
        target_citation = anchor.get_text(" ", strip=True) or ""
    if not target_citation:
        target_citation = after_span_text

    return SuinEdge(
        verb=canonical,
        raw_verb=raw_verb_text,
        scope=scope,
        target_doc_id=target_doc_id,
        target_fragment_id=target_fragment_id,
        target_citation=target_citation,
        container_kind=container_kind,
    )


def _text_after(span) -> str:
    parts: list[str] = []
    for sibling in span.next_siblings:
        if getattr(sibling, "name", None) == "a":
            break
        if hasattr(sibling, "get_text"):
            parts.append(sibling.get_text(" ", strip=True))
        else:
            parts.append(str(sibling).strip())
    return " ".join(part for part in parts if part)


def _parse_href(href: str) -> tuple[str | None, str | None]:
    """Return (doc_id, fragment_id) from a SUIN `viewDocument.asp?id=...#ver_...` URL."""
    if not href:
        return None, None
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    doc_id = (qs.get("id") or [None])[0]
    fragment = parsed.fragment or ""
    frag_match = _FRAGMENT_ID_RE.match(fragment)
    fragment_id = frag_match.group(1) if frag_match else None
    return doc_id, fragment_id


def _first_heading_line(text: str, number: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line[:500]
    return f"Artículo {number}"


def parse_documents(
    items: Iterable[tuple[str, str, str]],
    *,
    strict_verbs: bool = True,
) -> Sequence[SuinDocument]:
    """Parse many documents. Each tuple is `(doc_id, ruta, html)`."""
    return tuple(
        parse_document(html, doc_id=doc_id, ruta=ruta, strict_verbs=strict_verbs)
        for doc_id, ruta, html in items
    )


__all__ = [
    "CANONICAL_VERBS",
    "SuinArticle",
    "SuinDocument",
    "SuinEdge",
    "UnknownVerb",
    "normalize_article_key",
    "normalize_doc_id",
    "normalize_verb",
    "parse_document",
    "parse_documents",
]
