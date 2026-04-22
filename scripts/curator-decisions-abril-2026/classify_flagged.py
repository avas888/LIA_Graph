#!/usr/bin/env python3
"""
classify_flagged.py

Reads /sessions/optimistic-elegant-meitner/flagged_for_curator_review.csv
(565 rows flagged by classifier PASO 4), encodes per-row curator decisions,
and emits 7 deliverable artifacts into:

  /sessions/optimistic-elegant-meitner/mnt/Corpus/SELF-IMPROVEMENT/curator-decisions-abril-2026/

Decision model (per row):
  (a) ALIAS   — widen aliases on an existing subtopic in config/subtopic_taxonomy.json
  (b) NEW     — propose a new subtopic (label + 3-6 starter aliases + parent_topic_key)
  (c) BATCH   — batch-inherit by pattern (sibling triplets share a subtopic)
  (d) EXCLUDE — drop from corpus (binaries / .svg / .json guide artifacts)

Each row may ALSO carry a parent_topic_correction when PASO 1 mis-routed it
(the classifier fires on numeric substrings in file paths — e.g. Libros of the
ET ending up in 'iva', or Ley 1474 Anticorrupción landing in 'procedimiento_tributario').
"""
from __future__ import annotations
import csv
import json
import os
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------- paths ----------
INPUT_CSV  = '/sessions/optimistic-elegant-meitner/flagged_for_curator_review.csv'
OUTDIR     = '/sessions/optimistic-elegant-meitner/mnt/Corpus/SELF-IMPROVEMENT/curator-decisions-abril-2026'

os.makedirs(OUTDIR, exist_ok=True)

# ---------- existing catch-all subtopics (from taxonomy v2026-04-21-v1) ----------
# Only the keys I touch. The JSON patch will target these.
EXISTING = {
    'declaracion_renta.declaracion_de_renta_personas_juridicas',
    'declaracion_renta.beneficio_tributario_donaciones_becas_fuerzas_armadas',
    'emergencia_tributaria.exenciones_tributarias_covid_19',
    'otros_sectoriales.cumplimiento_normativo_sectorial_pymes',
    'laboral.aporte_parafiscales_icbf',
    'reformas_tributarias.reforma_tributaria_gmf_y_facturacion',
    'inversiones_incentivos.beneficios_tributarios_sector_editorial',
    'impuesto_patrimonio_personas_naturales.impuesto_al_patrimonio_excepcional_2011',
    'regimen_sancionatorio.ajuste_de_sanciones_por_inflacion',
    'regimen_tributario_especial.regimen_tributario_especial_san_andres',
    'retencion_en_la_fuente.implementacion_retencion_en_la_fuente_pyme',
    'zonas_francas.beneficios_tributarios_zonas_de_frontera',
    'presupuesto_hacienda.presupuesto_de_ingresos_y_egresos',
    'comercial_societario.matricula_y_renovacion_mercantil',
    'estados_financieros_niif.conciliacion_fiscal_2516_2517',  # hypothetical — patch will verify
    'facturacion_electronica.ecosistema_facturacion_electronica',
    'informacion_exogena.obligados_formatos_exogena_dian',
    'procedimiento_tributario.fiscalizacion_y_defensa_dian',
}

# ---------- decision records ----------
@dataclass
class Decision:
    row_num: int
    topic_detected: str            # what PASO 1 said
    topic_corrected: Optional[str] # if we override PASO 1
    action: str                    # 'a' | 'b' | 'c' | 'd'
    target_subtopic_key: Optional[str]  # e.g. 'cumplimiento_normativo_sectorial_pymes'
    alias_to_add: Optional[str]    # for (a)
    new_subtopic_ref: Optional[str]# for (b) — points to new_subtopics.json entry key
    batch_pattern: Optional[str]   # for (c) — SQL LIKE pattern
    exclude_reason: Optional[str]  # for (d)
    rationale: str
    relative_path: str
    knowledge_class: str

    @property
    def parent_key(self) -> str:
        return self.topic_corrected or self.topic_detected

