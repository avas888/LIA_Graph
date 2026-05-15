---
playbook_id: niif-conciliacion-fiscal-f2516-f2517
categoria: niif-fiscal
playbook_tipo: extendido
aplicabilidad_regimen: ordinario
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Conciliación fiscal — Formatos 2516 y 2517 (anexo de la declaración de renta)

> Toda persona jurídica obligada a llevar contabilidad presenta conciliación fiscal: **F2516** los grandes contribuyentes y obligados con ingresos brutos fiscales ≥ 45.000 UVT; **F2517** los demás obligados. Es anexo de la declaración de renta (formulario 110) y debe coincidir renglón a renglón con cifras NIIF, ajustes fiscales y depuración final. Sanciones por inexactitud aplican.

## Cómo lo pregunta un contador

- ¿Quién debe presentar F2516 y quién F2517?
- ¿Cuál es el tope en UVT para presentar F2516?
- ¿Qué sección del formato corresponde a las diferencias temporarias?
- ¿La conciliación fiscal sustituye la declaración de renta o es anexo?
- ¿Qué pasa si los renglones del 2516 no coinciden con el 110?
- ¿Hasta cuándo presento la conciliación fiscal?
- ¿Quiénes están exonerados de la conciliación fiscal?
- ¿Cómo registro una diferencia permanente en F2516?
- ¿La conciliación fiscal aplica al RST?
- Sanciones por inconsistencia en F2516

## Norma principal

- **Resolución DIAN 000071 de 2019 — Formatos 2516 y 2517**
- URL oficial: <https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000071%20de%2028-10-2019.pdf>
- **Resolución DIAN 000027 de 2021** — modificación menor de plantillas.
- **Resolución DIAN 000111 de 2021** — modificación estructural.
- **Resolución DIAN 000079 de 2022** — actualización de cifras y especificaciones técnicas.
- **Resolución DIAN 000162 de 2023** — actualización vigente para AG 2023+.
- **Para AG 2025/2026** — verificar última resolución DIAN actualizadora antes del cierre.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 772-1 ET | Conciliación fiscal como obligación | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr028.htm#772-1> |
| Decreto 1998 de 2017 | Reglamentación conciliación fiscal | <https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=85072> |
| Decreto 1625 de 2016 art. 1.7.1 | DUR — sección de conciliación fiscal | <https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=78659> |
| Art. 647 ET | Sanción por inexactitud | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#647> |
| Art. 651 ET | Sanción por no enviar información | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#651> |
| Art. 28 ET | Realización del ingreso | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr001.htm#28> |
| Arts. 105 y 137 ET | Realización del gasto y depreciación | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr004.htm#105> |

## Respuesta operativa

1. **Quién presenta F2516 vs F2517.**
   - **F2516** — Grandes contribuyentes calificados como tal por DIAN **O** contribuyentes con **ingresos brutos fiscales ≥ 45.000 UVT** en el año gravable. Para AG 2025 (UVT $47.065) el corte = **$2.117.925.000**.
   - **F2517** — Demás personas jurídicas y naturales obligadas a llevar contabilidad que NO califiquen para el 2516. Es versión simplificada.

2. **Quiénes NO están obligados.**
   - Personas naturales **no obligadas** a llevar contabilidad.
   - Contribuyentes del **RST** (Régimen Simple de Tributación) — la conciliación fiscal aplica solo a régimen ordinario.
   - Entidades del régimen tributario especial sin actividad comercial.
   - Contribuyentes que aplican el Marco normativo para microempresas (Grupo 3 NIIF) — verificar excepción puntual.

3. **Naturaleza — anexo, no sustituto.** La conciliación fiscal es **anexo** de la declaración de renta (formulario 110), **no** la sustituye. Debe presentarse en el mismo plazo y por el mismo contribuyente. Se carga en el portal MUISCA en formato XML según especificaciones técnicas de la resolución vigente.

