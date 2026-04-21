"""SUIN → existing-pipeline bridge.

Converts the `documents.jsonl` + `articles.jsonl` + `edges.jsonl` a harvest
produced into the `ParsedArticle` / `ClassifiedEdge` / `CorpusDocument`-shaped
rows the Supabase sink and Falkor loader already know how to persist.

Keeping the conversion here (rather than bolting SUIN awareness into the
generic parser) means the existing classifier stays pure — SUIN-derived edges
carry `confidence=1.0` because they come from DOM, not NLP.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

from ...graph.schema import EdgeKind, GraphEdgeRecord, NodeKind
from ...instrumentation import emit_event as _emit_event
from ..classifier import ClassifiedEdge
from ..parser import ParsedArticle
from .parser import CANONICAL_VERBS, normalize_article_key, normalize_doc_id

_log = logging.getLogger(__name__)


# SUIN canonical verb -> internal EdgeKind. `nota_editorial` is intentionally
# absent — those do not produce edges, they are document-level annotations.
_VERB_TO_KIND: dict[str, EdgeKind] = {
    "modifica": EdgeKind.MODIFIES,
    "adiciona": EdgeKind.MODIFIES,
    "deroga": EdgeKind.DEROGATES,
    "reglamenta": EdgeKind.REGLAMENTA,
    "suspende": EdgeKind.SUSPENDS,
    "anula": EdgeKind.ANULA,
    "declara_exequible": EdgeKind.DECLARES_EXEQUIBLE,
    "declara_inexequible": EdgeKind.STRUCK_DOWN_BY,
    "inhibida": EdgeKind.REFERENCES,
    "estarse_a_lo_resuelto": EdgeKind.REFERENCES,
}


@dataclass(frozen=True)
class SuinScope:
    """Parsed view of a SUIN harvest scope directory."""

    root: Path
    documents: tuple[dict[str, Any], ...]
    articles: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, Any], ...]
    manifest: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path | str) -> "SuinScope":
        root = Path(root)
        if not root.exists():
            raise FileNotFoundError(f"SUIN scope directory not found: {root}")
        return cls(
            root=root,
            documents=tuple(_iter_jsonl(root / "documents.jsonl")),
            articles=tuple(_iter_jsonl(root / "articles.jsonl")),
            edges=tuple(_iter_jsonl(root / "edges.jsonl")),
            manifest=_read_json_or_empty(root / "_harvest_manifest.json"),
        )


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _doc_id_for_source_path(doc_id_raw: str) -> tuple[str, str, str]:
    """Return `(source_path, relative_path, doc_id_hint)` consistent with the sink.

    We use the `suin://` scheme for source_path so it never collides with
    filesystem corpus documents and so the downstream sanitizer produces a
    stable `doc_id`. The sanitizer folds `/` to `_`, which is fine.
    """
    safe = normalize_doc_id(doc_id_raw) or "unknown"
    source_path = f"suin://{safe}"
    relative_path = f"suin/{safe}"
    return source_path, relative_path, safe


def build_parsed_articles(scope: SuinScope) -> tuple[ParsedArticle, ...]:
    """Convert `articles.jsonl` rows into `ParsedArticle` tuples.

    `article_key` is the normalized article number (stable ASCII, Spanish-safe).
    `status` comes from the document's vigencia field directly — no regex sniffing.
    """
    vigencia_by_doc: dict[str, str] = {
        str(row.get("doc_id") or ""): str(row.get("vigencia") or "desconocida")
        for row in scope.documents
    }
    out: list[ParsedArticle] = []
    for row in scope.articles:
        doc_id_raw = str(row.get("doc_id") or "")
        if not doc_id_raw:
            continue
        source_path, _rel, _safe = _doc_id_for_source_path(doc_id_raw)
        article_number = str(row.get("article_number") or "").strip()
        article_key = normalize_article_key(article_number) or normalize_article_key(
            str(row.get("article_fragment_id") or "")
        )
        if not article_key:
            continue
        heading = str(row.get("heading") or "") or f"Artículo {article_number}"
        body = str(row.get("body_text") or "")
        full_text = f"{heading}\n{body}".strip() if body else heading
        vigencia = vigencia_by_doc.get(doc_id_raw, "desconocida")
        status = "derogado" if vigencia == "derogada" else "vigente"
        out.append(
            ParsedArticle(
                article_key=article_key,
                article_number=article_number or article_key,
                heading=heading,
                body=body,
                full_text=full_text,
                status=status,
                source_path=source_path,
                paragraph_markers=(),
                reform_references=(),
                annotations=(),
            )
        )
    return tuple(out)


def build_classified_edges(scope: SuinScope) -> tuple[ClassifiedEdge, ...]:
    """Convert SUIN edges into `ClassifiedEdge` tuples. `nota_editorial` skipped.

    Confidence is 1.0 because the verb + target come straight from SUIN DOM —
    not from a heuristic classifier. The `rule` marks the provenance so
    downstream audits can distinguish SUIN DOM edges from NLP-classifier ones.
    """
    out: list[ClassifiedEdge] = []
    dropped = 0
    unresolved_target = 0
    for row in scope.edges:
        verb = str(row.get("verb") or "").strip()
        if verb not in CANONICAL_VERBS:
            dropped += 1
            continue
        kind = _VERB_TO_KIND.get(verb)
        if kind is None:
            # nota_editorial (or any future annotation-only verb) — skip.
            dropped += 1
            continue
        source_doc_id = str(row.get("source_doc_id") or "")
        target_doc_id = str(row.get("target_doc_id") or "")
        source_article_key = normalize_article_key(
            str(row.get("source_article_key") or "")
        )
        if not source_article_key or not source_doc_id:
            unresolved_target += 1
            continue
        target_article_key = normalize_article_key(
            str(row.get("target_article_key") or row.get("target_fragment_id") or "")
        )
        # Target is another SUIN document. Without a target article key we
        # still emit an edge at the document level by keying on the target
        # doc so graph traversal can find "things that modified this doc".
        target_kind = NodeKind.ARTICLE if target_article_key else NodeKind.REFORM
        target_key = target_article_key or _doc_reform_key(target_doc_id)
        if not target_key:
            unresolved_target += 1
            continue
        raw_citation = str(row.get("target_citation") or "")
        scope_text = str(row.get("scope") or "") if row.get("scope") else ""
        out.append(
            ClassifiedEdge(
                record=GraphEdgeRecord(
                    kind=kind,
                    source_kind=NodeKind.ARTICLE,
                    source_key=source_article_key,
                    target_kind=target_kind,
                    target_key=target_key,
                    properties={
                        "raw_reference": raw_citation or verb,
                        "context": f"SUIN:{verb}:{raw_citation}",
                        "relation_hint": kind.value,
                        "classifier_rule": "suin_dom_extraction",
                        "suin_verb": verb,
                        "suin_raw_verb": str(row.get("raw_verb") or ""),
                        "suin_container_kind": str(row.get("container_kind") or ""),
                        "suin_scope": scope_text,
                        "suin_source_doc_id": source_doc_id,
                        "suin_target_doc_id": target_doc_id,
                    },
                ),
                confidence=1.0,
                rule="suin_dom_extraction",
            )
        )
    if dropped or unresolved_target:
        _log.info(
            "SUIN bridge dropped=%d unresolved_target=%d total_in=%d",
            dropped,
            unresolved_target,
            len(scope.edges),
        )
    return tuple(out)


def _doc_reform_key(doc_id: str) -> str:
    safe = normalize_doc_id(doc_id)
    if not safe:
        return ""
    # Reform-style key so `_normalize_reform_key` / the graph loader treats it
    # as a REFORM node target.
    return f"SUIN-{safe}"


def build_document_rows(scope: SuinScope) -> list[dict[str, Any]]:
    """Build dicts matching the shape `SupabaseCorpusSink.write_documents` expects."""
    out: list[dict[str, Any]] = []
    for row in scope.documents:
        doc_id_raw = str(row.get("doc_id") or "")
        if not doc_id_raw:
            continue
        source_path, relative_path, _safe = _doc_id_for_source_path(doc_id_raw)
        emitter = str(row.get("emitter") or "").strip()
        ruta = str(row.get("ruta") or "").strip()
        rama = str(row.get("rama") or "").strip()
        materia = str(row.get("materia") or "").strip()
        archetype = _archetype_from_ruta(ruta)
        knowledge_class = (
            "jurisprudence" if archetype in {"sentencia", "auto"} else "normative_base"
        )
        out.append(
            {
                "source_path": source_path,
                "relative_path": relative_path,
                "title_hint": str(row.get("title") or relative_path),
                "markdown": "",  # body lives on chunks; doc-level has metadata only
                "family": "normativa",
                "knowledge_class": knowledge_class,
                "source_type": "suin_norma",
                "source_tier": "official_compilation",
                "authority_level": _authority_from_emitter(emitter),
                "topic_key": materia or "unknown",
                "subtopic_key": rama or None,
                "document_archetype": archetype,
                "pais": "colombia",
            }
        )
    return out


def build_stub_document_rows(
    unresolved_doc_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Minimal documents for targets SUIN edges point to but we didn't harvest.

    Satisfies Phase B gap #2: the Supabase FK integrity and the graph
    "skip unresolved edge" filter both need target rows. We mark them
    `curation_status="stub"` implicitly by using `source_type="suin_stub"` so
    operators can query / backfill later.
    """
    rows: list[dict[str, Any]] = []
    for doc_id in unresolved_doc_ids:
        if not doc_id:
            continue
        source_path, relative_path, _safe = _doc_id_for_source_path(doc_id)
        rows.append(
            {
                "source_path": source_path,
                "relative_path": relative_path,
                "title_hint": f"SUIN stub {doc_id}",
                "markdown": "",
                "family": "normativa",
                "knowledge_class": "normative_base",
                "source_type": "suin_stub",
                "source_tier": "official_compilation",
                "authority_level": "unknown",
                "topic_key": "unknown",
                "subtopic_key": None,
                "document_archetype": "stub",
                "pais": "colombia",
            }
        )
    return rows


