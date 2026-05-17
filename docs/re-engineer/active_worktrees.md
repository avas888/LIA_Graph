# Active worktrees roster

> Created by `docs/re-engineer/fix/fix_v22_may.md §9b.4 P2-T-Hygiene-3`. Lives at the canonical path teammates check during the stale-fix-doc audit (`§9b.3 #4`). Empty roster is the steady state.

## Rules of the road (mirror of `CLAUDE.md` Non-Negotiables → "Worktree + commit hygiene")

- Every worktree session ends with **land**, **snapshot+discard**, or **park with ETA** — no fourth option.
- A row in the roster below ONLY appears for the **park** outcome. Landed and snapshotted worktrees leave no trace here.
- An undated park row is invalid and will be auto-removed.
- Any row whose `Auto-discard after` date has passed is treated as abandoned — operator removes the worktree without further confirmation per `§9b.1 #1`.
- A worktree branch must NEVER outlive the worktree itself (`§9b.1 #3`).
- A lock owned by a dead PID is a stale lock, not a signal to preserve (`§9b.1 #2`).
- Live PID lock is honored; investigate before any forced removal.

## Audit cadence

- **At every v(NN+1) opening:** P1 of the next fix doc runs `git worktree list` + reads this file. Surfaces:
  - Rows past their `Auto-discard after` date.
  - Branches in `git branch --list` with no matching worktree.
  - Fix docs whose §⏯ "Last completed step" is older than 14 days and not at `✅`.
- **On every session start:** the operator scans this file before spinning a new worktree, to verify no in-flight work blocks the new branch.

## Park-row schema

| Worktree path | Branch | Slug | Operator | Parked on | Auto-discard after | Why parked | Resume recipe |
|---|---|---|---|---|---|---|---|

(empty — no parks open as of 2026-05-17)
