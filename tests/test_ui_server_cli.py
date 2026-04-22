"""Structural tests for the ui_server CLI extraction.

Phase 4 moves ``run_server`` / ``parser`` / ``main`` into
``ui_server_cli``. ``ui_server`` re-exports them so the
``pyproject.toml [project.scripts] lia-ui = "lia_graph.ui_server:main"``
entry point and ``python -m lia_graph.ui_server`` both continue to
resolve.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from lia_graph import ui_server, ui_server_cli


def test_cli_symbols_importable_from_both_modules():
    assert ui_server.main is ui_server_cli.main
    assert ui_server.parser is ui_server_cli.parser
    assert ui_server.run_server is ui_server_cli.run_server


def test_parser_returns_argparse_parser_with_expected_flags():
    p = ui_server_cli.parser()
    assert isinstance(p, argparse.ArgumentParser)
    help_text = p.format_help()
    for flag in ("--host", "--port", "--reload", "--reload-interval-seconds"):
        assert flag in help_text, flag


def test_python_dash_m_entry_point_help_exits_zero():
    # `python -m lia_graph.ui_server --help` must not hit the circular-import
    # shape that tripped the lazy re-export during Phase 4 setup.
    result = subprocess.run(
        [sys.executable, "-m", "lia_graph.ui_server", "--help"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--host" in result.stdout
    assert "--reload-interval-seconds" in result.stdout
