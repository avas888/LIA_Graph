# Lia — Taxonomy v2 — Respuesta SME

> **Autor:** Alejandro (contador público / asesor tributario y laboral PYMEs Colombia), apoyado por análisis del corpus actual de LIA Contador.
> **Fecha:** 2026-04-25.
> **Alcance:** Respuesta completa a las §6.1, §6.2 y §6.3 del brief `Lia — Taxonomy v2 expert brief`.
> **Premisa de diseño:** taxonomía orientada al uso real del contador de PYME colombiano (rangos $0–20.000 millones COP, 1–50 empleados), donde el mismo profesional debe responder por tributario, laboral, cumplimiento y societario. Por eso el árbol tiene tópicos top-level fuera de tributario nacional.
> **Convención de claves:** `snake_case` minúsculas, sin tildes, sin guiones medios.

---

## 0. Resumen ejecutivo de las decisiones

1. **Confirmo las dos clases nuevas top-level:** `impuesto_timbre` y `rut_responsabilidades`. El corpus actual de renta no las cubre como tópicos (verificado: timbre solo aparece como mención tangencial en exógena; RUT está disperso transversalmente sin slot propio).
2. **De las 7 maybe-missing del §5.4 propongo:**
   - Top-level nuevos: `parafiscales_seguridad_social`, `reforma_laboral_ley_2466`, `proteccion_datos_personales`, `niif_pymes`, `niif_plenas` (split del `estados_financieros_niif` actual).
   - Subtópicos: `renta_presuntiva` (subtópico de `declaracion_renta`), `zomac_zese_incentivos_geograficos` (subtópico de `inversiones_incentivos`).
   - Boundary entre `reforma_pensional` y `laboral`: ambos top-level, frontera explícita por norma fuente (Ley 2381/2024 + reglamentación → `reforma_pensional`; CST + Ley 100 régimen contributivo → `laboral`).
3. **Cinco reglas de mutua exclusividad** (codificables en `scope_out`): IVA sustantivo vs procedimiento; ET Libro 1 vs IVA; comercial_societario vs obligaciones_mercantiles (los fusiono); FE vs timbre; RUB vs RUT.
4. **Confirmo las 12 reclasificaciones** del §5.2 con ajustes menores en 2 (ver §3 abajo).
5. **Adicionalmente identifico 3 brechas de dominio adicionales** que el brief no menciona pero que un contador PYME enfrenta a diario: cambiaria/régimen cambiario (DCIN-83), dividendos y distribución de utilidades (frontera renta/societario), y régimen tributario especial / ESAL (suele ir mal a `declaracion_renta`).

---

## 1. Bloque §6.1 — Decisiones que desbloquean el freeze

### 1.1 Confirmación de las dos clases nuevas confirmadas (§5.3)

#### `impuesto_timbre`

- **Confirmación:** sí, top-level, con nombre `Impuesto de Timbre Nacional`.
- **Subtópicos sugeridos (opcionales — pueden esperar a v2.1):**
  - `timbre_actos_gravados` (qué genera el hecho generador).
  - `timbre_tarifas_y_exenciones` (incluye decretos como el 175/2025 que reactivó la tarifa del 1%).
  - `timbre_agentes_retenedores` (quién retiene y cómo declara — formulario 350).
- **Por qué top-level y no subtópico de otra cosa:** es un impuesto autónomo en ET Libro 4 con su propio hecho generador (acto jurídico formal), su propio formulario de retención, y desde 2025 con la suspensión/reactivación del Decreto 175 ha tenido alta consulta práctica en PYMEs (especialmente sobre escrituras y contratos > 6.000 UVT).

#### `rut_responsabilidades`

- **Confirmación:** sí, top-level.
- **Nombre alternativo recomendado:** `rut_y_responsabilidades_tributarias` (más legible al usuario que `rut_responsabilidades` a secas).
- **Razón para separar de `beneficiario_final_rub`:** RUT y RUB son registros distintos, con normativas distintas (RUT: arts. 555-1, 555-2 ET, Decreto 2460/2013, Resoluciones DIAN sucesivas; RUB: Ley 2155/2021 art. 4 + Resolución DIAN 000164/2021). Un contador PYME consulta RUT a diario (códigos de responsabilidad, actualización por cambio de actividad económica, inscripción de nuevas obligaciones) y RUB rara vez (1 vez al año + cuando cambia composición societaria).
- **Subtópicos sugeridos:**
  - `rut_inscripcion_y_actualizacion` (proceso operativo MUISCA).
  - `rut_codigos_de_responsabilidad` (catálogo de códigos: 05, 07, 11, 14, 22, 23, 32, 33, 35, 42, etc. — uno de los temas más consultados por contadores junior).
  - `rut_actividad_economica_ciiu` (selección y cambio de código CIIU).

---

### 1.2 Decisiones sobre las maybe-missing (§5.4)

| Propuesta brief | Decisión SME | Justificación |
|---|---|---|
| `renta_presuntiva` | **Subtópico** de `declaracion_renta` | Solo arts. 188-191 ET. Demasiado pequeño para top-level pero suficientemente confuso (cálculo, excesos, compensación) para merecer slot propio dentro de renta. |
| `proteccion_datos_personales` | **Top-level nuevo** | Régimen autónomo (Ley 1581/2012, Decreto 1377/2013, Decreto 1074/2015 Cap. 25, Circulares SIC). Aplicable a TODA PYME que maneje datos. Frontera con `datos_tecnologia` (que parece ser sobre uso de tecnología): protección de datos es cumplimiento legal específico, no un tema tecnológico. |
| `parafiscales` | **Top-level nuevo, renombrado a `parafiscales_seguridad_social`** | Régimen autónomo (Ley 100/1993, Ley 21/1982, Ley 89/1988, doctrina UGPP). Operativamente es PILA + UGPP + tarifas + exoneraciones (art. 114-1 ET). En el corpus de LIA ya aparece 328 veces como condicional para deducción, pero no tiene slot propio para preguntas sobre mecánica de aportes. |
| `zomac_incentivos` | **Subtópico** de `inversiones_incentivos`, renombrado a `zomac_zese_incentivos_geograficos` | Cubre ZOMAC + ZESE + Zonas Francas geográficas + incentivos por ubicación (Cúcuta, San Andrés, etc.). Es un cluster temático, pero está activo solo en regiones específicas → subtópico es suficiente. |
| `reforma_laboral_2466` | **Top-level nuevo, renombrado a `reforma_laboral_ley_2466`** | Ley 2466/2025 es transversal y modifica una docena de artículos del CST (recargos nocturnos, jornada, contratos a término fijo, aprendices SENA, licencias). El corpus actual NO la tiene (verificado: 0 ocurrencias). Mientras esté en transición de implementación (2025-2027), merece tópico propio para concentrar circulares MinTrabajo, conceptos, sentencias, y guías de transición. **Plan de evolución:** cuando la reforma esté completamente implementada (post-2028), se puede degradar a subtópico de `laboral`. Marcar `version_added: v2.0` y `sunset_review: v2.x cuando implementación esté completa`. |
| `reforma_pensional` (existente) | **Mantener top-level**, frontera explícita | Ley 2381/2024 (reforma pensional) está suspendida parcialmente y en revisión por la Corte Constitucional. Mientras dure la incertidumbre, top-level es apropiado. **Frontera con `laboral`:** todo lo que sea Ley 2381/2024 + reglamentación + sentencias C-XXX/2025 → `reforma_pensional`. Todo lo que sea Ley 100/1993 régimen contributivo histórico, mecánica de aportes pensionales actuales → `parafiscales_seguridad_social`. CST relación laboral → `laboral`. |
| `niif_pymes` vs `niif_plenas` | **Split en dos top-level** | Son marcos técnicos distintos (Decreto 2420/2015, Anexos 1, 2, 3). El contador de PYME que asesora a una empresa Grupo 2 (NIIF para PYMES) rara vez consulta NIIF Plenas, y viceversa. El slot único `estados_financieros_niif` mezcla audiencias. **Adicionalmente proponer un tercer top-level: `niif_microempresas`** (Anexo 3, marco técnico para Grupo 3, art. 2.1.3 DUR 2420/2015) — relevante para PYMEs muy pequeñas que aplican el marco simplificado. |

#### Brechas adicionales que el brief no enumeró pero detecté

| Propuesta SME | Razón | Posición sugerida |
|---|---|---|
| `regimen_cambiario` | DCIN-83 (Banrep), inversión extranjera, endeudamiento externo, declaración de cambios. PYMEs exportadoras / con préstamos en dólares lo enfrentan a diario. | Top-level nuevo. |
| `dividendos_y_distribucion_utilidades` | Frontera entre renta (arts. 48, 49, 242, 242-1, 245 ET — tarifas de dividendos) y societario (decisión de junta, reservas, dividendos en especie). Hoy probablemente termina mal en `declaracion_renta`. | Top-level nuevo, o subtópico de `declaracion_renta` con cross-reference a `comercial_societario`. **Mi voto: top-level**, porque también incluye consideraciones de NIIF (reconocimiento del pasivo) y de retención en la fuente sobre dividendos. |
| `regimen_tributario_especial_esal` | ESAL (Entidades Sin Ánimo de Lucro) tienen régimen propio (arts. 356-364-6 ET, Decreto 2150/2017). Cooperativas, fundaciones, cajas de compensación. PYMEs ESAL existen y necesitan slot. | Top-level nuevo. |

---

### 1.3 Reglas de mutua exclusividad para magnet topics (§5.5)

Estas son las reglas que codificas como `scope_out` en cada tópico. Las redacto en formato "si X → entonces tópico Y".

