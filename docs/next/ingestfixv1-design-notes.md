# ingestfixv1 — Phase 4 Frontend Design Notes

## Visual language

The ingest admin surface lives under `Sesiones` and inherits the Lia Graph dark-navy chrome (`--chrome-bg: var(--p-navy-900)`) paired with a flat `--page-background: #dfe7f0` canvas. Panels are white cards (`--card-bg`) with `--card-border` hairlines; emphasis is carried by `--p-navy-800` interactive primaries and a narrow accent stripe (`--accent-bar: var(--p-blue-500)`). Typography is IBM Plex: `IBM Plex Sans` for body/label copy, `IBM Plex Mono` for identifiers, counts, paths, durations, and log output. Status tones come from the Tier-3 ops palette (`--p-success-*`, `--p-amber-*`, `--p-red-*`, `--p-blue-*`). No raw hex values ship from Phase 4 — every colour traces back to a Tier-1 primitive via a Tier-2/3 alias.

## Components

### atom — `createProgressDot`

- Purpose: single-character status indicator for one stage in the ingest pipeline (pending, running, done, failed). Complements `statusDot` but is tuned for pipeline lifecycle semantics rather than generic session status.
- Atoms used: none (leaf DOM).
- Token aliases:
  - pending → `--p-neutral-300` fill, `--p-neutral-150` halo
  - running → `--p-blue-500` fill, `--p-neutral-100` halo, pulse via keyframes on `--p-blue-500`
  - done → `--p-success-600` fill, `--p-success-100` halo
  - failed → `--p-red-600` fill, `--p-red-100` halo
- State variants: four enum values, `running` auto-receives the pulse class. Re-invoking the factory produces a fresh node per call (stateless factory).
- Interaction notes: decorative. `role="status"` is attached so assistive tech can announce the surrounding label; optional `aria-label` exposes the stage name when the dot is used standalone.

### atom — `createFileChip`

- Purpose: pill representation of an uploaded file within the drag-to-ingest staging tray. Shows a text-only extension token, truncated filename, formatted byte size, and an optional remove affordance.
- Atoms used: none.
- Token aliases: `--pill-bg`, `--pill-border`, `--text-primary`, `--text-tertiary` for size text, `--p-red-50`/`--p-red-600` for remove-button hover. Remove icon is the ASCII `x` glyph — no inline SVG.
- State variants: presence vs absence of the remove button (`onRemove` handler). Truncation is purely CSS (`text-overflow: ellipsis`) so the chip width stays stable regardless of filename length.
- Interaction notes: `title` carries the full "{filename} - {size}" for mouse hover; the remove button stops propagation so dropping it onto a row never triggers row-level handlers. `formatBytes` is exported for reuse by molecules/organisms that display file sizes outside a chip.

### molecule — `createIntakeFileRow`

- Purpose: one horizontal row in the staging tray. Surfaces the file chip plus topic detection metadata (label, confidence, coercion method) and flags files that need human review.
- Atoms used: `createFileChip`, `createBadge` (topic), `createChip` (confidence, requires-review marker).
- Token aliases: `--p-neutral-150` for the muted bottom divider; confidence pill inherits `--chip-ok-*` / `--chip-warn-*` / `--chip-error-*` through tone mapping (≥80% ok, ≥50% warn, else error); `--status-warning` solid for the requires-review marker; `--text-tertiary` for the monospace coercion indicator.
- State variants: every meta cell is conditional. Missing topic/confidence/coercion simply omits that element; `requiresReview=true` adds a solid amber chip; the last row of a group drops its divider via `:last-child`.
- Interaction notes: file chip forwards its own remove handler; topic badge carries `data-topic` so downstream filtering or analytics can read the raw detection key independent of the Spanish label.

### molecule — `createStageProgressItem`

- Purpose: one row in the live pipeline progress timeline. Pairs a progress dot with the stage label, canonical counts, wall-clock duration, and (on failure) an inline error callout.
- Atoms used: `createProgressDot`.
- Token aliases: labels use `--text-primary`; counts/duration use `--text-secondary`/`--text-tertiary` monospace; failed state recolors the label to `--status-error` and renders the error callout with `--status-error-soft` background and `--p-red-200` left border; done state tints the label with `--p-success-700`.
- State variants: four statuses inherited from the dot; error callout only renders when `status === "failed"` AND `errorMessage` is truthy; duration only renders when both timestamps parse cleanly and `finishedAt ≥ startedAt`.
- Interaction notes: counts dict is flat and order-independent. Rendering pulls the canonical keys `docs`, `chunks`, `edges`, `embeddings_generated` in that order, capped at three to avoid overflowing the row. Unknown keys are silently ignored — the controller remains the source of truth for which metrics matter.

### molecule — `createLogTailViewer`

- Purpose: collapsible, auto-scrolling log surface for the ingest job's stdout. Exposes imperative append/clear handles so the controller can stream SSE frames without re-rendering the whole component.
- Atoms used: none (composes native `<details>`, `<summary>`, `<pre>`, and a vanilla copy button).
- Token aliases: outer shell uses `--card-bg`/`--card-border`; inner log body uses the existing Tier-3 log tokens (`--corpus-log-bg`, `--corpus-log-fg`) so it visually matches the corpus lifecycle log pane; copy button mirrors the admin secondary button (`--panel-bg-strong` bg, `--border-default` border, `--p-neutral-100` hover).
- State variants: `autoScroll` governs whether `scrollTop` is pinned to `scrollHeight` after every append. Expanded/collapsed is inherited from the native `<details>` widget. `clear()` wipes internal state and the DOM body in one step.
- Interaction notes: copy reads from the internal buffer (not from the DOM) to avoid losing text that browsers collapse in `<pre>` reflows. It guards against SSR/headless environments where `navigator.clipboard` is undefined, and still fires `onCopy` so the controller can show a toast regardless. Auto-scroll is applied on mount so rehydrated sessions open at the tail.
