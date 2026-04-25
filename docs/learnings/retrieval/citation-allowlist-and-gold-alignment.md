# Citation allow-list + gold-file taxonomy alignment

**Source:** `docs/done/next/ingestion_tunningv2.md` §6–§7 (phases 4–5); commits `e74f6d9`, `6ea134e`.

## Part 1 — Defensive citation allow-list (phase 4)

### The incident

The v5 panel flagged multiple contamination cases where the synthesized answer correctly scoped to the right topic but cited articles that had no business being in that topic's answer:

- **Q11** (nota crédito factura electrónica) cited ET Art. 516 and Art. 514 — those are **impuesto de timbre** articles, pure retrieval leakage.
- **Q27** (SAGRILAFT) cited ET Art. 148 — SAGRILAFT has no relevant ET anchors at all; any ET citation is leakage.
- **Q22** (saldo a favor) contained stray citations to retención-fuente articles outside the devolución-saldo-a-favor scope.

### The port from Lia Contadores

The ancestor product's `prompts/answer_policy_es.md` carried a per-topic **allow-list** of ET article numbers the answer was permitted to cite. Any other citation was silently dropped as retrieval leakage. This was one of Contadores's five anti-hallucination mechanisms.

Phase 4 (v6) ported the mechanism to `src/lia_graph/pipeline_d/_citation_allowlist.py`. Config lives in `config/citation_allow_list.json` — schema:

```json
{
  "topics": {
    "laboral": {
      "allowed_et_articles": ["383", "384", "385", "387", "387-1", "388", "108", "114-1"],
      "allowed_article_families": ["CST", "CODIGO_SUSTANTIVO_TRABAJO", "LEY_100", "PARAFISCAL"]
    },
    ...
  }
}
```

A citation passes iff **either** its ET article number is in `allowed_et_articles` **or** its authority/family matches one of `allowed_article_families`. Drops are recorded in `diagnostics["dropped_by_allowlist"]` for audit.

Flag: `LIA_POLICY_CITATION_ALLOWLIST={off|enforce}`, **default `enforce` since 2026-04-25** (was `off` until then; flipped per operator's "no off flags" directive). Higher-risk flip than coherence_gate — not yet end-to-end verified per the original six-gate policy; risk-forward internal-beta posture accepts the trade-off. Watch production for over-filtered citations; if accountants report missing valid cites, revert to `off`. 14 tests in `tests/test_citation_allowlist.py` (9 ET-allowlist + 5 norm-anchor for non-ET topics).

### Rules for seeding new topic allow-lists

1. **Start with 4 topics that the panel flagged.** In v6: `laboral`, `sagrilaft_ptee`, `facturacion_electronica`, `regimen_simple`. Do not add a topic allow-list without panel evidence of contamination — unguarded expansion creates over-drop risk.
2. **`allowed_article_families` > `allowed_et_articles`** for topics where the governing corpus is not ET (SAGRILAFT, NIIF, etc.). An empty `allowed_et_articles` with the right family names correctly drops all ET citations.
3. **Audit drops weekly** during rollout. A topic dropping >33 % of traffic citations is too narrow; widen the allow-list.
4. **Config-driven means no code changes to add topics.** Bump the config `version` string when you add entries.

---

## Part 2 — Gold-file vs taxonomy alignment (phase 5)

### The finding

Investigation I2 ran the 30 v5 eval questions through `detect_topic_from_text` directly. Result: the gold file's `expected_topic` strings **did not match** the taxonomy keys for 4 questions (6 after the v6 subtopic additions):

| qid | Gold file `expected_topic` | Real taxonomy key |
|---|---|---|
| Q19 | `obligaciones_mercantiles` | `comercial_societario` |
| Q25 | `impuesto_patrimonio` | `impuesto_patrimonio_personas_naturales` |
| Q26 | `dividendos` | `dividendos_utilidades` |
| Q29 | `perdidas_fiscales` | `perdidas_fiscales_art147` |
| Q21 (new) | `firmeza_declaraciones` | *added in phase 5* |
| Q22 (new) | `devoluciones_saldos_a_favor` | *added in phase 5* |

The classifier was returning the right topic; the gold file was using inconsistent shorthand. The eval compared strings and marked them as misroutes.

### The rule

**Gold files and taxonomies are coupled; version them together.** Every `evals/*.jsonl` row whose `expected_topic` doesn't exist in `config/topic_taxonomy.json` is a measurement bug waiting to fire. Add a CI check:

```python
# pre-commit or CI gate
tax_keys = {t["key"] for t in load_json("config/topic_taxonomy.json")["topics"]}
for row in load_jsonl("evals/gold_retrieval_v1.jsonl"):
    et = row.get("expected_topic")
    assert et is None or et in tax_keys, f"{row['qid']}: {et!r} missing from taxonomy"
```

When the taxonomy changes, re-run this check and patch the gold file in the same PR.

### Subtopic-override patterns for procedural children

Phase 5 added three subtopic entries under `declaracion_renta`: `firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`. Adding the keys to `config/topic_taxonomy.json` and keyword buckets to `src/lia_graph/topic_router_keywords.py` was **not sufficient** to route Q20/Q21/Q22 to the subtopic — the parent `declaracion_renta` still won by dict-iteration order on tied scores.

The fix: regex-based `_SUBTOPIC_OVERRIDE_PATTERNS` in `topic_router_keywords.py`. These fire **before** the score-based classifier, short-circuiting the decision. One caveat — they only fire in the production `resolve_chat_topic` path, not in the simpler `detect_topic_from_text` path used by ingest classification. The plan's §7.4 verification script used the wrong path, causing me to debug-chase a non-issue for 10 minutes. **Verify classifier changes via `resolve_chat_topic`, not `detect_topic_from_text`.**

## See also

- `docs/done/next/ingestion_tunningv2.md` §6 (phase 4), §7 (phase 5).
- `src/lia_graph/pipeline_d/_citation_allowlist.py` + `config/citation_allow_list.json`.
- `src/lia_graph/topic_router_keywords.py` — `_SUBTOPIC_OVERRIDE_PATTERNS`.
