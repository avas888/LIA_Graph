# TASK-04: Deploy & Shadow Mode

> **Status**: NOT STARTED
> **Depends on**: TASK-03 complete (eval shows Pipeline D ≥ Pipeline C)
> **Produces**: Production deployment with shadow mode

---

## Last Checkpoint

```
step: 0
description: Task not yet started
next_action: Create Railway service config
artifacts_produced: none
```

---

## Steps

### Step 1: Railway Service Config
- Separate Railway service for LIA_Graph
- Environment variables: Supabase URL/key, FalkorDB URI, OpenAI key
- Health check endpoint: `/health` (includes graph connectivity)

### Step 2: Shadow Mode
- `X-Lia-Pipeline: dual` runs both pipelines
- Pipeline C response served to user
- Pipeline D response logged to `shadow_responses` table
- Async comparison job scores both responses

### Step 3: Per-Tenant Beta
- Feature flag: `pipeline_d_enabled` on tenant row
- Selected tenants see Pipeline D responses
- Others continue with Pipeline C
- Rollback: flip flag back

### Step 4: Default Flip
- When Pipeline D metrics ≥ Pipeline C across all tenants:
  - Default changes to Pipeline D
  - Pipeline C becomes fallback
  - `X-Lia-Pipeline: c` header for explicit Pipeline C access

---

## Resumption Guide

If this task is interrupted:
1. Check `last_checkpoint.step` above
2. Deployment is atomic — either deployed or not
3. Shadow mode is non-destructive — can be toggled without risk
4. Feature flags are instant rollback