#### Regla 1 — `iva` vs `procedimiento_tributario`

```
SI el documento trata de:
  - hecho generador del IVA (art. 420 ET y ss.)
  - base gravable (arts. 447-462 ET)
  - tarifas y bienes/servicios excluidos/exentos (arts. 468, 477, 481, etc.)
  - responsables del IVA y régimen de responsabilidad (arts. 437, 437-1, 437-2 ET)
  - retención de IVA — reteIVA (arts. 437-1, 437-2 ET)
  - facturación específica en IVA (impuestos descontables — art. 488 ET)
ENTONCES → topic: iva

SI el documento trata de:
  - cómo presentar la declaración de IVA (formulario 300, periodicidad)
  - sanciones por no declarar / extemporaneidad de IVA
  - corrección de declaraciones de IVA
  - firmeza de la declaración de IVA
  - devoluciones de saldos a favor en IVA
  - cobro coactivo, embargos, recursos
ENTONCES → topic: procedimiento_tributario
```

**Test rápido:** si la respuesta a "¿cuánto IVA debo pagar?" → `iva`. Si la respuesta es "¿cómo y cuándo lo pago, lo declaro o lo discuto?" → `procedimiento_tributario`.

#### Regla 2 — `iva` vs familia renta (`declaracion_renta`, `costos_deducciones`, `ingresos_fiscales_renta`, etc.)

```
Default: si el artículo está en ET Libro 1 (arts. 5-364-6) → familia renta
Default: si el artículo está en ET Libro 3 (arts. 420-513) → iva

Excepción: artículos transversales (procedimiento — Libro 5, sanciones — Libro 5)
no van a iva ni a renta — van al tópico procedimental específico.
```

**Test rápido:** mira el número del artículo ET. Es el mejor desambiguador automatizable.

#### Regla 3 — `comercial_societario` vs `obligaciones_mercantiles` → **fusionar**

Mi recomendación: **un solo tópico**, llamado `comercial_societario`, que cubra:
- Constitución, transformación, fusión, escisión de sociedades.
- Obligaciones mercantiles del comerciante (libros, registro mercantil, conservación).
- Reformas estatutarias.
- Asambleas, juntas directivas.
- Disolución y liquidación.

**Razón:** desde el punto de vista del contador PYME, ambos son la misma asesoría: "cómo está mi sociedad estructurada y qué debo cumplir como comerciante". Separar agrega ambigüedad sin ganancia. Si el día de mañana el corpus crece a 10 documentos solo de obligaciones mercantiles puras (libros, registro), se puede crear `obligaciones_mercantiles` como subtópico.

#### Regla 4 — `facturacion_electronica` vs `impuesto_timbre`

```
SI documento trata de arts. 615, 616-1, 617, 618, 771-2 ET / Resoluciones DIAN
sobre factura, nota crédito, nota débito, RADIAN, nómina electrónica, DSE
ENTONCES → topic: facturacion_electronica

SI documento trata de arts. 514-540 ET (Libro 4) / Decreto 2076/1992 / Decreto
175/2025 sobre impuesto de timbre nacional
ENTONCES → topic: impuesto_timbre
```

**Test rápido:** es Libro 4 vs Libro 5 ET. Limpio, no overlap.

#### Regla 5 — `beneficiario_final_rub` vs `rut_responsabilidades`

```
SI documento trata de:
  - Ley 2155/2021 art. 4
  - Resolución DIAN 000164/2021 y modificatorias
  - Identificación de beneficiarios finales (personas naturales > 5% participación)
  - Estructuras sin personería jurídica (fideicomisos, etc.)
ENTONCES → topic: beneficiario_final_rub

SI documento trata de:
  - Inscripción / actualización RUT
  - Códigos de responsabilidad
  - Selección y cambio CIIU
  - Cancelación RUT
  - Resolución DIAN sobre RUT (las propias del registro, no las del RUB)
ENTONCES → topic: rut_responsabilidades
```

#### Regla 6 (adicional) — `laboral` vs `parafiscales_seguridad_social` vs `reforma_laboral_ley_2466` vs `reforma_pensional`

```
SI norma fuente es:
  - Ley 2466/2025 + reglamentación → reforma_laboral_ley_2466
  - Ley 2381/2024 + reglamentación → reforma_pensional
  - Ley 100/1993 (régimen contributivo SGSSS, SGP, ARL), Ley 21/1982, Ley 89/1988,
    Ley 1607/2012 art. 25 (CREE → exoneración 114-1 ET), Decreto 1273/2018 (PILA),
    doctrina UGPP → parafiscales_seguridad_social
  - CST (Ley 2663/1950) y reformas anteriores a 2466, contratación, prestaciones,
    terminación, seguridad y salud en el trabajo (Decreto 1072/2015 Libro 2 Parte 2
    Título 4 Cap. 6) → laboral
```

---

### 1.4 Validación de las 12 reclasificaciones (§5.2)

Confirmo todas las 12. Ajustes:

| Slot | Estado SME | Notas |
|---|---|---|
| `ingresos_fiscales_renta` | ✅ confirmado | ET arts. 26–57 (definición ingreso, INCRNGO, ingresos no gravados, realización del ingreso). |
| `patrimonio_fiscal_renta` | ✅ confirmado | ET arts. 261–298. **Adicional:** incluir conexión con conciliación 2516 (campo F2 patrimonio). |
| `firmeza_declaraciones` | ✅ confirmado | ET art. 714 + 689-3 (beneficio auditoría altera firmeza) + 117 Ley 2010/2019 (firmeza pérdidas fiscales). **Sub-tópico de** `procedimiento_tributario`, no top-level. |
| `devoluciones_saldos_a_favor` | ✅ confirmado | ET arts. 850–865 + Decreto 1206/2024 (devolución automática) + Resolución DIAN procedimiento. |
| `ganancia_ocasional` | ✅ confirmado | ET arts. 299–318. Top-level está bien. |
| `renta_liquida_gravable` | ✅ confirmado | ET arts. 178–187 (Cap. VII Libro 1). **Sub-tópico de** `declaracion_renta`. |
| `descuentos_tributarios_renta` | ✅ confirmado | ET arts. 254–260 + 256 (CTeI) + 257 (donaciones ESAL) + 258-1 (IVA bienes de capital). |
| `anticipos_retenciones_a_favor` | ✅ confirmado | ET arts. 365–371 (régimen general retención fuente). **Renombrar a `retencion_fuente_general`** para mayor claridad de nombre — "anticipos retenciones a favor" suena como técnico interno. Anticipo del impuesto (art. 807 ET) podría merecer su propio sub-tópico. |
| `tarifas_tasa_minima_renta` | ✅ confirmado | ET arts. 240, 240-1, 241, 242, 242-1, 243 + parágrafo 6 art. 240 (TTD). **Renombrar a `tarifas_renta_y_ttd`**. |
| `beneficio_auditoria` | ✅ confirmado | ET art. 689-3 (vigente AG 2024-2026). Cobertura ya existe en sección 18 del corpus actual. |
| `conciliacion_fiscal` | ✅ confirmado | DUR 1625/2016 art. 1.7.1; Resolución DIAN 000071/2019 (formato 2516); Resolución DIAN 000027/2024 (formato 2517). |
| `regimen_sancionatorio_extemporaneidad` | ✅ confirmado | ET arts. 641, 642, 644, 647, 648 + reducción art. 640. **Sub-tópico de** `procedimiento_tributario`. |

---

## 2. Bloque §6.2 — Definiciones por tópico

> **Convención:** cubro aquí (a) los nuevos top-level, (b) los reclasificados que necesitan re-fundación, y (c) los magnet-topics que necesitan re-definición. Para los 79 tópicos restantes que no están tocados por los hallazgos del audit, recomiendo revisión liviana en una segunda iteración (no bloqueante para el freeze).

### 2.1 Tópicos NUEVOS top-level

#### `impuesto_timbre`