# ---------- new subtopic catalog (case b) ----------
# key = f"{parent_topic}.{subtopic_key}"
NEW_SUBTOPICS = {
    # --- activos_exterior ---
    'activos_exterior.declaracion_activos_exterior_formulario_160': {
        'parent_topic_key': 'activos_exterior',
        'label': 'Declaración de activos en el exterior (Formulario 160)',
        'aliases': [
            'activos_exterior',
            'formulario_160',
            'declaracion_activos_exterior',
            'AEX',
            'art_607_ET',
            'activos_poseidos_en_el_exterior',
        ],
        'rationale_introduced': 'Formulario 160 es un régimen distinto con calendario propio; no encaja en declaración renta PJ catch-all.',
    },

    # --- comercial_societario ---
    'otros_sectoriales.estatuto_consumidor_ley_1480_2011': {
        'parent_topic_key': 'otros_sectoriales',  # CORRECCIÓN: Ley 1480 es consumidor, NO societario
        'label': 'Estatuto del Consumidor (Ley 1480/2011)',
        'aliases': [
            'ley_1480_2011',
            'estatuto_consumidor',
            'proteccion_consumidor',
            'SIC',
            'responsabilidad_productor',
            'derechos_consumidor',
        ],
        'rationale_introduced': 'Ley 1480/2011 es materia de protección al consumidor bajo la SIC, no tributario ni societario.',
    },
    'comercial_societario.regimen_emprendimiento_ley_2069_2020': {
        'parent_topic_key': 'comercial_societario',
        'label': 'Ley de Emprendimiento (Ley 2069/2020)',
        'aliases': [
            'ley_2069_2020',
            'ley_emprendimiento',
            'BIC_sociedades_beneficio_interes_colectivo',
            'compras_publicas_mipyme',
            'SECOP_emprendedores',
            'inscripcion_registro_nacional_emprendedores',
        ],
        'rationale_introduced': 'Régimen normativo específico con impactos tributarios y societarios (sociedades BIC, compras públicas MiPyME).',
    },
    'comercial_societario.regimen_mipyme_ley_590_905': {
        'parent_topic_key': 'comercial_societario',
        'label': 'Régimen MiPyME (Leyes 590/2000 y 905/2004)',
        'aliases': [
            'ley_590_2000',
            'ley_905_2004',
            'mipyme',
            'micro_pequena_mediana_empresa',
            'clasificacion_empresarial',
            'registro_mipyme',
        ],
        'rationale_introduced': 'Leyes fundacionales de la clasificación MiPyME; criterio de activos/ingresos que determina obligaciones diferenciadas.',
    },

    # --- datos_tecnologia ---
    'datos_tecnologia.teletrabajo_ley_1221_2008': {
        'parent_topic_key': 'datos_tecnologia',
        'label': 'Teletrabajo (Ley 1221/2008)',
        'aliases': [
            'ley_1221_2008',
            'teletrabajo',
            'trabajo_remoto',
            'dispositivos_tecnologicos_empleador',
            'auxilio_conectividad',
            'contrato_teletrabajador',
        ],
        'rationale_introduced': 'Marco específico de teletrabajo; impacta obligaciones laborales y pagos parafiscales.',
    },
    'datos_tecnologia.regulacion_tic_ley_1341_2009': {
        'parent_topic_key': 'datos_tecnologia',
        'label': 'Regulación TIC (Ley 1341/2009)',
        'aliases': [
            'ley_1341_2009',
            'MinTIC',
            'contribucion_tic',
            'operadores_servicios_tic',
            'CRC_comision_regulacion_comunicaciones',
            'fondo_TIC',
        ],
        'rationale_introduced': 'Marco TIC con contribuciones sectoriales; afecta empresas de telecomunicaciones y tecnología.',
    },

    # --- declaracion_renta ---
    'declaracion_renta.incentivos_regionales_zomac_zese': {
        'parent_topic_key': 'declaracion_renta',
        'label': 'Incentivos regionales ZOMAC y ZESE',
        'aliases': [
            'ZOMAC',
            'zonas_mas_afectadas_conflicto_armado',
            'ZESE',
            'zona_economica_especial',
            'tarifa_progresiva_ZOMAC',
            'renta_exenta_regional',
        ],
        'rationale_introduced': 'Incentivos de renta con tarifas progresivas específicas por región; beneficio tributario relevante para PYMEs en esas zonas.',
    },

    # --- gravamen_movimiento_financiero_4x1000 ---
    'gravamen_movimiento_financiero_4x1000.marco_legal_gmf_4x1000': {
        'parent_topic_key': 'gravamen_movimiento_financiero_4x1000',
        'label': 'Marco legal GMF 4x1000 (cuentas exentas)',
        'aliases': [
            'GMF',
            '4x1000',
            'gravamen_movimientos_financieros',
            'art_870_ET',
            'art_879_ET',
            'cuentas_exentas_GMF',
        ],
        'rationale_introduced': 'Parent topic sin ningún subtopic todavía; necesita punto de anclaje para las exenciones GMF art. 879.',
    },

    # --- impuestos_saludables ---
    'impuestos_saludables.impuestos_saludables_ibua_icui': {
        'parent_topic_key': 'impuestos_saludables',
        'label': 'Impuestos saludables IBUA e ICUI',
        'aliases': [
            'IBUA',
            'impuesto_bebidas_ultraprocesadas_azucaradas',
            'ICUI',
            'impuesto_comestibles_ultraprocesados',
            'ley_2277_2022_impuestos_saludables',
            'art_513_1_ET',
        ],
        'rationale_introduced': 'Impuestos creados por Ley 2277/2022 arts 513-1 a 513-13; producto objeto de régimen específico.',
    },

    # --- informacion_exogena ---
    'informacion_exogena.recurso_sancion_exogena_art_651_ET': {
        'parent_topic_key': 'informacion_exogena',
        'label': 'Recurso contra sanción por no presentar exógena (art. 651 ET)',
        'aliases': [
            'art_651_ET',
            'sancion_no_presentar_exogena',
            'recurso_reconsideracion_exogena',
            'reduccion_sancion_exogena',
            'defensa_sancion_informacion_exogena',
            'gradualidad_sancion_art_651',
        ],
        'rationale_introduced': 'Módulo defensivo con procedimiento propio (descuentos por allanamiento, recurso); amerita subtopic dedicado.',
    },

    # --- inversiones_incentivos (NEW subtopics, no bulk into catch-all editorial) ---
    'inversiones_incentivos.ley_paez_218_1995': {
        'parent_topic_key': 'inversiones_incentivos',
        'label': 'Ley Páez — incentivos Zona del Río Páez (Ley 218/1995)',
        'aliases': [
            'ley_218_1995',
            'ley_paez',
            'zona_rio_paez',
            'renta_exenta_paez',
            'incentivo_cauca_huila',
            'empresas_establecidas_paez',
        ],
        'rationale_introduced': 'Incentivo regional histórico con vigencia residual; empresas beneficiarias todavía activas.',
    },
    'inversiones_incentivos.progresividad_ley_1429_2010_formalizacion': {
        'parent_topic_key': 'inversiones_incentivos',
        'label': 'Progresividad de renta — Ley de Formalización (Ley 1429/2010)',
        'aliases': [
            'ley_1429_2010',
            'ley_formalizacion',
            'progresividad_renta',
            'pequenas_empresas_beneficios',
            'tarifa_progresiva_primeros_anos',
            'formalizacion_empresarial',
        ],
        'rationale_introduced': 'Régimen de progresividad todavía aplicable a empresas acogidas antes de derogatoria; marco de referencia para firmeza.',
    },
    'inversiones_incentivos.fnce_ley_1715_2014_energia_renovable': {
        'parent_topic_key': 'inversiones_incentivos',
        'label': 'Fuentes No Convencionales de Energía (Ley 1715/2014)',
        'aliases': [
            'ley_1715_2014',
            'FNCE',
            'fuentes_no_convencionales_energia',
            'deduccion_inversion_energia_renovable',
            'solar_eolico_incentivos',
            'UPME_certificacion',
        ],
        'rationale_introduced': 'Deducción especial renta + exclusión IVA; régimen de incentivos ambientales muy consultado.',
    },
    'inversiones_incentivos.transicion_energetica_ley_2099_2021': {
        'parent_topic_key': 'inversiones_incentivos',
        'label': 'Transición energética (Ley 2099/2021)',
        'aliases': [
            'ley_2099_2021',
            'transicion_energetica',
            'hidrogeno_verde',
            'eficiencia_energetica',
            'incentivos_energia_renovable_2099',
            'ampliacion_FNCE',
        ],
        'rationale_introduced': 'Amplía y complementa Ley 1715; incentivos tributarios específicos para hidrógeno y eficiencia.',
    },

    # --- laboral ---
    'laboral.reforma_laboral_ley_2466_2025': {
        'parent_topic_key': 'laboral',
        'label': 'Reforma Laboral (Ley 2466/2025)',
        'aliases': [
            'ley_2466_2025',
            'reforma_laboral_petro',
            'recargo_nocturno_6pm',
            'dominical_100_porciento',
            'contrato_termino_indefinido_obligatorio',
            'aprendiz_contrato_laboral',
        ],
        'rationale_introduced': 'Reforma laboral 2025 con impactos en nómina, recargos y contratación; materia de alta consulta 2026.',
    },

    # --- presupuesto_hacienda ---
    'presupuesto_hacienda.sistema_general_regalias_ley_1530_2012': {
        'parent_topic_key': 'presupuesto_hacienda',
        'label': 'Sistema General de Regalías (Ley 1530/2012)',
        'aliases': [
            'ley_1530_2012',
            'sistema_general_regalias',
            'SGR',
            'OCAD',
            'distribucion_regalias',
            'regalias_entidades_territoriales',
        ],
        'rationale_introduced': 'Régimen presupuestal específico; afecta contratación pública y PYMEs proveedoras de entidades territoriales.',
    },

    # --- procedimiento_tributario ---
    'procedimiento_tributario.cpaca_ley_1437_2011': {
        'parent_topic_key': 'procedimiento_tributario',
        'label': 'CPACA — Código de Procedimiento Administrativo (Ley 1437/2011)',
        'aliases': [
            'ley_1437_2011',
            'CPACA',
            'codigo_procedimiento_administrativo',
            'silencio_administrativo',
            'notificacion_administrativa',
            'medios_control_contencioso',
        ],
        'rationale_introduced': 'Marco procedimental que se aplica supletoriamente al procedimiento tributario; núcleo de las defensas.',
    },
    'otros_sectoriales.anticorrupcion_sagrilaft_ley_1474_2011': {
        'parent_topic_key': 'otros_sectoriales',  # CORRECCIÓN: Ley 1474 anticorrupción NO es procedimiento tributario
        'label': 'Ley Anticorrupción / SAGRILAFT (Ley 1474/2011)',
        'aliases': [
            'ley_1474_2011',
            'estatuto_anticorrupcion',
            'SAGRILAFT',
            'PTEE',
            'inhabilidades_contratacion',
            'prevencion_corrupcion',
        ],
        'rationale_introduced': 'Estatuto anticorrupción; base del SAGRILAFT y PTEE que obliga a empresas bajo SuperSociedades.',
    },
    'procedimiento_tributario.codigo_general_proceso_ley_1564_2012': {
        'parent_topic_key': 'procedimiento_tributario',
        'label': 'Código General del Proceso (Ley 1564/2012)',
        'aliases': [
            'ley_1564_2012',
            'CGP',
            'codigo_general_proceso',
            'proceso_ejecutivo',
            'mandamiento_pago',
            'medidas_cautelares',
        ],
        'rationale_introduced': 'Proceso ejecutivo base de los cobros coactivos DIAN; indispensable para defensa en cobro.',
    },

    # --- declaracion_renta (depreciación fiscal de fila de ica) ---
    'declaracion_renta.depreciacion_fiscal_pyme': {
        'parent_topic_key': 'declaracion_renta',
        'label': 'Depreciación fiscal para PYME',
        'aliases': [
            'depreciacion_fiscal',
            'art_137_ET',
            'vida_util_fiscal',
            'tasas_maximas_depreciacion',
            'diferencia_niif_fiscal_depreciacion',
            'activos_fijos_depreciables',
        ],
        'rationale_introduced': 'Subtopic puntual sobre tratamiento fiscal de la depreciación; alta consulta por la divergencia NIIF/fiscal.',
    },
}

