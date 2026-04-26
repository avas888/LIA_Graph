# Asymmetric corpus-mutation safety: add via GUI, retire via CLI only

> **Captured 2026-04-26** at the close of the additive-delta safety pass. Pattern lives in `src/lia_graph/ingestion/delta_runtime.py::materialize_delta` (parameter `allow_retirements: bool = False`). Triggered by an operator question on a live preview that showed `RETIRADOS=5` from an upload-only intent.

## The operator directive (binding)

> *"Lo que ya entra al corpus debe salir por CLI; no por 'volver a cargar un corpus' más débil. Si ya está en DB Supabase + Falkor en la nube, el borrado de un archivo debe ser absolutamente explícito. Para adicionar debe ser un procedimiento más ameno."*

Translated: **adding to the cloud corpus is the friendly path; deletion is the deliberate one.** A GUI button must never be one click away from soft-retiring production docs.

## The footgun this closes

The additive-delta planner (`delta_planner.plan_delta`) computes a **set diff** between the on-disk `knowledge_base/` and the published Supabase baseline. Anything in the baseline but missing on disk lands in the `removed` bucket; the sink's Pass 2 then soft-retires those rows + hard-deletes their chunks/edges, and the Falkor plan emits `DETACH DELETE` for their article keys.

Locally-canonical disk works fine when a single operator on a single machine owns `knowledge_base/`. But every one of these very common conditions makes the diff lie:

1. **Different machine.** Operator runs the additive flow from their laptop without first pulling the latest `knowledge_base/` from Dropbox / git / Drive. The 50 docs they don't have locally look "removed" to the planner — but they're actively serving in production.
2. **Partial sync.** Dropbox is mid-download, or a sync conflict left some files in `.conflict-…` paths the audit ignores. Same outcome.
3. **Scratch directory.** A test run pointed at a smaller `knowledge_base/` (e.g. a 50-doc fixture) and forgot to point back. Without the safety, that fixture defines "what should exist."
4. **File-system corruption / accidental rm.** Anything that silently shrinks the disk corpus.

In every case, the operator's intent was "add 3 new docs" — never "retire 50." A naïve apply would silently delete production data.

## The pattern

Asymmetric defaults at the function boundary:

```python
def materialize_delta(
    *,
    # ... lots of plumbing …
    allow_retirements: bool = False,
) -> DeltaRunReport:
    # … plan delta, compute summary, build report …

    # Asymmetric safety per operator directive (2026-04-26).
    diagnostic_removed_count = len(delta.removed)
    if not allow_retirements and diagnostic_removed_count > 0:
        emit_event(
            "ingest.delta.retirements.blocked",
            {
                "delta_id": delta.delta_id,
                "would_retire_count": diagnostic_removed_count,
                "reason": "allow_retirements=False (GUI default)",
            },
        )
        # CorpusDelta is frozen; mirror existing object.__setattr__ pattern.
        object.__setattr__(delta, "removed", ())

    report = DeltaRunReport(
        # …
        retirements_allowed=bool(allow_retirements),
        diagnostic_removed_count=int(diagnostic_removed_count),
    )
```

Three non-negotiable properties:
1. **The summary still shows the count** so the operator sees what would have been retired (visibility, not invisibility).
2. **The downstream sink + Falkor never see the removed bucket** when `allow_retirements=False`. They produce zero retirement statements. There's no "but this branch could…" — the data they consume is empty.
3. **The default is False.** Caller has to type True. There is no "convenience" call site that auto-enables.

## Where the default flips

Only one call site flips True: the CLI flag that the operator types by hand.

```bash
lia-graph-artifacts --additive --allow-retirements [...]
```

`--allow-retirements` is documented in `src/lia_graph/ingest.py` parser. Default is False. The operator must type the flag — there's no env var, no config file, no scheduled job that supplies it.

Every other call site uses the False default:

