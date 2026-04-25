# The "operates not defines" meta-rule

> **Captured 2026-04-25** from Alejandro (SME, contador público / asesor PYMEs) during the next_v3 30Q spot-review. Single most generalizable insight from the cycle. Encoded as a top-level heuristic block in the chat-resolver classifier prompt (managed by marker `SME_META_RULE_OP_VS_DEF` in `src/lia_graph/topic_router.py`).

## The rule

> **El TEMA es el que OPERA, no el que DEFINE.**
>
> Cuando una pregunta toca dos áreas, el tema es el área donde se EJECUTA la respuesta operativa, no el área donde se definen los conceptos involucrados.

In English: when a question touches two domains, the right topic is the one where the **operative answer lives**, not the one that **defines the concepts** mentioned in the question.

## Why this is so generalizable

Most topic-classification failures in a domain RAG aren't about novel topics — they're about queries that mention multiple topics where one is a definitional dependency and the other is the operative answer. The router sees "two topics mentioned" and picks based on lexical strength; the right answer is governed by **which topic is doing the work**.

Examples (all real failures from the next_v3 30Q):

| Query | Defines | Operates → topic |
|---|---|---|
| "Patrimonio líquido alto pero pérdida operativa, ¿qué pasa con la renta presuntiva?" | patrimonio (input data), renta líquida (input data) | renta presuntiva (the comparison mechanic) |
| "Descuento del IVA en bienes de capital" | IVA (the cost being recovered) | descuentos de renta (where the recovery executes — art. 258-1 ET) |
| "Tarifa del impuesto si la sociedad está en zona franca" | zona franca (the regime context) | tarifas (the rate computation) |
| "Llegó un emplazamiento para corregir la declaración de IVA" | IVA (the substantive tax) | procedimiento_tributario (the procedural artifact = emplazamiento) |
| "Sanción por no retener" | retención (what wasn't done) | regimen_sancionatorio (the operative consequence) |

Same shape every time. Once you see the pattern, you stop arguing case by case and start applying the rule.

## Heuristics that fall out of it

Alejandro derived several decision tests from the meta-rule. Each one is a tighter form of "operates not defines" applied to a specific class of question:

### Test 1 — Comparative tension

If the query mentions **two quantities in tension** ("X alto pero Y bajo", "X positivo aunque Y negativo"), the topic is the one that **operates on the comparison**, not the one that defines either quantity.

> *"Patrimonio líquido es muy alto pero la operación dio pérdida → renta_presuntiva, no patrimonio."*

### Test 2 — Cross-impuesto recovery

If the query is about how **a cost in impuesto A is recovered in impuesto B** ("descuento del IVA en bienes de capital", "IVA en obras por impuestos", "descuento del SIMPLE por aportes a pensión"), the topic is **B** (where the recovery executes), not A (where the cost was paid).

> *"Cuando la consulta es sobre cómo el IVA pagado se recupera en otro impuesto (renta, RST, ICA), el topic es el de ese otro impuesto, no IVA."*

### Test 3 — Procedural artifact rewrite test

If the query mentions a **procedural artifact** (emplazamiento, requerimiento especial, liquidación oficial, sanción, corregir declaración), and the question can be **rewritten changing the substantive impuesto without changing the operative answer**, the topic is **procedural** (Libro 5 ET), not the substantive impuesto.

> *"Llegó un emplazamiento para corregir la declaración de [renta / IVA / timbre / retención]" — la respuesta práctica es la misma. Eso es procedimiento.*

### Test 4 — Regime vs mechanic verb test

When a query coexists a **regime context** (zona franca, ZESE, ZOMAC, RST, ESAL) and a **fiscal mechanic** (tarifa, base, exención):

| Verb in query | Topic |
|---|---|
| "estoy pensando", "vale la pena", "qué régimen", "cómo califico" | regime (zonas_francas, regimen_simple, etc.) |
| "cuál es la tarifa", "cuánto pago", "cómo liquido" | mechanic (tarifas_renta_y_ttd, etc.) |

> *"Si la pregunta es sobre escoger/evaluar el régimen → topic = régimen. Si es sobre aplicar la mecánica una vez ya estás en el régimen → topic = mecánica, con régimen como secondary."*

### Test 5 — Verb of agent action (retención example)

In the retención family, three conjuncts coexist that the user disambiguates by **verb of action**:

| Verb in query | Conjunct → topic |
|---|---|
| "practico / consigno / certifico / presento mi 350" | as agent → retencion_fuente_general |
| "veo en mi certificado / descuento / imputo" | as taxable subject → declaracion_renta |
| "me sancionaron / corrijo extemporáneo" | sanction → regimen_sancionatorio_extemporaneidad |

> *"El verbo de acción del contador en la pregunta lo delata."*

## How to use this in code

The rule lives in two places, intentionally redundant:

1. **Chat-resolver prompt** (`src/lia_graph/topic_router.py` `_build_classifier_prompt`) — a top-level heuristic block above the topic catalog, with 4 example pairs. Marked `SME_META_RULE_OP_VS_DEF` for idempotent management by `artifacts/sme_pending/apply_sme_decisions.py`.
2. **Mutex rules in `config/topic_taxonomy.json`** — each carve-out (renta_presuntiva_vs_patrimonio, descuento_iva_bienes_capital, regime_vs_mechanic_routing, etc.) ships with the generalization clause attached. The LLM gets the same heuristic via two paths.

When you add a new mutex rule, **always include the generalization clause** ("Generalización: ..."). The rule isn't useful if it only solves the one case the SME named.

## When this rule does NOT apply

Not every two-topic query is operates-vs-defines. Sometimes both topics are operatively involved (a question genuinely needs both). Indicators:

- The query asks for **both** outcomes ("¿cuánto IVA pago Y cuánto puedo descontar de renta?")
- The verbs are coordinated ("compré ... y vendí ...")
- The user explicitly requests cross-reference ("también dime cómo afecta ...")

In these cases, the right move is `secondary_topics` on the result, not collapsing to one. The LLM prompt makes this explicit: *"secondary_topics: 0–3 temas del catálogo, sin repetir primary_topic."*

## Cross-references

- `src/lia_graph/topic_router.py` — `_build_classifier_prompt` (the prompt block) + `SME_META_RULE_OP_VS_DEF` marker
- `config/topic_taxonomy.json` — mutex_rules array (each rule has the generalization clause)
- `docs/aa_next/taxonomy_v2_sme_response.md` — Alejandro's full SME deliverable that surfaced the rule
- `docs/aa_next/taxonomy_v2_sme_spot_review.md` — the 7 questions that taught us the rule
- `docs/learnings/retrieval/router-llm-deferral-architecture.md` — how we make sure the LLM gets a chance to apply this rule