def build_stub_articles(
    scope: SuinScope,
    *,
    resolved_article_keys: set[str],
) -> tuple[ParsedArticle, tuple[str, ...]]:
    """Two-pass merge helper (docs/next/ingestion_suin.md Phase B step #13).

    Returns `(stub_articles, unresolved_doc_ids)`:

    - `stub_articles` — one `ParsedArticle(status="stub")` per SUIN edge whose
      target article key is known but not already in the resolved set.
    - `unresolved_doc_ids` — doc_ids for targets SUIN references but never
      materialized as articles or documents. Pass these to
      `build_stub_document_rows` so FK integrity holds.

    Both outputs are required inputs to the second pass; without them the
    loader's "skip unresolved ArticleNode edge" filter would silently discard
    most of the SUIN signal (Phase B gap #2).
    """
    known_doc_ids = {str(d.get("doc_id") or "") for d in scope.documents if d.get("doc_id")}
    stub_articles: dict[str, ParsedArticle] = {}
    unresolved_docs: set[str] = set()
    for row in scope.edges:
        verb = str(row.get("verb") or "").strip()
        if verb not in _VERB_TO_KIND:
            continue
        target_article_key = normalize_article_key(
            str(row.get("target_article_key") or row.get("target_fragment_id") or "")
        )
        target_doc_id = str(row.get("target_doc_id") or "")
        # Only stub target docs we did NOT actually harvest. Otherwise the real
        # document row from `build_document_rows` already covers FK integrity.
        if target_doc_id and target_doc_id not in known_doc_ids:
            unresolved_docs.add(target_doc_id)
        if not target_article_key or target_article_key in resolved_article_keys:
            continue
        if target_article_key in stub_articles:
            continue
        # The stub lives on the target doc, not the source doc — edges point at it.
        source_path, _rel, _safe = _doc_id_for_source_path(target_doc_id or "stub")
        stub_articles[target_article_key] = ParsedArticle(
            article_key=target_article_key,
            article_number=target_article_key,
            heading=f"Stub SUIN artículo {target_article_key}",
            body="",
            full_text=f"Stub SUIN artículo {target_article_key}",
            status="stub",
            source_path=source_path,
        )
    return tuple(stub_articles.values()), tuple(sorted(unresolved_docs))