# ---------- decisions (per row) ----------
# I encode with path-substring rules to stay maintainable.

def assign(row_num: int, topic: str, kclass: str, path: str) -> Decision:
    P = path  # alias for readability

    # ========== EXCLUSIONS (case d) ==========
    # form_guides .svg / .json artifacts
    if P.startswith('form_guides/'):
        return Decision(
            row_num=row_num, topic_detected=topic, topic_corrected=None,
            action='d', target_subtopic_key=None, alias_to_add=None,
            new_subtopic_ref=None, batch_pattern=None,
            exclude_reason='form_guides asset (.svg/.json) — binary artifact, no prose content',
            rationale='Estos son assets binarios de form_guides (PNG/SVG exportados + manifiestos JSON) — nunca deberían haber entrado al graph-parse gate.',
            relative_path=P, knowledge_class=kclass,
        )

    # Leyes derogadas (rows 133-134)
    if '/LEYES/DEROGADAS/' in P:
        return Decision(
            row_num=row_num, topic_detected=topic, topic_corrected=None,
            action='d', target_subtopic_key=None, alias_to_add=None,
            new_subtopic_ref=None, batch_pattern=None,
            exclude_reason='Ley derogada (histórica, sin vigencia)',
            rationale='Las leyes derogadas violan la regla de anti-contaminación del CLAUDE.md: "si no tiene vigencia, no existe en el corpus".',
            relative_path=P, knowledge_class=kclass,
        )

    # ========== ACTIVOS EXTERIOR (rows 1-2) ==========
    if topic == 'activos_exterior':
        return Decision(
            row_num=row_num, topic_detected=topic, topic_corrected=None,
            action='b', target_subtopic_key='declaracion_activos_exterior_formulario_160',
            alias_to_add=None, new_subtopic_ref='activos_exterior.declaracion_activos_exterior_formulario_160',
            batch_pattern=None, exclude_reason=None,
            rationale='Formulario 160 es un régimen con calendario y sanciones propios; crear subtopic dedicado en vez de mezclar con renta PJ.',
            relative_path=P, knowledge_class=kclass,
        )

    # ========== COMERCIAL_SOCIETARIO (rows 3-16) ==========
    if topic == 'comercial_societario':
        if 'Ley-223-1994' in P:
            return Decision(row_num, topic, 'reformas_tributarias', 'a',
                'reforma_tributaria_gmf_y_facturacion', 'ley_223_1994_reforma', None, None, None,
                'Ley 223/1994 es una reforma tributaria, no comercial societario. Alias al catch-all de reformas.',
                P, kclass)
        if 'Ley-1480-2011' in P:
            return Decision(row_num, topic, 'otros_sectoriales', 'b',
                'estatuto_consumidor_ley_1480_2011', None,
                'otros_sectoriales.estatuto_consumidor_ley_1480_2011', None, None,
                'Ley 1480/2011 es Estatuto del Consumidor (SIC), no societario — corrección de parent_topic + subtopic dedicado.',
                P, kclass)
        if 'Ley-2069-2020' in P:
            return Decision(row_num, topic, None, 'b',
                'regimen_emprendimiento_ley_2069_2020', None,
                'comercial_societario.regimen_emprendimiento_ley_2069_2020', None, None,
                'Ley 2069/2020 (Emprendimiento) introduce sociedades BIC y compras públicas MiPyME; merece subtopic propio.',
                P, kclass)
        if 'Ley-590-2000' in P or 'Ley-905-2004' in P:
            return Decision(row_num, topic, None, 'b',
                'regimen_mipyme_ley_590_905', None,
                'comercial_societario.regimen_mipyme_ley_590_905', None, None,
                'Leyes 590/2000 y 905/2004 fijan la clasificación MiPyME — criterio base para obligaciones diferenciadas.',
                P, kclass)
        if 'Ley-1151-2007' in P:
            return Decision(row_num, topic, 'presupuesto_hacienda', 'a',
                'presupuesto_de_ingresos_y_egresos', 'ley_1151_2007_pnd', None, None, None,
                'Ley 1151/2007 es el Plan Nacional de Desarrollo 2006-2010 — parent correcto es presupuesto_hacienda.',
                P, kclass)

    # ========== DATOS_TECNOLOGIA (rows 17-22) ==========
    if topic == 'datos_tecnologia':
        if '1221-2008' in P or '1221_2008' in P:
            return Decision(row_num, topic, None, 'b',
                'teletrabajo_ley_1221_2008', None,
                'datos_tecnologia.teletrabajo_ley_1221_2008', None, None,
                'Ley 1221/2008 regula teletrabajo — subtopic dedicado (impacta laboral y parafiscales).',
                P, kclass)
        if '1341-2009' in P or '1341_2009' in P:
            return Decision(row_num, topic, None, 'b',
                'regulacion_tic_ley_1341_2009', None,
                'datos_tecnologia.regulacion_tic_ley_1341_2009', None, None,
                'Ley 1341/2009 (TIC) — régimen contributivo sectorial MinTIC / CRC.',
                P, kclass)
        if 'seccion-28-casos-practicos' in P:
            return Decision(row_num, topic, 'declaracion_renta', 'a',
                'declaracion_de_renta_personas_juridicas', 'casos_practicos_renta_pj_seccion_28', None, None, None,
                'Sección 28 de casos prácticos es parte de la guía LOGGRO de declaración de renta PJ; PASO 1 la enrutó mal.',
                P, kclass)

    # ========== DECLARACION_RENTA (rows 23-45 + 35/36 ZOMAC) ==========
    if topic == 'declaracion_renta':
        if '/ZOMAC_INCENTIVOS/' in P:
            return Decision(row_num, topic, None, 'b',
                'incentivos_regionales_zomac_zese', None,
                'declaracion_renta.incentivos_regionales_zomac_zese', None, None,
                'ZOMAC/ZESE es un régimen de tarifa progresiva específico; merece subtopic dedicado.',
                P, kclass)
        if '/DONACIONES_DESCUENTOS/' in P:
            return Decision(row_num, topic, None, 'a',
                'beneficio_tributario_donaciones_becas_fuerzas_armadas',
                'donaciones_descuento_tributario_pyme', None, None, None,
                'Guía práctica de donaciones PYME encaja en el subtopic existente de donaciones/descuentos.',
                P, kclass)
        if '/RENTA/LOGGRO/' in P and 'seccion-' in P:
            m = re.search(r'seccion-(\d+)', P)
            alias = f'renta_pj_seccion_{m.group(1) if m else "x"}'
            return Decision(row_num, topic, None, 'a',
                'declaracion_de_renta_personas_juridicas', alias, None, None, None,
                'Sección LOGGRO de declaración renta PJ — alias al catch-all existente.',
                P, kclass)

    # ========== EMERGENCIA_TRIBUTARIA (rows 46-57) ==========
    if topic == 'emergencia_tributaria':
        # Aliasing into the covid-era subtopic is wrong semantically but it's the only
        # emergencia_tributaria subtopic in the taxonomy today. Wide aliases repurpose it as
        # general emergency-tax bucket.
        return Decision(row_num, topic, None, 'a',
            'exenciones_tributarias_covid_19',
            'emergencia_tributaria_decretos_1474_0240_2025_2026',
            None, None, None,
            'Decretos 1474/2025 y 0240/2026 (emergencia económica Catatumbo/La Guajira) — ampliar alias del catch-all '
            'existente hasta que se renombre el subtopic.',
            P, kclass)

    # ========== ESTADOS_FINANCIEROS_NIIF (rows 58-62) ==========
    if topic == 'estados_financieros_niif':
        if '/DESCUENTOS_INVENTARIOS_NIIF/' in P:
            return Decision(row_num, topic, None, 'a',
                'conciliacion_fiscal_2516_2517',
                'descuentos_pronto_pago_niif_15', None, None, None,
                'Descuentos pronto pago en compras — tratamiento NIIF 15 / conciliación fiscal. Alias al catch-all.',
                P, kclass)
        if 'Ley-1530-2012' in P:
            return Decision(row_num, topic, 'presupuesto_hacienda', 'b',
                'sistema_general_regalias_ley_1530_2012', None,
                'presupuesto_hacienda.sistema_general_regalias_ley_1530_2012', None, None,
                'Ley 1530/2012 = Sistema General de Regalías. No es NIIF; parent correcto es presupuesto_hacienda.',
                P, kclass)

    # ========== GMF 4x1000 (row 63) ==========
    if topic == 'gravamen_movimiento_financiero_4x1000':
        return Decision(row_num, topic, None, 'b',
            'marco_legal_gmf_4x1000', None,
            'gravamen_movimiento_financiero_4x1000.marco_legal_gmf_4x1000', None, None,
            'Parent topic sin subtopics aún; este documento establece el primer anclaje.',
            P, kclass)

    # ========== ICA (rows 64-69) — TODOS son parent_topic corrections ==========
    if topic == 'ica':
        if '/IMPUESTO_PATRIMONIO_PN/' in P:
            return Decision(row_num, topic, 'impuesto_patrimonio_personas_naturales', 'a',
                'impuesto_al_patrimonio_excepcional_2011',
                'impuesto_patrimonio_PN_guia_practica_2026', None, None, None,
                'No es ICA — es impuesto al patrimonio PN. Corrección de parent_topic + alias al catch-all PN.',
                P, kclass)
        if 'Ley-1530-2012' in P:
            return Decision(row_num, topic, 'presupuesto_hacienda', 'b',
                'sistema_general_regalias_ley_1530_2012', None,
                'presupuesto_hacienda.sistema_general_regalias_ley_1530_2012', None, None,
                'Ley 1530/2012 SGR — parent correcto es presupuesto_hacienda, no ICA.',
                P, kclass)
        if 'seccion-08-clasificacion' in P:
            return Decision(row_num, topic, 'declaracion_renta', 'a',
                'declaracion_de_renta_personas_juridicas',
                'clasificacion_depuracion_ingresos_renta_pj', None, None, None,
                'Sección 08 sobre clasificación y depuración de ingresos es de renta PJ, no ICA.',
                P, kclass)
        if 'seccion-19-facturacion-electronica' in P:
            return Decision(row_num, topic, 'facturacion_electronica', 'a',
                'ecosistema_facturacion_electronica',
                'nomina_electronica_documento_soporte', None, None, None,
                'Sección 19 es facturación electrónica, no ICA.',
                P, kclass)
        if '/DEPRECIACION_FISCAL/' in P:
            return Decision(row_num, topic, 'declaracion_renta', 'b',
                'depreciacion_fiscal_pyme', None,
                'declaracion_renta.depreciacion_fiscal_pyme', None, None,
                'Depreciación fiscal = declaración de renta PJ + subtopic dedicado.',
                P, kclass)
        if '/PROCEDIMIENTO_RECURSO_EXOGENA/' in P:
            return Decision(row_num, topic, 'informacion_exogena', 'b',
                'recurso_sancion_exogena_art_651_ET', None,
                'informacion_exogena.recurso_sancion_exogena_art_651_ET', None, None,
                'Recurso contra sanción exógena = informacion_exogena. Corrección de parent + subtopic dedicado.',
                P, kclass)

    # ========== IMPUESTO PATRIMONIO PN (rows 70-71) ==========
    if topic == 'impuesto_patrimonio_personas_naturales':
        return Decision(row_num, topic, None, 'a',
            'impuesto_al_patrimonio_excepcional_2011',
            'impuesto_patrimonio_PN_permanente_arts_292_298_ET',
            None, None, None,
            'Impuesto al patrimonio PN vigente (arts 292-298 ET, reformado por Ley 2277/2022). '
            'Alias al catch-all existente — el nombre actual "excepcional_2011" es histórico y debería renombrarse.',
            P, kclass)

    # ========== IMPUESTOS SALUDABLES (row 72) ==========
    if topic == 'impuestos_saludables':
        return Decision(row_num, topic, None, 'b',
            'impuestos_saludables_ibua_icui', None,
            'impuestos_saludables.impuestos_saludables_ibua_icui', None, None,
            'IBUA + ICUI creados por Ley 2277/2022; necesita subtopic dedicado.',
            P, kclass)

    # ========== INFORMACION EXOGENA (rows 73-74) ==========
    if topic == 'informacion_exogena':
        return Decision(row_num, topic, None, 'b',
            'recurso_sancion_exogena_art_651_ET', None,
            'informacion_exogena.recurso_sancion_exogena_art_651_ET', None, None,
            'Módulo defensivo específico: recurso contra sanción art. 651 ET. Subtopic dedicado.',
            P, kclass)

    # ========== INVERSIONES INCENTIVOS (rows 75-92) — cada Ley = NEW subtopic ==========
    if topic == 'inversiones_incentivos':
        if 'Ley-218-1995' in P or '218-1995' in P or '218_1995' in P:
            return Decision(row_num, topic, None, 'b',
                'ley_paez_218_1995', None,
                'inversiones_incentivos.ley_paez_218_1995', None, None,
                'Ley 218/1995 Ley Páez — incentivo regional con vigencia residual.',
                P, kclass)
        if 'Ley-1429-2010' in P or '1429-2010' in P or '1429_2010' in P:
            return Decision(row_num, topic, None, 'b',
                'progresividad_ley_1429_2010_formalizacion', None,
                'inversiones_incentivos.progresividad_ley_1429_2010_formalizacion', None, None,
                'Ley 1429/2010 progresividad de renta — todavía aplicable a acogidos antes de derogatoria.',
                P, kclass)
        if 'Ley-1715-2014' in P or '1715-2014' in P or '1715_2014' in P:
            return Decision(row_num, topic, None, 'b',
                'fnce_ley_1715_2014_energia_renovable', None,
                'inversiones_incentivos.fnce_ley_1715_2014_energia_renovable', None, None,
                'Ley 1715/2014 FNCE — deducción renta + exclusión IVA energía renovable.',
                P, kclass)
        if 'Ley-2099-2021' in P or '2099-2021' in P or '2099_2021' in P:
            return Decision(row_num, topic, None, 'b',
                'transicion_energetica_ley_2099_2021', None,
                'inversiones_incentivos.transicion_energetica_ley_2099_2021', None, None,
                'Ley 2099/2021 transición energética — amplía Ley 1715.',
                P, kclass)

    # ========== IVA (rows 93-107) — todas son parent_topic corrections ==========
    if topic == 'iva':
        if 'DT-1221-2008' in P:
            return Decision(row_num, topic, 'datos_tecnologia', 'b',
                'teletrabajo_ley_1221_2008', None,
                'datos_tecnologia.teletrabajo_ley_1221_2008', None, None,
                'DT-1221-2008 = Datos/Tecnología Ley 1221/2008 Teletrabajo. PASO 1 falsa coincidencia con "IVA".',
                P, kclass)
        if 'II-1429-2010' in P:
            return Decision(row_num, topic, 'inversiones_incentivos', 'b',
                'progresividad_ley_1429_2010_formalizacion', None,
                'inversiones_incentivos.progresividad_ley_1429_2010_formalizacion', None, None,
                'II-1429-2010 = Inversiones Incentivos Ley 1429. Corrección parent + subtopic dedicado.',
                P, kclass)
        if 'II-1715-2014' in P:
            return Decision(row_num, topic, 'inversiones_incentivos', 'b',
                'fnce_ley_1715_2014_energia_renovable', None,
                'inversiones_incentivos.fnce_ley_1715_2014_energia_renovable', None, None,
                'II-1715-2014 = Inversiones Incentivos Ley 1715 FNCE.',
                P, kclass)
        if 'II-2099-2021' in P:
            return Decision(row_num, topic, 'inversiones_incentivos', 'b',
                'transicion_energetica_ley_2099_2021', None,
                'inversiones_incentivos.transicion_energetica_ley_2099_2021', None, None,
                'II-2099-2021 = Inversiones Incentivos Ley 2099.',
                P, kclass)
        if 'II-218-1995' in P:
            return Decision(row_num, topic, 'inversiones_incentivos', 'b',
                'ley_paez_218_1995', None,
                'inversiones_incentivos.ley_paez_218_1995', None, None,
                'II-218-1995 = Inversiones Incentivos Ley Páez.',
                P, kclass)
        if 'NC-1530-2012' in P:
            return Decision(row_num, topic, 'presupuesto_hacienda', 'b',
                'sistema_general_regalias_ley_1530_2012', None,
                'presupuesto_hacienda.sistema_general_regalias_ley_1530_2012', None, None,
                'NC-1530-2012 = NIIF/Contable Ley 1530 SGR. Parent correcto = presupuesto_hacienda.',
                P, kclass)
        if 'PF-1437-2011' in P:
            return Decision(row_num, topic, 'procedimiento_tributario', 'b',
                'cpaca_ley_1437_2011', None,
                'procedimiento_tributario.cpaca_ley_1437_2011', None, None,
                'PF-1437-2011 = Procedimiento Fiscal CPACA. Corrección de parent + subtopic dedicado.',
                P, kclass)
        if 'PF-1438-2011' in P:
            return Decision(row_num, topic, 'otros_sectoriales', 'a',
                'cumplimiento_normativo_sectorial_pymes',
                'ley_1438_2011_reforma_salud', None, None, None,
                'PF-1438-2011 = Ley 1438 reforma salud. NO es procedimiento tributario — es sectorial (salud).',
                P, kclass)
        if 'PF-1474-2011' in P:
            return Decision(row_num, topic, 'otros_sectoriales', 'b',
                'anticorrupcion_sagrilaft_ley_1474_2011', None,
                'otros_sectoriales.anticorrupcion_sagrilaft_ley_1474_2011', None, None,
                'PF-1474-2011 = Estatuto Anticorrupción. NO es procedimiento tributario — base SAGRILAFT/PTEE.',
                P, kclass)
        if 'PF-1564-2012' in P:
            return Decision(row_num, topic, 'procedimiento_tributario', 'b',
                'codigo_general_proceso_ley_1564_2012', None,
                'procedimiento_tributario.codigo_general_proceso_ley_1564_2012', None, None,
                'PF-1564-2012 = Código General del Proceso.',
                P, kclass)
        if 'PH-225-1995' in P:
            return Decision(row_num, topic, 'presupuesto_hacienda', 'a',
                'presupuesto_de_ingresos_y_egresos',
                'ley_225_1995_organica_presupuesto', None, None, None,
                'PH-225-1995 = Presupuesto/Hacienda Ley Orgánica de Presupuesto.',
                P, kclass)
        if '/RENTA/NORMATIVA/' in P:
            # ET Libros — all parent_topic should be declaracion_renta
            return Decision(row_num, topic, 'declaracion_renta', 'a',
                'declaracion_de_renta_personas_juridicas',
                'et_libro_normativa_base', None, None, None,
                'Archivos NORMATIVA de Libros del ET — parent correcto es declaracion_renta.',
                P, kclass)
        if '/FE_OPERATIVA/' in P:
            return Decision(row_num, topic, 'facturacion_electronica', 'a',
                'ecosistema_facturacion_electronica',
                'fe_habilitacion_contingencia_operativa', None, None, None,
                'FE_OPERATIVA = Facturación Electrónica operativa.',
                P, kclass)

    # ========== LABORAL (rows 108-132) ==========
    if topic == 'laboral':
        if 'Ley-2466-2025' in P or 'Ley_2466' in P or 'Reforma_Laboral_Ley_2466' in P:
            return Decision(row_num, topic, None, 'b',
                'reforma_laboral_ley_2466_2025', None,
                'laboral.reforma_laboral_ley_2466_2025', None, None,
                'Reforma Laboral Ley 2466/2025 — material nuevo con alto impacto en nómina. Subtopic dedicado.',
                P, kclass)
        # Para TODAS las demás leyes laborales: alias al catch-all con el número de ley
        m = re.search(r'Ley[-_](\d+)[-_](\d{4})', P)
        if m:
            alias = f'ley_{m.group(1)}_{m.group(2)}_laboral'
        else:
            alias = 'parafiscal_especial_marco_legal'
        return Decision(row_num, topic, None, 'a',
            'aporte_parafiscales_icbf', alias, None, None, None,
            f'Ley laboral — alias al catch-all parafiscal existente (alias: {alias}).',
            P, kclass)

    # ========== NIA (row 135) ==========
    if topic == 'normas_internacionales_auditoria':
        return Decision(row_num, topic, 'estados_financieros_niif', 'a',
            'conciliacion_fiscal_2516_2517',
            'normas_internacionales_auditoria_NIA', None, None, None,
            'NIA (Normas Internacionales de Auditoría) — parent correcto es estados_financieros_niif.',
            P, kclass)

    # ========== OTROS_SECTORIALES (rows 136-488) — BATCH INHERIT ==========
    if topic == 'otros_sectoriales':
        return Decision(row_num, topic, None, 'c',
            'cumplimiento_normativo_sectorial_pymes', None, None,
            '%/LEYES/OTROS_SECTORIALES/%',
            None,
            'Todos los archivos LEYES/OTROS_SECTORIALES/* son leyes sectoriales heterogéneas. '
            'Batch inherit al catch-all existente (UPDATE SQL único) — 353 docs en una sola operación.',
            P, kclass)

    # ========== PRESUPUESTO_HACIENDA (rows 489-495) ==========
    if topic == 'presupuesto_hacienda':
        m = re.search(r'Ley[-_](\d+)[-_](\d{4})', P)
        alias = f'ley_{m.group(1)}_{m.group(2)}_presupuesto' if m else 'presupuesto_ley_generica'
        return Decision(row_num, topic, None, 'a',
            'presupuesto_de_ingresos_y_egresos', alias, None, None, None,
            'Ley presupuestal / PND — alias al catch-all existente.',
            P, kclass)

    # ========== PROCEDIMIENTO_TRIBUTARIO (rows 496-515) ==========
    if topic == 'procedimiento_tributario':
        if 'Ley-1437-2011' in P:
            return Decision(row_num, topic, None, 'b',
                'cpaca_ley_1437_2011', None,
                'procedimiento_tributario.cpaca_ley_1437_2011', None, None,
                'Ley 1437/2011 CPACA — subtopic dedicado.',
                P, kclass)
        if 'Ley-1438-2011' in P:
            return Decision(row_num, topic, 'otros_sectoriales', 'a',
                'cumplimiento_normativo_sectorial_pymes',
                'ley_1438_2011_reforma_salud', None, None, None,
                'Ley 1438/2011 reforma salud — NO es procedimiento tributario, parent correcto = otros_sectoriales.',
                P, kclass)
        if 'Ley-1474-2011' in P:
            return Decision(row_num, topic, 'otros_sectoriales', 'b',
                'anticorrupcion_sagrilaft_ley_1474_2011', None,
                'otros_sectoriales.anticorrupcion_sagrilaft_ley_1474_2011', None, None,
                'Ley 1474/2011 Estatuto Anticorrupción — parent correcto = otros_sectoriales, subtopic SAGRILAFT/PTEE.',
                P, kclass)
        if 'Ley-1564-2012' in P:
            return Decision(row_num, topic, None, 'b',
                'codigo_general_proceso_ley_1564_2012', None,
                'procedimiento_tributario.codigo_general_proceso_ley_1564_2012', None, None,
                'Ley 1564/2012 CGP — subtopic dedicado (proceso ejecutivo cobro coactivo).',
                P, kclass)
        if '/RENTA/NORMATIVA/' in P:
            return Decision(row_num, topic, 'declaracion_renta', 'a',
                'declaracion_de_renta_personas_juridicas',
                'et_libro_normativa_base_renta_bruta', None, None, None,
                'Normativa Libro 1 T1 Cap3 Renta Bruta — parent correcto = declaracion_renta.',
                P, kclass)
        if 'RUT_RESPONSABILIDADES' in P:
            return Decision(row_num, topic, None, 'a',
                'fiscalizacion_y_defensa_dian',
                'RUT_responsabilidades_actualizacion', None, None, None,
                'RUT y responsabilidades — alias al catch-all de procedimiento.',
                P, kclass)
        if '/URLS-PIPELINE-DIAN/' in P:
            return Decision(row_num, topic, None, 'a',
                'fiscalizacion_y_defensa_dian',
                'urls_operativas_dian_directorio', None, None, None,
                'Directorio operativo URLs DIAN — alias al catch-all procedimiento.',
                P, kclass)
        # Default: corpus procedimiento tributario base
        return Decision(row_num, topic, None, 'a',
            'fiscalizacion_y_defensa_dian',
            'procedimiento_tributario_corpus_base', None, None, None,
            'Documento base de procedimiento tributario — alias al catch-all.',
            P, kclass)

    # ========== REFORMAS_TRIBUTARIAS (rows 516-550) ==========
    if topic == 'reformas_tributarias':
        m = re.search(r'Ley[-_](\d+)[-_](\d{4})', P)
        alias = f'ley_{m.group(1)}_{m.group(2)}_reforma_tributaria' if m else 'reforma_tributaria_generica'
        return Decision(row_num, topic, None, 'a',
            'reforma_tributaria_gmf_y_facturacion', alias, None, None, None,
            f'Ley histórica de reforma tributaria — alias al catch-all.',
            P, kclass)

    # ========== REGIMEN_SANCIONATORIO (rows 551-552) ==========
    if topic == 'regimen_sancionatorio':
        return Decision(row_num, topic, None, 'a',
            'ajuste_de_sanciones_por_inflacion',
            'regimen_sancionatorio_reduccion_gradualidad_fiscalizacion', None, None, None,
            'Régimen sancionatorio (reducción, gradualidad, fiscalización) — alias al catch-all.',
            P, kclass)

    # ========== REGIMEN_TRIBUTARIO_ESPECIAL / ESAL (rows 553-554) ==========
    if topic == 'regimen_tributario_especial':
        return Decision(row_num, topic, None, 'a',
            'regimen_tributario_especial_san_andres',
            'ESAL_regimen_tributario_especial', None, None, None,
            'ESAL — alias al catch-all existente de régimen tributario especial.',
            P, kclass)

    # ========== RETENCION EN LA FUENTE (rows 555-557) ==========
    if topic == 'retencion_en_la_fuente':
        return Decision(row_num, topic, None, 'a',
            'implementacion_retencion_en_la_fuente_pyme',
            'retencion_fuente_agente_retenedor_decreto_572', None, None, None,
            'Retención en la fuente (agente retenedor, Decreto 572) — alias al catch-all.',
            P, kclass)

    # ========== UNKNOWN (rows 558-563) ==========
    if topic == 'unknown':
        return Decision(row_num, topic, None, 'd',
            None, None, None, None,
            'form_guides asset o unknown — ya excluido arriba por path',
            'Excluir. (fallback para rows con topic=unknown que no matched el filtro form_guides)',
            P, kclass)

    # ========== ZONAS FRANCAS (rows 564-565) ==========
    if topic == 'zonas_francas':
        return Decision(row_num, topic, None, 'a',
            'beneficios_tributarios_zonas_de_frontera',
            'zonas_francas_regimen_tributario', None, None, None,
            'Zonas francas — alias al catch-all existente de zonas de frontera/francas.',
            P, kclass)

    # ========== FALLBACK ==========
    return Decision(row_num, topic, None, 'a',
        None, None, None, None, None,
        f'SIN DECISIÓN ENCODADA — revisar manualmente. topic={topic}, path={P}',
        P, kclass)