4. **Estructura del F2516 — secciones principales.**
   - **Sección Estado de Resultados Integral (ERI)** — Reproduce el ERI contable bajo NIIF línea a línea.
   - **Sección Estado de Situación Financiera (ESF)** — Reproduce activos, pasivos y patrimonio.
   - **Sección Conciliación Patrimonio Contable vs Patrimonio Fiscal** — Diferencias temporarias (DT) y diferencias permanentes (DP).
   - **Sección Conciliación Renta** — Partidas conciliatorias entre la utilidad NIIF y la renta líquida fiscal.
   - **Sección Impuesto Diferido** — Activo y pasivo diferido, conciliados con notas a EE.FF.
   - **Sección Anexos** — Detalles de ingresos, costos, gastos, deducciones y otros movimientos relevantes.

5. **Diferencias temporarias vs permanentes — clasificación obligatoria.**
   - **Temporarias (DT):** se revierten en períodos futuros y generan impuesto diferido. Ejemplo: depreciación acelerada fiscal (137 ET) vs depreciación contable lineal (NIC 16/Sección 17), provisión de cartera no deducida hasta cumplir requisitos (145 ET), pérdidas fiscales por compensar.
   - **Permanentes (DP):** no se revierten. No generan impuesto diferido. Ejemplo: 50 % del GMF no deducible (115 ET), gastos sin RUT del proveedor, sanciones e intereses moratorios fiscales, multas penales.

6. **Renglones críticos a auditar antes de presentar.**
   - **Total Ingresos NIIF (ERI)** debe coincidir con balance contable certificado.
   - **Renta líquida fiscal final del 2516** debe ser **idéntica** al renglón "Renta líquida del ejercicio" del formulario 110.
   - **Impuesto neto de renta** del 2516 = impuesto neto de renta del 110.
   - **Patrimonio fiscal del 2516** = patrimonio fiscal del 110.
   - Cualquier desfase entre 110 y 2516 dispara revisión DIAN.

7. **Cómo registrar una diferencia temporaria — ejemplo paso a paso.**
   - PYME compra una maquinaria por **$100.000.000** el 1 enero 2025. Vida útil NIIF: 10 años (depreciación lineal $10.000.000/año). Vida útil fiscal: 10 años (art. 137 ET, máquinaria 10 % anual).
   - Sin embargo, el art. 290 ET (regla de transición) permite acelerar fiscalmente bajo ciertos supuestos. Si se opta por depreciación fiscal acelerada del 20 % anual: depreciación fiscal año 1 = $20.000.000.
   - **Diferencia temporaria año 1 = $20.000.000 − $10.000.000 = $10.000.000** (deducción fiscal mayor que contable).
   - Genera **pasivo por impuesto diferido** = $10.000.000 × 35 % = **$3.500.000**.
   - En el F2516, registrar:
     - Sección ERI: gasto depreciación contable $10.000.000.
     - Sección Conciliación: menor base fiscal $10.000.000 → reduce renta líquida fiscal año 1.
     - Sección Impuesto Diferido: pasivo diferido $3.500.000.

8. **Cómo registrar una diferencia permanente — ejemplo.**
   - PYME pagó **$2.000.000** en GMF durante el AG. Bajo art. 115 inciso 2 ET, solo el 50 % ($1.000.000) es deducible.
   - El otro **$1.000.000 es diferencia permanente** — NO genera impuesto diferido.
   - En F2516:
     - Sección ERI: gasto GMF $2.000.000.
     - Sección Conciliación → renglón Diferencias Permanentes: +$1.000.000 (gasto no deducible).
     - Renta líquida fiscal aumenta en $1.000.000 frente a la utilidad NIIF.

9. **Plazo de presentación.** Mismo plazo de la declaración de renta del año correspondiente, según calendario DIAN. Para AG 2025 se presenta a lo largo de 2026 según el último dígito del NIT. La conciliación fiscal **no tiene plazo independiente**.

