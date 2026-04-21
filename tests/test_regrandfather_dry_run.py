"""Tests for ``scripts/regrandfather_corpus.py`` (Phase 5c of ingestfixv1).

Verifies the regrandfather CLI against a synthetic ``knowledge_base``
fixture rooted in ``tmp_path``:

- (a) empty corpus completes cleanly with ``docs_processed=0``,
- (b) already-canonical doc keeps ``coercion_method=native`` and commit
  mode does not mutate the file bytes,
- (c) non-canonical doc classifies as heuristic/llm and commit mode
  rewrites the file,
- (d) dry-run mode never mutates files, even for non-canonical docs,
- (e) errored docs are reported and do not abort the walk,
- (f) ``--limit 1`` stops after the first doc,
- (g) the JSON report is written at the expected path.

The script is imported via ``importlib`` (it lives under ``scripts/``
rather than an installed package) and invoked in-process through
``main(argv)`` for speed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "regrandfather_corpus.py"


# ---------------------------------------------------------------------------
# Module loader — keep a single cached import so tests can monkeypatch it.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rgr_module():
    spec = importlib.util.spec_from_file_location(
        "regrandfather_corpus_under_test", _SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load regrandfather_corpus.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["regrandfather_corpus_under_test"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_markdown() -> str:
    """Already-canonical doc: all 8 headings, bodies above ``min_chars``.

    Must round-trip byte-for-byte through the coercer's native path so the
    commit-mode "no mutation on native input" invariant holds.
    """
    from lia_graph.ingestion_section_coercer import coerce_to_canonical_template

    raw = (
        "## Identificacion\n"
        "- titulo: Ley de prueba tributaria con nombre suficientemente largo\n"
        "- autoridad: Congreso de la Republica de Colombia\n"
        "- numero: 99\n"
        "- fecha_emision: 2024-01-01\n"
        "- fecha_vigencia: 2024-01-01\n"
        "- ambito_tema: tributario\n"
        "- doc_id: LEY-99-2024\n"
        "\n"
        "## Texto base referenciado (resumen tecnico)\n"
        "El articulo 1 establece la obligacion tributaria sustancial para personas "
        "juridicas del regimen ordinario y fija la tarifa general del impuesto.\n"
        "\n"
        "## Regla operativa para LIA\n"
        "Al redactar la respuesta: cita el articulo 1, explica el calculo paso a paso "
        "y recuerda verificar la UVT vigente del ejercicio fiscal correspondiente.\n"
        "\n"
        "## Condiciones de aplicacion\n"
        "Aplica a personas juridicas con ingresos brutos anuales superiores a 3500 UVT "
        "dentro del regimen ordinario del impuesto sobre la renta.\n"
        "\n"
        "## Riesgos de interpretacion\n"
        "La DIAN suele exigir pruebas contables; evitar interpretaciones expansivas y "
        "confirmar siempre con doctrina vigente antes de emitir concepto profesional.\n"
        "\n"
        "## Relaciones normativas\n"
        "- modifica: Ley 1819 de 2016 articulo 240\n"
        "- reglamentada_por: Decreto 1625 de 2016 Libro 1 Parte 2\n"
        "- concordante_con: Estatuto Tributario articulo 240\n"
        "\n"
        "## Checklist de vigencia\n"
        "- vigencia: vigente al 2026-03-01 segun la Secretaria Juridica\n"
        "- verificado_en: 2026-03-01 por el equipo de curaduria normativa\n"
        "\n"
        "## Historico de cambios\n"
        "2024-01-01 emision original publicada en el Diario Oficial numero 52500.\n"
        "2025-06-10 modificada parcialmente por la Ley 2200 articulo 12.\n"
    )

    # Round-trip through the coercer so the file on disk is exactly what
    # the regrandfather script would produce — guarantees commit-mode on
    # an already-canonical doc is a byte-identical no-op.
    return coerce_to_canonical_template(raw, skip_llm=True).coerced_markdown


def _non_canonical_markdown() -> str:
    """Alias-heading doc missing one canonical section → heuristic path.

    The coercer classifies a doc as ``native`` iff all 8 canonical
    sections resolve. Dropping ``## Historia`` leaves the mapper at 7/8,
    which forces the heuristic branch (threshold is 6/8) and guarantees
    the output carries a placeholder + freshly-rendered Metadata v2
    block, so commit mode has something to rewrite.
    """
    return (
        "## Encabezado\n"
        "- titulo: Decreto de ejemplo con nombre largo para el fixture sintetico\n"
        "- autoridad: Ministerio de Hacienda de la Republica de Colombia\n"
        "- numero: 501\n"
        "- fecha_emision: 2023-05-15\n"
        "- fecha_vigencia: 2023-06-01\n"
        "- ambito_tema: tributario\n"
        "- doc_id: DEC-501-2023\n"
        "\n"
        "## Articulos\n"
        "El articulo 1 establece el hecho generador del tributo especial y define "
        "las bases gravables aplicables durante la vigencia del presente decreto.\n"
        "\n"
        "## Regla de uso\n"
        "Al citar este decreto, verificar primero que la tarifa no haya sido "
        "modificada por una norma posterior antes de aplicarla al caso concreto.\n"
        "\n"
        "## Condiciones\n"
        "Aplica unicamente a contribuyentes personas juridicas domiciliadas en "
        "Colombia que superen el umbral de ingresos definido en el articulo 2.\n"
        "\n"
        "## Alertas\n"
        "La doctrina reciente de la DIAN ha restringido el alcance del articulo 1, "
        "revisar concepto 100208221-0452 de 2024 antes de aplicar la norma.\n"
        "\n"
        "## Cadena normativa\n"
        "- modifica: Decreto 1625 de 2016 articulo 1.2.1.5.1.\n"
        "- concordante_con: Estatuto Tributario articulo 240-1.\n"
        "\n"
        "## Vigencia\n"
        "- vigencia: vigente al 2026-03-01 segun consulta oficial de rutina.\n"
    )


def _make_corpus(
    root: Path,
    files: dict[str, str],
) -> None:
    """Write ``files`` (relative-path -> content) under ``root/knowledge_base``."""
    kb = root / "knowledge_base"
    kb.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = kb / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _base_argv(
    tmp_path: Path,
    *,
    commit: bool = False,
    extra: list[str] | None = None,
) -> list[str]:
    argv = [
        "--knowledge-base",
        str(tmp_path / "knowledge_base"),
        "--artifacts-dir",
        str(tmp_path / "artifacts"),
        "--skip-llm",
    ]
    argv.append("--commit" if commit else "--dry-run")
    if extra:
        argv.extend(extra)
    return argv


def _find_report(tmp_path: Path, *, mode: str) -> Path:
    artifacts = tmp_path / "artifacts"
    if not artifacts.is_dir():
        return artifacts  # non-existent path; caller will assert
    candidates = sorted(artifacts.glob(f"regrandfather_{mode}_*.json"))
    assert candidates, f"no regrandfather report written in {artifacts}"
    return candidates[-1]


# ---------------------------------------------------------------------------
# (a) Empty knowledge_base → docs_processed == 0 and no crash
# ---------------------------------------------------------------------------


def test_empty_knowledge_base_completes_cleanly(tmp_path, rgr_module):
    (tmp_path / "knowledge_base").mkdir()
    rc = rgr_module.main(_base_argv(tmp_path))
    assert rc == 0

    report_path = _find_report(tmp_path, mode="dry_run")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 0
    assert payload["error_count"] == 0
    assert payload["per_coercion_method"] == {}
    assert payload["docs"] == []


# ---------------------------------------------------------------------------
# (b) Already-canonical doc → native + commit keeps file bytes unchanged
# ---------------------------------------------------------------------------


def test_canonical_doc_is_native_and_commit_does_not_touch_bytes(tmp_path, rgr_module):
    content = _canonical_markdown()
    _make_corpus(tmp_path, {"laboral/canonical.md": content})
    target = tmp_path / "knowledge_base" / "laboral" / "canonical.md"

    original_bytes = target.read_bytes()
    rc = rgr_module.main(_base_argv(tmp_path, commit=True))
    assert rc == 0
    # Commit mode must NOT rewrite files whose coerced output matches input.
    assert target.read_bytes() == original_bytes

    report_path = _find_report(tmp_path, mode="commit")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 1
    assert payload["per_coercion_method"].get("native") == 1
    assert payload["docs"][0]["mutated"] is False


# ---------------------------------------------------------------------------
# (c) Non-canonical doc → heuristic/llm; commit mode rewrites the file
# ---------------------------------------------------------------------------


def test_non_canonical_doc_is_rewritten_in_commit_mode(tmp_path, rgr_module):
    content = _non_canonical_markdown()
    _make_corpus(tmp_path, {"tributario/decreto.md": content})
    target = tmp_path / "knowledge_base" / "tributario" / "decreto.md"

    original_bytes = target.read_bytes()
    rc = rgr_module.main(_base_argv(tmp_path, commit=True))
    assert rc == 0

    # File must be mutated AND the new content must carry the canonical
    # Metadata v2 block + the 8 canonical H2 headings.
    new_bytes = target.read_bytes()
    assert new_bytes != original_bytes
    new_text = new_bytes.decode("utf-8")
    assert "## Metadata v2" in new_text
    for heading in (
        "## Identificacion",
        "## Texto base referenciado (resumen tecnico)",
        "## Regla operativa para LIA",
        "## Condiciones de aplicacion",
        "## Riesgos de interpretacion",
        "## Relaciones normativas",
        "## Checklist de vigencia",
        "## Historico de cambios",
    ):
        assert heading in new_text, f"missing canonical heading {heading!r}"

    report_path = _find_report(tmp_path, mode="commit")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 1
    assert payload["error_count"] == 0
    method = payload["docs"][0]["coercion_method"]
    assert method in {"heuristic", "llm"}
    assert payload["docs"][0]["mutated"] is True


# ---------------------------------------------------------------------------
# (d) Dry-run mode → no FS mutation even for non-canonical docs
# ---------------------------------------------------------------------------


def test_dry_run_never_mutates_files(tmp_path, rgr_module):
    _make_corpus(
        tmp_path,
        {
            "tributario/decreto.md": _non_canonical_markdown(),
            "laboral/canonical.md": _canonical_markdown(),
        },
    )
    decreto = tmp_path / "knowledge_base" / "tributario" / "decreto.md"
    canonical = tmp_path / "knowledge_base" / "laboral" / "canonical.md"

    decreto_bytes_before = decreto.read_bytes()
    canonical_bytes_before = canonical.read_bytes()

    rc = rgr_module.main(_base_argv(tmp_path))  # dry-run default
    assert rc == 0

    assert decreto.read_bytes() == decreto_bytes_before
    assert canonical.read_bytes() == canonical_bytes_before

    report_path = _find_report(tmp_path, mode="dry_run")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 2
    # dry-run never marks a doc as mutated, regardless of coercion method.
    assert all(entry["mutated"] is False for entry in payload["docs"])


# ---------------------------------------------------------------------------
# (e) Errored doc → recorded in report; other docs still processed
# ---------------------------------------------------------------------------


def test_errored_doc_is_reported_and_walk_continues(tmp_path, rgr_module, monkeypatch):
    _make_corpus(
        tmp_path,
        {
            "tributario/decreto.md": _non_canonical_markdown(),
            "laboral/canonical.md": _canonical_markdown(),
        },
    )

    real_coerce = rgr_module.coerce_to_canonical_template

    def _fake_coerce(markdown, *, skip_llm=False, filename=None, **kwargs):
        if filename == "canonical.md":
            raise RuntimeError("boom on canonical.md")
        return real_coerce(markdown, skip_llm=skip_llm, filename=filename, **kwargs)

    monkeypatch.setattr(rgr_module, "coerce_to_canonical_template", _fake_coerce)

    rc = rgr_module.main(_base_argv(tmp_path, commit=True))
    # commit mode with errors exits with rc=2
    assert rc == 2

    report_path = _find_report(tmp_path, mode="commit")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 1
    assert payload["error_count"] == 1
    assert len(payload["errors"]) == 1
    assert "canonical.md" in payload["errors"][0]["path"]
    # The good doc still got processed and mutated.
    assert payload["docs"][0]["path"].endswith("decreto.md")


# ---------------------------------------------------------------------------
# (f) --limit 1 stops after one doc
# ---------------------------------------------------------------------------


def test_limit_stops_after_first_doc(tmp_path, rgr_module):
    _make_corpus(
        tmp_path,
        {
            "tributario/decreto_a.md": _non_canonical_markdown(),
            "tributario/decreto_b.md": _non_canonical_markdown(),
            "laboral/canonical.md": _canonical_markdown(),
        },
    )

    rc = rgr_module.main(_base_argv(tmp_path, extra=["--limit", "1"]))
    assert rc == 0

    report_path = _find_report(tmp_path, mode="dry_run")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["docs_processed"] == 1
    assert len(payload["docs"]) == 1


# ---------------------------------------------------------------------------
# (g) JSON report file written at the expected path (default + explicit)
# ---------------------------------------------------------------------------


def test_json_report_is_written_to_expected_path(tmp_path, rgr_module):
    _make_corpus(tmp_path, {"laboral/canonical.md": _canonical_markdown()})

    # Explicit --report-path wins over the default slot.
    explicit_path = tmp_path / "out" / "my_report.json"
    rc = rgr_module.main(
        _base_argv(
            tmp_path,
            extra=["--report-path", str(explicit_path)],
        )
    )
    assert rc == 0
    assert explicit_path.is_file()

    payload = json.loads(explicit_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["docs_processed"] == 1
    assert payload["report_path"].endswith("my_report.json")

    # Default-path branch still works when --report-path is omitted.
    rc2 = rgr_module.main(_base_argv(tmp_path))
    assert rc2 == 0
    default_report = _find_report(tmp_path, mode="dry_run")
    assert default_report.is_file()
    assert default_report.name.startswith("regrandfather_dry_run_")