```yaml
key: impuesto_timbre
label: Impuesto de Timbre Nacional
definition: Impuesto sobre actos jurídicos formales (escrituras públicas, contratos privados, documentos sin cuantía determinada) regulado en ET Libro 4, arts. 514-540.
scope_in: |
  - Hecho generador del impuesto de timbre (arts. 514-519 ET).
  - Sujetos pasivos y responsables (art. 515 ET).
  - Base gravable y tarifas (arts. 519, 521 ET; Decreto 175/2025 sobre tarifa 1% reactivada bajo emergencia económica).
  - Causación, retención y declaración del timbre (arts. 539-1, 539-2, 539-3 ET; formulario 350).
  - Exenciones (arts. 530, 530-1 ET).
  - Documentos sin cuantía determinada (art. 521 ET).
  - Conceptos DIAN sobre actos gravados controvertidos (cesiones de cuotas SAS, contratos atípicos, acuerdos marco).
scope_out: |
  - Notas crédito/débito en factura electrónica → facturacion_electronica.
  - Estampillas departamentales o municipales (estampilla pro-universidad, pro-ancianos, etc.) → impuestos_territoriales (subtópico estampillas).
  - Impuesto de registro (Ley 223/1995 art. 226 — gobernaciones) → impuestos_territoriales.
  - Sanciones por no declarar timbre → procedimiento_tributario (sub: regimen_sancionatorio_extemporaneidad).
typical_sources:
  - ET Libro 4 (Decreto 624/1989 arts. 514-540).
  - Decreto 2076/1992 (reglamentación clásica del timbre).
  - Decreto 175/2025 (reactivación tarifa 1% bajo Decreto 1085/2025 — emergencia económica).
  - Decreto 1474/2025 (suspensión / modulación del régimen — verificar status post-Corte).
  - Conceptos DIAN sobre actos gravados (oficio 0904 de 2021, oficio 901832 de 2022, otros).
  - Doctrina especializada: Actualícese, Legis, Brigard Urrutia, PHR sobre reactivación 2025.
keyword_anchors:
  - "impuesto de timbre"
  - "timbre nacional"
  - "timbre 1 por ciento"
  - "Decreto 175 de 2025"
  - "tarifa de timbre"
  - "exencion de timbre"
  - "actos sin cuantia"
  - "ET 519"
  - "ET 521"
  - "escritura publica timbre"
  - "contrato privado timbre"
  - "retencion de timbre"
  - "agente retenedor de timbre"
  - "timbre cesion de cuotas"
  - "formulario 350 timbre"
allowed_et_articles:
  - "514"
  - "515"
  - "516"
  - "517"
  - "518"
  - "519"
  - "521"
  - "522"
  - "523"
  - "524"
  - "525"
  - "526"
  - "527"
  - "528"
  - "529"
  - "530"
  - "530-1"
  - "531"
  - "532"
  - "533"
  - "534"
  - "535"
  - "536"
  - "537"
  - "538"
  - "539"
  - "539-1"
  - "539-2"
  - "539-3"
  - "540"
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `rut_y_responsabilidades_tributarias`

```yaml
key: rut_y_responsabilidades_tributarias
label: RUT y Responsabilidades Tributarias
definition: Registro Único Tributario — inscripción, actualización, códigos de responsabilidad y selección de actividad económica (CIIU). Aplicable a personas naturales y jurídicas inscritas ante la DIAN.
scope_in: |
  - Inscripción inicial RUT (arts. 555-1, 555-2 ET; Decreto 2460/2013).
  - Actualización RUT por cambio de obligaciones, dirección, representación legal, socios.
  - Códigos de responsabilidad (catálogo: 05 IVA régimen común, 07 retención fuente, 11 IVA, 14 declarante renta, 22 obligado a facturar, 32 RST, 33 régimen especial, 35 facturador electrónico, 42 obligado a presentar exógena, etc.).
  - Selección y cambio de actividad económica CIIU.
  - Cancelación RUT / suspensión.
  - Sanciones del art. 658-3 ET por no inscribirse / no actualizar.
scope_out: |
  - Beneficiarios finales (RUB) → beneficiario_final_rub.
  - Régimen Simple de Tributación per se (mecánica del impuesto SIMPLE) → regimen_simple_tributacion (aunque la inscripción al SIMPLE se hace vía RUT).
  - Régimen tributario especial ESAL (calificación) → regimen_tributario_especial_esal (aunque genera responsabilidad 33 en RUT).
  - Facturación electrónica per se → facturacion_electronica (aunque genera responsabilidad 35 en RUT).
typical_sources:
  - ET arts. 555-1, 555-2, 658-3.
  - Decreto 2460/2013 + modificatorios.
  - DUR 1625/2016 Título 6 (RUT).
  - Resoluciones DIAN sobre RUT (000139/2012, 000060/2017, 000070/2019, 000022/2024, etc.).
  - Cartilla RUT de la DIAN.
  - Manual MUISCA RUT.
keyword_anchors:
  - "RUT"
  - "registro unico tributario"
  - "inscripcion RUT"
  - "actualizacion RUT"
  - "codigo de responsabilidad"
  - "responsabilidad 05"
  - "responsabilidad 07"
  - "responsabilidad 11"
  - "responsabilidad 32"
  - "responsabilidad 33"
  - "responsabilidad 42"
  - "actividad economica CIIU"
  - "cambio CIIU"
  - "cancelacion RUT"
  - "art 658-3 ET"
  - "Decreto 2460 de 2013"
allowed_et_articles:
  - "555-1"
  - "555-2"
  - "555-3"
  - "658-3"
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `parafiscales_seguridad_social`

```yaml
key: parafiscales_seguridad_social
label: Parafiscales y Seguridad Social
definition: Aportes parafiscales (SENA, ICBF, Cajas de Compensación) y aportes a seguridad social (salud, pensión, ARL) para empleadores. Incluye PILA, exoneración del art. 114-1 ET, fiscalización UGPP.
scope_in: |
  - Aportes a salud, pensión, ARL del régimen contributivo (Ley 100/1993).
  - Parafiscales SENA, ICBF, Cajas (Ley 21/1982, Ley 89/1988).
  - Exoneración del art. 114-1 ET (CREE → Ley 1819/2016 → Ley 2010/2019).
  - PILA — planilla integrada de aportes (Decreto 1273/2018, Resolución 1995/2019 y modificatorios).
  - Bases de cotización (IBC), pisos, techos, aportes mínimos.
  - Aportes de independientes (Ley 1955/2019 art. 244, Decreto 1601/2022).
  - Fiscalización UGPP (Decreto 1762/2024 reglamentación reciente; doctrina UGPP).
  - Sanciones UGPP (art. 179 Ley 1607/2012; gradualidad post-conciliación).
scope_out: |
  - Reforma laboral Ley 2466/2025 → reforma_laboral_ley_2466.
  - Reforma pensional Ley 2381/2024 → reforma_pensional.
  - Relación laboral / contratación / prestaciones sociales / liquidación → laboral.
  - Aportes deducibles en renta — frontera con costos_deducciones: el art. 108 ET remite aquí, pero la mecánica del aporte se queda aquí; el efecto en renta queda en costos_deducciones.
  - Nómina electrónica (DSE) → facturacion_electronica.
typical_sources:
  - Ley 100/1993; Ley 21/1982; Ley 89/1988.
  - Decreto 1273/2018 (PILA mes vencido independientes).
  - Decreto 1601/2022 (esquema de presunción de costos independientes).
  - Decreto 1762/2024 (UGPP).
  - Resolución 1995/2019 (PILA), modificatorias.
  - Doctrina UGPP (conceptos publicados, requerimientos típicos).
  - ET art. 114-1 (exoneración).
  - Conceptos UGPP sobre fiscalizaciones, pisos de cotización, IBC.
keyword_anchors:
  - "parafiscales"
  - "seguridad social"
  - "PILA"
  - "UGPP"
  - "aportes salud"
  - "aportes pension"
  - "ARL"
  - "ICBF"
  - "SENA"
  - "caja de compensacion"
  - "exoneracion 114-1"
  - "art 114-1 ET"
  - "IBC"
  - "base de cotizacion"
  - "aportes independientes"
  - "Decreto 1601 de 2022"
  - "presuncion de costos independientes"
  - "fiscalizacion UGPP"
allowed_et_articles:
  - "108"  # condición deducibilidad (cross-ref)
  - "114-1"  # exoneración aportes
  - "126-1"  # aportes voluntarios pensión (cross-ref con renta)
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `reforma_laboral_ley_2466`

```yaml
key: reforma_laboral_ley_2466
label: Reforma Laboral — Ley 2466 de 2025
definition: Régimen transitorio y modificaciones al CST introducidas por Ley 2466/2025 (recargos nocturnos, jornada, contratos a término fijo, aprendices SENA, licencias, otros).
scope_in: |
  - Modificaciones al CST por Ley 2466/2025 (artículos modificados directamente).
  - Decretos reglamentarios de Ley 2466/2025 emitidos por MinTrabajo.
  - Circulares MinTrabajo sobre transición e implementación.
  - Conceptos MinTrabajo sobre interpretación de la reforma.
  - Sentencias de la Corte Constitucional sobre Ley 2466/2025.
  - Calendario de entrada en vigencia escalonada.
scope_out: |
  - CST original (Ley 2663/1950) — artículos NO modificados → laboral.
  - Aportes y exoneración 114-1 ET (no afectados directamente por 2466) → parafiscales_seguridad_social.
  - Reforma pensional (Ley 2381/2024) — distinta reforma → reforma_pensional.
  - Procedimiento ante MinTrabajo (querellas, multas) — no modificado por 2466 → laboral o procedimiento_administrativo_sancionatorio.
typical_sources:
  - Ley 2466/2025 (texto sancionado).
  - Decretos reglamentarios MinTrabajo.
  - Circulares MinTrabajo 2025-2027.
  - Doctrina especializada: Actualícese, Legis, Godoy Hoyos, Brigard Urrutia (publicaciones 2025-2026 sobre la reforma).
keyword_anchors:
  - "Ley 2466"
  - "reforma laboral 2025"
  - "reforma laboral 2466"
  - "recargo nocturno"
  - "jornada laboral 2466"
  - "contrato a termino fijo 2466"
  - "aprendices SENA reforma"
  - "licencia menstrual"
  - "transicion reforma laboral"
  - "MinTrabajo circular reforma"
allowed_et_articles: []  # No es ET, es CST
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
sunset_review: "Reevaluar en v2.x cuando implementación 2466 esté completa (estimado post-2028); posible degradación a subtópico de laboral."
```

#### `proteccion_datos_personales`

```yaml
key: proteccion_datos_personales
label: Protección de Datos Personales (Habeas Data)
definition: Régimen de protección de datos personales (Ley 1581/2012 + reglamentación), aplicable a toda PYME que recolecte, almacene o trate datos de empleados, clientes, proveedores. Incluye el RNBD.
scope_in: |
  - Ley 1581/2012 + Decreto 1377/2013 + Decreto 1074/2015 Libro 2 Parte 2 Título 25.
  - Registro Nacional de Bases de Datos (RNBD) ante la SIC.
  - Política de tratamiento de datos.
  - Autorización del titular.
  - Transferencia y transmisión internacional de datos.
  - Sanciones SIC.
  - Habeas data financiero (Ley 1266/2008) — datos crediticios.
  - Circulares SIC (Circular Externa Única SIC).
