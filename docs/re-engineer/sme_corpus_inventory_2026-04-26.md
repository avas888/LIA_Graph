# SME corpus inventory — top-24 normas (2026-04-26)

> **Source:** SME analysis pasted into operator session 2026-04-26 evening, in response to operator's request for "shortlist of documents safe to flag wholesale-derogated for Activity 1 surgical fix."
>
> **Reproduced verbatim** because this is the authoritative operational map of which laws actually load-bear in the LIA Graph product. Use it as the reference any time a fix proposes to mark a document/article as derogada, suspendida, or to deprioritize a corpus source.
>
> **Critical operational implication for Activity 1+:** **None of the 24 laws in this inventory should be wholesale-flagged as derogada.** The SME explicitly distinguishes:
> - **Normas vivas** (vigente in full — touched weekly): ET, Ley 2277/2022, DUR 1625/2016
> - **Normas con artículos sobrevivientes** (mostly derogated BUT key articles survive — must NOT wholesale-flag; need per-article granularity from Fix 1B): Ley 1819/2016, Ley 2010/2019, Ley 1607/2012
> - **Normas de andamiaje** (vigente; commercial / labor / professional support): Código de Comercio, CST, Ley 43/1990, Ley 9/1991
> - **Suspendido** (one entry — Decreto 1474/2025 — suspended by Auto 082/2026 of Corte Constitucional). **This is the ONLY candidate for wholesale `vigencia = 'suspendida'` flagging from this inventory.**
>
> Documents NOT in this inventory (e.g. `Ley-1429-2010.md`) are by SME's implicit signal "not operationally load-bearing" — flagging them is lower-risk because the corpus doesn't rely on them for vigente answers.

---

## Las leyes (y cuerpos de ley) más importantes del corpus

Ojo a una distinción que vale la pena hacer antes de la tabla: el corpus tiene **~52 leyes citadas**, pero no todas tienen el mismo peso operativo. Hay tres tipos:

1. **Normas vivas** que el contador toca cada semana (ET, Ley 2277/2022, DUR 1625/2016).
2. **Normas con artículos sobrevivientes** — leyes viejas cuya mayoría está derogada pero quedaron 2 o 3 artículos vigentes que seguimos citando (Ley 1819/2016, Ley 2010/2019, Ley 1607/2012).
3. **Normas de andamiaje** — soporte comercial, laboral o profesional (Código de Comercio, CST, Ley 43/1990).

La tabla siguiente está ordenada por **importancia operativa real**, no por jerarquía formal. El "título exacto del archivo" se refiere al nombre del archivo dentro del corpus donde la norma está más densamente referenciada (no necesariamente donde aparece el texto literal de la ley — el corpus es interpretativo, no es una compilación de textos legales).

