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
import json
import logging
from pathlib import Path
from typing import Any

from ...graph.schema import EdgeKind, GraphEdgeRecord, NodeKind
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


__all__ = [
    "SuinScope",
    "build_classified_edges",
    "build_document_rows",
    "build_parsed_articles",
    "build_stub_articles",
    "build_stub_document_rows",
]
