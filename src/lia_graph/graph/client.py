"""Dependency-light FalkorDB client scaffolds for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
import re
import socket
import ssl
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlparse

from .schema import (
    DEFAULT_GRAPH_NAME,
    EdgeKind,
    GraphEdgeRecord,
    GraphNodeRecord,
    GraphSchema,
    NodeKind,
    default_graph_schema,
)


class GraphClientError(RuntimeError):
    """Raised when the scaffold client cannot execute a requested operation."""


@dataclass(frozen=True)
class GraphClientConfig:
    url: str = ""
    graph_name: str = DEFAULT_GRAPH_NAME
    connect_timeout_seconds: float = 3.0
    # Phase 2c (v6): per-query server-side TIMEOUT and client socket read
    # timeout. 30s default covers an UNWIND of 500 nodes + MERGE on an
    # indexed label; tune up only if writes legitimately take longer.
    # The 2026-04-24 cloud-sink stall was caused by the old implicit
    # default (no TIMEOUT) making both client recv() and server-side
    # Cypher run forever when a single MERGE happened to be slow.
    query_timeout_seconds: float = 30.0
    # Batch sizes for UNWIND-based bulk writes. Node batches are smaller
    # because each row carries a properties map; edge rows only carry
    # two keys + small props. Match FalkorDB bulk-load guidance.
    batch_size_nodes: int = 500
    batch_size_edges: int = 1000

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        graph_name: str = DEFAULT_GRAPH_NAME,
    ) -> "GraphClientConfig":
        env = os.environ if environ is None else environ
        configured_graph_name = str(env.get("FALKORDB_GRAPH", graph_name) or graph_name).strip()
        # Optional timeout override (default 3s is tight for large TEMA
        # fan-outs like iva/laboral when TEMA-first retrieval is on). Any
        # value below 1.0 is clamped up to 1.0 to avoid accidental hangs.
        timeout_raw = str(env.get("FALKORDB_TIMEOUT_SECONDS", "") or "").strip()
        try:
            timeout = max(1.0, float(timeout_raw)) if timeout_raw else 3.0
        except ValueError:
            timeout = 3.0
        query_timeout_raw = str(env.get("FALKORDB_QUERY_TIMEOUT_SECONDS", "") or "").strip()
        try:
            query_timeout = max(1.0, float(query_timeout_raw)) if query_timeout_raw else 30.0
        except ValueError:
            query_timeout = 30.0
        try:
            batch_nodes = max(1, int(env.get("FALKORDB_BATCH_NODES", "") or 500))
        except ValueError:
            batch_nodes = 500
        try:
            batch_edges = max(1, int(env.get("FALKORDB_BATCH_EDGES", "") or 1000))
        except ValueError:
            batch_edges = 1000
        return cls(
            url=str(env.get("FALKORDB_URL", "") or "").strip(),
            graph_name=configured_graph_name or graph_name,
            connect_timeout_seconds=timeout,
            query_timeout_seconds=query_timeout,
            batch_size_nodes=batch_nodes,
            batch_size_edges=batch_edges,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    @property
    def query_timeout_ms(self) -> int:
        """Server-side TIMEOUT clause in milliseconds."""
        return max(100, int(self.query_timeout_seconds * 1000))

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
            "query_timeout_seconds": self.query_timeout_seconds,
            "batch_size_nodes": self.batch_size_nodes,
            "batch_size_edges": self.batch_size_edges,
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
    ok: bool = True
    error: str | None = None
    rows: tuple[Mapping[str, object], ...] = ()
    stats: Mapping[str, object] = field(default_factory=dict)
    skipped: bool = False
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "query": self.query,
            "parameters": dict(self.parameters),
            "ok": self.ok,
            "error": self.error,
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
        graph_name = schema.graph_name if schema is not None else DEFAULT_GRAPH_NAME
        return cls(
            config=GraphClientConfig.from_env(environ, graph_name=graph_name),
            schema=schema,
            executor=executor,
        )

    def stage_node(self, record: GraphNodeRecord) -> GraphWriteStatement:
        self.schema.validate_node_record(record)
        node_type = self.schema.node_type(record.kind)
        query = (
            f"MERGE (node:{record.kind.value} {{{node_type.key_field}: $key}})\n"
            "SET node += $properties\n"
        )
        return GraphWriteStatement(
            description=f"Upsert {record.kind.value}:{record.key}",
            query=query,
            parameters={"key": record.key, "properties": dict(record.properties)},
        )

    def stage_detach_delete(self, kind: NodeKind, key: str) -> GraphWriteStatement:
        """Stage a ``MATCH ... DETACH DELETE`` against a single node by key.

        Used by the additive-corpus-v1 Phase 5 delta loader to remove the
        article nodes that belong to a retired doc. The DETACH clause deletes
        the node and all of its inbound/outbound edges in one statement.
        """
        if not key or not str(key).strip():
            raise ValueError("stage_detach_delete requires a non-empty key")
        node_type = self.schema.node_type(kind)
        query = (
            f"MATCH (node:{kind.value} {{{node_type.key_field}: $key}})\n"
            "DETACH DELETE node\n"
        )
        return GraphWriteStatement(
            description=f"Detach-delete {kind.value}:{key}",
            query=query,
            parameters={"key": str(key)},
        )

    def stage_delete_outbound_edges(
        self,
        source_kind: NodeKind,
        source_key: str,
        *,
        relation_subset: Iterable[EdgeKind] | None = None,
    ) -> GraphWriteStatement:
        """Stage a ``MATCH ... DELETE`` over outbound edges from a single node.

        When ``relation_subset`` is supplied the DELETE is scoped to those
        edge kinds; otherwise every outbound edge is removed. Used by the
        delta loader to wipe stale outbound edges for modified-doc articles
        before the re-MERGE step.
        """
        if not source_key or not str(source_key).strip():
            raise ValueError("stage_delete_outbound_edges requires a non-empty source_key")
        source_type = self.schema.node_type(source_kind)
        if relation_subset is None:
            edge_clause = "[rel]"
        else:
            names = sorted({k.value for k in relation_subset})
            if not names:
                edge_clause = "[rel]"
            else:
                edge_clause = "[rel:" + "|".join(names) + "]"
        query = (
            f"MATCH (source:{source_kind.value} {{{source_type.key_field}: $source_key}})"
            f"-{edge_clause}->()\n"
            "DELETE rel\n"
        )
        return GraphWriteStatement(
            description=f"Delete outbound edges from {source_kind.value}:{source_key}",
            query=query,
            parameters={"source_key": str(source_key)},
        )

    def stage_index(self, kind: NodeKind) -> GraphWriteStatement:
        """Idempotent ``CREATE INDEX FOR (n:<kind>) ON (n.<key>)``.

        Phase 2c (v6): must run before any bulk MERGE on this label,
        otherwise each MERGE does a label scan (O(N)) and the total load
        degrades quadratically with graph size. FalkorDB treats
        ``CREATE INDEX`` as idempotent — safe to run on every ingest.
        """
        node_type = self.schema.node_type(kind)
        query = f"CREATE INDEX FOR (n:{kind.value}) ON (n.{node_type.key_field})\n"
        return GraphWriteStatement(
            description=f"CreateIndex {kind.value}.{node_type.key_field}",
            query=query,
            parameters={},
        )

    def stage_indexes_for_merge_labels(self) -> tuple[GraphWriteStatement, ...]:
        """Return one ``CREATE INDEX`` per node kind in the schema.

        Called at the head of a bulk load. All schema-registered labels
        get an index on their key field; this is the one-time setup that
        turns the MERGE pattern from O(N) into O(log N).
        """
        return tuple(self.stage_index(kind) for kind in self.schema.node_types.keys())

    def stage_node_batch(
        self,
        kind: NodeKind,
        rows: Iterable[Mapping[str, Any]],
    ) -> GraphWriteStatement:
        """Stage a single UNWIND+MERGE over ``rows`` — MUCH faster than N stage_node calls.

        Each row must carry ``key`` and ``properties`` (the same shape
        ``stage_node`` consumes). The statement rewrites to:

            UNWIND $rows AS r
            MERGE (n:<kind> {<key_field>: r.key})
            SET n += r.properties

        Phase 2c (v6): one parse + one plan + one reply per batch, vs.
        one-per-row. 50–100× throughput on batches of 500.
        """
        node_type = self.schema.node_type(kind)
        rows_list = [
            {"key": str(r.get("key", "")), "properties": dict(r.get("properties") or {})}
            for r in rows
        ]
        if not rows_list:
            return GraphWriteStatement(
                description=f"BatchUpsert {kind.value} (empty)",
                query="RETURN 0 AS skipped\n",
                parameters={},
            )
        query = (
            "UNWIND $rows AS r\n"
            f"MERGE (node:{kind.value} {{{node_type.key_field}: r.key}})\n"
            "SET node += r.properties\n"
        )
        return GraphWriteStatement(
            description=f"BatchUpsert {kind.value} x{len(rows_list)}",
            query=query,
            parameters={"rows": rows_list},
        )

    def stage_edge_batch(
        self,
        *,
        edge_kind: EdgeKind,
        source_kind: NodeKind,
        target_kind: NodeKind,
        rows: Iterable[Mapping[str, Any]],
    ) -> GraphWriteStatement:
        """Stage a single UNWIND+MATCH+MERGE over ``rows`` — the edge analog.

        Each row must carry ``source_key``, ``target_key``, and
        ``properties``. Rewrites to:

            UNWIND $rows AS r
            MATCH (s:<source_kind> {<src_key>: r.source_key})
            MATCH (t:<target_kind> {<dst_key>: r.target_key})
            MERGE (s)-[rel:<edge_kind>]->(t)
            SET rel += r.properties

        Endpoints use MATCH (not MERGE) so a missing node silently
        no-ops that row instead of creating a naked stub. This matches
        the pre-batch ``stage_edge`` semantics.
        """
        source_type = self.schema.node_type(source_kind)
        target_type = self.schema.node_type(target_kind)
        rows_list = [
            {
                "source_key": str(r.get("source_key", "")),
                "target_key": str(r.get("target_key", "")),
                "properties": dict(r.get("properties") or {}),
            }
            for r in rows
        ]
        if not rows_list:
            return GraphWriteStatement(
                description=f"BatchEdge {edge_kind.value} (empty)",
                query="RETURN 0 AS skipped\n",
                parameters={},
            )
        query = (
            "UNWIND $rows AS r\n"
            f"MATCH (source:{source_kind.value} {{{source_type.key_field}: r.source_key}})\n"
            f"MATCH (target:{target_kind.value} {{{target_type.key_field}: r.target_key}})\n"
            f"MERGE (source)-[rel:{edge_kind.value}]->(target)\n"
            "SET rel += r.properties\n"
        )
        return GraphWriteStatement(
            description=(
                f"BatchEdge {edge_kind.value}:{source_kind.value}->{target_kind.value} "
                f"x{len(rows_list)}"
            ),
            query=query,
            parameters={"rows": rows_list},
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
        if self.config.is_configured:
            try:
                return _execute_live_statement(statement, self.config)
            except GraphClientError as exc:
                if strict:
                    raise
                return GraphQueryResult(
                    description=statement.description,
                    query=statement.query,
                    parameters=statement.parameters,
                    ok=False,
                    error=str(exc),
                    diagnostics={
                        "reason": "live_execution_failed",
                        "graph_name": self.config.graph_name,
                        "configured_url": self.config.redacted_url,
                    },
                )
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

    def execute_many(
        self,
        statements: Iterable[GraphWriteStatement],
        *,
        strict: bool = False,
    ) -> tuple[GraphQueryResult, ...]:
        queued = tuple(statements)
        if not queued:
            return ()
        if self._executor is not None or not self.config.is_configured:
            return tuple(self.execute(statement, strict=strict) for statement in queued)
        return _execute_live_statements(queued, self.config, strict=strict)


def _execute_live_statement(
    statement: GraphWriteStatement,
    config: GraphClientConfig,
) -> GraphQueryResult:
    try:
        raw_response, connection_diagnostics = _run_graph_query(statement, config)
    except GraphClientError as exc:
        if _is_benign_index_error(statement, exc):
            return GraphQueryResult(
                description=statement.description,
                query=statement.query,
                parameters=statement.parameters,
                skipped=True,
                stats={"indices_already_present": 1},
                diagnostics={"reason": "index_already_exists"},
            )
        raise
    rows, stats, response_diagnostics = _decode_graph_query_response(raw_response)
    diagnostics = dict(connection_diagnostics)
    diagnostics.update(response_diagnostics)
    return GraphQueryResult(
        description=statement.description,
        query=statement.query,
        parameters=statement.parameters,
        rows=rows,
        stats=stats,
        diagnostics=diagnostics,
    )


def _is_benign_index_error(
    statement: GraphWriteStatement, exc: GraphClientError
) -> bool:
    """Phase 2c (v6): FalkorDB's ``CREATE INDEX`` is NOT idempotent in
    practice — re-running a load-plan against a graph that already has
    its indexes errors with ``Attribute '<x>' is already indexed``.

    We treat that specific error as success for ``CreateIndex``
    statements. Any other error — or that error text on a different
    statement kind — still propagates.
    """
    if not statement.description.startswith("CreateIndex"):
        return False
    message = str(exc).lower()
    return "already indexed" in message


def _execute_live_statements(
    statements: tuple[GraphWriteStatement, ...],
    config: GraphClientConfig,
    *,
    strict: bool = False,
) -> tuple[GraphQueryResult, ...]:
    try:
        sock, connection_diagnostics = _open_graph_socket(config)
    except GraphClientError as exc:
        if strict:
            raise
        return tuple(_live_failure_result(statement, config, exc) for statement in statements)

    results: list[GraphQueryResult] = []
    with sock:
        for index, statement in enumerate(statements):
            try:
                raw_response, query_diagnostics = _run_graph_query_over_socket(
                    statement,
                    sock,
                    config,
                    connection_diagnostics,
                )
                rows, stats, response_diagnostics = _decode_graph_query_response(raw_response)
                diagnostics = dict(query_diagnostics)
                diagnostics.update(response_diagnostics)
                results.append(
                    GraphQueryResult(
                        description=statement.description,
                        query=statement.query,
                        parameters=statement.parameters,
                        rows=rows,
                        stats=stats,
                        diagnostics=diagnostics,
                    )
                )
            except GraphClientError as exc:
                # Phase 2c (v6): FalkorDB's CREATE INDEX is NOT idempotent —
                # "already indexed" is the expected state on every run after
                # the first. Treat as success + continue.
                if _is_benign_index_error(statement, exc):
                    results.append(
                        GraphQueryResult(
                            description=statement.description,
                            query=statement.query,
                            parameters=statement.parameters,
                            skipped=True,
                            stats={"indices_already_present": 1},
                            diagnostics={"reason": "index_already_exists"},
                        )
                    )
                    continue
                if strict:
                    raise
                results.append(_live_failure_result(statement, config, exc))
                if _is_transport_error(exc):
                    results.extend(
                        _live_failure_result(remaining, config, exc)
                        for remaining in statements[index + 1 :]
                    )
                    break
    return tuple(results)


def _run_graph_query(
    statement: GraphWriteStatement,
    config: GraphClientConfig,
) -> tuple[Any, dict[str, object]]:
    sock, connection_diagnostics = _open_graph_socket(config)
    with sock:
        return _run_graph_query_over_socket(statement, sock, config, connection_diagnostics)


def _open_graph_socket(
    config: GraphClientConfig,
) -> tuple[socket.socket, dict[str, object]]:
    parsed = urlparse(config.url)
    host = parsed.hostname
    port = int(parsed.port or 6379)
    if not host:
        raise GraphClientError("FALKORDB_URL is not parseable.")

    diagnostics: dict[str, object] = {
        "graph_name": config.graph_name,
        "configured_url": config.redacted_url,
        "host": host,
        "port": port,
        "scheme": parsed.scheme or "redis",
    }
    database_index = _database_index(parsed.path)
    if database_index is not None:
        diagnostics["database"] = database_index

    sock: socket.socket | None = None
    try:
        base_socket = socket.create_connection((host, port), timeout=config.connect_timeout_seconds)
        base_socket.settimeout(config.connect_timeout_seconds)
        # Phase 2c (v6): TCP keepalive prevents indefinite recv() blocks
        # when a cloud NAT silently drops an idle connection mid-query.
        # macOS/Linux both accept SO_KEEPALIVE; the per-platform TCP_* knobs
        # are best-effort and only applied when available.
        try:
            base_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "TCP_KEEPIDLE"):
                base_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
            if hasattr(socket, "TCP_KEEPINTVL"):
                base_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, "TCP_KEEPCNT"):
                base_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        except (OSError, AttributeError):
            # Keepalive is best-effort; not all platforms / sockets support
            # every option. Don't abort the connection over it.
            pass
        if parsed.scheme == "rediss":
            context = ssl.create_default_context()
            sock = context.wrap_socket(base_socket, server_hostname=host)
        else:
            sock = base_socket

        if parsed.password:
            if parsed.username:
                sock.sendall(_resp_encode("AUTH", parsed.username, parsed.password))
            else:
                sock.sendall(_resp_encode("AUTH", parsed.password))
            auth_response = _read_resp(sock)
            diagnostics["auth_response"] = auth_response
            if isinstance(auth_response, dict) and auth_response.get("error"):
                raise GraphClientError(
                    f"FalkorDB AUTH failed: {auth_response['error']}"
                )

        if database_index is not None:
            sock.sendall(_resp_encode("SELECT", str(database_index)))
            select_response = _read_resp(sock)
            diagnostics["select_response"] = select_response
            if isinstance(select_response, dict) and select_response.get("error"):
                raise GraphClientError(
                    f"FalkorDB SELECT failed: {select_response['error']}"
                )
    except GraphClientError:
        if sock is not None:
            sock.close()
        raise
    except Exception as exc:  # noqa: BLE001
        if sock is not None:
            sock.close()
        raise GraphClientError(f"FalkorDB query transport failed: {exc}") from exc
    return sock, diagnostics


def _run_graph_query_over_socket(
    statement: GraphWriteStatement,
    sock: socket.socket,
    config: GraphClientConfig,
    connection_diagnostics: Mapping[str, object],
) -> tuple[Any, dict[str, object]]:
    diagnostics = dict(connection_diagnostics)
    rendered_query = _render_parameterized_query(
        statement.query,
        statement.parameters,
    )
    diagnostics["parameter_keys"] = sorted(statement.parameters)
    diagnostics["query_timeout_ms"] = config.query_timeout_ms
    # Phase 2c (v6): client-side read timeout. Before this, recv() could
    # block forever on a slow Cypher MERGE because the connect-timeout
    # value didn't propagate to post-auth reads. Give the server 2× its
    # TIMEOUT budget to reply (server aborts at ``query_timeout_ms``; we
    # wait a little longer for the error message to arrive).
    read_budget_seconds = config.query_timeout_seconds * 2
    try:
        sock.settimeout(read_budget_seconds)
    except OSError:
        # Non-blocking SSL socket quirk; continue without raising.
        pass
    try:
        # Append ``TIMEOUT <ms>`` so the server self-aborts on slow
        # queries and rolls back partial writes. Per FalkorDB docs,
        # GRAPH.QUERY accepts a trailing TIMEOUT argument.
        sock.sendall(
            _resp_encode(
                "GRAPH.QUERY",
                config.graph_name,
                rendered_query,
                "TIMEOUT",
                str(config.query_timeout_ms),
            )
        )
        raw_response = _read_resp(sock)
    except socket.timeout as exc:
        raise GraphClientError(
            f"FalkorDB query transport failed: read timeout after "
            f"{read_budget_seconds:.1f}s (server TIMEOUT={config.query_timeout_ms}ms)"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise GraphClientError(f"FalkorDB query transport failed: {exc}") from exc

    if isinstance(raw_response, dict) and raw_response.get("error"):
        raise GraphClientError(
            f"FalkorDB returned an error for {statement.description}: {raw_response['error']}"
        )
    return raw_response, diagnostics


def _live_failure_result(
    statement: GraphWriteStatement,
    config: GraphClientConfig,
    exc: GraphClientError,
) -> GraphQueryResult:
    return GraphQueryResult(
        description=statement.description,
        query=statement.query,
        parameters=statement.parameters,
        ok=False,
        error=str(exc),
        diagnostics={
            "reason": "live_execution_failed",
            "graph_name": config.graph_name,
            "configured_url": config.redacted_url,
        },
    )


def _is_transport_error(exc: GraphClientError) -> bool:
    return str(exc).startswith("FalkorDB query transport failed:")


def _database_index(path: str) -> int | None:
    normalized = str(path or "").strip("/")
    if not normalized:
        return None
    head = normalized.split("/", maxsplit=1)[0]
    if not head:
        return None
    try:
        return int(head)
    except ValueError:
        return None


def _render_parameterized_query(query: str, parameters: Mapping[str, object]) -> str:
    if not parameters:
        return query
    assignments = " ".join(
        f"{name}={_cypher_literal(parameters[name])}"
        for name in sorted(parameters)
    )
    return f"CYPHER {assignments} {query}"


def _cypher_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GraphClientError("Cypher parameter values must be finite numbers.")
        return repr(value)
    if isinstance(value, str):
        return _cypher_string(value)
    if isinstance(value, Mapping):
        parts = [
            f"{_cypher_map_key(key)}: {_cypher_literal(item)}"
            for key, item in value.items()
        ]
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_cypher_literal(item) for item in value) + "]"
    return _cypher_string(str(value))


def _cypher_map_key(value: object) -> str:
    key = str(value)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return "`" + key.replace("`", "``") + "`"


def _cypher_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _decode_graph_query_response(
    raw_response: Any,
) -> tuple[tuple[Mapping[str, object], ...], dict[str, object], dict[str, object]]:
    rows: tuple[Mapping[str, object], ...] = ()
    stats: dict[str, object] = {}
    diagnostics: dict[str, object] = {
        "response_type": type(raw_response).__name__,
    }
    if not isinstance(raw_response, list):
        diagnostics["response_shape"] = "non_list"
        return rows, stats, diagnostics

    diagnostics["top_level_items"] = len(raw_response)
    if len(raw_response) == 1:
        stats = _parse_graph_query_stats(raw_response[0])
        return rows, stats, diagnostics
    if len(raw_response) >= 3:
        header = raw_response[0]
        raw_rows = raw_response[1]
        stats = _parse_graph_query_stats(raw_response[2])
        rows = _coerce_query_rows(header, raw_rows)
        diagnostics["returned_row_count"] = len(rows)
        return rows, stats, diagnostics

    diagnostics["response_shape"] = "unexpected"
    return rows, stats, diagnostics


def _coerce_query_rows(
    header: Any,
    raw_rows: Any,
) -> tuple[Mapping[str, object], ...]:
    if not isinstance(header, list) or not isinstance(raw_rows, list):
        return ()
    columns = [_header_name(item, index=index) for index, item in enumerate(header, start=1)]
    rows: list[dict[str, object]] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, list):
            continue
        row: dict[str, object] = {}
        for index, column in enumerate(columns):
            if index >= len(raw_row):
                break
            row[column] = _coerce_query_value(raw_row[index])
        rows.append(row)
    return tuple(rows)


def _header_name(item: Any, *, index: int) -> str:
    # FalkorDB's `GRAPH.QUERY` header element may arrive in two shapes:
    #   - compact mode: `[type_code, column_name]`  (we read index 1)
    #   - plain  mode: just the column name as a bare string
    # Prior versions only handled the compact shape, so every `RETURN x AS y`
    # silently became `column_1, column_2, ...` downstream — breaking every
    # retriever that tried `row.get("article_key")` / `.get("heading")`.
    if isinstance(item, list) and len(item) >= 2:
        return str(item[1])
    if isinstance(item, (str, bytes)):
        value = item.decode("utf-8") if isinstance(item, bytes) else item
        if value:
            return value
    return f"column_{index}"


def _coerce_query_value(value: Any) -> object:
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
        return value[1]
    return value


def _parse_graph_query_stats(raw_stats: Any) -> dict[str, object]:
    if not isinstance(raw_stats, list):
        return {}
    stats: dict[str, object] = {}
    for item in raw_stats:
        if not isinstance(item, str) or ":" not in item:
            continue
        label, raw_value = item.split(":", maxsplit=1)
        key = label.strip().lower().replace(" ", "_")
        value = raw_value.strip()
        if value.endswith(" milliseconds"):
            numeric_value = value.removesuffix(" milliseconds").strip()
            try:
                stats[key] = float(numeric_value)
            except ValueError:
                stats[key] = value
            continue
        try:
            stats[key] = int(value)
        except ValueError:
            try:
                stats[key] = float(value)
            except ValueError:
                stats[key] = value
    return stats


def _resp_encode(*parts: str) -> bytes:
    payload = [f"*{len(parts)}\r\n".encode("utf-8")]
    for part in parts:
        encoded = str(part).encode("utf-8")
        payload.append(f"${len(encoded)}\r\n".encode("utf-8"))
        payload.append(encoded)
        payload.append(b"\r\n")
    return b"".join(payload)


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("Connection closed while reading response.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_line(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise RuntimeError("Connection closed while reading line.")
        chunks.append(chunk)
        if len(chunks) >= 2 and chunks[-2] == b"\r" and chunks[-1] == b"\n":
            return b"".join(chunks[:-2])


def _read_resp(sock: socket.socket) -> Any:
    prefix = _read_exact(sock, 1)
    if prefix == b"+":
        return _read_line(sock).decode("utf-8", errors="replace")
    if prefix == b"-":
        return {"error": _read_line(sock).decode("utf-8", errors="replace")}
    if prefix == b":":
        return int(_read_line(sock).decode("utf-8", errors="replace"))
    if prefix == b"$":
        length = int(_read_line(sock).decode("utf-8", errors="replace"))
        if length < 0:
            return None
        value = _read_exact(sock, length)
        _read_exact(sock, 2)
        return value.decode("utf-8", errors="replace")
    if prefix == b"*":
        count = int(_read_line(sock).decode("utf-8", errors="replace"))
        if count < 0:
            return None
        return [_read_resp(sock) for _ in range(count)]
    raise RuntimeError(f"Unsupported RESP prefix: {prefix!r}")
