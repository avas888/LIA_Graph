# A1 — first real canonicalizer run (2026-04-27 Bogotá morning)

**Run id:** `canonicalizer-A1-20260427T152120Z`
**Outcome:** **0/25 veredictos, 25 refusals** (will re-run after fixes below).
**Why:** the network/scraper plumbing was wrong AND the skill prompt + parser
contract was loose enough that Gemini's outputs failed validation on
~half the norms even when sources were OK.

This doc is the consolidated learning so the next batches don't
re-discover any of it. It's organized by failure mode, with the fix
that landed in this session and the open follow-ups.

## Tl;dr

| What broke | Where | Fix landed | Status |
|---|---|---|---|
| Senado HTTPS port 443 unreachable | `secretariasenado.gov.co` | Switched scraper to HTTP | ✅ |
| Senado URL had `/codigo/` segment that 404s | `secretaria_senado.py` | Removed `/codigo/` | ✅ |
| Senado pr-segment formula `n // 10` wrong | `secretaria_senado.py` | Replaced with precomputed `var/senado_et_pr_index.json` (887 articles) | ✅ |
| SUIN-Juriscol Sectigo cert not trusted by macOS Python | `scrapers/base.py` | Added `_ssl_context_with_certifi` + retries + browser UA | ✅ |
| DIAN normograma had no ET handler — only one source for ET articles | `dian_normograma.py` | Added `et.*` resolver pointing at full-ET page | ✅ |
| Full-ET page (3.9 MB) overflows Gemini context | `dian_normograma.py` | Article-scoped slicing via `[[ART:N]]` markers (4-9 KB per article) | ✅ |
| Prompt context budget per source was 6000 chars (too small for relevant sections) | `vigencia_extractor.py::_build_prompt` | Bumped to 16000 chars/source | ✅ |
| Skill prompt didn't enforce JSON shape strictly | `vigencia_extractor.py::_build_prompt` | Rewrote with literal example + hard rules | ✅ |
| Raw Gemini blob discarded on validation failure | `vigencia_extractor.py::_parse_skill_output` | Now persisted at `evals/vigencia_extraction_v1/_debug/<norm_id>.json` | ✅ |
| Senado IPv4 / region-routing or maintenance-window unknown | network | not in scope; HTTP fallback works | open |
| Skill could still emit malformed change_source / dates | parser | post-relaunch triage; debug blobs will inform | open |
| Vigencia parser is strict (`_parse_date` raises) — no graceful per-field fallback | `vigencia.py` | not loosening; tighten prompt instead | open |

## What we observed (raw refusal bucket)

