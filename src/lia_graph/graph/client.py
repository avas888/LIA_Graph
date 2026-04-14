"""Dependency-light FalkorDB client scaffolds for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .schema import (
    DEFAULT_GRAPH_NAME,
    GraphEdgeRecord,
    GraphNodeRecord,
    GraphSchema,
    default_graph_schema,
)


class GraphClientError(RuntimeError):
    """Raised when the scaffold client cannot execute a requested operation."""


@dataclass(frozen=True)
class GraphClientConfig:
    url: str = ""
    graph_name: str = DEFAULT_GRAPH_NAME
    connect_timeout_seconds: float = 3.0

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        graph_name: str = DEFAULT_GRAPH_NAME,
    ) -> "GraphClientConfig":
        env = os.environ if environ is None else environ
        configured_graph_name = str(env.get("FALKORDB_GRAPH", graph_name) or graph_name).strip()
        return cls(
            url=str(env.get("FALKORDB_URL", "") or "").strip(),
            graph_name=configured_graph_name or graph_name,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    @property
    def redacted_url(self) -> str:
        if not self.url:
            return ""
        parsed = urlparse(self.url)
        hostname = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        username = parsed.username or ""
        if username:
            auth = f"{username}:***@"
        elif parsed.password:
            auth = ":***@"
        else:
            auth = ""
        return f"{parsed.scheme}://{auth}{hostname}{port}"

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.redacted_url,
            "graph_name": self.graph_name,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "is_configured": self.is_configured,
        }


@dataclass(frozen=True)
class GraphWriteStatement:
    description: str
    query: str
    parameters: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "query": self.query,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class GraphQueryResult:
    description: str
    query: str
    parameters: Mapping[str, object]
    rows: tuple[Mapping[str, object], ...] = ()
    stats: Mapping[str, object] = field(default_factory=dict)
    skipped: bool = False
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "query": self.query,
            "parameters": dict(self.parameters),
            "rows": [dict(row) for row in self.rows],
            "stats": dict(self.stats),
            "skipped": self.skipped,
            "diagnostics": dict(self.diagnostics),
        }


QueryExecutor = Callable[[GraphWriteStatement, GraphClientConfig], GraphQueryResult]


class GraphClient:
    """Stages graph writes now and can execute them later via an injected adapter."""

    def __init__(
        self,
        *,
        config: GraphClientConfig | None = None,
        schema: GraphSchema | None = None,
        executor: QueryExecutor | None = None,
    ) -> None:
        self.config = config or GraphClientConfig()
        self.schema = schema or default_graph_schema()
        self._executor = executor

    @classmethod
    def from_env(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        schema: GraphSchema | None = None,
        executor: QueryExecutor | None = None,
    ) -> "GraphClient":
        return cls(
            config=GraphClientConfig.from_env(environ),
            schema=schema,
            executor=executor,
        )

    def stage_node(self, record: GraphNodeRecord) -> GraphWriteStatement:
        self.schema.validate_node_record(record)
        node_type = self.schema.node_type(record.kind)
        query = (
            f"MERGE (node:{record.kind.value} {{{node_type.key_field}: $key}})\n"
            "SET node += $properties\n"
            "RETURN node"
        )
        return GraphWriteStatement(
            description=f"Upsert {record.kind.value}:{record.key}",
            query=query,
            parameters={"key": record.key, "properties": dict(record.properties)},
        )

    def stage_edge(self, record: GraphEdgeRecord) -> GraphWriteStatement:
        self.schema.validate_edge_record(record)
        source_type = self.schema.node_type(record.source_kind)
        target_type = self.schema.node_type(record.target_kind)
        query = (
            f"MATCH (source:{record.source_kind.value} {{{source_type.key_field}: $source_key}})\n"
            f"MATCH (target:{record.target_kind.value} {{{target_type.key_field}: $target_key}})\n"
            f"MERGE (source)-[rel:{record.kind.value}]->(target)\n"
            "SET rel += $properties\n"
            "RETURN rel"
        )
        return GraphWriteStatement(
            description=(
                f"Upsert {record.kind.value}:{record.source_kind.value}:{record.source_key}"
                f"->{record.target_kind.value}:{record.target_key}"
            ),
            query=query,
            parameters={
                "source_key": record.source_key,
                "target_key": record.target_key,
                "properties": dict(record.properties),
            },
        )

    def execute(
        self,
        statement: GraphWriteStatement,
        *,
        strict: bool = False,
    ) -> GraphQueryResult:
        if self._executor is not None:
            return self._executor(statement, self.config)
        if strict:
            raise GraphClientError(
                "GraphClient has no executor configured for live FalkorDB queries."
            )
        diagnostics = {
            "reason": "no_executor_configured",
            "graph_name": self.config.graph_name,
            "configured_url": self.config.redacted_url,
        }
        if not self.config.is_configured:
            diagnostics["reason"] = "missing_falkordb_url"
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            skipped=True,
            diagnostics=diagnostics,
        )
