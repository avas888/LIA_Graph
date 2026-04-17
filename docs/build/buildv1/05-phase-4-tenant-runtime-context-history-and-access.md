# 05 — Phase 4: Tenant Runtime Context, History and Access

## Status

- `phase_id`: 4
- `status`: PLANNED
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T00:00:00-04:00
- `depends_on`: phases 1 to 3 complete
- `exit_criteria`:
  - tenant/company context influences answers without leakage
  - runtime context scope is bounded and documented
  - interaction history and company context can be persisted and reused
  - tenant separation stays in runtime and does not fork the corpus

## Intent

- objetivo de la fase: lograr day-1 multi-tenancy correcta sin convertir al tenant en una particion de conocimiento
- valor de negocio: preserva historial, permisos y contexto empresarial reusable sin duplicar el corpus
- superficies afectadas:
  - tenant isolation
  - company scoping
  - conversation memory
  - runtime traceability

## Implementation Scope

### Entra

- integracion con company context
- reglas de acceso y aislamiento
- historial conversacional y chat runs por tenant
- uso de company context y metadatos de interaccion en el motor compartido

### No Entra

- corpus por tenant
- grafo de conocimiento por tenant
- retrieval de documentos distintos por tenant

## RBAC Alignment With Lia Contadores

El shell de producto debe heredar de `Lia_Contadores` las reglas maduras de acceso, invitaciones y administracion de tenants, pero sin reinterpretar el conocimiento como multi-tenant.

### Invariantes operativos

- los roles base siguen siendo `tenant_user`, `tenant_admin` y `platform_admin`
- `tenant_user` consume producto; no administra usuarios, tenants ni ops
- `tenant_admin` administra usuarios e invitaciones dentro de su tenant
- `platform_admin` administra tenants y puede operar cross-tenant
- el corpus y el grafo siguen siendo compartidos; RBAC controla runtime y superficies de administracion, no particiones de conocimiento

### Seed parity que se debe preservar

- mantener los 10 usuarios autorizados `@lia.dev` ya sembrados en las migraciones
- `admin@lia.dev` debe seguir siendo `platform_admin`
- `admin@lia.dev` es el usuario que destraba la shell administrativa completa y debe seguir viendo tabs criticos como Backstage, Activity, Ingesta, Orchestration, Ratings y API
- los usuarios `usuario1@lia.dev` a `usuario10@lia.dev` siguen siendo el set de prueba autorizado para validar login, invitaciones y aislamiento por rol

### Fuentes de verdad actuales

- `supabase/migrations/20260325000002_seed_platform_users.sql`
- `supabase/migrations/20260405000002_seed_test_users_shared_password.sql`
- `supabase/migrations/20260408000002_seed_users_4_to_10.sql`
- `src/lia_graph/platform_auth.py`
- `src/lia_graph/user_management.py`
- `src/lia_graph/ui_user_management_controllers.py`
- `frontend/src/shared/auth/tabAccess.ts`

### Regla de diseño

- copiar el comportamiento de shell/RBAC de `Lia_Contadores`
- no copiar ninguna suposicion de corpus por tenant
- cualquier permiso extra para ingestion, Falkor o promotion debe modelarse como capacidad administrativa sobre un corpus compartido, no como ownership de un subgrafo por tenant

## Files To Create

- nuevas migraciones para contexto runtime si se requieren - nuevas

## Files To Modify

- `src/lia_graph/contracts/company.py` - existente
- `src/lia_graph/access_guardrails.py` - existente
- `src/lia_graph/conversation_store.py` - existente
- `src/lia_graph/ui_chat_persistence.py` - existente
- `src/lia_graph/user_management.py` - existente

## Tests For This Surface

### Unitarias

- company-context scoping
- persistence y reload de contexto runtime
- tenant guardrails

### Integracion

- tenant isolation end to end
- historial y chat runs aislados por tenant
- reuse de company context en consultas sobre el corpus compartido

### Smoke/Eval

- no cross-tenant leakage
- contextual answer quality en escenarios representativos

## Execution Steps

1. Definir el alcance del runtime context multi-tenant.
2. Integrar company context y access guardrails.
3. Alinear historial, chat runs y persistence con el motor compartido.
4. Resolver como el planner y composer consumen contexto de empresa e interaccion.
5. Validar persistencia y reutilizacion de contexto aprobado.

## Checkpoint Log

- `current_step`: 0
- `completed_steps`: []
- `blocked_by`: ["phase 3 no ejecutada"]
- `artifacts_created`: ["docs/build/buildv1/05-phase-4-tenant-runtime-context-history-and-access.md"]
- `notes`: "Esta fase protege la multi-tenancy del producto sin introducir corpus o grafo por tenant."

## Failure Recovery

- como retomar:
  - revisar si las migraciones de contexto runtime existen
  - verificar si el planner ya consume company context
  - confirmar que los tests de tenant isolation siguen pasando
- que verificar antes de continuar:
  - reglas de acceso
  - modelo de company context
  - estrategia de persistencia de historial y runtime context

## Open Questions

- si company context debe entrar completo al planner o como un resumen derivado
- si parte del historial reciente debe resumirse antes de entrar al motor compartido

## Decision Log

- no se construira corpus ni grafo de conocimiento por tenant
- tenant significa aislamiento de runtime, no particion de conocimiento