def _archetype_from_ruta(ruta: str) -> str:
    lower = (ruta or "").lower()
    for marker, archetype in (
        # Jurisprudence — match before "sentencia" generic so the right archetype wins.
        ("consejoestado", "sentencia"),
        ("consejo_estado", "sentencia"),
        ("corteconstitucional", "sentencia"),
        ("corte_constitucional", "sentencia"),
        ("cortesuprema", "sentencia"),
        ("sentencia", "sentencia"),
        # Normativa archetypes
        ("leyes", "ley"),
        ("decretos", "decreto"),
        ("resoluciones", "resolucion"),
        ("circulares", "circular"),
        ("acuerdos", "acuerdo"),
        ("instrucciones", "instruccion"),
    ):
        if marker in lower:
            return archetype
    return "normativa"


def _authority_from_emitter(emitter: str) -> str:
    lower = (emitter or "").lower()
    if "congreso" in lower:
        return "congreso"
    if "presidencia" in lower or "presidente" in lower:
        return "presidencia"
    if "corte constitucional" in lower:
        return "corte_constitucional"
    if "consejo de estado" in lower:
        return "consejo_estado"
    if "dian" in lower:
        return "dian"
    if "minhacienda" in lower or "ministerio de hacienda" in lower:
        return "minhacienda"
    return emitter.strip().lower() or "unknown"


