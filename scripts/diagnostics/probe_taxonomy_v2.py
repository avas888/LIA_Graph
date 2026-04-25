"""next_v3 §8.2 — post-rebuild Cypher verification of taxonomy v2 flips.

Asserts the 5 flip rows + 1 unchanged row documented in next_v3.md §8.2:

| # | Article / path                                     | Pre-v2 wrong topic                         | Expected post-v2 topic             |
|---|----------------------------------------------------|---------------------------------------------|-------------------------------------|
| 1 | art. 148 from 06_Libro1_T1_Cap5_Deducciones.md      | iva                                         | costos_deducciones_renta            |
| 2 | all articles from 17_Libro4_Timbre.md (514–540)     | facturacion_electronica                     | impuesto_timbre                     |
| 3 | all articles from 10_Libro1_T2_Patrimonio.md        | sector_cultura                              | patrimonio_fiscal_renta             |
| 4 | all articles from 02_Libro1_T1_Cap1_Ingresos.md     | iva                                         | ingresos_fiscales_renta             |
| 5 | articles from 18/19_Libro5_Procedimiento*.md        | iva                                         | procedimiento_tributario (family)   |
| 6 | all articles from 20_Libro6_GMF.md                  | (already correct)                           | gravamen_movimiento_financiero_4x1000 (unchanged) |

Reads cloud Falkor connection from environment (source .env.staging first).
Exits 0 if all 5 flip rows pass + unchanged row stays unchanged; non-zero otherwise.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, "src")

from lia_graph.graph.client import GraphClient, GraphClientConfig, GraphWriteStatement


@dataclass
class ProbeRow:
    row_id: int
    description: str
    path_needle: str
    expected_topics: tuple[str, ...]  # any hit counts as pass
    wrong_topics: tuple[str, ...]     # any hit counts as failure (unless only_expected=False)
    only_expected: bool = True        # True = every TEMA must be in expected set


PROBES: tuple[ProbeRow, ...] = (
    ProbeRow(
        row_id=1,
        description="art. 148 from 06_Libro1_T1_Cap5_Deducciones.md",
        path_needle="06_Libro1_T1_Cap5_Deducciones",
        expected_topics=("costos_deducciones_renta", "declaracion_renta"),
        wrong_topics=("iva", "sagrilaft_ptee"),
    ),
    ProbeRow(
        row_id=2,
        description="ET Libro 4 Timbre (514-540)",
        path_needle="17_Libro4_Timbre",
        expected_topics=("impuesto_timbre",),
        wrong_topics=("facturacion_electronica",),
    ),
    ProbeRow(
        row_id=3,
        description="ET Libro 1 T2 Patrimonio (261-298)",
        path_needle="10_Libro1_T2_Patrimonio",
        expected_topics=("patrimonio_fiscal_renta", "declaracion_renta"),
        wrong_topics=("sector_cultura", "iva"),
    ),
    ProbeRow(
        row_id=4,
        description="ET Libro 1 T1 Cap 1 Ingresos (26-57)",
        path_needle="02_Libro1_T1_Cap1_Ingresos",
        expected_topics=("ingresos_fiscales_renta", "declaracion_renta"),
        wrong_topics=("iva",),
    ),
    ProbeRow(
        row_id=5,
        description="ET Libro 5 Procedimiento",
        path_needle="Libro5_Procedimiento",
        expected_topics=(
            "procedimiento_tributario",
            "firmeza_declaraciones",
            "devoluciones_saldos_a_favor",
            "regimen_sancionatorio_extemporaneidad",
            "regimen_sancionatorio",
        ),
        wrong_topics=("iva",),
    ),
    ProbeRow(
        row_id=6,
        description="ET Libro 6 GMF (unchanged)",
        path_needle="20_Libro6_GMF",
        expected_topics=("gravamen_movimiento_financiero_4x1000",),
        wrong_topics=(),
        only_expected=True,
    ),
)


CYPHER = """
MATCH (a:ArticleNode)-[:TEMA]->(t:TopicNode)
WHERE a.source_path CONTAINS $needle
RETURN a.article_id AS article,
       a.source_path AS path,
       collect(DISTINCT t.topic_key) AS topics
ORDER BY article
LIMIT 200
"""


def _run_probe(client: GraphClient, row: ProbeRow) -> tuple[bool, str]:
    stmt = GraphWriteStatement(
        description=f"probe_v2_row_{row.row_id}",
        query=CYPHER,
        parameters={"needle": row.path_needle},
    )
    result = client.execute(stmt, strict=True)
    rows = list(result.rows or [])
    if not rows:
        return False, f"no articles found for path containing {row.path_needle!r}"

    # Aggregate the set of topic_keys bound to any article in this path slice.
    # FalkorDB's Python client serializes collect(DISTINCT ...) as a bracketed
    # string "[key1, key2]" rather than a Python list — parse it here.
    def _topics_of(row: dict) -> list[str]:
        raw = row.get("topics")
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        if isinstance(raw, str):
            stripped = raw.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped[1:-1]
            return [t.strip(" \"'") for t in stripped.split(",") if t.strip(" \"'")]
        return []

    seen: set[str] = set()
    for r in rows:
        for t in _topics_of(r):
            if t:
                seen.add(t)

    expected = set(row.expected_topics)
    wrong = set(row.wrong_topics)

    hit_expected = bool(seen & expected)
    hit_wrong = seen & wrong

    # Pass criterion:
    #   - must hit at least one expected topic
    #   - must NOT hit any wrong topic
    if not hit_expected:
        return False, (
            f"none of expected {sorted(expected)} bound; found topics: {sorted(seen)}"
        )
    if hit_wrong:
        return False, (
            f"wrong-topic leakage still present: {sorted(hit_wrong)}; "
            f"expected {sorted(expected)}; found {sorted(seen)}"
        )
    return True, f"ok ({len(rows)} articles) — topics: {sorted(seen)}"


def main() -> int:
    url = os.environ.get("FALKORDB_URL", "")
    graph = os.environ.get("FALKORDB_GRAPH", "")
    if not url or not graph:
        print("FALKORDB_URL / FALKORDB_GRAPH unset — source .env.staging first", file=sys.stderr)
        return 2

    print(f"# next_v3 §8.2 verification — graph={graph}")
    print(f"# taxonomy v2 flip rows")
    print()

    cfg = GraphClientConfig.from_env()
    client = GraphClient(config=cfg)

    passes = 0
    failures: list[tuple[ProbeRow, str]] = []
    for row in PROBES:
        ok, msg = _run_probe(client, row)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] Row {row.row_id}: {row.description}")
        print(f"        {msg}")
        if ok:
            passes += 1
        else:
            failures.append((row, msg))
        print()

    print(f"SUMMARY: {passes}/{len(PROBES)} rows pass")
    if failures:
        print("DECISION: FAIL — next_v3 §8.2 requires 5/5 flip rows + unchanged row stable.")
        for row, msg in failures:
            print(f"  - Row {row.row_id}: {msg}")
        return 1
    print("DECISION: PASS — next_v3 §8.2 Cypher verification green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
