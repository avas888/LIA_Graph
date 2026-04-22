# Memo de curaduría — Revisión de 565 documentos marcados por PASO 4

**Fecha:** 21 de abril de 2026
**Scope:** `flagged_for_curator_review.csv` (565 filas)
**Taxonomía base:** `config/subtopic_taxonomy.json` v2026-04-21-v1
**Decisor:** curator-decisions-abril-2026 (auto + revisión humana)

---

## 1. Distribución de acciones

| Acción | Qué es | Filas | % |
|---|---|---:|---:|
| (a) Alias a subtopic existente | Ampliar `aliases[]` en JSON para que el backfill los absorba | 127 | 22,5% |
| (b) Subtopic nuevo | Crear entrada nueva en taxonomy con label + 3-6 aliases semilla | 69 | 12,2% |
| (c) Batch-inherit por patrón | `UPDATE ... WHERE relative_path LIKE ...` sobre triplets NORMATIVA/EXPERTOS/LOGGRO | 353 | 62,5% |
| (d) Excluir del corpus | Assets binarios (`.svg`/`.json`) + leyes derogadas | 16 | 2,8% |

**Lectura rápida:** 62,5% de los flagged son un mismo hallazgo estructural (LEYES/OTROS_SECTORIALES) que se resuelve con **un solo UPDATE SQL**. El trabajo real está en las 196 filas restantes de (a)+(b).

---

## 2. Hallazgos estructurales (y qué haría yo sobre el clasificador, no sólo sobre la taxonomía)

### 2.1 El "flood" de `otros_sectoriales` (353 filas = 62,5% del backlog)

Todas las 353 filas están bajo `CORE ya Arriba/LEYES/OTROS_SECTORIALES/{consolidado,EXPERTOS,LOGGRO,NORMATIVA}/Ley-XXXX-YYYY.md`. El clasificador las rutea a `otros_sectoriales` correctamente en PASO 1 — pero cae en PASO 4 porque el catch-all `cumplimiento_normativo_sectorial_pymes` no tiene alias por número de ley.

**Decisión:** batch-inherit al catch-all. Un solo SQL hace todo:

```sql
UPDATE documents
SET subtema = 'cumplimiento_normativo_sectorial_pymes'
WHERE relative_path LIKE '%/LEYES/OTROS_SECTORIALES/%'
  AND subtema IS NULL;
```

**Recomendación al pipeline:** agregar una regla de PASO 4 pre-LLM: si `parent_topic == 'otros_sectoriales'` y la taxonomía tiene un único subtopic catch-all con `evidence_count > 100`, auto-asignar sin llamar al LLM. Se ahorran ~350 llamadas cada vez que ingestamos leyes sectoriales nuevas.

### 2.2 PASO 1 está confundiendo coincidencias numéricas con parent_topic (39 correcciones)

El clasificador tiene una heurística que mira substrings numéricos en `relative_path` y los mapea a topics como `iva`, `ica`, `reformas_tributarias`, etc. Eso produce 39 misrouteos:

| Misroute | Casos | Causa raíz |
|---|---:|---|
| `procedimiento_tributario → otros_sectoriales` | 6 | Ley 1438/2011 (salud) y Ley 1474/2011 (anticorrupción) están en carpeta PROCEDIMIENTO_FISCAL pero NO son procedimiento tributario |
| `comercial_societario → otros_sectoriales` | 4 | Ley 1480/2011 (Estatuto del Consumidor) es SIC, no societario |
| `iva → inversiones_incentivos` | 4 | `NORMATIVA_LEYES/II-1429-2010-NORMATIVA.md` — el "II-" es prefijo de Inversiones Incentivos; el clasificador lo lee como "IVA" |
| `iva → declaracion_renta` | 3 | Libros del ET (`01_Libro1_T1_Sujetos_Pasivos.md`, etc.) — el clasificador ve "1" y dispara IVA |
| `ica → *` | 6 | TODAS las filas etiquetadas `ica` son falsos positivos — ninguna es sobre ICA. El patrón "ICA" aparece en nombres como `FISCALIZACION_DIAN` (FI-...) o similar |
| `iva → presupuesto_hacienda` | 2 | `PH-225-1995-NORMATIVA.md` y similar — "PH-" es Presupuesto/Hacienda, no IVA |
| `iva → procedimiento_tributario` | 2 | `PF-1437-2011-NORMATIVA.md` — "PF-" es Procedimiento Fiscal |
| `estados_financieros_niif → presupuesto_hacienda` | 3 | Ley 1530/2012 (Sistema General de Regalías) está mal archivada en NIIF_CONTABLE |
| `comercial_societario → reformas_tributarias` | 1 | Ley 223/1994 es reforma tributaria |
| `comercial_societario → presupuesto_hacienda` | 1 | Ley 1151/2007 es el Plan Nacional de Desarrollo 2006-2010 |
| `datos_tecnologia → declaracion_renta` | 1 | `seccion-28-casos-practicos.md` fue archivado bajo LOGGRO/RENTA pero se coló como DT |