scope_out: |
  - Reserva tributaria (art. 583 ET) → procedimiento_tributario (es protección de info tributaria por la DIAN, no datos personales del titular).
  - Datos / tecnología en general (uso de software, ciberseguridad operativa) → datos_tecnologia.
typical_sources:
  - Ley 1581/2012; Ley 1266/2008.
  - Decretos 1377/2013, 886/2014, 1759/2016, 090/2018.
  - Decreto 1074/2015 Libro 2 Parte 2 Título 25 (compilación).
  - Circular Externa Única SIC.
  - Sentencias Corte Constitucional sobre habeas data.
  - Conceptos SIC.
keyword_anchors:
  - "habeas data"
  - "proteccion de datos"
  - "Ley 1581"
  - "RNBD"
  - "registro nacional bases de datos"
  - "SIC datos personales"
  - "politica tratamiento datos"
  - "autorizacion titular"
  - "habeas data financiero"
  - "Ley 1266"
  - "centrales de riesgo"
allowed_et_articles: []
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `niif_pymes` (split de `estados_financieros_niif`)

```yaml
key: niif_pymes
label: NIIF para PYMES (Grupo 2)
definition: Marco técnico normativo NIIF para PYMES — Anexo 2 del DUR 2420/2015. Aplicable a empresas Grupo 2 (PYMEs ordinarias).
scope_in: |
  - Las 35 secciones de NIIF para PYMES (IFRS for SMEs).
  - Decreto 3022/2013 original.
  - DUR 2420/2015 Anexo 2 (vigente).
  - Modificaciones IASB y su adopción local.
  - Conceptos del CTCP sobre aplicación NIIF PYMES.
  - Diferencias contables vs fiscales en aplicación NIIF PYMES (cross-ref a conciliacion_fiscal).
scope_out: |
  - NIIF Plenas (Grupo 1) → niif_plenas.
  - Marco técnico microempresas (Grupo 3) → niif_microempresas.
  - Conciliación fiscal NIIF vs base fiscal → conciliacion_fiscal.
typical_sources:
  - Decreto 2420/2015 Anexo 2.
  - Decreto 2483/2018 (modificación NIIF PYMES — versión revisada 2015).
  - Conceptos CTCP.
  - Material IASB.
keyword_anchors:
  - "NIIF para PYMES"
  - "Grupo 2"
  - "IFRS for SMEs"
  - "Decreto 3022"
  - "Decreto 2420 Anexo 2"
  - "Seccion 17 propiedad planta"
  - "Seccion 23 ingresos"
  - "Seccion 29 impuesto a las ganancias"
  - "CTCP NIIF PYMES"
allowed_et_articles: []
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
note: "Reemplaza estados_financieros_niif (deprecado, split en niif_pymes / niif_plenas / niif_microempresas)."
```

#### `niif_plenas`

```yaml
key: niif_plenas
label: NIIF Plenas (Grupo 1)
definition: Marco técnico normativo NIIF Plenas — Anexo 1 del DUR 2420/2015. Aplicable a empresas Grupo 1 (emisores valores, entidades de interés público, empresas grandes).
scope_in: |
  - NIIF Plenas (IFRS Standards completos): NIC 1-41, NIIF 1-17.
  - DUR 2420/2015 Anexo 1.
  - Modificaciones IASB y adopción local.
  - Conceptos CTCP sobre aplicación NIIF Plenas.
scope_out: |
  - NIIF para PYMES → niif_pymes.
  - Microempresas → niif_microempresas.
typical_sources:
  - Decreto 2420/2015 Anexo 1 + modificatorios.
  - Conceptos CTCP.
  - Material IASB.
keyword_anchors:
  - "NIIF Plenas"
  - "Grupo 1"
  - "IFRS"
  - "NIC 12"
  - "NIIF 15 ingresos"
  - "NIIF 16 arrendamientos"
  - "NIIF 9 instrumentos financieros"
allowed_et_articles: []
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `niif_microempresas`

```yaml
key: niif_microempresas
label: Marco Técnico Microempresas (Grupo 3)
definition: Marco simplificado de información financiera para microempresas — Anexo 3 del DUR 2420/2015.
scope_in: |
  - Marco técnico Grupo 3 (simplificado).
  - DUR 2420/2015 Anexo 3.
  - Decreto 2706/2012 original.
scope_out: |
  - NIIF PYMES → niif_pymes.
  - NIIF Plenas → niif_plenas.
typical_sources:
  - Decreto 2706/2012.
  - DUR 2420/2015 Anexo 3.
  - Conceptos CTCP sobre microempresas.
keyword_anchors:
  - "microempresas"
  - "Grupo 3"
  - "Decreto 2706"
  - "marco simplificado"
  - "informacion financiera microempresas"
allowed_et_articles: []
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `regimen_cambiario`

```yaml
key: regimen_cambiario
label: Régimen Cambiario (DCIN-83)
definition: Régimen cambiario para operaciones de cambio (importaciones, exportaciones, inversión extranjera, endeudamiento externo) ante el Banco de la República.
scope_in: |
  - Resolución Externa 1/2018 JDBR + DCIN-83 (compilación).
  - Declaración de cambio (formulario 1, 2, 3, 4, 5).
  - Inversión extranjera directa (registro, sustitución, cancelación).
  - Endeudamiento externo (registro, novación, cancelación).
  - Cuentas de compensación.
  - Sanciones cambiarias (DIAN — cumple función cambiaria).
scope_out: |
  - Régimen tributario de la inversión extranjera (retención dividendos, presencia económica significativa) → declaracion_renta o dividendos_y_distribucion_utilidades.
  - Aspectos contables de operaciones en moneda extranjera (NIC 21) → niif_pymes / niif_plenas.
  - Precios de transferencia → precios_transferencia.
typical_sources:
  - Resolución Externa 1/2018 JDBR.
  - DCIN-83 (Banco de la República).
  - Boletines del Banco de la República.
  - Decreto 1735/1993 (régimen cambiario base).
  - Estatuto de Inversiones Internacionales (Decreto 1068/2015 Parte 17 Cap. 2).
  - Conceptos Banrep.
  - Sanciones cambiarias DIAN.
keyword_anchors:
  - "regimen cambiario"
  - "DCIN-83"
  - "declaracion de cambio"
  - "inversion extranjera"
  - "endeudamiento externo"
  - "cuenta de compensacion"
  - "Banco de la Republica cambios"
  - "Resolucion 1 2018 JDBR"
  - "sancion cambiaria"
allowed_et_articles: []
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `dividendos_y_distribucion_utilidades`

```yaml
key: dividendos_y_distribucion_utilidades
label: Dividendos y Distribución de Utilidades
definition: Régimen tributario y societario de la distribución de utilidades, dividendos en efectivo, en acciones, en especie. Incluye tarifas de dividendos arts. 242, 242-1, 245 ET y mecánica societaria.
scope_in: |
  - Arts. 48, 49 ET (utilidades no gravadas, fórmula art. 49).
  - Arts. 242, 242-1 ET (tarifa dividendos personas naturales residentes).
  - Art. 245 ET (tarifa dividendos extranjeros / no residentes).
  - Retención en la fuente sobre dividendos (Decreto 1457/2020 y modificatorios).
  - Decisión societaria de distribución (Código de Comercio, Ley 222/1995).
  - Reservas legales y voluntarias.
  - Dividendos en especie.
  - Disminución de capital con devolución de aportes (vs dividendo).
scope_out: |
  - Cálculo de la utilidad contable que origina el dividendo → niif_pymes / niif_plenas.
  - Constitución y reformas societarias en general → comercial_societario.
  - Ganancia ocasional por venta de acciones → ganancia_ocasional.
typical_sources:
  - ET arts. 48, 49, 242, 242-1, 245.
  - Decreto 1457/2020 (retención sobre dividendos) + modificatorios.
  - Código de Comercio arts. 451-456 (distribución utilidades).
  - Ley 222/1995 (reformas).
  - Conceptos DIAN sobre dividendos.
  - Doctrina firmas (Brigard Urrutia, PHR, Big4) sobre reformas tributarias y dividendos.
keyword_anchors:
  - "dividendos"
  - "distribucion utilidades"
  - "tarifa dividendos"
  - "art 48 ET"
  - "art 49 ET"
  - "art 242 ET"
  - "art 242-1 ET"
  - "art 245 ET"
  - "retencion dividendos"
  - "Decreto 1457 de 2020"
  - "dividendos en especie"
  - "disminucion capital"
  - "reserva legal"
allowed_et_articles:
  - "48"
  - "49"
  - "30"   # definición dividendo
  - "242"
  - "242-1"
  - "245"
  - "246"
  - "246-1"
  - "247"
  - "33-3"
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

#### `regimen_tributario_especial_esal`

