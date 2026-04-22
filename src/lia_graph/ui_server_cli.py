"""CLI entry points for the Lia UI HTTP server.

Phase 4 of the decouplingv1 plan moves ``run_server`` / ``parser`` /
``main`` off ``ui_server``. ``ui_server`` keeps thin re-exports so
``pyproject.toml [project.scripts] lia-ui = "lia_graph.ui_server:main"``
and ``python -m lia_graph.ui_server`` continue to resolve.
"""

from __future__ import annotations

import argparse
import os
import threading
from http.server import ThreadingHTTPServer

from .ui_server_constants import WORKSPACE_ROOT
from .ui_server_handler_dispatch import LiaUIHandler
from .ui_server_helpers import _start_reload_watcher


def run_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    reload: bool = False,
    reload_interval_seconds: float = 1.0,
) -> int:
    server = ThreadingHTTPServer((host, port), LiaUIHandler)
    stop_event: threading.Event | None = None
    reload_event: threading.Event | None = None
    watcher: threading.Thread | None = None
    if reload:
        watch_roots = (
            WORKSPACE_ROOT / "src" / "lia_graph",
            WORKSPACE_ROOT / "ui",
        )
        stop_event, reload_event, watcher = _start_reload_watcher(
            server=server,
            watch_roots=watch_roots,
            interval_seconds=max(0.2, float(reload_interval_seconds)),
        )
    print(f"LIA UI disponible en http://{host}:{port}")
    if reload:
        print("Modo reload activo: el servidor se detiene cuando detecta cambios de código.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if stop_event is not None:
            stop_event.set()
        if watcher is not None:
            watcher.join(timeout=1.0)
        server.server_close()
    if reload and reload_event is not None and reload_event.is_set():
        print("Cambio detectado. Saliendo con código 3 para reinicio automático.")
        return 3
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Servidor local de UI para chat con LIA")
    p.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("PORT", "8787")))
    p.add_argument("--reload", action="store_true", help="Auto-detener servidor al detectar cambios en src/ui.")
    p.add_argument(
        "--reload-interval-seconds",
        type=float,
        default=1.0,
        help="Frecuencia de sondeo para modo reload (segundos).",
    )
    return p


def main() -> int:
    from .env_loader import load_dotenv_if_present
    load_dotenv_if_present()
    args = parser().parse_args()
    reload_enabled = bool(getattr(args, "reload", False))
    reload_interval = float(getattr(args, "reload_interval_seconds", 1.0))
    try:
        outcome = run_server(
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            reload_interval_seconds=reload_interval,
        )
        return int(outcome) if isinstance(outcome, int) else 0
    except TypeError as exc:
        if "unexpected keyword argument 'reload'" not in str(exc):
            raise
        legacy_outcome = run_server(host=args.host, port=args.port)  # type: ignore[misc]
        return int(legacy_outcome) if isinstance(legacy_outcome, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