**Recomendación al pipeline (mayor palanca):** reescribir el prompt de PASO 1 para que **no** use substrings del path como señal fuerte. Los prefijos de carpeta (`DT-`, `II-`, `PF-`, `PH-`, `NC-`, `RET-`, `PAT-`, `GMF-`, `FE-`, `RUT-`, `DON-`, `ZF-`) son el mejor indicador — pero el path completo confunde al clasificador cuando coincide con números de leyes.

**Alternativa más simple:** tabla de lookup `prefix → parent_topic` que se aplica antes del LLM cuando el prefijo es conocido (zero-shot correcto en ~20% de los docs).

### 2.3 `form_guides/*` nunca debería haber entrado al graph-parse (14 filas)

Los 14 assets en `form_guides/formulario_*/(assets/page_*.svg | *.json)` son:
- `page_02.svg`, `page_06.svg` — imágenes rasterizadas/vectoriales de los formularios.
- `guide_manifest.json`, `structured_guide.json`, `sources.json`, `interactive_map.json`, `citation_profile.json` — manifiestos estructurales sin prosa.

**Recomendación al pipeline:** filtro de admisión antes del graph-parse:

```python
EXCLUDED_EXTENSIONS = {'.svg', '.png', '.jpg', '.jpeg', '.pdf.raw'}
EXCLUDED_FILENAMES = {'guide_manifest.json', 'structured_guide.json', 'sources.json',
                      'interactive_map.json', 'citation_profile.json'}
if any(p.endswith(ext) for ext in EXCLUDED_EXTENSIONS): skip()
if path.name in EXCLUDED_FILENAMES: skip()
```

### 2.4 Leyes derogadas todavía están en el corpus (2 filas)

`Ley-52-1975.md` y `Ley-1-1976.md` en `LEYES/DEROGADAS/` son explícitamente históricas. Según la regla de anti-contaminación del `CLAUDE.md` ("si no tiene vigencia, no existe en el corpus"), deben eliminarse.

**Recomendación:** mover `LEYES/DEROGADAS/` fuera del path de ingesta (a un `_archive/` al mismo nivel).

---

## 3. Decisiones por tema (detalle)

### 3.1 Subtopics nuevos propuestos (20 entries)

Ver `new_subtopics.json`. Los más impactantes:

| Full key | Parent | Por qué |
|---|---|---|
| `activos_exterior.declaracion_activos_exterior_formulario_160` | activos_exterior | Parent topic sin subtopics; Formulario 160 tiene calendario y sanciones propios |
| `gravamen_movimiento_financiero_4x1000.marco_legal_gmf_4x1000` | GMF | Parent topic sin subtopics |
| `impuestos_saludables.impuestos_saludables_ibua_icui` | impuestos_saludables | Parent topic sin subtopics; IBUA/ICUI arts 513-1 a 513-13 ET |
| `laboral.reforma_laboral_ley_2466_2025` | laboral | Reforma laboral 2025 — alto impacto en nómina 2026 |
| `procedimiento_tributario.cpaca_ley_1437_2011` | procedimiento_tributario | CPACA = base supletoria del procedimiento tributario |
| `procedimiento_tributario.codigo_general_proceso_ley_1564_2012` | procedimiento_tributario | CGP = base de procesos ejecutivos (cobro coactivo DIAN) |
| `otros_sectoriales.anticorrupcion_sagrilaft_ley_1474_2011` | otros_sectoriales | Base de SAGRILAFT/PTEE — obligación para empresas SuperSociedades |
| `otros_sectoriales.estatuto_consumidor_ley_1480_2011` | otros_sectoriales | Estatuto del Consumidor (SIC) |
| `inversiones_incentivos.fnce_ley_1715_2014_energia_renovable` | inversiones_incentivos | Deducción renta + exclusión IVA energía renovable |
| `inversiones_incentivos.transicion_energetica_ley_2099_2021` | inversiones_incentivos | Amplía Ley 1715; hidrógeno verde |
| `inversiones_incentivos.progresividad_ley_1429_2010_formalizacion` | inversiones_incentivos | Progresividad renta todavía aplicable a acogidos |
| `inversiones_incentivos.ley_paez_218_1995` | inversiones_incentivos | Incentivo regional histórico con vigencia residual |
| `datos_tecnologia.teletrabajo_ley_1221_2008` | datos_tecnologia | Marco teletrabajo — afecta parafiscales |
| `datos_tecnologia.regulacion_tic_ley_1341_2009` | datos_tecnologia | Régimen contributivo MinTIC |
| `declaracion_renta.incentivos_regionales_zomac_zese` | declaracion_renta | Régimen de tarifa progresiva ZOMAC/ZESE |
| `declaracion_renta.depreciacion_fiscal_pyme` | declaracion_renta | Divergencia NIIF/fiscal en depreciación |
| `comercial_societario.regimen_mipyme_ley_590_905` | comercial_societario | Clasificación MiPyME base |
| `comercial_societario.regimen_emprendimiento_ley_2069_2020` | comercial_societario | Sociedades BIC + compras públicas MiPyME |
| `presupuesto_hacienda.sistema_general_regalias_ley_1530_2012` | presupuesto_hacienda | SGR — afecta contratación con entidades territoriales |
| `informacion_exogena.recurso_sancion_exogena_art_651_ET` | informacion_exogena | Módulo defensivo con procedimiento propio |

### 3.2 Aliases agregados a subtopics existentes (15 subtopics, 127 alias nuevos en total)

Ver `alias_additions.json`. Los mayores absorbedores:

| Subtopic | Aliases nuevos | Motivo |
|---|---:|---|
| `reformas_tributarias.reforma_tributaria_gmf_y_facturacion` | ~14 | Una alias por cada Ley histórica de reforma (1111/2006, 1430/2010, 1607/2012, 1739/2014, 1819/2016, 1943/2018, 2010/2019, 2155/2021, 2277/2022, 223/1995, 49/1990, 6/1992, 75/1986, 863/2003, 488/1998) |
| `laboral.aporte_parafiscales_icbf` | ~12 | Una alias por cada Ley laboral no-2466 (1010/2006, 1468/2011, 1822/2017, 21/1982, 2101/2021, 27/1974, 50/1990, 789/2002, 797/2003) |
| `declaracion_renta.declaracion_de_renta_personas_juridicas` | ~12 | Alias por cada sección 07-27 LOGGRO del flujo renta PJ |
| `emergencia_tributaria.exenciones_tributarias_covid_19` | 1 | Alias amplia `emergencia_tributaria_decretos_1474_0240_2025_2026` (nota: **renombrar el subtopic** eventualmente — el nombre actual sigue siendo COVID) |

### 3.3 Correcciones de parent_topic (39 filas)

Ver `parent_topic_corrections.sql`. Todas son `UPDATE documents SET parent_topic_key = ... WHERE relative_path = ...` con path exacto (no LIKE — para evitar afectar filas no-flagged que ya están bien).

### 3.4 Batch inherit (353 filas, 1 UPDATE)

Ver `batch_inherit.sql`. Un solo `UPDATE` cubre todas las filas de LEYES/OTROS_SECTORIALES.

### 3.5 Exclusiones (16 filas)

Ver `exclusions.txt`. 14 `form_guides/*` + 2 `LEYES/DEROGADAS/*`.

---

