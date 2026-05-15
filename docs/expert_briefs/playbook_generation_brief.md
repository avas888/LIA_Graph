# Brief para Expertos — Playbooks de Lia (Asistente Fiscal para Contadores PYME)

*Versión 1.0 — 14 de mayo de 2026*

---

## 1. Contexto en 30 segundos

- **Qué es Lia:** un asistente conversacional para contadores de PYMEs en Colombia. Cuando un contador hace una consulta fiscal o laboral, Lia responde con base en el Estatuto Tributario, el Código Sustantivo del Trabajo, decretos, resoluciones DIAN y jurisprudencia vigente.
- **Para qué te buscamos:** queremos que Lia responda los temas más consultados a **calidad de contador senior** — no genérica, no académica, no de Wikipedia. Para lograrlo, necesitamos tu experiencia escrita en un formato que Lia pueda usar directamente.
- **Qué vas a producir:** un archivo `.md` por tema (lo que llamamos un *playbook*). El equipo técnico convierte tu playbook en conocimiento operativo que Lia usa para responder cualquier pregunta sobre ese tema.
- **Cuántos:** la lista priorizada está en la Sección 5. Empieza por los Tier 1.

---

## 2. Qué te pedimos exactamente

| Punto | Detalle |
|---|---|
| Formato | Un archivo `.md` (texto plano con formato markdown) por tema |
| Extensión | Entre 300 y 800 palabras por playbook — denso, no extenso |
| Idioma | Español, registro de contador profesional dirigido a otro contador |
| URLs | Cada artículo, decreto, ley, resolución o sentencia citada debe llevar **URL exacta a la fuente oficial** (no homepage, no buscador, no blog) |
| Verificación | Cero ejemplos inventados — toda tarifa, plazo, monto o caso debe estar verificado contra la norma o la práctica documentada |
| Reformas | Si la norma fue modificada por una reforma reciente (Ley 2277/2022, Decreto 572/2025, etc.), márcalo claramente |

---

## 3. Plantilla del playbook — campos obligatorios

Cada archivo `.md` debe tener exactamente esta estructura, en este orden:

```markdown
# [Nombre del tema]

> Una frase de máximo 25 palabras que describa qué cubre este playbook.

## Cómo lo pregunta un contador

[Lista de 8–15 frases o sinónimos que un contador usaría al consultar este tema. Cuanto más variadas, mejor — incluye coloquiales, abreviaciones, jerga del oficio.]

- Frase típica 1
- Frase típica 2
- ...

## Norma principal

- **[Artículo o norma con número exacto]**
- URL: <https://...> *(URL exacta al texto vigente)*
- Resumen del contenido en 1–2 líneas

## Normas relacionadas

| Norma | Para qué se cita | URL |
|---|---|---|
| Art. XYZ ET | razón breve | https://... |
| Decreto NNNN de AAAA | razón breve | https://... |

## Respuesta operativa (5–7 puntos)

[Estos 5–7 puntos son la respuesta de fondo que Lia va a dar al contador. Cada punto debe ser una afirmación accionable, con cifras, plazos, artículos. Evita generalidades.]

1. **Regla general (porcentaje, base, condición):** ...
2. **Cómo calcular o aplicar:** ...
3. **Dónde se registra en la declaración** (renglón + formulario 110 / 210 / 350 según aplique): ...
4. **Soporte documental obligatorio:** ...
5. **Tip operativo o de planeación:** ...
6. *(opcional)* **Excepciones o casos especiales:** ...
7. *(opcional)* **Cómo se concilia con NIIF si aplica:** ...

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| ... | BAJO / MEDIO / ALTO | ... |

## Qué NO cubre este playbook

- Escenario relacionado 1 → ver playbook de [tema relacionado]
- Escenario relacionado 2 → ver playbook de [tema relacionado]

## Vigencia

- ¿La norma fue modificada recientemente? (Sí / No / Pendiente)
- Última reforma relevante: [Ley X de AAAA / Decreto Y de AAAA]
- URL a la versión vigente: <https://...>

## Fuentes secundarias consultadas

- Actualícese — [título del artículo] — <https://...>
- Gerencie.com — [título] — <https://...>
- Consultor Contable / DIAN concepto / sentencia — <https://...>
```

---

## 4. Ejemplo completo — Deducción del GMF (4×1000)

> Este es un playbook real ya entregado. Úsalo como referencia de tono, densidad y nivel de detalle esperado.

---