10. **Soportes — qué archivar.**
    - Balance certificado por contador/revisor fiscal.
    - ERI completo bajo NIIF.
    - Hojas de trabajo de cada partida conciliatoria.
    - Cálculo del impuesto diferido con tasas vigentes.
    - Notas a estados financieros con divulgación de impuestos.
    - Copia del XML cargado y acuse de recibo MUISCA.
    - **Plazo de conservación: 5 años** (art. 632 ET) o **hasta firmeza** de la declaración correspondiente.

## Caso práctico — utilidad NIIF $500.000.000 a renta fiscal

PYME AG 2025 con utilidad NIIF antes de impuestos **$500.000.000**:

| Concepto | Valor | Tipo |
|---|---|---|
| Utilidad NIIF antes impuestos | 500.000.000 | — |
| (+) 50 % GMF no deducible (art. 115) | 2.000.000 | Permanente |
| (+) Sanciones e intereses fiscales | 1.500.000 | Permanente |
| (+) Provisión cartera incobrable no deducida (art. 145) | 8.000.000 | Temporaria |
| (−) Depreciación fiscal mayor a contable | (10.000.000) | Temporaria |
| (+) Gastos sin soporte RUT/fact. electrónica | 3.500.000 | Permanente |
| **Renta líquida fiscal** | **505.000.000** | — |
| Impuesto renta 35 % | 176.750.000 | — |

Las temporarias $8.000.000 + $10.000.000 (neto −$2.000.000 a favor) generan **activo neto por impuesto diferido** ≈ $700.000 si la PYME espera revertirlas en futuros años.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| F2516 no coincide con renglones del formulario 110 | ALTO | Cuadrar línea a línea antes de enviar XML |
| Clasificar mal temporaria vs permanente | ALTO | Aplicar prueba de reversibilidad; consultar NIC 12 |
| No reconocer impuesto diferido cuando hay DT material | ALTO | Sección 29 NIIF PYMES / NIC 12 — obligatorio |
| Presentar F2517 cuando se debió F2516 | ALTO | Verificar ingresos fiscales contra UVT corte |
| Conciliar utilidad contable Colgaap en lugar de NIIF | ALTO | NIIF es la única base aceptada (Ley 1314/2009) |
| No conservar hojas de trabajo de partidas conciliatorias | MEDIO | Archivo de 5 años con detalle |
| Sanciones e intereses tratados como deducibles | ALTO | Diferencia permanente — no deducibles (art. 105 ET) |

## Qué NO cubre este playbook

- Régimen Simple de Tributación (RST) — no aplica conciliación fiscal. Ver playbook RST.
- Régimen tributario especial sin actividad comercial — exonerados; ver playbook ESAL.
- Conciliación patrimonial detallada — playbook hermano sobre patrimonio fiscal vs NIIF.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? Las resoluciones DIAN actualizan plantillas casi anualmente. **Verifique la resolución vigente para el AG que está presentando.**
- Última gran modificación: Resolución 000162/2023; para AG 2025 puede haber actualización adicional. Consultar antes de cargar el XML.
- Zona gris: tratamiento de pérdidas por deterioro en NIIF (Sección 27 / NIC 36) vs gasto fiscal por deterioro de cartera (art. 145 ET) — son temporarias mientras no se cumplan requisitos fiscales; conservar trazabilidad detallada para defender la posición.

## Fuentes secundarias consultadas

- Actualícese — *Formato 2516 y 2517 conciliación fiscal AG 2025* — <https://actualicese.com/formato-2516-conciliacion-fiscal/>
- Gerencie.com — *Cómo diligenciar la conciliación fiscal* — <https://www.gerencie.com/conciliacion-fiscal.html>
- KPMG Colombia — *Guía conciliación fiscal NIIF vs ET* — <https://kpmg.com/co/>
- DIAN — *Especificaciones técnicas formatos* — <https://www.dian.gov.co/impuestos/sociedades/Paginas/conciliacion-fiscal.aspx>