| # | Norma / Cuerpo de ley | Por qué importa | Archivo del corpus donde está más densamente tratada |
|---|---|---|---|
| 1 | **Decreto 624/1989 — Estatuto Tributario (ET)** | Es el cuerpo central. Todas las 28 secciones del corpus son, en última instancia, lecturas operativas del ET. Sin esto, no hay corpus. | `seccion-02-marco-legal-vigente.md` (mapa general); `regulacion-referenciada-enriquecida.md` (inventario) |
| 2 | **Ley 2277/2022 — Reforma Tributaria "para la igualdad y la justicia social"** | Es la reforma estructural vigente. Modificó tarifa PJ al 35%, creó la TTD (par. 6 art. 240), reestructuró cédulas de PN, cambió tarifas de dividendos y de ganancia ocasional, redefinió zonas francas, introdujo PES, modificó descuentos. **Casi todo lo que LIA debe responder hoy depende de esta ley.** | `seccion-02-marco-legal-vigente.md` |
| 3 | **Ley 2294/2023 — Plan Nacional de Desarrollo 2022-2026** | Su art. 69 prorrogó el beneficio de auditoría (art. 689-3 ET) para AG 2024, 2025 y 2026 — el blindaje fiscal más usado por PYMEs en planeación tributaria. También modificó ZESE (art. 147). | `seccion-18-beneficio-de-auditoria.md` |
| 4 | **Decreto 1625/2016 — Decreto Único Reglamentario (DUR) Tributario** | Es la "constitución reglamentaria" del ET. Compila plazos, procedimientos, formatos, exclusiones, requisitos operativos. Cada norma reglamentaria nueva se incorpora aquí. Lo que en el ET es regla, en el DUR es operación. | `seccion-06-calendario-tributario.md`; `seccion-22-saldos-a-favor-y-devoluciones.md` |
| 5 | **Ley 2155/2021 — Ley de Inversión Social** | Su art. 51 creó el art. 689-3 ET (beneficio de auditoría). Esta es la matriz original — Ley 2294/2023 solo prorrogó. | `seccion-18-beneficio-de-auditoria.md`; `T-E-beneficio-auditoria-fuentes-secundarias.md` |
| 6 | **Ley 2010/2019 — Ley de Crecimiento Económico** | Sobrevive porque su art. 117 unificó el plazo de firmeza de declaraciones con pérdidas en 5 años (par. 4 art. 714 ET). Su art. 96 modificó el art. 259-2 ET (eliminación de descuentos no enumerados). Su art. 95 creó el descuento del IVA en activos fijos (art. 258-1 ET). | `seccion-12-determinacion-renta-liquida-gravable.md`; `seccion-15-descuentos-tributarios.md` |
| 7 | **Ley 1819/2016 — Reforma Tributaria Estructural** | Creó arts. estructurales que siguen vigentes: art. 21-1 ET (sistema de determinación fiscal sobre marcos NIIF), art. 147 ET reformado (12 años para pérdidas), art. 290 ET (régimen de transición pre-2017), art. 772-1 ET (conciliación fiscal). Todo el formato 2516 nace de esta ley. | `seccion-11-conciliacion-fiscal.md`; `seccion-12-determinacion-renta-liquida-gravable.md` |
| 8 | **Decreto 410/1971 — Código de Comercio** | Es el andamiaje societario. Define qué es un comerciante, deber de llevar libros (art. 60: 10 años), reglas de fusión y escisión, capital social, distribución de utilidades (art. 30 — momento de causación de dividendos). El RST y el régimen ordinario presuponen que la SAS, LTDA, etc. son comerciantes bajo este código. | `seccion-04-sujetos-obligados-a-declarar-renta.md`; `seccion-27-checklists-operativos-para-el-contador.md` |
| 9 | **Ley 2155/2021 + Ley 2010/2019 (combo de descuentos)** | Es el par que sostiene el régimen actual de descuentos tributarios (arts. 254 a 260 ET). Sin estas dos, la Sección 15 no existiría. | `seccion-15-descuentos-tributarios.md` |
| 10 | **Decreto Legislativo 1474/2025 — Medidas tributarias por emergencia económica** ⛔ | **Suspendido por Auto 082/2026 de la Corte Constitucional.** Originalmente introducía normalización al 19%, impuesto al patrimonio con umbral reducido a 40.000 UVT, conciliaciones, sanciones reducidas. Es referencia obligada porque hay clientes que actuaron creyendo que estaba vigente. | `seccion-21-medidas-transitorias-decreto-1474-emergencia-economica.md`; `T-I-decreto-1474-2025-estado-post-suspension-corte-constitucional.md` |
| 11 | **Ley 1715/2014 — Energías Renovables** | Modificada por Ley 2099/2021. Da una deducción del 50% por inversiones en energía renovable, depreciación acelerada, y exclusión de IVA. Para PYMEs industriales o agropecuarias que evalúan inversiones en autogeneración solar, es definitiva. | `seccion-09-costos-y-deducciones.md`; `seccion-24-planeacion-tributaria-pymes-estrategias-legitimas.md` |
| 12 | **Ley 1437/2011 — CPACA (Código de Procedimiento Administrativo y Contencioso Administrativo)** | Regula los recursos administrativos contra actos de la DIAN, los plazos contencioso-administrativos (art. 164 — 4 meses para demandar), y silencio administrativo. Sin esto, la defensa ante la DIAN es ciega. | `seccion-26-fiscalizacion-y-defensa-ante-la-dian.md` |
| 13 | **Ley 43/1990 — Ley del Contador Público** | Define la responsabilidad disciplinaria del contador, la tarjeta profesional, y las obligaciones éticas. Aunque no toca cifras, define **qué le pueden hacer al contador** si firma una declaración con errores. | `seccion-27-checklists-operativos-para-el-contador.md` |
| 14 | **Decreto 957/2019 — Clasificación MIPYME** | Define qué es micro, pequeña, mediana empresa por ingresos por actividades ordinarias. Importa porque varios beneficios tributarios (Ley 1429, ZOMAC, Ley 2099) se cruzan con esta clasificación. | `seccion-01-objetivo-y-alcance.md` |
| 15 | **Ley 361/1997 — Personas con Discapacidad** | Su art. 31 da una deducción del 200% sobre salarios pagados a empleados con discapacidad. Para PYMEs que califican para el beneficio, vale millones. | `seccion-09-costos-y-deducciones.md` |
| 16 | **Ley 2099/2021 — Transición Energética** | Modificó la Ley 1715/2014 ampliando los beneficios para energías no convencionales. Su art. 8 aumentó la deducción al 50%. | `seccion-09-costos-y-deducciones.md` |
| 17 | **Ley 1955/2019 — PND 2018-2022** | Su art. 268 creó las ZESE (Zonas Económicas y Sociales Especiales). Su art. 190 creó las becas por impuestos (art. 257-1 ET). Aunque el PND original venció, estos artículos siguen produciendo efectos. | `seccion-13-tarifas-del-impuesto.md` |
| 18 | **Ley 1607/2012 — Reforma Tributaria** | Sobrevive porque creó el art. 49 ET vigente (cálculo de dividendos no gravados), el sistema cedular original (luego reformado), y porque introdujo el CREE (derogado pero relevante para pérdidas pre-2017). | `seccion-08-clasificacion-y-depuracion-de-ingresos.md`; `seccion-12-determinacion-renta-liquida-gravable.md` |
| 19 | **Ley 1819/2016 — Reforma Tributaria Estructural (segunda mención)** | Su art. 237 creó el régimen ZOMAC (tarifas reducidas para Zonas Más Afectadas por el Conflicto Armado). | `seccion-13-tarifas-del-impuesto.md` |
| 20 | **Ley 2380/2024 — "Ley anticontrabando"** | Sobrevive porque su art. 2 adicionó el par. 1 al art. 257 ET creando un descuento del 37% por donaciones de alimentos a bancos de alimentos del RTE. Beneficio nuevo y específico, fácil de aplicar. | `seccion-15-descuentos-tributarios.md` |
| 21 | **Resolución Externa 1/2018 JDBR + DCIN-83 (Banco de la República)** | No es ley sino normativa administrativa, pero **funciona como cuerpo de ley** para todo lo cambiario. Define operaciones canalizables, declaraciones de cambio, IMC, cuentas de compensación, registro de inversión extranjera. **Para PYMEs importadoras/exportadoras es la norma maestra.** | (No hay un archivo dedicado; las referencias están dispersas en respuestas de tópico `regimen_cambiario`) |
| 22 | **Decreto-Ley 2663/1950 — Código Sustantivo del Trabajo (CST)** | Andamiaje laboral. El RST integra parafiscales (art. 114-1 ET). Las deducciones por nómina del art. 108 ET presuponen un contrato laboral válido bajo el CST. | (No tiene archivo dedicado en el corpus actual — es una de las brechas Tier 2) |
| 23 | **Ley 9/1991 — Régimen Cambiario** | Es la base legal del régimen cambiario (la Resolución Externa 1/2018 JDBR la reglamenta). Sus arts. 6 y 7 definen las operaciones obligatorias de canalización. | (No hay archivo dedicado — brecha del corpus actual) |
| 24 | **Constitución Política de Colombia 1991** | Andamiaje constitucional. Arts. 95 num. 9 (deber de contribuir), 338 (legalidad tributaria), 363 (equidad/eficiencia/progresividad), 215 (emergencia económica — base del Decreto 1474/2025). | `seccion-02-marco-legal-vigente.md` |

