---
playbook_id: renta-sancion-correccion
categoria: renta-procedimiento
playbook_tipo: estandar
aplicabilidad_regimen: ambos
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Sanción por corrección de la declaración (art. 644 ET)

> Corregir voluntariamente la declaración aumentando impuesto o disminuyendo saldo a favor cuesta **10 %** del mayor valor a pagar (o menor saldo a favor) si se hace **antes de emplazamiento**, y **20 %** si se hace **después de emplazamiento para corregir** y antes de requerimiento especial. Es independiente de los intereses moratorios.

## Cómo lo pregunta un contador

- ¿Cuánto cuesta corregir la declaración de renta?
- ¿La sanción es 10 % o 20 %?
- ¿Cuándo aplica el 20 % en vez del 10 %?
- ¿Si me equivoqué a favor mío, hay sanción por corregir?
- ¿La corrección que disminuye el impuesto tiene sanción?
- ¿Puedo aplicar la reducción del art. 640 ET en la corrección?
- ¿La corrección reinicia el plazo de firmeza?
- Art. 644 ET — sanción por corrección
- Art. 588 ET — procedimiento de corrección
- ¿Cuánto tiempo tengo para corregir voluntariamente?

## Norma principal

- **Art. 644 ET — Sanción por corrección de las declaraciones**
- URL oficial: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#644>
- URL espejo: <https://estatuto.co/644>
- Sanción del **10 %** del mayor valor a pagar o menor saldo a favor (corrección voluntaria) o **20 %** (después de emplazamiento para corregir y antes de requerimiento especial). Aplica la sanción mínima art. 639 ET.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 588 ET | Procedimiento para corrección que aumenta impuesto | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr023.htm#588> |
| Art. 589 ET | Procedimiento cuando disminuye impuesto o aumenta saldo a favor | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr023.htm#589> |
| Art. 640 ET | Reducción de sanciones | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#640> |
| Art. 685 ET | Emplazamiento para corregir | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr028.htm#685> |
| Art. 647 ET | Sanción por inexactitud (no se acumula con la de corrección) | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#647> |

## Respuesta operativa

1. **Distinga el tipo de corrección:**
   - **Aumenta impuesto o disminuye saldo a favor** → art. 588 ET (corrección "que perjudica al fisco"). Procedimiento: presentación directa de declaración correctora vía MUISCA dentro del plazo de firmeza. **Genera sanción art. 644 ET.**
   - **Disminuye impuesto o aumenta saldo a favor** → art. 589 ET. Requiere solicitud ante la DIAN dentro de **1 año** desde el vencimiento. **NO genera sanción.**
2. **Porcentaje de sanción (art. 644 ET):**
   - **10 %** del mayor valor a pagar (o menor saldo a favor) si la corrección se hace **antes del emplazamiento para corregir** (art. 685 ET).
   - **20 %** si se hace **después del emplazamiento para corregir** y antes de notificación del requerimiento especial.
3. **Plazo:** la corrección bajo art. 588 ET puede hacerse mientras la declaración no esté en firme. El plazo es de **3 años** (firmeza ordinaria) o **5 años** (con pérdidas) desde el vencimiento — ver playbook firmeza.
4. **Liquidación de la sanción:**
   - Mayor valor a pagar = impuesto corregido − impuesto inicial.
   - Sanción = 10 % × mayor valor (o 20 % si aplica).
   - Sanción mínima art. 639 ET: **10 UVT** ($470.650 con UVT 2025).
5. **Intereses moratorios:** se liquidan **además** de la sanción, sobre el mayor valor del impuesto, desde el vencimiento original hasta el pago efectivo (art. 634 ET).
6. **Reducción art. 640 ET — aplicación a corrección:**
   - **50 %** si en los 2 años anteriores no se ha cometido la misma conducta y se paga antes del pliego.
   - **75 %** si nunca se ha cometido.
   - La reducción aplica claramente cuando la sanción la propone la DIAN. Para autoliquidación voluntaria, la DIAN ha aceptado la reducción del 50 % cuando el contribuyente paga la sanción al presentar la corrección.
7. **Corrección sin afectar valores fiscales:** correcciones que solo modifican información (errores de digitación, RUT, código actividad) sin cambiar impuesto ni saldo a favor → **no genera sanción** del art. 644 ET, pero puede generar sanción por inconsistencia (art. 650-3 ET) en casos calificados.
8. **Corrección y firmeza:** la corrección bajo art. 588 ET **reinicia el plazo de firmeza** desde la fecha de la corrección (art. 714 ET). Importante para no perder oportunidad de revisión por parte del contribuyente.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Liquidar 10 % cuando ya hubo emplazamiento | ALTO | Verificar si hay emplazamiento art. 685 ET notificado |
| Olvidar liquidar intereses moratorios además de la sanción | ALTO | Sanción + intereses son independientes |
| Aplicar art. 588 cuando la corrección disminuye impuesto | CRÍTICO | Si disminuye → art. 589 ET, vía solicitud |
| Pretender que la corrección extingue la sanción de extemporaneidad | MEDIO | Si la original era extemporánea, esa sanción se conserva |
| No aplicar sanción mínima cuando el 10 % da menos de 10 UVT | MEDIO | Mínimo legal 10 UVT |
| Asumir que la corrección "sana" inexactitudes detectables | ALTO | Solo evita art. 647 ET si es voluntaria sin emplazamiento previo |

## Qué NO cubre este playbook

- Corrección que disminuye impuesto (art. 589 ET) → procedimiento distinto, requiere solicitud DIAN.
- Sanción por inexactitud (art. 647 ET) → playbook `playbook_renta_sancion_inexactitud.md`.
- Procedimiento detallado del emplazamiento para corregir (art. 685 ET) → playbook de fiscalización.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? Última reforma relevante: Ley 1819 de 2016 (modificó art. 644 ET).
- URL versión vigente: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#644>
- Zona gris: aplicación de la reducción del art. 640 ET sobre la sanción autoliquidada en corrección voluntaria — Consejo de Estado ha aceptado el 50 % cuando se autoliquida y paga inmediatamente; la DIAN puede objetar en revisión. Posición conservadora: liquidar al 100 % y discutir si la DIAN aplica la reducida.

## Fuentes secundarias consultadas

- Actualícese — *Sanción por corrección — liquidación práctica* — <https://actualicese.com/sancion-correccion-declaracion/>
- Gerencie.com — *Sanción por corrección de declaraciones* — <https://www.gerencie.com/sancion-por-correccion.html>
- Consejo de Estado — sentencias sobre reducción del art. 640 ET en autoliquidaciones.