```markdown
# Deducción del GMF (4×1000) en la declaración de renta

> El 50 % del GMF efectivamente pagado durante el año gravable es deducible en la depuración ordinaria de renta, sin exigir relación de causalidad con la actividad económica.

## Cómo lo pregunta un contador

- ¿Es deducible el GMF?
- ¿Qué porcentaje del 4×1000 puedo deducir?
- ¿Cómo registro el cuatro por mil en la depuración?
- ¿Necesito certificado del banco para deducir el GMF?
- ¿El GMF de la cuenta personal del socio se puede meter en la renta de la empresa?
- ¿Puedo tomar el GMF como descuento tributario o solo como deducción?
- Gravamen a los movimientos financieros — deducibilidad
- ¿Qué pasa con el GMF de las cuentas exentas?
- Tratamiento fiscal del 4 × 1000 año gravable 2025

## Norma principal

- **Art. 115 inciso 2 ET — Deducción del GMF**
- URL: <https://estatuto.co/115>
- Permite deducir el cincuenta por ciento (50 %) del GMF efectivamente pagado durante el AG, independientemente de su causalidad con la actividad productora de renta. Es una excepción explícita al art. 107 ET.

## Normas relacionadas

| Norma | Para qué se cita | URL |
|---|---|---|
| Art. 870 ET | Define el GMF como tributo | <https://estatuto.co/870> |
| Art. 871 ET | Hecho generador | <https://estatuto.co/871> |
| Art. 872 ET | Tarifa (4×1000) | <https://estatuto.co/872> |
| Art. 879 ET | Cuentas exentas del GMF (una por persona) | <https://estatuto.co/879> |
| Art. 107 ET | Regla general de causalidad — el art. 115 inciso 2 es excepción a este | <https://estatuto.co/107> |

## Respuesta operativa

1. **Regla general:** el 50 % del GMF efectivamente pagado durante el AG es deducible en la depuración ordinaria de renta, conforme al art. 115 inciso 2 ET, **sin requerir relación de causalidad** con la actividad productora de renta.
2. **Cómo calcular:** 50 % × (total del GMF certificado por cada entidad financiera donde el contribuyente tuvo cuentas durante el AG). Ejemplo verificable: si la PYME pagó $20.000.000 de 4×1000 durante el AG, deduce $10.000.000.
3. **Dónde se registra:** renglón de **"Otras deducciones"** de la depuración ordinaria del formulario 110 (PJ) o 210 (PN obligada a llevar contabilidad). El otro 50 % queda como gasto contable no deducible y no afecta la renta líquida.
4. **Soporte obligatorio:** certificado anual emitido por cada entidad financiera con el GMF efectivamente retenido durante el AG. Sin este certificado bancario, la deducción es objetable en revisión DIAN.
5. **Tip de planeación:** si el contribuyente tiene una cuenta marcada como exenta de GMF (art. 879 ET — una cuenta por persona natural o jurídica), evaluar si conviene canalizar el mayor volumen transaccional por ella. La exención completa puede valer más que la deducción del 50 % del GMF pagado.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Deducir el 100 % del GMF en vez del 50 % | ALTO | Aplicar siempre el 50 % textual del art. 115 inciso 2 |
| Deducir el GMF sin certificado bancario | ALTO | Pedir el certificado anual al cierre de cada AG |
| Tratar el mismo valor como costo Y como gasto | MEDIO | El art. 115 ET lo prohíbe explícitamente |
| Deducir GMF de cuentas personales del socio en la renta de la empresa | ALTO | El GMF de cuentas personales no es deducible para la sociedad |

## Qué NO cubre este playbook

- Tratamiento del GMF como descuento tributario → no procede; la deducción del 50 % es la única vía bajo el art. 115 inciso 2.
- Exención del GMF por cuenta marcada (art. 879 ET) → ver playbook [Cuentas exentas del GMF].
- Devolución del GMF retenido por error (art. 881 ET) → ver playbook [Devolución del GMF].

## Vigencia

- ¿La norma fue modificada recientemente? No.
- Última reforma relevante: Ley 1739 de 2014 (modificación menor sin afectar el inciso 2).
- URL a la versión vigente: <https://estatuto.co/115>

## Fuentes secundarias consultadas

- Actualícese — *Deducción del GMF en renta AG 2025* — <https://actualicese.com/...> *(sustituir por URL real)*
- Gerencie.com — *50 % del 4×1000 deducible* — <https://gerencie.com/...>
- DIAN Concepto N° 100208... — <https://www.dian.gov.co/...>
```

---

## 5. Lista priorizada de temas — Tier 1 (críticos) y Tier 2 (alto valor)