| Caller | `allow_retirements` |
|---|---|
| `ui_ingest_delta_controllers._handle_preview` (`/api/ingest/additive/preview`) | not passed → False |
| `ingestion/delta_worker._run_delta_worker` (`/api/ingest/additive/apply`) | not passed → False |
| Any future HTTP handler / background job / scheduled script | **must** stay False |
| CLI `--additive` without `--allow-retirements` | False |
| CLI `--additive --allow-retirements` | True |

If you build a new ingestion entrypoint, default `allow_retirements=False` and only flip True when the call site is an explicitly-typed CLI command — **never** an HTTP handler, never a button, never a script that runs unattended. If automated retirement ever becomes a genuine product need, design a separate flow with explicit per-doc intent (named doc_id manifest + operator confirmation), not a piggyback on additive-delta.

## Where the user sees this

`frontend/src/shared/ui/molecules/additiveDeltaBanner.ts` relabels the bucket:

| Before | After |
|---|---|
| Title: **"Retirados"** | Title: **"Faltan en disco (no se retiran)"** |
| Tone: `error` (red) | Tone: `warning` (yellow) |
| Description: *"Documentos que ya no existen en disco."* | Description: *"Estos archivos están en la base publicada pero no en disco. Por seguridad, este flujo NO los retira de Supabase + Falkor. Si genuinamente querés retirarlos, hacelo por CLI explícito: `lia-graph-artifacts --additive --allow-retirements`."* |

Card body copy (`additiveDeltaCard.ts`) carries the same contract above the action row, BEFORE the operator clicks Previsualizar:

> Compara `knowledge_base/` contra la base ya publicada y procesa **solo agregados y modificados**. Los archivos llegan a la carpeta en el **Paso 1 arriba** (arrastre, Dropbox o editor directo). **Nunca retira docs de producción**: si un archivo está en la base pero falta en disco, este flujo lo marca como diagnóstico y sigue. El borrado de cloud es CLI-only y explícito (`--allow-retirements`).

## Why surface the count even though we won't act on it

Visibility prevents the silent-drift failure mode. If the diagnostic shows `RETIRADOS = 0`, the operator knows their local disk is in sync with cloud. If it shows `RETIRADOS = 50`, they know to investigate (probably pull the latest sync, or run the CLI explicitly if they really want to retire).

Hiding the bucket would create a worse failure: operators wouldn't know their disk was drifting from cloud until something else surfaced it (a chat answer missing context, a parity-check mismatch, a confused SME).

## What this is NOT

- **Not a feature flag.** There's no env var to turn this off. The asymmetric default is a permanent contract.
- **Not "safe mode" with an opt-out toggle in the UI.** No GUI affordance flips it. The GUI surface is structurally incapable of retiring.
- **Not a deferral / TODO.** Retirement IS supported — it just lives on the CLI surface where the operator's intent is unambiguous (they typed the flag).

## Companion cut

The same cycle removed the **"Análisis profundo"** GUI button, for a parallel reason: it was a button that did expensive work whose results couldn't be applied through the same card (`Aplicar` uses the content-hash shortcut and ignores the deep-preview's reclassifications). Operators clicking it expected `Aplicar` to commit what they saw, but it didn't. Same family of bug as silent retirement: the GUI affordance suggested an action that the underlying flow couldn't honor.

The corrected pattern: **a GUI button means exactly what it says, with no surprising downstream "but actually…" semantics.** If the action a button claims to do can't be executed by the surface that hosts it, remove the button or move the action to a surface that CAN execute it.

## Cross-references

- Code: `src/lia_graph/ingestion/delta_runtime.py::materialize_delta`, `src/lia_graph/ingest.py` (`--allow-retirements` flag), `frontend/src/shared/ui/molecules/additiveDeltaBanner.ts` (yellow diagnostic), `frontend/src/shared/ui/organisms/additiveDeltaCard.ts` (body copy).
- Non-negotiable in `CLAUDE.md` and `AGENTS.md` (2026-04-26 entries).
- Env-matrix change-log: `docs/guide/orchestration.md` row `v2026-04-26-additive-no-retire`.
- GUI ingestion learnings catalog: `docs/done/next/gui_ingestion_v1.md §15`.