```yaml
key: regimen_tributario_especial_esal
label: Régimen Tributario Especial — ESAL
definition: Régimen tributario especial aplicable a Entidades Sin Ánimo de Lucro (ESAL): fundaciones, corporaciones, asociaciones, cooperativas. Calificación, permanencia, actualización ante la DIAN.
scope_in: |
  - Arts. 356-364-6 ET.
  - Decreto 2150/2017 (reglamentación RTE).
  - Calificación inicial al RTE (formulario web DIAN).
  - Actualización anual / permanencia.
  - Requisitos para acceder al beneficio (objeto social meritorio, no distribución, etc.).
  - Donaciones recibidas (descuento o deducción para el donante).
  - Cooperativas (Ley 79/1988; régimen especial cooperativo art. 19-4 ET).
  - Memoria económica anual.
scope_out: |
  - ESAL régimen ordinario (que no califican / pierden RTE) → declaracion_renta.
  - Donaciones — efecto en el donante → descuentos_tributarios_renta o costos_deducciones.
  - Constitución de la entidad ESAL → comercial_societario (subtópico ESAL constitución).
typical_sources:
  - ET arts. 356-364-6.
  - Decreto 2150/2017.
  - DUR 1625/2016 Sección Régimen Tributario Especial.
  - Conceptos DIAN sobre RTE.
  - Resoluciones DIAN sobre formularios y trámites RTE.
  - Ley 79/1988 (cooperativas).
keyword_anchors:
  - "ESAL"
  - "regimen tributario especial"
  - "RTE"
  - "fundacion"
  - "asociacion sin animo de lucro"
  - "cooperativa"
  - "Decreto 2150 de 2017"
  - "art 356 ET"
  - "art 19 ET"
  - "art 19-4 ET"
  - "calificacion RTE"
  - "permanencia RTE"
  - "memoria economica"
  - "donaciones a ESAL"
allowed_et_articles:
  - "19"
  - "19-1"
  - "19-2"
  - "19-3"
  - "19-4"
  - "19-5"
  - "356"
  - "356-1"
  - "356-2"
  - "356-3"
  - "357"
  - "358"
  - "358-1"
  - "359"
  - "360"
  - "361"
  - "362"
  - "363"
  - "364"
  - "364-1"
  - "364-2"
  - "364-3"
  - "364-4"
  - "364-5"
  - "364-6"
parent: null
status: active
version_added: "v2.0 (2026-04-25)"
```

---

### 2.2 Tópicos RECLASIFICADOS (re-fundación de los 12 vacíos)

Para no inflar el documento, doy las plantillas mínimas (definition + scope_in + scope_out + keyword_anchors + allowed_et_articles + parent). Los demás campos siguen el patrón de §2.1.

#### `ingresos_fiscales_renta`

- **definition:** Tratamiento fiscal de los ingresos en el impuesto de renta — definición, realización, INCRNGO, ingresos no gravados.
- **scope_in:** ET arts. 26-57 (Libro 1 Cap. 1 Tít. 1) — definición de ingreso, ingreso ordinario vs extraordinario, realización para obligados/no obligados a llevar contabilidad, ingresos no constitutivos de renta ni ganancia ocasional (INCRNGO).
- **scope_out:** clasificación operativa de ingresos en la declaración → declaracion_renta. Renta exenta → rentas_exentas. Ganancia ocasional → ganancia_ocasional.
- **keyword_anchors:** `["ingresos fiscales", "INCRNGO", "ingresos no gravados", "realizacion del ingreso", "art 26 ET", "art 27 ET", "art 28 ET", "art 36 ET", "art 36-3 ET", "ingreso ordinario"]`
- **allowed_et_articles:** `["26", "27", "28", "29", "30", "31", "32", "33", "33-1", "33-2", "33-3", "33-4", "33-5", "34", "35", "35-1", "36", "36-1", "36-2", "36-3", "36-4", "37", "38", "39", "40", "40-1", "41", "42", "43", "44", "45", "46", "46-1", "47", "47-1", "47-2", "48", "49", "50", "51", "52", "53", "54", "55", "56", "56-1", "57", "57-1", "57-2"]`
- **parent:** `declaracion_renta` (subtópico).

#### `patrimonio_fiscal_renta`

- **definition:** Determinación del patrimonio fiscal en la declaración de renta — ET arts. 261-298.
- **scope_in:** Patrimonio bruto, deudas, patrimonio líquido, valoración de activos (efectivo, inventarios, propiedad planta, intangibles, inversiones), conciliación con patrimonio contable.
- **scope_out:** Conciliación contable-fiscal del patrimonio (formato 2516 sección 2) → conciliacion_fiscal. Impuesto al patrimonio (es un impuesto distinto) → impuesto_al_patrimonio.
- **keyword_anchors:** `["patrimonio fiscal", "patrimonio bruto", "patrimonio liquido", "valoracion de activos", "art 261 ET", "art 267 ET", "art 277 ET", "art 287 ET", "deudas fiscales", "valor patrimonial"]`
- **allowed_et_articles:** `["261", "262", "263", "264", "265", "266", "267", "267-1", "268", "269", "270", "271", "271-1", "272", "273", "274", "275", "276", "277", "278", "279", "280", "281", "282", "283", "284", "285", "286", "287", "288", "289", "290", "291", "292", "292-1", "292-2", "292-3", "293", "293-1", "293-2", "294", "295", "295-1", "295-2", "295-3", "296", "296-1", "296-2", "296-3", "297", "297-1", "297-2", "297-3", "298"]`
- **parent:** `declaracion_renta` (subtópico).

#### `firmeza_declaraciones`

- **definition:** Reglas de firmeza de declaraciones tributarias — plazos generales y especiales (beneficio auditoría, pérdidas fiscales, precios de transferencia).
- **scope_in:** ET art. 714 (firmeza general), 689-3 (beneficio auditoría), 117 Ley 2010/2019 (firmeza pérdidas), 147 ET parágrafo (compensación pérdidas — firmeza relacionada), 260-5 par. (firmeza precios transferencia), interrupción y suspensión de firmeza.
- **scope_out:** Procedimiento de fiscalización (requerimientos, liquidaciones) → procedimiento_tributario. Beneficio auditoría como mecanismo per se → beneficio_auditoria.
- **keyword_anchors:** `["firmeza", "art 714 ET", "firmeza declaracion", "firmeza renta", "interrupcion firmeza", "suspension firmeza", "prescripcion fiscalizacion", "firmeza perdidas fiscales", "art 117 Ley 2010"]`
- **allowed_et_articles:** `["705", "705-1", "706", "714", "147", "689-3", "260-5"]`
- **parent:** `procedimiento_tributario` (subtópico).

#### `devoluciones_saldos_a_favor`

- **definition:** Devolución y compensación de saldos a favor en impuestos nacionales (renta, IVA, retención) ante la DIAN.
- **scope_in:** ET arts. 850-865, Decreto 1206/2024 (devolución automática), Resolución DIAN procedimiento, requisitos, plazos, garantías, intereses moratorios a favor del contribuyente, compensación entre impuestos.
- **scope_out:** Saldos a favor que no se devuelven sino se imputan al período siguiente (mecánica de la declaración) → declaracion_renta o iva.
- **keyword_anchors:** `["devolucion saldo a favor", "compensacion saldo a favor", "art 850 ET", "art 855 ET", "art 857 ET", "Decreto 1206 de 2024", "devolucion automatica", "intereses devolucion", "garantia devolucion"]`
- **allowed_et_articles:** `["850", "850-1", "851", "852", "853", "854", "855", "856", "857", "857-1", "858", "859", "860", "861", "862", "863", "864", "865"]`
- **parent:** `procedimiento_tributario` (subtópico).

#### `ganancia_ocasional`

- **definition:** Impuesto complementario de ganancias ocasionales — ET arts. 299-318.
- **scope_in:** Hechos gravables (venta activos fijos > 2 años, herencias, legados, donaciones, loterías, indemnizaciones), tarifas (15%, 20% loterías), depuración, costos fiscales especiales, exenciones (vivienda, herederos línea descendente, etc.), ganancia ocasional gravable vs no gravable.
- **scope_out:** Ingreso de venta < 2 años → renta ordinaria → declaracion_renta. Conciliación con NIIF → conciliacion_fiscal.
- **keyword_anchors:** `["ganancia ocasional", "art 299 ET", "art 300 ET", "art 311 ET", "art 313 ET", "tarifa 15 por ciento", "venta activo fijo", "herencia", "donacion", "loteria", "indemnizacion seguro", "exencion vivienda"]`
- **allowed_et_articles:** `["299", "300", "301", "302", "303", "303-1", "304", "305", "306", "306-1", "307", "308", "309", "310", "311", "311-1", "312", "313", "314", "315", "316", "317", "318"]`
- **parent:** null (top-level autónomo — es impuesto complementario distinto).

#### `renta_liquida_gravable`

- **definition:** Determinación de la renta líquida gravable — ET arts. 178-187 + arts. 188-191 (renta presuntiva como referencia).
- **scope_in:** Cálculo de la renta líquida ordinaria, comparación con renta presuntiva, compensación de pérdidas fiscales (art. 147), compensación de excesos de renta presuntiva (art. 191).
- **scope_out:** Renta presuntiva en sí (cálculo del 0,25%) → renta_presuntiva. Tarifas y TTD → tarifas_renta_y_ttd.
- **keyword_anchors:** `["renta liquida gravable", "renta liquida ordinaria", "compensacion perdidas", "art 147 ET", "art 178 ET", "exceso renta presuntiva", "art 191 ET"]`
- **allowed_et_articles:** `["178", "179", "180", "181", "182", "183", "184", "185", "186", "187", "147", "191"]`
- **parent:** `declaracion_renta` (subtópico).

#### `renta_presuntiva` (NUEVO subtópico)

- **definition:** Renta presuntiva — ET arts. 188-191 (cálculo 0,25% del patrimonio líquido).
- **scope_in:** Cálculo, depuración del patrimonio líquido base, exclusiones (acciones nacionales, primeros 8.000 UVT vivienda, etc.), comparación con renta líquida ordinaria, excesos.
- **scope_out:** Compensación de excesos en años siguientes → renta_liquida_gravable. Patrimonio fiscal → patrimonio_fiscal_renta.
- **keyword_anchors:** `["renta presuntiva", "art 188 ET", "art 189 ET", "0.25 por ciento patrimonio", "depuracion patrimonio liquido", "exclusion acciones renta presuntiva"]`
- **allowed_et_articles:** `["188", "189", "190", "191"]`
- **parent:** `declaracion_renta` (subtópico).