> Empieza por **Tier 1**. Cuando lo termines, pasa a Tier 2. Si encuentras un tema crítico que falta en esta lista, escríbelo y avísanos.

### Tier 1 — Críticos para SMB-contador

#### A. Renta — Deducciones específicas

- *(✅ ya tenemos)* Deducción del GMF (4×1000) — art. 115 inciso 2 ET
- *(✅ ya tenemos)* Deducción del ICA — art. 115 inciso 1 ET
- *(✅ ya tenemos)* Deducción del predial — art. 115 inciso 1 ET
- *(✅ ya tenemos)* Deducción de intereses + subcapitalización — arts. 117 y 118-1 ET
- *(✅ ya tenemos)* Tratamiento fiscal del leasing — art. 127-1 ET
- *(✅ ya tenemos)* Deducción del 120 % por primer empleo — art. 108-5 ET
- **Depreciación fiscal de activos** — art. 137 ET (tabla de vida útil)
- **Atenciones a clientes y empleados** — art. 107-1 ET (tope del 1 % de ingresos netos)
- **Cartera de difícil recaudo (provisiones)** — arts. 145 y 146 ET
- **Donaciones deducibles** — art. 125 ET (deducción) y art. 257 ET (descuento)
- **Compensación de pérdidas fiscales** — art. 147 ET (12 años)
- **Salario integral — tratamiento fiscal** — art. 132 CST y art. 27 Ley 50/1990
- **Pagos no constitutivos de salario — desalarización** — art. 128 CST + Sentencia CSJ SL4655 de 2021
- **Aportes parafiscales y de seguridad social** — Ley 100/1993 + Ley 21/1982
- **Exoneración de parafiscales (114-1)** — art. 114-1 ET (empleados ≤ 10 SMMLV)
- **Limitación pagos en efectivo** — art. 771-5 ET
- **Soporte documental — factura electrónica** — arts. 771-2 y 616-1 ET

#### B. Renta — Descuentos tributarios

- **ICA como descuento tributario (50 %)** — art. 115-1 ET (alternativa a la deducción del 100 %)
- **IVA en activos fijos reales productivos** — art. 258-1 ET
- **Donaciones como descuento** — art. 257 ET
- **CTeI — inversiones en ciencia, tecnología e innovación** — art. 158-1 ET
- **Energías renovables** — art. 11 Ley 1715/2014 (modificado por Ley 2099/2021)
- **Discapacidad — 200 % del salario** — art. 31 Ley 361/1997
- **Mujeres víctimas de violencia — 200 % del salario** — art. 23 Ley 1257/2008
- **Factura electrónica — 1 %** — art. 7 Ley 2277/2022

#### C. Renta — Tarifas y régimen

- **Tarifa general personas jurídicas (35 %)** — art. 240 ET
- **Tasa de Tributación Depurada (TTD)** — art. 240 par. 6 ET (Ley 2277/2022)
- **Tarifa dividendos para personas naturales residentes** — art. 242 ET
- **Régimen Simple de Tributación — tarifas consolidadas** — art. 908 ET (modificado por Ley 2277/2022)
- **Zona franca — doble tarifa desde AG 2024** — art. 240-1 ET
- **ZOMAC y ZESE** — art. 237 Ley 1819/2016 + art. 268 Ley 1955/2019

#### D. Renta — Procedimiento

- **Beneficio de auditoría** — art. 689-3 ET (vigente AG 2022–2026)
- **Firmeza de declaraciones** — art. 714 ET
- **Anticipo de impuesto de renta** — arts. 807 y 809 ET
- **Devolución / compensación de saldos a favor** — art. 850 ET
- **Sanción por extemporaneidad** — art. 641 ET
- **Sanción por corrección** — art. 644 ET
- **Sanción por inexactitud** — art. 647 ET
- **Notificaciones electrónicas DIAN** — art. 566-1 ET

#### E. IVA

- **Hecho generador del IVA** — arts. 420 a 437 ET
- **Régimen común vs simplificado** — arts. 437-1 y 437-2 ET
- **IVA descontable — proporcionalidad y prorrateo** — arts. 488 a 491 ET
- **Devolución de saldos a favor en IVA** — art. 481 ET (exportaciones y exentos)
- **Bienes excluidos vs exentos del IVA** — art. 424 ET (excluidos) + art. 477 ET (exentos)

#### F. Retención en la fuente

- **Tablas de retención AG 2025 + AG 2026** — Resolución DIAN sobre UVT + Decreto 572/2025
- **Retención por salarios** — art. 383 ET (procedimientos 1 y 2)
- **Retención por servicios** — art. 392 ET
- **Autoretención** — Decreto 2201/2016 y siguientes
- **Bases mínimas de retención** — Decreto 572/2025

