# Appendix C — State Template

Use this template inside every phase file and for ad-hoc execution notes.

```md
## Status

- `phase_id`:
- `status`:
- `owner`:
- `last_updated`:
- `depends_on`:
- `exit_criteria`:

## Intent

- objetivo de la fase:
- valor de negocio:
- superficies afectadas:

## Implementation Scope

### Entra

- 

### No Entra

- 

## Files To Create

- 

## Files To Modify

- 

## Tests For This Surface

### Unitarias

- 

### Integracion

- 

### Smoke/Eval

- 

## Execution Steps

1. 

## Checkpoint Log

- `current_step`:
- `completed_steps`:
- `blocked_by`:
- `artifacts_created`:
- `notes`:

## Failure Recovery

- como retomar:
- que verificar antes de continuar:

## Open Questions

- 

## Decision Log

- 
```

When the phase touches ingestion or corpus admission, also record:

- whether a corpus audit gate exists
- which audit artifacts are expected
- whether labels are mandatory, optional, or graph-derived for that phase
