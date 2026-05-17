"""Typed schema scaffolds for the shared regulatory graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

DEFAULT_GRAPH_NAME = "LIA_REGULATORY_GRAPH"


class NodeKind(str, Enum):
    ARTICLE = "ArticleNode"
    REFORM = "ReformNode"
    CONCEPT = "ConceptNode"
    PARAMETER = "ParameterNode"
    # ingestfix-v2 Phase 5: curated subtopic anchor.
    SUBTOPIC = "SubTopicNode"
    # ingestionfix_v2 §4 Phase 5: curated topic anchor.
    TOPIC = "TopicNode"
    # fixplan_v3 §0.3.2 — first-class norm node, mirrors `norms` catalog.
    NORM = "Norm"
    # fix_v10_may Phase 10C §3.C — expert-commentary anchor. Mirrors the
    # `documents.knowledge_class='interpretative_guidance'` rows in
    # Supabase; one InterpretationNode per expert brief (Crowe, EY,
    # KPMG, …). Linked to ArticleNode via INTERPRETS and to TopicNode
    # via COVERS_TOPIC. Provider/authority strings live as properties;
    # promoting them to dedicated ExpertProviderNodes + AUTHORED_BY
    # edges is deferred to v10.1 per §9.4.
    INTERPRETATION = "InterpretationNode"


class EdgeKind(str, Enum):
    REFERENCES = "REFERENCES"
    MODIFIES = "MODIFIES"
    SUPERSEDES = "SUPERSEDES"
    EXCEPTION_TO = "EXCEPTION_TO"
    COMPUTATION_DEPENDS_ON = "COMPUTATION_DEPENDS_ON"
    REQUIRES = "REQUIRES"
    DEFINES = "DEFINES"
    PART_OF = "PART_OF"
    # SUIN-derived kinds. See docs/next/ingestion_suin.md Phase B mapping table.
    # Alphabetized inside this block so new additions land deterministically.
    ANULA = "ANULA"
    DECLARES_EXEQUIBLE = "DECLARES_EXEQUIBLE"
    DEROGATES = "DEROGATES"
    REGLAMENTA = "REGLAMENTA"
    STRUCK_DOWN_BY = "STRUCK_DOWN_BY"
    SUSPENDS = "SUSPENDS"
    # ingestfix-v2 Phase 5: doc → curated subtopic link.
    HAS_SUBTOPIC = "HAS_SUBTOPIC"
    # ingestionfix_v2 §4 Phase 5: thematic edges.
    TEMA = "TEMA"                    # Article/Reform → Topic
    SUBTEMA_DE = "SUBTEMA_DE"        # SubTopic → Topic (static taxonomy)
    # fixplan_v3 §0.3.2 — directional pairs for norm-keyed vigencia mirror.
    # The `(:Norm)` node is added as a separate kind below; these edges
    # connect a `(:Norm)` to its source artifact `(:Norm)`.
    MODIFIED_BY = "MODIFIED_BY"
    DEROGATED_BY = "DEROGATED_BY"
    SUSPENDED_BY = "SUSPENDED_BY"
    INEXEQUIBLE_BY = "INEXEQUIBLE_BY"
    CONDITIONALLY_EXEQUIBLE_BY = "CONDITIONALLY_EXEQUIBLE_BY"
    MODULATED_BY = "MODULATED_BY"
    REVIVED_BY = "REVIVED_BY"
    CITES = "CITES"
    IS_SUB_UNIT_OF = "IS_SUB_UNIT_OF"
    # fix_v10_may Phase 10C §3.C — interpretation-anchor edges. INTERPRETS
    # connects an InterpretationNode to every ArticleNode it analyzes
    # (many-to-many; capped per node in the planner query). COVERS_TOPIC
    # connects an InterpretationNode to its primary TopicNode for the
    # topic-only fan-out path. AUTHORED_BY → ExpertProviderNode is
    # deferred to v10.1 per §9.4.
    INTERPRETS = "INTERPRETS"
    COVERS_TOPIC = "COVERS_TOPIC"


@dataclass(frozen=True)
class GraphNodeType:
    label: NodeKind
    key_field: str
    description: str
    required_fields: tuple[str, ...] = ()
    # v4: Properties that are declared-but-optional. Consumers reading them
    # from Cypher must tolerate NULL. The retriever-contract tests validate
    # every Cypher-bound property against `required_fields ∪ optional_fields
    # ∪ {key_field}`, so any new property used by retrieval must be declared
    # here (or in required_fields) before landing.
    optional_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphEdgeType:
    label: EdgeKind
    source_kinds: tuple[NodeKind, ...]
    target_kinds: tuple[NodeKind, ...]
    description: str


@dataclass(frozen=True)
class GraphNodeRecord:
    kind: NodeKind
    key: str
    properties: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "key": self.key,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class GraphEdgeRecord:
    kind: EdgeKind
    source_kind: NodeKind
    source_key: str
    target_kind: NodeKind
    target_key: str
    properties: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "source_kind": self.source_kind.value,
            "source_key": self.source_key,
            "target_kind": self.target_kind.value,
            "target_key": self.target_key,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class GraphSchema:
    graph_name: str
    node_types: Mapping[NodeKind, GraphNodeType]
    edge_types: Mapping[EdgeKind, GraphEdgeType]

    def node_type(self, kind: NodeKind) -> GraphNodeType:
        return self.node_types[kind]

    def edge_type(self, kind: EdgeKind) -> GraphEdgeType:
        return self.edge_types[kind]

    def validate_node_record(self, record: GraphNodeRecord) -> None:
        if not record.key.strip():
            raise ValueError("Graph node keys must be non-empty.")
        node_type = self.node_type(record.kind)
        missing = [
            field_name
            for field_name in node_type.required_fields
            if record.properties.get(field_name) in (None, "", ())
        ]
        if missing:
            raise ValueError(
                f"Node {record.kind.value}:{record.key} missing required fields: {missing}"
            )

    def validate_edge_record(self, record: GraphEdgeRecord) -> None:
        if not record.source_key.strip() or not record.target_key.strip():
            raise ValueError("Graph edge endpoints must be non-empty.")
        edge_type = self.edge_type(record.kind)
        if record.source_kind not in edge_type.source_kinds:
            raise ValueError(
                f"{record.kind.value} cannot start from {record.source_kind.value}"
            )
        if record.target_kind not in edge_type.target_kinds:
            raise ValueError(
                f"{record.kind.value} cannot target {record.target_kind.value}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "graph_name": self.graph_name,
            "node_types": {
                kind.value: {
                    "key_field": node_type.key_field,
                    "description": node_type.description,
                    "required_fields": list(node_type.required_fields),
                }
                for kind, node_type in self.node_types.items()
            },
            "edge_types": {
                kind.value: {
                    "source_kinds": [source_kind.value for source_kind in edge_type.source_kinds],
                    "target_kinds": [target_kind.value for target_kind in edge_type.target_kinds],
                    "description": edge_type.description,
                }
                for kind, edge_type in self.edge_types.items()
            },
        }


def default_graph_schema() -> GraphSchema:
    node_types = {
        NodeKind.ARTICLE: GraphNodeType(
            label=NodeKind.ARTICLE,
            key_field="article_id",
            description="Versionable normative unit from the shared regulatory corpus.",
            # v4: `article_number` moved from required_fields → optional_fields
            # so prose-only docs (whole-doc-fallback parser output with empty
            # article_number) can be materialized as ArticleNodes. The loader
            # emits an `is_prose_only` property so consumers can filter cleanly.
            # See docs/next/ingestionfix_v4.md §2.
            required_fields=("heading", "text_current", "status"),
            optional_fields=(
                "article_number",
                "is_prose_only",
                "source_path",
                "paragraph_markers",
                "reform_references",
                "annotations",
                # v5 §1.A — secondary topics this article serves under, in
                # addition to its canonical owner topic. Populated from
                # `config/article_secondary_topics.json` at ingest time.
                # Consumed by `topic_safety.detect_topic_misalignment` so the
                # coherence-gate accepts queries routed to either the canonical
                # owner topic OR any of these secondary topics.
                "secondary_topics",
                # v19 Fase 3 — canonical norm_id (e.g. `cst.art.64`,
                # `et.art.420`, `ley.50.1990.art.64`). Derived from
                # `(source_path, article_number)` via `norm_id_rules.derive_norm_id`.
                # Null on prose-only nodes (whole-doc-fallback), SUIN nodes (v6
                # canonical via `:Norm`), and the small OTHER bucket pending
                # path rules. Unique index in cloud Falkor; safe to query with
                # `MATCH (a:ArticleNode {norm_id: ...})`.
                "norm_id",
            ),
        ),
        NodeKind.REFORM: GraphNodeType(
            label=NodeKind.REFORM,
            key_field="reform_id",
            description="Normative act that changes or contextualizes article text.",
            required_fields=("citation",),
        ),
        NodeKind.CONCEPT: GraphNodeType(
            label=NodeKind.CONCEPT,
            key_field="concept_id",
            description="Canonical tax concept anchor used by graph traversal.",
            required_fields=("name",),
        ),
        NodeKind.PARAMETER: GraphNodeType(
            label=NodeKind.PARAMETER,
            key_field="parameter_id",
            description="Versioned fiscal or accounting parameters such as UVT values.",
            required_fields=("name", "value"),
        ),
        NodeKind.SUBTOPIC: GraphNodeType(
            label=NodeKind.SUBTOPIC,
            key_field="sub_topic_key",
            description=(
                "Curated subtopic anchor from config/subtopic_taxonomy.json. "
                "Documents link to these via HAS_SUBTOPIC for retrieval boost."
            ),
            required_fields=("sub_topic_key", "parent_topic", "label"),
        ),
        NodeKind.TOPIC: GraphNodeType(
            label=NodeKind.TOPIC,
            key_field="topic_key",
            description=(
                "Curated topic anchor from config/topic_taxonomy.json. "
                "Documents link to these via TEMA for topic-first retrieval fan-out."
            ),
            required_fields=("topic_key", "label"),
        ),
        NodeKind.NORM: GraphNodeType(
            label=NodeKind.NORM,
            key_field="norm_id",
            description=(
                "fixplan_v3 §0.3.2 — first-class legal norm. Mirrors `norms` catalog. "
                "Edges (MODIFIED_BY / DEROGATED_BY / etc.) carry the v3 vigencia history. "
                "VIGENCIA STATE IS NEVER STORED HERE — it lives in Supabase "
                "`norm_vigencia_history` and is read via the `norm_vigencia_at_date(norm_id, asof)` "
                "SQL RPC. Cypher branches like `WHERE n.vigencia_status = 'vigente'` always "
                "return empty by design (fix_v6.md §1 yellow-flag #3)."
            ),
            required_fields=("norm_id", "norm_type", "display_label"),
            optional_fields=(
                "parent_norm_id",
                "is_sub_unit",
                "sub_unit_kind",
                "emisor",
                "fecha_emision",
                "canonical_url",
            ),
        ),
        NodeKind.INTERPRETATION: GraphNodeType(
            label=NodeKind.INTERPRETATION,
            key_field="doc_id",
            description=(
                "fix_v10_may Phase 10C §3.C — expert-commentary anchor. "
                "Mirrors interpretive_guidance documents in Supabase. The "
                "planner anchors interpretation retrieval on these via "
                "INTERPRETS edges, the same way it anchors article retrieval "
                "via MODIFIES/REFERENCES. Provider strings stay as bag "
                "properties on the node (promotion to ExpertProviderNode + "
                "AUTHORED_BY is v10.1 scope per §9.4)."
            ),
            required_fields=("doc_id", "source_label"),
            optional_fields=(
                "authority",
                "trust_tier",
                "topic_key",
                "pais",
                "provider_labels",
                "relative_path",
            ),
        ),
    }

    article_targets = (NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT, NodeKind.PARAMETER)
    edge_types = {
        EdgeKind.REFERENCES: GraphEdgeType(
            label=EdgeKind.REFERENCES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT),
            target_kinds=article_targets,
            description="Generic normative or conceptual reference.",
        ),
        EdgeKind.MODIFIES: GraphEdgeType(
            label=EdgeKind.MODIFIES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A reform chain or article text change.",
        ),
        EdgeKind.SUPERSEDES: GraphEdgeType(
            label=EdgeKind.SUPERSEDES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A repeal or full replacement relationship.",
        ),
        EdgeKind.EXCEPTION_TO: GraphEdgeType(
            label=EdgeKind.EXCEPTION_TO,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE,),
            description="One article behaves as an exception to another.",
        ),
        EdgeKind.COMPUTATION_DEPENDS_ON: GraphEdgeType(
            label=EdgeKind.COMPUTATION_DEPENDS_ON,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE, NodeKind.PARAMETER),
            description="Computation order or formula dependency.",
        ),
        EdgeKind.REQUIRES: GraphEdgeType(
            label=EdgeKind.REQUIRES,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE, NodeKind.CONCEPT, NodeKind.PARAMETER),
            description="A requirement or prerequisite relationship.",
        ),
        EdgeKind.DEFINES: GraphEdgeType(
            label=EdgeKind.DEFINES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.CONCEPT),
            target_kinds=(NodeKind.CONCEPT, NodeKind.ARTICLE),
            description="A legal or vocabulary definition relationship.",
        ),
        EdgeKind.PART_OF: GraphEdgeType(
            label=EdgeKind.PART_OF,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.CONCEPT,),
            description="Structural grouping between articles and topic anchors.",
        ),
        # SUIN-derived edges. Source/target cover ArticleNode and ReformNode so
        # we can represent both intra-ET modifications and law→article edges.
        EdgeKind.ANULA: GraphEdgeType(
            label=EdgeKind.ANULA,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="Consejo de Estado annulment (nulidad) of an article or act.",
        ),
        EdgeKind.DECLARES_EXEQUIBLE: GraphEdgeType(
            label=EdgeKind.DECLARES_EXEQUIBLE,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="Corte Constitucional affirms the article's constitutionality.",
        ),
        EdgeKind.DEROGATES: GraphEdgeType(
            label=EdgeKind.DEROGATES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A law or article derogates another.",
        ),
        EdgeKind.REGLAMENTA: GraphEdgeType(
            label=EdgeKind.REGLAMENTA,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A decreto reglamentario regulates a law or article.",
        ),
        EdgeKind.STRUCK_DOWN_BY: GraphEdgeType(
            label=EdgeKind.STRUCK_DOWN_BY,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="Corte Constitucional declares article inexequible.",
        ),
        EdgeKind.SUSPENDS: GraphEdgeType(
            label=EdgeKind.SUSPENDS,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="An authority temporarily suspends the article's effect.",
        ),
        EdgeKind.HAS_SUBTOPIC: GraphEdgeType(
            label=EdgeKind.HAS_SUBTOPIC,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT),
            target_kinds=(NodeKind.SUBTOPIC,),
            description=(
                "Links a document-origin node (Article/Reform/Concept) to a "
                "curated SubTopic anchor — used by retrieval to boost chunks "
                "under a detected subtopic intent."
            ),
        ),
        EdgeKind.TEMA: GraphEdgeType(
            label=EdgeKind.TEMA,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT),
            target_kinds=(NodeKind.TOPIC,),
            description=(
                "Chunk/article-level thematic edge to a curated Topic anchor. "
                "Enables topic-first retrieval fan-out from ``planner.topic_hint`` "
                "to all chunks under the topic."
            ),
        ),
        EdgeKind.SUBTEMA_DE: GraphEdgeType(
            label=EdgeKind.SUBTEMA_DE,
            source_kinds=(NodeKind.SUBTOPIC,),
            target_kinds=(NodeKind.TOPIC,),
            description=(
                "Static taxonomy edge from SubTopic → parent Topic. Emitted "
                "once per subtopic at load time so the graph can walk "
                "subtopic ↔ topic without consulting the JSON taxonomy."
            ),
        ),
        # fixplan_v3 §0.3.2 — Norm-keyed vigencia mirror edges.
        EdgeKind.MODIFIED_BY: GraphEdgeType(
            label=EdgeKind.MODIFIED_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm modified by another Norm (typically a posterior reforma).",
        ),
        EdgeKind.DEROGATED_BY: GraphEdgeType(
            label=EdgeKind.DEROGATED_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm derogated (expresa or tácita) by another Norm.",
        ),
        EdgeKind.SUSPENDED_BY: GraphEdgeType(
            label=EdgeKind.SUSPENDED_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm under suspensión provisional by an auto/sentencia.",
        ),
        EdgeKind.INEXEQUIBLE_BY: GraphEdgeType(
            label=EdgeKind.INEXEQUIBLE_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm declared inexequible by a sentencia C-.",
        ),
        EdgeKind.CONDITIONALLY_EXEQUIBLE_BY: GraphEdgeType(
            label=EdgeKind.CONDITIONALLY_EXEQUIBLE_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm declared exequibilidad condicionada (EC) by a sentencia C-.",
        ),
        EdgeKind.MODULATED_BY: GraphEdgeType(
            label=EdgeKind.MODULATED_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm under non-CC modulación (VC) — concepto DIAN posterior, doctrina, etc.",
        ),
        EdgeKind.REVIVED_BY: GraphEdgeType(
            label=EdgeKind.REVIVED_BY,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Norm revivida tras inexequibilidad de la norma derogante (RV).",
        ),
        EdgeKind.CITES: GraphEdgeType(
            label=EdgeKind.CITES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT, NodeKind.NORM),
            target_kinds=(NodeKind.NORM,),
            description="A document chunk / article cites a canonical Norm (with role + anchor_strength on the edge).",
        ),
        EdgeKind.IS_SUB_UNIT_OF: GraphEdgeType(
            label=EdgeKind.IS_SUB_UNIT_OF,
            source_kinds=(NodeKind.NORM,),
            target_kinds=(NodeKind.NORM,),
            description="Sub-unit norm (parágrafo / inciso / numeral / literal) → its parent norm.",
        ),
        # fix_v10_may Phase 10C §3.C — interpretation anchors. INTERPRETS is
        # the load-bearing edge for Phase 10C: when the chat is about to cite
        # `Art. 124-2 ET`, the planner runs
        #
        #   MATCH (a:ArticleNode {key:'art_124_2_et'})<-[:INTERPRETS]-(i:InterpretationNode)
        #   RETURN i.doc_id ORDER BY i.trust_tier DESC LIMIT 8
        #
        # and hands the doc_ids to `retriever_supabase.fetch_interpretation_candidates`
        # as an anchor seed. Cap of 8 per article keeps the planner queries
        # bounded — rerank does the final ordering.
        EdgeKind.INTERPRETS: GraphEdgeType(
            label=EdgeKind.INTERPRETS,
            source_kinds=(NodeKind.INTERPRETATION,),
            target_kinds=(NodeKind.ARTICLE,),
            description=(
                "An expert commentary doc analyzes / interprets a specific "
                "article. Many-to-many (one brief can interpret many articles)."
            ),
        ),
        EdgeKind.COVERS_TOPIC: GraphEdgeType(
            label=EdgeKind.COVERS_TOPIC,
            source_kinds=(NodeKind.INTERPRETATION,),
            target_kinds=(NodeKind.TOPIC,),
            description=(
                "An expert commentary doc is filed under a curated topic — "
                "enables a planner fan-out when no specific article is in "
                "scope (e.g. broad 'planeación tributaria' questions). One "
                "InterpretationNode → 0..N TopicNodes; in practice usually 1."
            ),
        ),
    }

    return GraphSchema(
        graph_name=DEFAULT_GRAPH_NAME,
        node_types=node_types,
        edge_types=edge_types,
    )