## 4. Orden de ejecución recomendado

1. **Aplicar correcciones de parent_topic** (`parent_topic_corrections.sql`) — 39 filas. **Primero**, porque los aliases y nuevos subtopics se emparejan con el parent_topic, así que hay que corregirlo antes del backfill.
2. **Mergear `alias_additions.json` y `new_subtopics.json` en la taxonomía** (escribir script `taxonomy_merge.py` o hacerlo a mano según tu flow).
3. **Correr backfill de PASO 4** — los 127 filas de (a) y 69 filas de (b) se auto-resuelven porque los aliases ya están.
4. **Aplicar `batch_inherit.sql`** — 353 filas de (c). Esto es redundante si el backfill con el catch-all ya las atrapó, pero el SQL es idempotente (`AND subtema IS NULL` es el guardrail).
5. **Borrar las 16 filas de `exclusions.txt`** — `DELETE FROM documents WHERE relative_path IN (...)`. Y mover los archivos fuera del pipeline de ingesta.

---

## 5. Seguimiento (qué agregar al pipeline para evitar que vuelva a pasar)

1. **Tabla de prefijos de carpeta → parent_topic.** Hoy el clasificador infiere el parent por heurísticas. Hay una señal mucho más fuerte: el prefijo de nombre de archivo (`DT-`, `II-`, `PF-`, `PH-`, `NC-`, `RET-`, `PAT-`, `GMF-`, `FE-`, `RUT-`, `DON-`, `ZF-`, `L-XX-`, `N-XX-`, `T-XX-`). Mapearlo a parent_topic elimina la mayoría de misrouteos sin tocar el LLM.

2. **Filtro de admisión para `form_guides/*` binarios.** Ver §2.3.

3. **Regla "catch-all auto-assign"**: si el parent_topic tiene un único subtopic con evidence_count > 100, autoasignar en PASO 4 sin llamar al LLM.

4. **Renombrar el subtopic `emergencia_tributaria.exenciones_tributarias_covid_19`** a algo más neutral tipo `emergencia_tributaria_decretos_transitorios`. El nombre actual es histórico (COVID-19) pero el subtopic ahora absorbe Decretos 1474/2025 y 0240/2026.

5. **Renombrar el subtopic `impuesto_patrimonio_personas_naturales.impuesto_al_patrimonio_excepcional_2011`** a `impuesto_patrimonio_personas_naturales_permanente`. El nombre "excepcional_2011" es histórico; el impuesto actual es permanente desde Ley 2277/2022.

6. **Mover `LEYES/DEROGADAS/` fuera del path de ingesta.** `_archive/LEYES_DEROGADAS/` al mismo nivel del repo.

7. **Auditoría trimestral de catch-alls con `evidence_count > 150`**: cuando un catch-all absorbe demasiado, la calidad de retrieval se degrada. Vale la pena bajar `cumplimiento_normativo_sectorial_pymes` (232 + 353 = 585 post-backfill) a subtopics por sector (ej. `agropecuario`, `salud`, `servicios_publicos`, `deportes_cultura_recreacion`, `minero_energetico`, `transporte`) en una segunda iteración.

---

## 6. Archivos generados

- `decisions.csv` — 565 filas, una decisión por doc, con rationale.
- `alias_additions.json` — patches de aliases (case a).
- `new_subtopics.json` — 20 entradas nuevas de taxonomía (case b).
- `parent_topic_corrections.sql` — 39 UPDATEs de parent_topic.
- `batch_inherit.sql` — 1 UPDATE masivo para 353 docs otros_sectoriales.
- `exclusions.txt` — 16 paths a eliminar.
- `strategy-memo.md` — este documento.

---

**Último punto (opinión):** la taxonomía v2026-04-21-v1 está bien estructurada, pero 3 de los parent_topics (`activos_exterior`, `gravamen_movimiento_financiero_4x1000`, `impuestos_saludables`) estaban vacíos de subtopics — por eso sus docs cayeron a PASO 4. Tener al menos un subtopic seed por parent_topic desde el día 1 evitaría ese patrón. Lo mismo para parents futuros (cuando se abra `precios_transferencia` o `SIMPLE`).