#### G. Labor / Nómina (primera categoría — alcance del producto)

- **Liquidación mensual de nómina** — salarios, recargos, horas extras
- **Prestaciones sociales** — cesantías (Ley 50/1990), prima, vacaciones
- **Liquidación al terminar contrato** — indemnizaciones art. 64 CST
- **PILA — Planilla Integrada de Liquidación de Aportes**
- **UGPP — fiscalización de aportes** — Ley 1607/2012 art. 178
- **Nómina electrónica — DSPNE** — Resolución DIAN 000013/2021 y siguientes
- **Contratos de prestación de servicios vs contratos laborales** — art. 23 CST + jurisprudencia
- **Subsidios — auxilio de transporte y alimentación**
- **Embargos sobre salario** — art. 154 CST + Ley 1564/2012
- **Contrato de aprendizaje SENA** — Ley 789/2002
- **Teletrabajo y trabajo en casa** — Ley 1221/2008 y Ley 2088/2021
- **Liquidación de SMMLV y auxilio de transporte anual**

#### H. NIIF — Fiscal

- **Conciliación fiscal F2516 / F2517** — Resolución DIAN sobre formatos
- **Impuesto diferido — NIC 12** — diferencias temporarias vs permanentes (DPARL)
- **Depreciación NIIF vs fiscal** — NIC 16 vs art. 137 ET
- **Leasing NIIF 16 vs art. 127-1 ET** — *(ya cubierto parcialmente en el playbook de leasing)*
- **Ingresos por contratos — NIIF 15 vs art. 28 ET**

#### I. Información exógena

- **Formato 1001 — pagos a terceros** — Resolución DIAN anual
- **Formato 1005 — IVA descontable**
- **Formato 1007 — ingresos**
- **Formato 1003 — retenciones practicadas**
- **Umbrales y plazos AG 2025** — Resolución DIAN 000162/2023

---

### Tier 2 — Alto valor (segunda ola)

- **Renta presuntiva — histórico** — art. 188 ET (derogado pero usado en históricos)
- **Impuesto al patrimonio** — Ley 2277/2022
- **INC — Impuesto Nacional al Consumo** — art. 512-1 ET
- **Precios de transferencia — umbrales** — art. 260-1 y ss. ET
- **Documentación comprobatoria — Informe Local F1125 / F1729**
- **Recursos ante DIAN** — reconsideración, revocatoria directa
- **Aportes voluntarios a pensión y AFC** — arts. 55, 56-1 y 126-1 ET
- **Capitalización de utilidades** — art. 36 ET
- **Dividendos no gravados — determinación** — art. 49 ET
- **Renta cedular para personas naturales** — arts. 330 a 343 ET
- **Régimen tributario especial (ESAL)** — art. 19 ET y ss.
- **Cláusula anti-abuso** — arts. 869, 869-1 y 869-2 ET
- **Omisión de activos y defraudación fiscal — tipo penal** — art. 434-A Código Penal

---

## 6. Estándares de calidad

### Tono

- Escribe como si estuvieras explicándole a otro contador, no a un cliente lego. Asume conocimiento básico de depuración de renta, plan único de cuentas, formularios DIAN.
- Lenguaje directo y operativo. Verbos en imperativo o en infinitivo de acción ("registra", "calcula", "verifica"), no en abstracto ("se podría considerar la posibilidad de").
- Cero adornos académicos. No definir términos básicos.

### Estructura

- Cada bullet en "Respuesta operativa" debe ser una afirmación con sujeto, verbo, objeto y consecuencia.
- Cifras: usa formato numérico colombiano (`$20.000.000`, no `$20,000,000`).
- Tarifas y plazos: siempre en bold (`**50 %**`, `**5 años**`).
- Citas a artículos: formato `art. 115 ET` o `art. 115 inciso 2 ET`. Nunca abreviaturas no estándar.

### Lo que NO incluyes

- Opiniones políticas sobre la norma (ej. "esta reforma fue mal pensada"). Solo describes la norma vigente.
- Casos hipotéticos vagos ("imagínate que..."). Si pones un caso, debe ser específico con cifras y verificable contra el texto de la norma.
- Referencias cruzadas a otros playbooks sin explicar la relación. Usa la sección "Qué NO cubre este playbook" para esto.
- Texto de relleno ("es importante destacar que...", "vale la pena mencionar que..."). Cero.

---