# ---------------------------------------------------------------------------
# Canonical 8-section markdown synthesis (Phase 5b of ingestfixv1)
# ---------------------------------------------------------------------------
#
# `synthesize_canonical_markdown` renders a SUIN document row + its filtered
# articles/edges into the canonical 8-section legal-doc template plus the
# top-of-document `## Metadata v2` block used by the rest of the ingestion
# pipeline. SUIN is a raw scrape source: operational rule sections
# (`Regla operativa para LIA`, `Condiciones de aplicacion`,
# `Riesgos de interpretacion`) are intentionally left as placeholders because
# those fields are curator responsibility, not scraper responsibility.
#
# Field-mapping notes:
# - The SUIN document row uses `title` / `emitter` / `number` as written by
#   the harvester. We accept the Spanish alias `titulo` / `autoridad` /
#   `numero` as fallbacks so curated rows from alternate feeds still map
#   cleanly without requiring a second loader.
# - Issuance/effective dates: the harvester writes `date_issued` /
#   `date_effective` (and historically `fecha_publicacion` / `fecha_emision`
#   / `fecha_vigencia`). We probe all variants and pick the first populated
#   value per canonical key.
# - `topic` accepts a single string or a list — both are joined into the
#   `vocabulary_labels` metadata-v2 bullet.

_SUIN_BRIDGE_COERCION_METHOD = "suin_bridge"
_SUIN_CANONICAL_SECTIONS: tuple[str, ...] = (
    "Identificacion",
    "Texto base referenciado (resumen tecnico)",
    "Regla operativa para LIA",
    "Condiciones de aplicacion",
    "Riesgos de interpretacion",
    "Relaciones normativas",
    "Checklist de vigencia",
    "Historico de cambios",
)
_SUIN_IDENTIFICATION_KEYS: tuple[str, ...] = (
    "titulo",
    "autoridad",
    "numero",
    "fecha_emision",
    "fecha_vigencia",
    "ambito_tema",
    "doc_id",
)
_SUIN_METADATA_V2_KEYS: tuple[str, ...] = (
    "version_canonical_template",
    "coercion_method",
    "coercion_confidence",
    "source_tier",
    "authority_level",
    "parse_strategy",
    "source_type",
    "corpus_family",
    "vocabulary_labels",
    "review_priority",
    "country_scope",
    "language",
    "generated_at",
    "source_relative_path",
)
_SUIN_PLACEHOLDER = "(sin datos)"
_SUIN_CURATOR_PLACEHOLDER = "(sin datos — fuente SUIN)"
# Edges that carry vigencia signal (listed separately in the checklist).
_SUIN_VIGENCIA_VERBS: tuple[str, ...] = (
    "suspende",
    "deroga",
    "anula",
    "declara_inexequible",
)