---

## Tres observaciones que valen la pena para el sistema

**Primera —** Si tuvieras que construir un MVP del corpus con solo **6 archivos normativos** (no del corpus interpretativo, sino de los textos legales literales como referencia indexada), serían: ET completo, Ley 2277/2022, Ley 2294/2023, Ley 2155/2021, Ley 2010/2019, DUR 1625/2016. Con eso cubres el 80% de las preguntas de PYMEs.

**Segunda —** El corpus actual es **renta-céntrico**. Las normas comerciales (Código de Comercio), laborales (CST + Ley 50/1990 + Ley 789/2002), y cambiarias (Ley 9/1991 + DCIN-83) están subrepresentadas. Esto es coherente con tu plan de Tier 1 (IVA, nómina, retención, ICA), pero conviene tenerlo explícito: hoy LIA no puede responder bien preguntas que requieran la **intersección** entre tributario y societario, o entre tributario y laboral.

**Tercera —** La fila #10 (Decreto 1474/2025 suspendido) es paradójicamente una de las más útiles del corpus. La Sección 21 documenta extensivamente el estado post-suspensión, y T-I lo desarrolla. Es uno de los pocos casos donde el corpus está **sincronizado con la realidad jurídica del momento** (suspensión de diciembre 2025 / enero 2026) — vale la pena replicar ese patrón cuando aparezcan otras emergencias o sentencias importantes.

---

## How this inventory is used by the fix plan

| Fix | Use of this inventory |
|---|---|
| **Activity 1** (SQL-only filter ship) | No direct use — the migration is purely a SQL filter change. Inventory informs that no document on this list should be wholesale-flagged in Activity 1.5. |
| **Activity 1.5** (document-level flagging) | Only `Decreto 1474/2025` → `vigencia = 'suspendida'`. Optionally `Ley-1429-2010.md` → `derogada` (NOT on this list, lower-risk). Nothing else wholesale-flagged. |
| **Fix 1B** (LLM extraction over 7,883 articles) | The inventory's "normas con artículos sobrevivientes" block (Ley 1819/2016, Ley 2010/2019, Ley 1607/2012) is the test bed for "this document is mixed-vigencia — extractor must distinguish per-article." |
| **Fix 4** (corpus completeness audit) | The "brechas del corpus actual" notes (CST, Ley 9/1991, DCIN-83 dispersa) are the immediate populate-or-deregister candidates for the audit. |
| **Fix 5** (golden answers) | Each canonical answer's `must_cite` list anchors against this inventory's article-level pointers (e.g. art. 689-3 ET via Ley 2155/2021 + Ley 2294/2023 prorroga). |
| **Fix 6** (corpus consistency editorial pass) | The "tres observaciones" §3 (Decreto 1474/2025 paradox; renta-centric corpus) point at the consistency boundary that Fix 6 has to enforce. |
| **Vigencia research agent skill** (queued) | This inventory IS the seed dataset — the skill validates against it before it's trusted on unknown laws. |