# ---------- main ----------
def main():
    with open(INPUT_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    decisions = []
    for r in rows:
        d = assign(int(r['#']), r['topic'], r['knowledge_class'], r['relative_path'])
        decisions.append(d)

    # -------- Stats --------
    action_counts = Counter(d.action for d in decisions)
    print(f'Total rows: {len(decisions)}')
    print('Action distribution:')
    for a, n in action_counts.most_common():
        print(f'  ({a}): {n}')

    parent_corrections = [d for d in decisions if d.topic_corrected]
    print(f'\nParent-topic corrections: {len(parent_corrections)}')
    correction_pairs = Counter((d.topic_detected, d.topic_corrected) for d in parent_corrections)
    for (src, tgt), n in correction_pairs.most_common():
        print(f'  {src} -> {tgt}: {n}')

    # -------- decisions.csv --------
    decisions_path = os.path.join(OUTDIR, 'decisions.csv')
    with open(decisions_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            '#', 'topic_detected', 'topic_corrected', 'action',
            'target_subtopic_key', 'alias_to_add', 'new_subtopic_ref',
            'batch_pattern', 'exclude_reason', 'rationale',
            'relative_path', 'knowledge_class',
        ])
        for d in decisions:
            w.writerow([
                d.row_num, d.topic_detected, d.topic_corrected or '', d.action,
                d.target_subtopic_key or '', d.alias_to_add or '', d.new_subtopic_ref or '',
                d.batch_pattern or '', d.exclude_reason or '', d.rationale,
                d.relative_path, d.knowledge_class,
            ])
    print(f'\nWrote {decisions_path}')

    # -------- alias_additions.json --------
    # Map: full_key -> sorted unique list of aliases to add
    alias_add = defaultdict(set)
    for d in decisions:
        if d.action == 'a' and d.target_subtopic_key and d.alias_to_add:
            parent = d.parent_key
            full_key = f'{parent}.{d.target_subtopic_key}'
            alias_add[full_key].add(d.alias_to_add)
    alias_out = {
        'taxonomy_version_base': '2026-04-21-v1',
        'patch_generated': '2026-04-21',
        'patch_generated_by': 'curator-decisions-abril-2026',
        'description': 'Aliases to add to existing subtopics to absorb flagged docs (case a).',
        'patches': [
            {
                'subtopic_full_key': k,
                'aliases_to_add': sorted(aliases),
            } for k, aliases in sorted(alias_add.items())
        ],
    }
    alias_path = os.path.join(OUTDIR, 'alias_additions.json')
    with open(alias_path, 'w') as f:
        json.dump(alias_out, f, indent=2, ensure_ascii=False)
    print(f'Wrote {alias_path} — {len(alias_out["patches"])} subtopics get aliases')

    # -------- new_subtopics.json --------
    # Only include subtopics that actually got referenced
    referenced = {d.new_subtopic_ref for d in decisions if d.new_subtopic_ref}
    new_out = {
        'taxonomy_version_base': '2026-04-21-v1',
        'patch_generated': '2026-04-21',
        'patch_generated_by': 'curator-decisions-abril-2026',
        'description': 'New subtopic entries to add to taxonomy (case b).',
        'new_subtopics': [
            {
                'full_key': k,
                'parent_topic_key': v['parent_topic_key'],
                'subtopic_key': k.split('.', 1)[1],
                'label': v['label'],
                'aliases': v['aliases'],
                'evidence_count_seed': sum(1 for d in decisions if d.new_subtopic_ref == k),
                'rationale_introduced': v['rationale_introduced'],
            }
            for k, v in sorted(NEW_SUBTOPICS.items())
            if k in referenced
        ],
    }
    new_path = os.path.join(OUTDIR, 'new_subtopics.json')
    with open(new_path, 'w') as f:
        json.dump(new_out, f, indent=2, ensure_ascii=False)
    print(f'Wrote {new_path} — {len(new_out["new_subtopics"])} new subtopics')

    # -------- parent_topic_corrections.sql --------
    sql_path = os.path.join(OUTDIR, 'parent_topic_corrections.sql')
    with open(sql_path, 'w') as f:
        f.write('-- Parent-topic corrections for PASO 1 mis-routed docs\n')
        f.write('-- Generated: 2026-04-21 | source: curator-decisions-abril-2026\n')
        f.write('-- Apply BEFORE running subtopic backfill, so aliases match the corrected parent.\n\n')
        for d in decisions:
            if not d.topic_corrected:
                continue
            # Safe SQL escaping for single quote
            safe_path = d.relative_path.replace("'", "''")
            safe_doc_id = (d.relative_path.replace("'", "''"))
            f.write(
                f"-- Row #{d.row_num}: {d.topic_detected} -> {d.topic_corrected}\n"
                f"-- Rationale: {d.rationale}\n"
                f"UPDATE documents SET parent_topic_key = '{d.topic_corrected}' "
                f"WHERE relative_path = '{safe_path}';\n\n"
            )
    print(f'Wrote {sql_path} — {len(parent_corrections)} parent corrections')

    # -------- batch_inherit.sql --------
    batch_sql_path = os.path.join(OUTDIR, 'batch_inherit.sql')
    with open(batch_sql_path, 'w') as f:
        f.write('-- Batch-inherit SQL updates (case c): sibling triplets share a subtopic\n')
        f.write('-- Generated: 2026-04-21\n')
        f.write('-- Run AFTER parent_topic_corrections.sql and AFTER applying alias_additions.json + new_subtopics.json\n\n')

        # Group by batch_pattern + target_subtopic_key
        buckets = defaultdict(list)
        for d in decisions:
            if d.action == 'c' and d.batch_pattern and d.target_subtopic_key:
                key = (d.batch_pattern, d.parent_key, d.target_subtopic_key)
                buckets[key].append(d)

        for (pattern, parent, subtopic), ds in sorted(buckets.items()):
            f.write(
                f"-- Pattern: {pattern}\n"
                f"-- Parent topic: {parent}\n"
                f"-- Target subtopic: {subtopic}\n"
                f"-- Affected docs: {len(ds)} (flagged rows {ds[0].row_num}-{ds[-1].row_num})\n"
                f"UPDATE documents\n"
                f"SET parent_topic_key = '{parent}',\n"
                f"    subtema = '{subtopic}'\n"
                f"WHERE relative_path LIKE '{pattern}'\n"
                f"  AND subtema IS NULL;\n\n"
            )
    print(f'Wrote {batch_sql_path}')

    # -------- exclusions.txt --------
    excl_path = os.path.join(OUTDIR, 'exclusions.txt')
    with open(excl_path, 'w') as f:
        f.write('# Paths to exclude from corpus (case d)\n')
        f.write('# Generated: 2026-04-21\n')
        f.write('# Action: DELETE FROM documents WHERE relative_path IN (...) AND remove from upload pipeline\n\n')
        excl = [d for d in decisions if d.action == 'd']
        grouped = defaultdict(list)
        for d in excl:
            grouped[d.exclude_reason or 'unspecified'].append(d)
        for reason, ds in sorted(grouped.items()):
            f.write(f'## {reason} ({len(ds)} docs)\n')
            for d in ds:
                f.write(f'{d.relative_path}\n')
            f.write('\n')
    print(f'Wrote {excl_path} — {sum(1 for d in decisions if d.action == "d")} exclusions')

    # -------- Stats returned for memo --------
    return {
        'total': len(decisions),
        'action_counts': dict(action_counts),
        'parent_corrections': len(parent_corrections),
        'correction_pairs': dict(correction_pairs),
        'new_subtopics_count': len(new_out['new_subtopics']),
        'alias_patches_count': len(alias_out['patches']),
        'batch_patterns_count': len(buckets),
        'exclusions_count': sum(1 for d in decisions if d.action == 'd'),
    }


if __name__ == '__main__':
    import json as _json
    stats = main()
    print('\n=== SUMMARY STATS ===')
    print(_json.dumps(stats, indent=2, default=str))
