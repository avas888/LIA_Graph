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
    raw_response, connection_diagnostics = _run_graph_query(statement, config)
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
    try:
        sock.sendall(_resp_encode("GRAPH.QUERY", config.graph_name, rendered_query))
        raw_response = _read_resp(sock)
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
    if isinstance(item, list) and len(item) >= 2:
        return str(item[1])
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