## 7. Reglas de URL

| Tipo de fuente | URL aceptada | URL NO aceptada |
|---|---|---|
| Artículo ET | `estatuto.co/115`, `normograma.dian.gov.co/dian/compilacion/.../115` | Búsquedas, blogs sobre el artículo |
| Decreto / Ley | `suin-juriscol.gov.co/...` con el ID del documento | Homepage de SUIN |
| Resolución DIAN | `dian.gov.co/normatividad/Normatividad/Resolución 000XXX de AAAA` | Homepage DIAN |
| Sentencia | `cortesuprema.gov.co/...` o `corteconstitucional.gov.co/...` con número de radicado | Reseñas de prensa |
| Concepto DIAN | `dian.gov.co/normatividad/.../Conceptos` con número y año | Resumen en blog |
| Fuente secundaria (Actualícese, Gerencie, etc.) | URL al artículo específico | Homepage del sitio |

**Regla de oro:** un colega contador que abra tu URL debe llegar exactamente al texto que estás citando, sin tener que buscar más. Si tu URL es a una página de búsqueda o a una homepage, no sirve.

---

## 8. Cómo entregar

- **Repositorio:** el equipo te confirmará el destino (Dropbox / Drive / Git).
- **Un archivo por tema** — no agrupes varios temas en un solo `.md`.
- **Nombre del archivo:** `playbook_<categoria>_<tema-en-kebab-case>.md`. Ejemplo: `playbook_renta_deduccion_gmf.md` o `playbook_labor_exoneracion_parafiscales_114_1.md`.
- **Avisa al terminar cada uno** — no esperes a tener los 50. El equipo conecta cada playbook al sistema en cuanto llega.
- **Cadencia objetivo:** 2–4 playbooks por semana. Sin presión absoluta — preferimos calidad sobre velocidad.

---

## 9. Preguntas frecuentes

| Situación | Qué hacer |
|---|---|
| Dos fuentes secundarias dicen cosas distintas sobre el mismo artículo | Cita la norma original (texto del artículo) como autoridad. Las fuentes secundarias son apoyo, no decisión. |
| La norma cambió recientemente y no es claro si la versión nueva ya rige | Cita ambas versiones, marca cuál rige y para qué AG, y deja la fecha explícita en la sección **Vigencia**. |
| El tema es muy amplio para un solo playbook (ej. "IVA en general") | Divídelo en sub-temas más concretos. Pregúntanos antes de empezar si no estás seguro del corte. |
| No estoy seguro si esto va aquí o en otro tema | Escribe el playbook donde tenga más sentido y agrega una nota en **Qué NO cubre este playbook** apuntando al tema relacionado. |
| Encontré un error en un playbook ya entregado | Re-envíalo con `_v2` en el nombre y nota brevemente qué cambió en la primera línea. |
| El cliente típico hace esta pregunta de 5 formas distintas, ¿pongo todas? | Sí. La sección **Cómo lo pregunta un contador** se beneficia de variedad — incluye sinónimos, abreviaciones, jerga ("4×1000" = "4 x 1000" = "cuatro por mil" = "GMF"). Cuantos más sinónimos, mejor responde Lia. |
| Encontré una sentencia o concepto DIAN que cambia el tratamiento práctico | Inclúyela en **Normas relacionadas** con URL exacta y resume su efecto en una línea. |
| La norma tiene reglamentación en un Decreto Único Reglamentario (DUR 1625/2016) | Cita el artículo del DUR específicamente con su número (`art. 1.2.1.27.5 DUR 1625/2016`). |

---

## 10. Qué pasa después de tu entrega

1. El equipo técnico revisa el `.md` y verifica que las URLs respondan.
2. Si todo está en orden, conectamos el playbook al sistema. Lia empieza a responder ese tema con tu contenido al día siguiente.
3. Si encontramos ambigüedades, te escribimos con preguntas puntuales antes de conectar.
4. Una vez en producción, monitoreamos cómo Lia responde preguntas de ese tema. Si un patrón de pregunta no está cubierto, podríamos pedirte una ampliación del playbook o un playbook hermano.

---

## 11. Contacto

- **Coordinación del proyecto:** *(equipo de Lia — llenar contacto)*
- **Dudas técnicas sobre la plantilla:** *(persona del equipo — llenar contacto)*
- **Dudas fiscales o de criterio sobre un tema:** entre expertos — usen el canal interno de consultas

---

*Gracias por escribir estos playbooks. Cada uno deja a miles de contadores PYME con una respuesta correcta, citada y operativa donde antes había duda.*
