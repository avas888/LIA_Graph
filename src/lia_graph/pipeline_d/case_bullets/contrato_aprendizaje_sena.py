"""v17 b3 — contrato de aprendizaje SENA (Ley 789/2002 arts. 30-34).

Anchored at ET art. 108 (deducción del costo laboral / apoyo de
sostenimiento). El régimen sustantivo está en Ley 789/2002 + Decretos
933/2003 y 451/2008, citados en bullets.
"""
from __future__ import annotations

from ..case_detectors import is_contrato_aprendizaje_sena_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="contrato_aprendizaje_sena",
    detector=is_contrato_aprendizaje_sena_case,
    bullets=(
        "**Quién está obligado a tener aprendices (Ley 789/2002 art. 33):** empresas privadas de cualquier sector económico con **15 o más trabajadores permanentes** (excluyen temporales y aprendices del cómputo). **Menos de 15 trabajadores no están obligadas**, pueden contratar aprendices voluntariamente. El SENA fija la cuota por acto administrativo basado en la planta reportada en PILA.",
        "**Cálculo de la cuota:** fórmula general **1 aprendiz por cada 20 trabajadores** (o fracción superior a 10). Tabla operativa: 15–19 trabajadores → 1 aprendiz; 20–39 → 1; 40–59 → 2; y así sucesivamente.",
        "**Apoyo de sostenimiento (Ley 789/2002 art. 30 + 32):** etapa lectiva = **50 % del SMMLV** (formación teórica en aula); etapa práctica = **75 % del SMMLV** (trabajo en la empresa). **Excepción:** si la tasa de desempleo nacional es < 10 %, etapa práctica sube al **100 % del SMMLV** (parágrafo art. 30). Para 2026 la tasa se mantiene > 10 %, por lo que sigue siendo **75 %**.",
        "**Monetización (Ley 789/2002 art. 34 + Decreto 451/2008):** si la empresa no contrata los aprendices que le corresponden, paga al SENA mensualmente el equivalente al **5 % de un SMMLV por cada aprendiz no contratado**. Pago en formulario SENA vía PSE.",
        "**Afiliación a seguridad social — solo salud + ARL:** **etapa lectiva** = únicamente **salud** (subsidiado o cobertura SENA), **NO** pensión ni ARL (no hay riesgo laboral en aula). **Etapa práctica** = **salud (régimen contributivo) + ARL**, ambas a cargo del **empleador**. **No cotiza a pensión** durante el aprendizaje.",
        "**El aprendiz NO recibe prestaciones sociales:** no hay cesantías, prima ni intereses; tampoco vacaciones remuneradas como tales (sí receso académico del programa). **No** hay liquidación al final del contrato. **Duración máxima del contrato: 2 años**. Debe formalizarse por escrito y registrarse en el sistema del SENA — el no registro genera presunción de relación laboral ordinaria.",
        "**Tratamiento contable y fiscal:** apoyo de sostenimiento = **gasto laboral deducible** en renta (cuenta 5105 / 5145) con soportes del contrato y planillas PILA — soporte del **art. 108 ET** para la deducción. La monetización al SENA = gasto parafiscal (cuenta 5135), igualmente deducible. Sanciones por incumplimiento de cuota ni monetización: multas SENA + eventualmente Min. Trabajo, hasta **100 SMMLV** por reincidencia.",
    ),
    keywords=(
        "aprendiz", "aprendices",
        "contrato de aprendizaje",
        "aprendiz sena",
        "cuota sena",
        "cuota de aprendices",
        "cuota de aprendizaje",
        "monetización", "monetizacion",
        "monetizar aprendices",
        "apoyo de sostenimiento",
        "etapa lectiva",
        "etapa práctica", "etapa practica",
        "ley 789 de 2002", "ley 789/2002",
        "art. 30 ley 789", "art 30 ley 789",
        "art. 32 ley 789", "art 32 ley 789",
        "art. 33 ley 789", "art 33 ley 789",
        "art. 34 ley 789", "art 34 ley 789",
        "decreto 933 de 2003",
        "decreto 451 de 2008",
        "resolución 1-0224", "resolucion 1-0224",
        "50% smmlv", "50 % smmlv", "50% del smmlv",
        "75% smmlv", "75 % smmlv", "75% del smmlv",
        "100% smmlv", "100 % smmlv",
        "15 trabajadores",
        "1 aprendiz por cada 20",
        "5% smmlv", "5 % smmlv",
        "salud subsidiado",
        "salud contributivo",
        "centro de servicios empresariales",
        "art. 108", "art 108",
        "100 smmlv",
    ),
    anchor_articles=("108",),
    search_queries=(
        "contrato de aprendizaje sena ley 789 de 2002 cuota apoyo sostenimiento",
        "monetizacion cuota sena 5 por ciento smmlv decreto 451 de 2008",
        "etapa lectiva practica apoyo 50 75 por ciento smmlv afiliacion arl salud",
    ),
    source_label="contrato_aprendizaje_sena_anchor",
)
