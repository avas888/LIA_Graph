---
playbook_id: renta-notificaciones-electronicas
categoria: renta-procedimiento
playbook_tipo: estandar
aplicabilidad_regimen: ambos
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Notificaciones electrónicas de la DIAN (art. 566-1 ET)

> La notificación electrónica al buzón electrónico registrado en el RUT es el **medio preferente y obligatorio** para los actos de la DIAN. La notificación se entiende surtida al **quinto día hábil** siguiente al envío del mensaje al buzón. El RUT debe contener correo válido y vigente.

## Cómo lo pregunta un contador

- ¿Cómo me notifica la DIAN ahora?
- ¿La notificación electrónica es obligatoria?
- ¿Cuándo se entiende notificada una resolución por correo?
- ¿Qué pasa si no abro el correo de la DIAN?
- ¿Cómo registro el buzón electrónico en el RUT?
- ¿Puedo pedir que me notifiquen físicamente?
- Art. 566-1 ET — notificaciones electrónicas
- ¿Los plazos para responder corren desde el envío o desde que lo leo?
- ¿Qué pasa si el correo está desactualizado?
- Resolución DIAN sobre notificación electrónica

## Norma principal

- **Art. 566-1 ET — Notificación electrónica**
- URL oficial: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr020.htm#566-1>
- URL espejo: <https://estatuto.co/566-1>
- Introducido por la **Ley 1607 de 2012** y modificado por **Ley 2010 de 2019 art. 95**. Establece la notificación electrónica como medio preferente; el acto se entiende notificado **al quinto día hábil siguiente** al envío del mensaje al buzón electrónico registrado en el RUT.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 555-2 ET | RUT — registro único tributario y obligación de actualización | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr019.htm#555-2> |
| Art. 565 ET | Formas de notificación | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr020.htm#565> |
| Art. 568 ET | Notificaciones devueltas — subsidiariedad | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr020.htm#568> |
| Resolución DIAN 000038 de 2020 | Reglamenta la notificación electrónica | <https://www.dian.gov.co/normatividad/Normatividad/Resolucion%20000038%20de%2030-04-2020.pdf> |
| Decreto 358 de 2020 | Modificaciones al procedimiento de notificación | <https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=110828> |

## Respuesta operativa

1. **Registre y mantenga vigente el correo electrónico en el RUT.** El correo del RUT es el **buzón electrónico oficial** para notificaciones DIAN. La actualización es obligación del contribuyente (art. 555-2 ET); el correo desactualizado **no es defensa** frente a una notificación.
2. **Fecha de notificación = quinto día hábil:** la DIAN envía el acto al buzón; la notificación se entiende surtida al **5° día hábil** siguiente al envío, independientemente de si el contribuyente abrió el mensaje o no. Desde ese día corren los plazos procesales (recursos, respuesta a requerimiento, etc.).
3. **Actos que se notifican electrónicamente:**
   - Requerimientos ordinarios (art. 684 ET).
   - Emplazamientos para corregir (art. 685 ET) y para declarar (art. 715 ET).
   - Requerimientos especiales (art. 703 ET).
   - Liquidaciones oficiales (arts. 710 y siguientes ET).
   - Resoluciones sanción.
   - Citaciones y autos de trámite.
   - Resoluciones de devolución/compensación.
4. **Subsidiariedad (art. 568 ET):** si la notificación electrónica falla por causa imputable a la DIAN (caída del sistema oficial, comprobada), se procederá por otros medios (correo físico, edicto, personal) según prelación del art. 565 ET. **La falla del correo del contribuyente NO es causa de subsidiariedad** — esa falla recae sobre el contribuyente.
5. **Acuse y constancia:** la DIAN debe conservar evidencia electrónica del envío (logs del sistema MUISCA / portal del contribuyente). Esa constancia es prueba suficiente para acreditar la notificación.
6. **Cómo el contador debe gestionar el buzón:**
   - Configurar **correo institucional dedicado** (no correo personal del representante legal).
   - Revisar el buzón con **frecuencia mínima semanal**, idealmente diaria en períodos de fiscalización.
   - Configurar reglas/etiquetas para correos de `notificacionesdian.dian.gov.co` y dominios oficiales.
   - Actualizar inmediatamente cuando cambia: representante legal, contador, correo, dirección.
7. **Notificación al apoderado:** si hay poder vigente registrado, la notificación también se entiende surtida al apoderado por su buzón electrónico. Mantener actualizado el correo del apoderado en el sistema DIAN.
8. **Defensa procesal por defectos de notificación:** la única defensa viable es demostrar que el correo **nunca fue registrado** en el RUT o que la DIAN envió a un correo distinto del registrado. Argumentos como "no lo vi", "estaba en spam", "no abrí el mensaje" **no proceden**.
9. **Personas naturales no obligadas a RUT:** mantienen notificación física residual; pero si tienen RUT (declarantes de renta), la notificación electrónica aplica.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| No actualizar el correo del RUT tras cambio de contador | CRÍTICO | Actualización inmediata vía MUISCA |
| Asumir que el plazo corre desde la lectura del correo | ALTO | Corre desde el 5° día hábil del envío |
| Usar correo personal del representante (alta rotación) | ALTO | Usar correo institucional dedicado a notificaciones |
| Ignorar correos del dominio DIAN — caer en spam | CRÍTICO | Configurar reglas y revisar carpeta spam |
| No registrar el correo del apoderado | MEDIO | Actualizar tras conferir poder |
| Alegar mala notificación cuando el correo estaba vigente | ALTO | No es defensa procesal — perder el recurso |

## Qué NO cubre este playbook

- Procedimiento general de fiscalización → playbook fiscalización DIAN.
- Recurso de reconsideración (arts. 720 y ss. ET) → playbook recursos.
- Notificación de actos no tributarios (UGPP, Supersociedades) → ámbito distinto.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **Sí** — Ley 2010 de 2019 art. 95; Decreto 358 de 2020; Resolución DIAN 000038 de 2020.
- URL versión vigente: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr020.htm#566-1>
- Zona gris: tratamiento de notificaciones cuando el sistema DIAN presentó caídas documentadas — el Consejo de Estado ha aceptado la nulidad cuando hay prueba directa de falla del sistema oficial el día del envío.

## Fuentes secundarias consultadas

- Actualícese — *Notificación electrónica DIAN — reglas vigentes* — <https://actualicese.com/notificacion-electronica-dian/>
- Gerencie.com — *Notificación electrónica art. 566-1 ET* — <https://www.gerencie.com/notificacion-electronica.html>
- DIAN — Resolución 000038 de 2020 y guía operativa MUISCA.
