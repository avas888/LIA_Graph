"""Guard that CLI scripts auto-load .env / .env.local on CLI invocation.

Regression of the bug that forced ``set -a; source .env.local; set +a``
incantations before running any of these scripts (§1.2 / §0.5 item #3):
without autoload the scripts bailed with ``GEMINI_API_KEY not set``.

We invoke the scripts as subprocesses so the autoload runs in a clean
Python process (mirrors the real CLI invocation). Running the autoload
only inside ``main()`` — not at module top-level — keeps pytest-session
``os.environ`` uncontaminated when a test imports the module directly.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


def _run_python(
    code: str,
    *,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONPATH": f"{SRC_DIR}:{REPO_ROOT}",
        "LIA_DISABLE_DOTENV": "",
        "HOME": str(cwd),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(cwd),
    )


@pytest.mark.parametrize(
    ("module_name", "main_attr"),
    [
        ("scripts.embedding_ops", "main"),
        ("scripts.backfill_subtopic", "main"),
        ("scripts.sync_subtopic_taxonomy_to_supabase", "main"),
    ],
)
def test_main_calls_load_dotenv(tmp_path: Path, module_name: str, main_attr: str) -> None:
    """Invoking ``main()`` of each CLI script calls ``load_dotenv_if_present``."""
    code = textwrap.dedent(
        f"""
        import sys
        # Patch env_loader BEFORE importing the script so the spy binds.
        import lia_graph.env_loader as env_loader
        calls = {{'n': 0}}
        original = env_loader.load_dotenv_if_present
        def spy(*a, **kw):
            calls['n'] += 1
            return original(*a, **kw)
        env_loader.load_dotenv_if_present = spy

        mod = __import__('{module_name}', fromlist=['{main_attr}'])
        # Also patch the module's own reference (star-import style rebinds).
        setattr(mod, 'load_dotenv_if_present', spy)
        try:
            mod.{main_attr}(['--help'])
        except SystemExit:
            pass
        print('CALLS=', calls['n'])
        """
    )
    result = _run_python(code, cwd=REPO_ROOT)
    assert result.returncode == 0, (
        f"CLI main({main_attr!r}) errored: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    assert tail.startswith("CALLS= "), f"unexpected tail: {tail!r}"
    count = int(tail.split("=", 1)[1].strip())
    assert count >= 1, f"expected load_dotenv to be called, got {count}"


def test_sentinel_var_from_dotenv_reaches_subprocess(tmp_path: Path) -> None:
    """A .env.local next to cwd is auto-loaded when load_dotenv_if_present runs."""
    (tmp_path / ".env.local").write_text(
        "LIA_DOTENV_SENTINEL=hello_from_dotenv\n", encoding="utf-8"
    )
    code = textwrap.dedent(
        """
        import os, sys
        from pathlib import Path
        repo_root = Path(os.environ['_REPO_ROOT'])
        sys.path.insert(0, str(repo_root / 'src'))
        sys.path.insert(0, str(repo_root))
        from lia_graph.env_loader import load_dotenv_if_present
        load_dotenv_if_present()
        print('SENTINEL=', os.environ.get('LIA_DOTENV_SENTINEL', ''))
        """
    )
    result = _run_python(
        code,
        cwd=tmp_path,
        extra_env={"_REPO_ROOT": str(REPO_ROOT)},
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert "SENTINEL= hello_from_dotenv" in result.stdout, result.stdout


def test_embedding_ops_reads_gemini_from_dotenv_on_invocation(tmp_path: Path) -> None:
    """Regression: ``scripts/ingestion/embedding_ops.py`` used to fail with
    ``GEMINI_API_KEY not set`` when invoked without first sourcing
    ``.env.local``. After A2, invoking ``main()`` triggers autoload and
    the sentinel GEMINI_API_KEY becomes visible.
    """
    (tmp_path / ".env.local").write_text(
        "GEMINI_API_KEY=sentinel-key-for-test\n", encoding="utf-8"
    )
    code = textwrap.dedent(
        """
        import os, sys
        from pathlib import Path
        repo_root = Path(os.environ['_REPO_ROOT'])
        sys.path.insert(0, str(repo_root / 'src'))
        sys.path.insert(0, str(repo_root))
        # Invoke the CLI's autoload pathway directly (no argparse).
        import scripts.embedding_ops as eo
        eo.load_dotenv_if_present()
        key = os.environ.get('GEMINI_API_KEY', '')
        print('KEY_VALUE=', key)
        """
    )
    result = _run_python(
        code,
        cwd=tmp_path,
        extra_env={"_REPO_ROOT": str(REPO_ROOT)},
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert "sentinel-key-for-test" in result.stdout, result.stdout


def test_module_import_alone_does_not_mutate_environ(tmp_path: Path) -> None:
    """Importing the CLI modules must NOT call load_dotenv_if_present.

    Otherwise unrelated pytest runs pick up the user's real .env.local and
    leak FALKORDB_URL / SUPABASE_URL into tests that expect them unset.
    """
    (tmp_path / ".env.local").write_text(
        "LIA_IMPORT_ONLY_CANARY=leaked\n", encoding="utf-8"
    )
    code = textwrap.dedent(
        """
        import os, sys
        from pathlib import Path
        repo_root = Path(os.environ['_REPO_ROOT'])
        sys.path.insert(0, str(repo_root / 'src'))
        sys.path.insert(0, str(repo_root))
        # Only import — do NOT invoke main.
        import scripts.backfill_subtopic  # noqa: F401
        import scripts.embedding_ops  # noqa: F401
        import scripts.sync_subtopic_taxonomy_to_supabase  # noqa: F401
        canary = os.environ.get('LIA_IMPORT_ONLY_CANARY', '')
        print('CANARY=', canary)
        """
    )
    result = _run_python(
        code,
        cwd=tmp_path,
        extra_env={"_REPO_ROOT": str(REPO_ROOT)},
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert "CANARY= \n" in result.stdout or result.stdout.strip().endswith(
        "CANARY="
    ), (
        "import of script modules leaked .env.local into os.environ: "
        f"{result.stdout!r}"
    )