#### `descuentos_tributarios_renta`

- **definition:** Descuentos del impuesto de renta — ET arts. 254-260.
- **scope_in:** Descuento por impuestos pagados en el exterior (art. 254), donaciones (arts. 257, 258), CTeI (art. 256), inversión bienes de capital (art. 258-1), generación de empleo (art. 257-1).
- **scope_out:** Descuento del SIMPLE → regimen_simple_tributacion. Descuentos del IVA descontable → iva.
- **keyword_anchors:** `["descuento tributario", "art 254 ET", "art 256 ET", "art 257 ET", "art 258 ET", "art 258-1 ET", "donaciones descuento", "CTeI descuento", "impuestos exterior descuento", "tax credit"]`
- **allowed_et_articles:** `["254", "255", "256", "256-1", "257", "257-1", "257-2", "258", "258-1", "258-2", "259", "259-1", "260"]`
- **parent:** `declaracion_renta` (subtópico).

#### `retencion_fuente_general` (renombrado de `anticipos_retenciones_a_favor`)

- **definition:** Régimen general de retención en la fuente (a título de renta) — ET arts. 365-419.
- **scope_in:** Conceptos sometidos a retención, agentes retenedores, tarifas, autorretención, certificados de retención (art. 378), declaración mensual (formulario 350), anticipo del impuesto (art. 807 ET).
- **scope_out:** Retención de IVA → iva. Retención de timbre → impuesto_timbre. Sanciones por no retener → procedimiento_tributario.
- **keyword_anchors:** `["retencion en la fuente", "agente retenedor", "autorretencion", "art 365 ET", "art 368 ET", "art 378 ET", "certificado de retencion", "formulario 350", "anticipo del impuesto", "art 807 ET"]`
- **allowed_et_articles:** `["365", "366", "366-1", "367", "368", "368-1", "368-2", "369", "370", "371", "372", "373", "374", "375", "376", "377", "378", "378-1", "379", "380", "381", "382", "383", "384", "385", "386", "387", "387-1", "388", "389", "390", "391", "392", "393", "394", "395", "396", "397", "398", "399", "400", "401", "401-1", "401-2", "401-3", "402", "403", "404", "404-1", "405", "406", "407", "408", "409", "410", "411", "412", "413", "414", "415", "416", "417", "418", "419", "807"]`
- **parent:** null (top-level — es régimen autónomo aplicado a múltiples impuestos).

#### `tarifas_renta_y_ttd` (renombrado de `tarifas_tasa_minima_renta`)

- **definition:** Tarifas del impuesto de renta y Tasa Mínima de Tributación Depurada (TTD).
- **scope_in:** Tarifa general PJ (art. 240), tarifa zona franca (240-1), tarifas PN cédula general (art. 241 + 336), tarifa dividendos (242, 242-1, 245), TTD (parágrafo 6 art. 240).
- **scope_out:** Cálculo de la TTD operativo paso a paso → conciliacion_fiscal o seccion específica TTD. Tarifa SIMPLE → regimen_simple_tributacion.
- **keyword_anchors:** `["tarifa renta", "art 240 ET", "art 240-1 ET", "art 241 ET", "tasa minima tributacion", "TTD", "parrafo 6 art 240", "tarifa zona franca", "tarifa progresiva personas naturales"]`
- **allowed_et_articles:** `["240", "240-1", "241", "242", "242-1", "243", "245"]`
- **parent:** `declaracion_renta` (subtópico).

#### `beneficio_auditoria`

- **definition:** Beneficio de auditoría — firmeza anticipada por incremento del impuesto neto de renta (ET art. 689-3).
- **scope_in:** Requisitos (incremento INR 25% / 35%), exclusiones, firmeza 6/12 meses, casos de no aplicación (pérdidas, INR cero, beneficio auditoría inválido), interacción con saldos a favor.
- **scope_out:** Firmeza general → firmeza_declaraciones.
- **keyword_anchors:** `["beneficio de auditoria", "art 689-3 ET", "firmeza anticipada", "incremento INR", "incremento impuesto neto renta", "firmeza 6 meses", "firmeza 12 meses"]`
- **allowed_et_articles:** `["689-3"]`
- **parent:** null (top-level — es mecanismo distintivo y vigente AG 2024-2026).

#### `conciliacion_fiscal`

- **definition:** Conciliación fiscal — formato 2516 (PJ obligadas) y formato 2517 (PN obligadas), DUR 1625/2016 art. 1.7.1.
- **scope_in:** Diferencias temporarias y permanentes, llenado del formato, casos prácticos de partidas conciliatorias (depreciaciones, deterioros, provisiones, NIIF vs ET).
- **scope_out:** Marco NIIF en sí → niif_pymes / niif_plenas / niif_microempresas. Diferencias por revaluación de PP&E → niif_pymes (con cross-ref). Tratamiento del impuesto diferido → niif_pymes (Sección 29) / niif_plenas (NIC 12).
- **keyword_anchors:** `["conciliacion fiscal", "formato 2516", "formato 2517", "diferencias temporarias", "diferencias permanentes", "DUR 1.7.1", "Resolucion 000071 de 2019", "Resolucion 000027 de 2024", "ESF y ERI conciliacion"]`
- **allowed_et_articles:** `["772-1"]`
- **parent:** null (top-level — es obligación autónoma).

#### `regimen_sancionatorio_extemporaneidad`

- **definition:** Régimen sancionatorio tributario — sanciones por extemporaneidad, inexactitud, no declarar, errores en información.
- **scope_in:** ET arts. 641, 642, 644, 647, 648, 651 (info exógena), 652 (factura), 657 (clausura), 658-3 (RUT), 658-1 (representación), reducción de sanciones art. 640, gradualidad.
- **scope_out:** Mecanismo procesal (requerimiento, liquidación, recurso) → procedimiento_tributario.
- **keyword_anchors:** `["sancion por extemporaneidad", "art 641 ET", "art 644 ET", "sancion por inexactitud", "art 647 ET", "art 648 ET", "art 651 ET", "art 652 ET", "art 657 ET", "art 658-3 ET", "reduccion sancion", "art 640 ET", "gradualidad sancion"]`
- **allowed_et_articles:** `["640", "641", "642", "643", "644", "645", "646", "647", "647-1", "648", "649", "650-1", "650-2", "651", "652", "652-1", "653", "654", "655", "656", "657", "657-1", "657-2", "658", "658-1", "658-2", "658-3"]`
- **parent:** `procedimiento_tributario` (subtópico).

---

### 2.3 Tópicos magnet existentes — re-definición

Estos ya existen pero el audit mostró contaminación. Las re-definiciones siguientes los hacen mutuamente excluyentes con el resto.

#### `iva` (re-definido)

- **definition:** Impuesto sobre las Ventas (IVA) — ET Libro 3, arts. 420-513. Cubre el derecho sustantivo del impuesto: hecho generador, base, tarifa, exenciones, responsabilidad, impuestos descontables.
- **scope_in:** Hecho generador, sujetos, base gravable, tarifas (general 19%, diferencial 5%, exclusiones, exenciones), regímenes de responsabilidad, retención de IVA (reteIVA), impuestos descontables (art. 488), facturación con IVA, periodicidad (art. 600).
- **scope_out:**
  - Mecánica procesal de declaración / corrección / firmeza / sanción IVA → procedimiento_tributario.
  - Devolución del saldo a favor IVA → devoluciones_saldos_a_favor.
  - Documentación electrónica del IVA (factura) → facturacion_electronica.
  - Renta sobre el IVA (no es directamente — descartar).
- **keyword_anchors:** `["IVA", "impuesto valor agregado", "art 420 ET", "art 437 ET", "art 437-1 ET", "art 437-2 ET", "art 477 ET", "art 488 ET", "tarifa 19", "tarifa 5", "reteIVA", "responsable IVA", "no responsable IVA", "impuesto descontable", "regimen comun IVA", "formulario 300"]`
- **allowed_et_articles:** todos los arts. del ET Libro 3 (420-513) salvo procedimentales puros que se vayan a procedimiento.
- **parent:** null.

#### `procedimiento_tributario` (re-definido como contenedor de subtópicos)

- **definition:** Procedimiento tributario — ET Libro 5 — fiscalización, recursos, sanciones, firmeza, devoluciones, cobro coactivo.
- **scope_in:** Marco general del Libro 5 ET; fiscalización (arts. 684-696); discusión (709-734); sanciones (640-658-3); firmeza (705, 705-1, 706, 714); devoluciones (850-865); cobro coactivo (823-849).
- **scope_out:** Derecho sustantivo de cada impuesto → topic correspondiente (iva, declaracion_renta, etc.).
- **subtopics suggested:** `firmeza_declaraciones`, `devoluciones_saldos_a_favor`, `regimen_sancionatorio_extemporaneidad`, `fiscalizacion_dian`, `cobro_coactivo_y_emplazamientos`.
- **keyword_anchors:** `["procedimiento tributario", "Libro 5 ET", "fiscalizacion", "requerimiento especial", "liquidacion oficial", "recurso reconsideracion", "art 705 ET", "art 714 ET", "cobro coactivo", "embargo DIAN"]`

#### `comercial_societario` (fusionado con `obligaciones_mercantiles`)