| Reason | Count (estimate, in the 25-norm A1 run) | Cause |
|---|---|---|
| `INSUFFICIENT_PRIMARY_SOURCES` | ~10 | DIAN's full-ET text was truncated at 6000 chars before reaching the article in question; Gemini only saw 1 of 2 sources mention it. **Fix: article-scoped slicing.** |
| `invalid_vigencia_shape: state_from is required` | ~3 | Gemini omitted `state_from` from the top-level. **Fix: prompt now explicitly says `state_from` is required + shows the literal shape.** |
| `invalid_vigencia_shape: 'norm_id'` | ~3 | KeyError while parsing — `Vigencia.from_dict` expected a `norm_id` field somewhere it wasn't. **Fix: prompt shows the schema; parser logs raw blob for triage.** |
| `invalid_vigencia_shape: 'str' object has no attribute 'get'` | ~5 | Gemini emitted a string where a dict was expected (e.g. `change_source: "ley.2294.2023"` instead of `{"type": "...", "source_norm_id": "..."}`. **Fix: prompt now mandates `change_source` is an object, with literal example.** |
| `invalid_vigencia_shape: Cannot parse date from 'et'` / `'et.decreto.624.1989'` | ~2 | Gemini put a norm_id where a date was expected. **Fix: prompt now reads "every date field must be `YYYY-MM-DD`. NEVER put a norm_id … into a date field."** |
| `Insufficient primary sources. Only one of the provided sources contains evidence` | ~2 | Same root cause as INSUFFICIENT_PRIMARY_SOURCES — DIAN content for the specific article was missing from the truncated window. **Fix: article-scoped slicing.** |

## Cross-cutting patterns + recovery

### "All ET norms refuse with INSUFFICIENT_PRIMARY_SOURCES"
- Always check that BOTH Senado and DIAN slicing are returning per-article content.
- Smoke command:
  ```
  LIA_LIVE_SCRAPER_TESTS=1 PYTHONPATH=src:. uv run python -c "
  from lia_graph.scrapers.cache import ScraperCache
  from lia_graph.scrapers.dian_normograma import DianNormogramaScraper
  from lia_graph.scrapers.secretaria_senado import SecretariaSenadoScraper
  for cls in (SecretariaSenadoScraper, DianNormogramaScraper):
      r = cls(ScraperCache(), live_fetch=True).fetch('et.art.555-2')
      print(cls.__name__, len(r.parsed_text or '') if r else 'None')
  "
  ```
- Both should return ≥ 1000 chars. If one returns ~150 chars (a 404 soft-error) or None, the resolver is wrong; rebuild the index or re-check coverage.

### "Validator refuses but the source is fine"
- Open the most-recent debug blob: `evals/vigencia_extraction_v1/_debug/<norm_id>.json`.
- Look at `raw_output` — that's what Gemini actually returned. If the shape diverges from the prompt's literal example, tighten the prompt with a more pointed rule for the specific failure. Don't loosen the parser — bad data through the gate is worse than a refusal.

### "All A1 norms ran in 4 minutes — way too fast for real Gemini calls"
- That's the failure mode where the harness short-circuits at "missing_double_primary_source" before even calling Gemini. Check: `evals/vigencia_extraction_v1/audit.jsonl` should have wall-time-ish entries; if every refusal is sub-50ms, the harness never reached Gemini. That signals a scraper bug (cache cold, URL wrong, SSL fail) — NOT a Gemini problem.

## Network / SSL / cert facts (linked from `docs/learnings/sites/`)

- **Senado port 443**: unreachable from this network. **Use HTTP (port 80).** The site does not redirect HTTP→HTTPS for the basedoc paths.
- **SUIN cert**: Sectigo Public Server CA EV R36, valid through Dec 2026. Trust requires `certifi`'s CA bundle; Python's macOS default doesn't include the chain. The base scraper now uses certifi automatically.
- **DIAN normograma**: HTTPS works fine; certifi resolves it. The full-ET page is 3.9 MB and must be sliced before passing to Gemini.
- **Corte Constitucional + Consejo de Estado**: HTTPS works fine; certifi resolves them. Coverage matters only for `sentencia.cc.*`, `auto.cc.*`, `sentencia.ce.*`, `auto.ce.*` norm_ids — not ET articles.

See `docs/learnings/sites/<site>.md` for the per-site detail.

## Cost note

Even though A1 had 0 veredictos, every refusal that came from Gemini
(the `INSUFFICIENT_PRIMARY_SOURCES` and `invalid_vigencia_shape:*` ones)
DID consume Gemini API calls. The harness short-circuit refusals
(`missing_double_primary_source`) did NOT — those refuse before the
network call. For the next run with proper slicing, expect every norm
to consume one Gemini call.

## What "next batches flow better" means going into A1 re-run

1. **DIAN slicing is in.** Each ET article gets its own ~5 KB blob.
2. **Senado HTTP + corrected URL pattern is in.** Index lookup works.
3. **certifi + retries + browser UA in base.** SUIN + future sites benefit.
4. **Prompt has literal JSON example + hard rules.** The shape errors
   should drop materially.
5. **Debug blobs persist on validation failure.** Triage cycle is now
   read-from-disk, not re-extract.

If A1 re-run still gets > 25% refusals, open every `evals/vigencia_extraction_v1/_debug/*.json` from the run, group by error message, and add the next round of prompt rules with literal examples for those specific shapes. Do this in the prompt, not in the parser.

## Update — A1 launch #3 in flight (10:35 AM Bogotá)

The five fixes worked. First veredicto landed cleanly: `et.art.555-2 = VM`,
with proper `change_source.type = "reforma"`, valid `state_from = "2021-09-14"`,
and a well-formed `modificado_por` list (Ley 2010/2019 + Ley 2155/2021).

But a new pattern surfaced almost immediately: **Gemini invents
`change_source.type` values not in the v3 enum**. Observed so far:

- `'compilacion'` (et.art.555 — Gemini probably saw a DUR reference)
- `'adopcion'` (et.art.556 — likely a sustitución de texto)
- `'jurisprudencia'` (et.art.557 — Gemini conflating sentencia_cc with a generic "jurisprudencia")

The v3 enum (`ChangeSourceType` in `src/lia_graph/vigencia.py`) is strict and
allows: `reforma`, `derogacion_expresa`, `derogacion_tacita`, `sentencia_cc`,
`auto_ce_suspension`, `sentencia_ce_nulidad`, `reviviscencia`, `vacatio`,
`concepto_dian_modificatorio`, `modulacion_doctrinaria`. **Nothing else.**

**Fix landed** (will take effect on launch #4): the prompt now explicitly
enumerates these 10 values with one-line semantics each, plus an explicit
"NEVER invent new types like `compilacion`, `adopcion`, `sustitucion`"
rule. Same pattern: tighten the prompt, don't loosen the parser.

Also added explicit enumerations for `effect_type` (4 values) and
`applies_to_kind` (3 values) in the same prompt — pre-empting similar
invention patterns we'd otherwise discover one batch at a time.

## Suggested next-prompt-iteration triggers

Add another rule to the prompt when the next run surfaces:

- A new `change_source.type` value not in the enum.
- A new `effect_type` value not in `{pro_futuro, retroactivo, diferido, per_period}`.
- A new `applies_to_kind` value not in `{always, per_year, per_period}`.
- A new shape mismatch on `modificado_por`, `derogado_por`, `suspension`,
  `inexequibilidad`, `regimen_transicion`, or `fuentes_primarias_consultadas`.

The debug-blob file gives you the literal Gemini output to base the new
rule on. Group blobs by error string; the largest cluster is the next
rule.