def _suin_first_populated(row: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty string value among ``keys`` in ``row``."""
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _suin_topic_list(row: dict[str, Any]) -> list[str]:
    """Extract topic labels as a list; accept str or list."""
    raw = row.get("topic")
    if raw is None:
        raw = row.get("topics") or row.get("materia") or row.get("rama")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).strip()
    return [text] if text else []


def _suin_verb_label(verb: str) -> str:
    """Human-readable label for a SUIN canonical verb used in section text."""
    mapping = {
        "modifica": "Modifica",
        "adiciona": "Adiciona",
        "deroga": "Deroga",
        "reglamenta": "Reglamenta",
        "suspende": "Suspende",
        "anula": "Anula",
        "declara_exequible": "Declara exequible",
        "declara_inexequible": "Declara inexequible",
        "inhibida": "Inhibida",
        "estarse_a_lo_resuelto": "Estarse a lo resuelto",
    }
    if verb in mapping:
        return mapping[verb]
    # Fall back to human-friendly form: underscores -> spaces, capitalized.
    friendly = verb.replace("_", " ").strip()
    return friendly[:1].upper() + friendly[1:] if friendly else verb


def _suin_edge_target_key(edge: dict[str, Any]) -> str:
    """Best-effort rendering of the target side of a SUIN edge for text display."""
    citation = str(edge.get("target_citation") or "").strip()
    if citation:
        return citation
    doc_id = str(edge.get("target_doc_id") or "").strip()
    article_key = str(
        edge.get("target_article_key") or edge.get("target_fragment_id") or ""
    ).strip()
    if doc_id and article_key:
        return f"{doc_id} art. {article_key}"
    return doc_id or article_key or _SUIN_PLACEHOLDER


def _suin_edge_sort_key(edge: dict[str, Any]) -> str:
    """Stable chronological key for historical ordering of edges.

    SUIN edges don't always carry a date, so we pile on several candidate
    fields and fall back to empty string (which sorts first).
    """
    return _suin_first_populated(
        edge,
        "date",
        "fecha",
        "fecha_modificacion",
        "date_modified",
        "date_issued",
    )


def _suin_format_bullets(pairs: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in pairs)


def _suin_build_identificacion(document_row: dict[str, Any]) -> str:
    titulo = _suin_first_populated(document_row, "title", "titulo")
    autoridad_raw = _suin_first_populated(document_row, "authority", "autoridad", "emitter")
    autoridad = _authority_from_emitter(autoridad_raw) if autoridad_raw else ""
    numero = _suin_first_populated(document_row, "number", "numero")
    fecha_emision = _suin_first_populated(
        document_row,
        "date_issued",
        "fecha_emision",
        "fecha_publicacion",
    )
    fecha_vigencia = _suin_first_populated(
        document_row,
        "date_effective",
        "fecha_vigencia",
        "fecha_efectiva",
    )
    topics = _suin_topic_list(document_row)
    ambito_tema = ", ".join(topics) if topics else ""
    doc_id = _suin_first_populated(document_row, "doc_id", "id")

    values = {
        "titulo": titulo,
        "autoridad": autoridad,
        "numero": numero,
        "fecha_emision": fecha_emision,
        "fecha_vigencia": fecha_vigencia,
        "ambito_tema": ambito_tema,
        "doc_id": doc_id,
    }
    pairs = [
        (key, values[key] if values[key] else _SUIN_PLACEHOLDER)
        for key in _SUIN_IDENTIFICATION_KEYS
    ]
    return _suin_format_bullets(pairs)


def _suin_build_texto_base(articles_for_doc: Sequence[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for art in articles_for_doc:
        heading = str(art.get("heading") or "").strip()
        body = str(art.get("body_text") or art.get("body") or "").strip()
        if heading and body:
            blocks.append(f"{heading}\n{body}")
        elif heading:
            blocks.append(heading)
        elif body:
            blocks.append(body)
    if not blocks:
        return _SUIN_PLACEHOLDER
    return "\n\n".join(blocks)


def _suin_build_relaciones(edges_for_doc: Sequence[dict[str, Any]]) -> str:
    # Group edges by verb (skipping nota_editorial + non-canonical verbs).
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edges_for_doc:
        verb = str(edge.get("verb") or "").strip()
        if verb == "nota_editorial":
            continue
        if verb not in CANONICAL_VERBS:
            continue
        grouped.setdefault(verb, []).append(edge)
    if not grouped:
        return _SUIN_PLACEHOLDER
    # Order verbs by canonical verb ordering for stable output.
    lines: list[str] = []
    for verb in CANONICAL_VERBS:
        if verb == "nota_editorial":
            continue
        if verb not in grouped:
            continue
        label = _suin_verb_label(verb)
        for edge in grouped[verb]:
            target = _suin_edge_target_key(edge)
            lines.append(f"- {label} → {target}")
    return "\n".join(lines) if lines else _SUIN_PLACEHOLDER


def _suin_build_vigencia_checklist(
    document_row: dict[str, Any],
    edges_for_doc: Sequence[dict[str, Any]],
) -> str:
    vigencia = _suin_first_populated(document_row, "vigencia", "status").lower()
    # Map SUIN vigencia -> canonical checklist term.
    if vigencia.startswith("derog"):
        vigencia_display = "derogado"
    elif vigencia.startswith("susp"):
        vigencia_display = "suspendido"
    elif vigencia.startswith("vig"):
        vigencia_display = "vigente"
    elif vigencia:
        vigencia_display = vigencia
    else:
        vigencia_display = _SUIN_PLACEHOLDER
    lines: list[str] = [f"- vigencia: {vigencia_display}"]
    for edge in edges_for_doc:
        verb = str(edge.get("verb") or "").strip()
        if verb not in _SUIN_VIGENCIA_VERBS:
            continue
        label = _suin_verb_label(verb)
        target = _suin_edge_target_key(edge)
        lines.append(f"- {label} ← {target}")
    return "\n".join(lines)


def _suin_build_historico(
    document_row: dict[str, Any],
    edges_for_doc: Sequence[dict[str, Any]],
) -> str:
    entries: list[tuple[str, str]] = []
    fecha_emision = _suin_first_populated(
        document_row,
        "date_issued",
        "fecha_emision",
        "fecha_publicacion",
    )
    titulo = _suin_first_populated(document_row, "title", "titulo")
    if fecha_emision or titulo:
        entries.append(
            (
                fecha_emision or "",
                f"{fecha_emision or _SUIN_PLACEHOLDER} → {titulo or _SUIN_PLACEHOLDER}",
            )
        )
    mod_verbs = {"modifica", "adiciona", "deroga", "suspende", "anula"}
    mod_edges = [
        edge
        for edge in edges_for_doc
        if str(edge.get("verb") or "").strip() in mod_verbs
    ]
    mod_edges.sort(key=_suin_edge_sort_key)
    for edge in mod_edges:
        verb = str(edge.get("verb") or "").strip()
        label = _suin_verb_label(verb)
        target = _suin_edge_target_key(edge)
        date = _suin_edge_sort_key(edge)
        line = f"{date or _SUIN_PLACEHOLDER} → {label}: {target}"
        entries.append((date or "", line))
    if not entries:
        return _SUIN_PLACEHOLDER
    # Sort by date key (empty strings go first, which is fine — they
    # correspond to the doc's own emission row + undated edges).
    entries.sort(key=lambda pair: pair[0])
    return "\n".join(f"- {line}" for _key, line in entries)


def _suin_build_metadata_v2(
    document_row: dict[str, Any],
    coercion_method: str,
    coercion_confidence: float,
) -> str:
    topics = _suin_topic_list(document_row)
    authority_raw = _suin_first_populated(document_row, "authority", "autoridad", "emitter")
    authority_level = _authority_from_emitter(authority_raw) if authority_raw else ""
    doc_id = _suin_first_populated(document_row, "doc_id", "id")
    values = {
        "version_canonical_template": "1",
        "coercion_method": coercion_method,
        "coercion_confidence": f"{coercion_confidence:.2f}",
        "source_tier": "suin_harvest",
        "authority_level": authority_level or "primary_legal_authority",
        "parse_strategy": "suin_dom",
        "source_type": "scraped_legal_document",
        "corpus_family": "normativa",
        "vocabulary_labels": ", ".join(topics),
        "review_priority": "none",
        "country_scope": "colombia",
        "language": "es",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_relative_path": doc_id,
    }
    pairs = [(k, values.get(k, "")) for k in _SUIN_METADATA_V2_KEYS]
    body = _suin_format_bullets(pairs)
    return f"## Metadata v2\n{body}"


def synthesize_canonical_markdown(
    document_row: dict[str, Any],
    articles_for_doc: Sequence[dict[str, Any]],
    edges_for_doc: Sequence[dict[str, Any]],
    *,
    emit_events: bool = False,
) -> str:
    """Render one SUIN document row into the canonical 8-section template.

    The renderer consumes already-filtered inputs — callers are expected to
    filter ``articles.jsonl`` / ``edges.jsonl`` to the rows matching
    ``document_row["doc_id"]`` before invoking this function.

    The emitted markdown always contains:

    - a top-of-document ``## Metadata v2`` block with all 14 canonical keys;
    - the 8 canonical H2 headings in their canonical order;
    - ``(sin datos)`` or ``(sin datos — fuente SUIN)`` placeholders where
      SUIN does not carry the field (operational rules are curator work).

    When ``emit_events=True`` the function writes
    ``ingest.suin.bridge.start`` / ``ingest.suin.bridge.done`` events via
    :func:`lia_graph.instrumentation.emit_event`.
    """

    doc_id = _suin_first_populated(document_row, "doc_id", "id")

    if emit_events:
        _emit_event(
            "ingest.suin.bridge.start",
            {
                "suin_doc_id": doc_id,
                "article_count": len(articles_for_doc),
                "edge_count": len(edges_for_doc),
            },
        )

    identificacion_body = _suin_build_identificacion(document_row)
    texto_base_body = _suin_build_texto_base(articles_for_doc)
    relaciones_body = _suin_build_relaciones(edges_for_doc)
    vigencia_body = _suin_build_vigencia_checklist(document_row, edges_for_doc)
    historico_body = _suin_build_historico(document_row, edges_for_doc)

    section_bodies: dict[str, str] = {
        "Identificacion": identificacion_body,
        "Texto base referenciado (resumen tecnico)": texto_base_body,
        "Regla operativa para LIA": _SUIN_CURATOR_PLACEHOLDER,
        "Condiciones de aplicacion": _SUIN_CURATOR_PLACEHOLDER,
        "Riesgos de interpretacion": _SUIN_CURATOR_PLACEHOLDER,
        "Relaciones normativas": relaciones_body,
        "Checklist de vigencia": vigencia_body,
        "Historico de cambios": historico_body,
    }

    coercion_method = _SUIN_BRIDGE_COERCION_METHOD
    coercion_confidence = 1.0

    # Optional verification pass: run the Phase 1.5 coercer with skip_llm=True.
    # The coercer's `coercion_method` becomes authoritative when it fires.
    try:  # pragma: no cover - defensive / nicety pass
        from ...ingestion_section_coercer import coerce_to_canonical_template

        initial_markdown = _suin_assemble(
            section_bodies,
            metadata_block=_suin_build_metadata_v2(
                document_row,
                coercion_method=_SUIN_BRIDGE_COERCION_METHOD,
                coercion_confidence=1.0,
            ),
        )
        coerce_result = coerce_to_canonical_template(
            initial_markdown,
            skip_llm=True,
            filename=doc_id or None,
        )
        if coerce_result.sections_matched_count == 8:
            coercion_method = coerce_result.coercion_method
            coercion_confidence = coerce_result.confidence
    except Exception:
        # If the coercer isn't importable or trips, we still emit a valid doc.
        pass

    metadata_block = _suin_build_metadata_v2(
        document_row,
        coercion_method=coercion_method,
        coercion_confidence=coercion_confidence,
    )
    markdown_out = _suin_assemble(section_bodies, metadata_block=metadata_block)

    if emit_events:
        _emit_event(
            "ingest.suin.bridge.done",
            {
                "suin_doc_id": doc_id,
                "section_count": len(_SUIN_CANONICAL_SECTIONS),
                "coercion_method": coercion_method,
            },
        )

    return markdown_out


def _suin_assemble(
    section_bodies: dict[str, str],
    *,
    metadata_block: str,
) -> str:
    blocks: list[str] = [metadata_block]
    for name in _SUIN_CANONICAL_SECTIONS:
        body = section_bodies.get(name, "") or _SUIN_PLACEHOLDER
        blocks.append(f"## {name}\n{body}")
    return "\n\n".join(blocks).rstrip() + "\n"


__all__ = [
    "SuinScope",
    "build_classified_edges",
    "build_document_rows",
    "build_parsed_articles",
    "build_stub_articles",
    "build_stub_document_rows",
    "synthesize_canonical_markdown",
]