- **definition:** Régimen comercial y societario — Código de Comercio, Ley 222/1995, Ley 1258/2008 (SAS), Ley 1116/2006 (insolvencia), obligaciones del comerciante, libros, registro mercantil, asambleas, reformas, transformación, fusión, escisión, disolución y liquidación.
- **scope_in:** Constitución de sociedades, tipos societarios (SAS, S.A., LTDA., E.U.), registro mercantil ante Cámara de Comercio, libros oficiales, asambleas y juntas, reformas estatutarias, transformación, fusión, escisión, disolución, liquidación, insolvencia (Ley 1116/2006, Decreto 560/2020 emergencia covid — verificar vigencia).
- **scope_out:**
  - Distribución de utilidades / dividendos → dividendos_y_distribucion_utilidades.
  - Constitución de ESAL (régimen tributario) → regimen_tributario_especial_esal.
  - Beneficiario final → beneficiario_final_rub.
  - Libros oficiales en NIIF (cómo se llevan) → niif_pymes / niif_plenas (con cross-ref).
  - Reforma laboral en relaciones contractuales → laboral / reforma_laboral_ley_2466.

#### `beneficiario_final_rub` (re-definido)

- **definition:** Registro Único de Beneficiarios Finales (RUB) — Ley 2155/2021 art. 4, Resolución DIAN 000164/2021 y modificatorias. Identificación de personas naturales beneficiarias finales de personas jurídicas y estructuras sin personería jurídica.
- **scope_in:** Sujetos obligados, identificación del BF (criterios participación >5%, control efectivo), información a reportar, plazos de actualización, sanciones art. 658-3 ET por no actualizar.
- **scope_out:** RUT general → rut_y_responsabilidades_tributarias. Régimen ESAL en sí → regimen_tributario_especial_esal. Sanciones generales del 658-3 por RUT → rut_y_responsabilidades_tributarias.
- **keyword_anchors:** `["RUB", "registro unico beneficiarios", "beneficiario final", "Ley 2155 art 4", "Resolucion 000164 de 2021", "actualizacion RUB", "estructura sin personeria juridica"]`
- **allowed_et_articles:** `["631-5", "658-3"]` (concretamente).

#### `laboral` (re-definido — boundary explícito)

- **definition:** Régimen laboral — CST (Ley 2663/1950) y reformas anteriores a Ley 2466/2025 vigentes; contratación, prestaciones sociales, terminación, seguridad y salud en el trabajo (Decreto 1072/2015 Libro 2 Parte 2 Título 4 Capítulo 6).
- **scope_in:** CST (no modificado por 2466), tipos de contrato, jornada (no modificada), prestaciones sociales (cesantías, intereses, prima, vacaciones), terminación (justas e injustas), liquidaciones, SST, conflictos laborales individuales y colectivos, querellas MinTrabajo.
- **scope_out:**
  - Modificaciones al CST por Ley 2466/2025 → reforma_laboral_ley_2466.
  - Aportes a seguridad social y parafiscales → parafiscales_seguridad_social.
  - Reforma pensional (Ley 2381/2024) → reforma_pensional.
  - Nómina electrónica (DSE) → facturacion_electronica.
  - Deducción fiscal de la nómina (art. 108 ET) → costos_deducciones (con cross-ref a parafiscales_seguridad_social).
- **keyword_anchors:** `["CST", "codigo sustantivo trabajo", "contrato laboral", "contrato termino fijo", "contrato termino indefinido", "prestaciones sociales", "cesantias", "prima de servicios", "vacaciones", "liquidacion contrato", "justa causa", "indemnizacion despido", "SST", "seguridad y salud en el trabajo", "Decreto 1072 de 2015"]`

---

## 3. Bloque §6.3 — Inputs opcionales

### 3.1 Edge-case docs (test cases para el clasificador)

Estos son documentos con ambigüedad real que deberías incluir en una suite de evaluación post-rebuild:

| Doc / tema | Topic ambiguo entre | Topic correcto (mi voto) | Por qué |
|---|---|---|---|
| Concepto DIAN sobre retención en la fuente sobre dividendos pagados a no residentes | retencion_fuente_general / dividendos_y_distribucion_utilidades / declaracion_renta | dividendos_y_distribucion_utilidades | El tópico de fondo es la mecánica del dividendo (residente o no, tarifa). La retención es accesoria. |
| Decreto 175/2025 (reactivación tarifa 1% timbre bajo emergencia) | impuesto_timbre / decretos_emergencia_economica | impuesto_timbre | El emergency framing es contextual, el contenido sustantivo es timbre. |
| Concepto UGPP sobre IBC de un independiente que también es socio | parafiscales_seguridad_social / declaracion_renta | parafiscales_seguridad_social | Tema central es la base de cotización, no el impuesto sobre el ingreso. |
| Sentencia C-XXX/2025 que suspende el Decreto 1474/2025 | declaracion_renta / decretos_emergencia / [tópico afectado] | El tópico afectado por el decreto suspendido (probablemente impuesto_timbre o tarifas_renta_y_ttd) | La sentencia importa por su efecto material, no por el formato. |
| Resolución DIAN sobre formato 2516 (conciliación) en ESAL | regimen_tributario_especial_esal / conciliacion_fiscal | conciliacion_fiscal | La aplicación a ESAL es un parámetro, no el tema. |
| Concepto sobre deducción de nómina cuando no se pagaron parafiscales | costos_deducciones / parafiscales_seguridad_social | costos_deducciones | El tema es la deducibilidad del gasto. Los parafiscales son condición. |
| Doctrina sobre aplicación del art. 771-2 ET (factura como soporte) | facturacion_electronica / costos_deducciones | costos_deducciones | El tema es la procedencia del costo/deducción. La factura es soporte. |
| Concepto sobre dividendos en especie (entrega activos) | dividendos_y_distribucion_utilidades / ganancia_ocasional | dividendos_y_distribucion_utilidades, con cross-ref a ganancia_ocasional | El acto es distribución; la ganancia ocasional es efecto en el receptor del activo. |

### 3.2 User-question samples (30 preguntas reales con topic asignado)

Aquí va una lista que puedes usar para validación post-rebuild. Las redacto como las haría un contador, sin incluir números de artículo (siguiendo la convención de testing del proyecto):

| # | Pregunta | Topic esperado |
|---|---|---|
| 1 | "Mi cliente firmó una promesa de compraventa por 800 millones, ¿debe pagar timbre nacional?" | impuesto_timbre |
| 2 | "Cambié de actividad económica en mi sociedad, ¿cómo actualizo el RUT?" | rut_y_responsabilidades_tributarias |
| 3 | "El nuevo socio entró con el 30%, ¿en qué plazo debo actualizar el RUB?" | beneficiario_final_rub |
| 4 | "Mi PYME no pagó los aportes a seguridad social a tiempo del trimestre pasado, ¿cómo regularizo y qué pasa con la deducción?" | parafiscales_seguridad_social (con cross-ref costos_deducciones) |
| 5 | "¿Aplica la nueva jornada de 42 horas a mi empresa de manufactura desde 2026?" | reforma_laboral_ley_2466 |
| 6 | "Como contador con base de datos de clientes, ¿debo registrarme en el RNBD de la SIC?" | proteccion_datos_personales |
| 7 | "Mi cliente importa de China, ¿cómo declaro el cambio?" | regimen_cambiario |
| 8 | "Vamos a distribuir utilidades de los últimos 3 años, ¿cuánto retengo a los socios personas naturales colombianas?" | dividendos_y_distribucion_utilidades |
| 9 | "La fundación de mi cliente perdió la calificación al RTE, ¿qué pasa?" | regimen_tributario_especial_esal |
| 10 | "¿Cuándo prescribe la facultad de la DIAN de cuestionar mi declaración de renta?" | firmeza_declaraciones |
| 11 | "Tengo saldo a favor en renta del año pasado, ¿lo solicito en devolución o lo imputo?" | devoluciones_saldos_a_favor |
| 12 | "Mi cliente vendió el local del negocio que tenía hace 8 años, ¿cómo liquido el impuesto?" | ganancia_ocasional |
| 13 | "El patrimonio líquido es muy alto pero la operación dio pérdida, ¿qué pasa con la renta presuntiva?" | renta_presuntiva |
| 14 | "Mi cliente compró maquinaria nueva en 2025, ¿le sirve el descuento del IVA en bienes de capital?" | descuentos_tributarios_renta |
| 15 | "Soy nuevo agente retenedor en la fuente, ¿cómo presento mi primer formulario?" | retencion_fuente_general |
| 16 | "¿Le aplica el beneficio de auditoría a un cliente con pérdida fiscal?" | beneficio_auditoria |
| 17 | "Estoy llenando el formato 2516, ¿cómo concilio una depreciación NIIF más alta que la fiscal?" | conciliacion_fiscal |
| 18 | "¿Qué sanción me aplica si presento renta 2 días tarde?" | regimen_sancionatorio_extemporaneidad |
| 19 | "Mi cliente vende productos exentos de IVA, ¿cómo tramita la devolución del saldo a favor?" | iva (con cross-ref devoluciones_saldos_a_favor) |
| 20 | "Necesito constituir una SAS para un cliente, ¿cuáles son los pasos?" | comercial_societario |
| 21 | "El proveedor no me envía la factura electrónica, ¿pierdo la deducción?" | costos_deducciones (con cross-ref facturacion_electronica) |
| 22 | "Mi cliente Grupo 2 pasó a Grupo 1 por crecimiento, ¿qué cambia?" | niif_pymes (con cross-ref niif_plenas) |
| 23 | "Tengo un independiente que cobra honorarios mixtos, ¿cuál es su base de cotización?" | parafiscales_seguridad_social |
| 24 | "¿Qué documentos debe conservar el comerciante y por cuánto tiempo?" | comercial_societario |
| 25 | "Mi cliente recibió una herencia, ¿cómo la declara?" | ganancia_ocasional |
| 26 | "Llegó un emplazamiento para corregir la declaración de IVA, ¿qué hago?" | procedimiento_tributario |
| 27 | "Vendí acciones que tenía hace 6 meses, ¿es renta o ganancia ocasional?" | declaracion_renta o ganancia_ocasional (test ambigüedad) |
| 28 | "¿Cuál es la tarifa del impuesto si la sociedad está en zona franca?" | tarifas_renta_y_ttd |
| 29 | "Mi cliente del SIMPLE quiere salirse y volver al ordinario, ¿qué consecuencias tiene?" | regimen_simple_tributacion (con cross-ref declaracion_renta) |
| 30 | "Hay un acuerdo entre socios para distribuir utilidades en activos en especie, ¿cómo lo manejo fiscalmente?" | dividendos_y_distribucion_utilidades |

### 3.3 Currency / vigencia hints — documentos que cambian con frecuencia

Estos tópicos requieren `currency_awareness: high` en la metadata, y revisión de vigencia al menos anual:

| Tópico | Cambia anualmente | Cambia trimestralmente | Cambia con cada reforma tributaria |
|---|---|---|---|
| `tarifas_renta_y_ttd` | UVT cada año | — | Sí |
| `parafiscales_seguridad_social` | Salario mínimo / IBC; actos UGPP | — | Sí |
| `iva` (especialmente bienes excluidos / exentos) | — | — | Sí (siempre se mueven listas) |
| `rut_y_responsabilidades_tributarias` | Resoluciones DIAN sobre formato | — | Cuando cambian códigos |
| `facturacion_electronica` | Resoluciones DIAN periódicas | Calendarios de implementación | Cuando hay nuevos sujetos obligados |
| `informacion_exogena` | Resolución anual DIAN | — | Sí |
| `calendario_tributario` | Decreto plazos cada año | — | — |
| `impuesto_timbre` | — | — | Sí (Decreto 175/2025 ejemplo de movimiento abrupto) |
| `reforma_laboral_ley_2466` | Reglamentación escalonada | Circulares MinTrabajo | — (es reforma una vez) |
| `reforma_pensional` | Reglamentación pendiente | Sentencias Corte | — |
| `regimen_simple_tributacion` | UVT de umbrales | — | Sí |
| `precios_transferencia` | Resolución anual de tasas | — | Sí |
| `regimen_cambiario` | Resoluciones JDBR | Boletines Banrep | — |

---

## 4. Recomendaciones adicionales para el equipo de ingeniería

Estas son observaciones que salen del análisis y que conviene tener en cuenta al implementar v2:

### 4.1 Sobre el `allowed_et_articles` filter

La protección por allow-list de artículos ET es **excelente para tópicos de derecho tributario sustantivo** (donde cada tópico tiene un rango bien delimitado del ET). Pero tiene **limitaciones obvias** para tópicos no-tributarios:

- Tópicos como `laboral`, `proteccion_datos_personales`, `comercial_societario`, `regimen_cambiario`, `parafiscales_seguridad_social`, `niif_*` **no se citan con artículos del ET**. Se citan con CST, Códigos, Decretos, Resoluciones, Circulares.
- Para esos tópicos sugiero implementar un **`allowed_norm_anchors`** análogo: lista de patrones canónicos como `["CST art. \d+", "Decreto 1072 de 2015", "Ley 1581/2012", ...]`.
- O bien aceptar que el filtro por allow-list aplica solo a tópicos con `et_centric: true` y para los demás se usa otra heurística (autoridad emisora, palabras clave en el path del corpus, etc.).

### 4.2 Sobre el patrón "tópico vs subtópico"

He propuesto algunos como subtópico (`renta_presuntiva` bajo `declaracion_renta`; `firmeza_declaraciones` bajo `procedimiento_tributario`). Sugerencia operativa: **el labeler debe poder asignar AL TÓPICO PADRE cuando un documento abarca varios subtópicos**. Es decir, un decreto que toca firmeza + sanciones + corrección puede legítimamente quedar en `procedimiento_tributario` (padre) y no forzosamente en uno de los hijos.

Esto se refleja en cómo construyas el prompt del labeler: dale primero los padres top-level, y solo si hay clara especificidad ofrece los subtópicos. Si no, devuelve el padre.

### 4.3 Sobre el versionado normativo

La taxonomía debería tener un **campo `vigencia_window`** por tópico que indique:
- Tópicos `evergreen` (cubren toda la historia): ej. `comercial_societario`, `iva`.
- Tópicos `transitorios` con sunset claro: ej. `reforma_laboral_ley_2466` (post-implementación), `decreto_1474_emergencia`.
- Tópicos con `vigencia_anual`: ej. `calendario_tributario` (cada año vence).

Esto permite que la respuesta a "¿qué dice la ley sobre X hoy?" filtre por vigencia automáticamente.

### 4.4 Sobre la cobertura del corpus actual de LIA

El corpus actual de LIA es 100% **renta-céntrico**. Las 28 secciones + T-series + regulación enriquecida cubren casi exclusivamente impuesto sobre la renta + complementarios. Los tópicos no-renta del taxonomy (laboral, comercial, IVA, datos personales, cambiario, etc.) **no tienen aún corpus que los soporte**. Esto significa:

- Si el taxonomy v2 incluye `proteccion_datos_personales`, `regimen_cambiario`, `reforma_laboral_ley_2466`, etc. → el labeler tendrá esos slots vacíos hasta que se ingieran documentos correspondientes.
- **Recomendación:** mantener esos tópicos en el taxonomy desde v2 (no posponerlos), pero con flag `corpus_coverage: pending`. Así cuando se ingiera el primer documento de protección de datos, ya tiene casa.

### 4.5 Sobre la vocabulario del usuario en `keyword_anchors`

Yo redacté `keyword_anchors` mezclando vocabulario formal ("art. 514 ET") y coloquial ("timbre 1 por ciento"). Mi recomendación: **mantenlos en mezcla**. El contador real busca por ambas formas. Y el sin-tildes es importante: el contador escribe "RUT" sin acentos, "responsabilidades" sin acentos, etc. — no porque no sepa, sino porque el teclado / la prisa / la convención.

### 4.6 Sobre las diferencias contables en NIIF

La razón de proponer split de `estados_financieros_niif` en tres tópicos (PYMES, Plenas, Microempresas) es **práctica de mercado**: el contador Grupo 2 y el Grupo 1 hablan idiomas distintos. Mezclar los marcos en un mismo tópico genera ruido en retrieval.

---

## 5. Resumen de entregables a `config/topic_taxonomy.json` v2

| Acción | Cantidad |
|---|---|
| Tópicos NUEVOS top-level | 10 (`impuesto_timbre`, `rut_y_responsabilidades_tributarias`, `parafiscales_seguridad_social`, `reforma_laboral_ley_2466`, `proteccion_datos_personales`, `niif_pymes`, `niif_plenas`, `niif_microempresas`, `regimen_cambiario`, `dividendos_y_distribucion_utilidades`, `regimen_tributario_especial_esal`) |
| Tópicos NUEVOS subtópico | 1 (`renta_presuntiva` bajo `declaracion_renta`); `zomac_zese_incentivos_geograficos` bajo `inversiones_incentivos` |
| Tópicos RECLASIFICADOS (los 12) | 12 (con 2 ajustes de nombre y 5 reasignados a subtópico) |
| Tópicos FUSIONADOS | 1 par (`comercial_societario` + `obligaciones_mercantiles` → `comercial_societario`) |
| Tópicos DEPRECADOS | 1 (`estados_financieros_niif` → split en 3) |
| Tópicos magnet RE-DEFINIDOS (con scope_out explícito) | 6 (`iva`, `procedimiento_tributario`, `comercial_societario`, `facturacion_electronica`, `beneficiario_final_rub`, `laboral`) |
| Reglas mutex codificables | 6 (las 5 del brief + 1 sobre laboral/parafiscales/reformas) |

Total tópicos top-level proyectados: **~80–85 después de la limpieza** (vs 79 actuales). El cambio neto es `+10 nuevos − 1 fusión − 1 deprecación + 3 splits NIIF = +11 brutos`, y reorganización interna de los 12 vacíos.

---

## 6. Próximos pasos sugeridos al equipo de ingeniería

1. Aplicar este documento a `config/topic_taxonomy.json` v2 — empezar por los 10 top-level nuevos y los 6 magnet re-definidos (los más altos en impacto sobre contaminación).
2. Codificar las 6 reglas mutex en el prompt del labeler como instrucción dura, no como sugerencia.
3. Implementar `allowed_norm_anchors` para tópicos no-ET (paralelo a `allowed_et_articles`).
4. Re-correr la suite de 30 preguntas del §3.2 contra el clasificador post-rebuild — debería tener ≥27/30 correctas para considerar la taxonomía aprobada.
5. Marcar los tópicos sin corpus aún (proteccion_datos, cambiario, reforma_laboral_2466, etc.) con `corpus_coverage: pending` y agendar ingesta posterior.
6. Para v2.1: revisar los 60+ tópicos no tocados por este SME-pass y hacer revisión liviana (definition + scope_out solamente).

---

*Respuesta cerrada. Si el equipo de ingeniería necesita refinamiento de algún tópico individual o una segunda pasada sobre los tópicos no tocados aquí, lo abordamos en una iteración corta posterior.*
