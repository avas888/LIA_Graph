-- Parent-topic corrections for PASO 1 mis-routed docs
-- Generated: 2026-04-21 | source: curator-decisions-abril-2026
-- Apply BEFORE running subtopic backfill, so aliases match the corrected parent.

-- Row #3: comercial_societario -> reformas_tributarias
-- Rationale: Ley 223/1994 es una reforma tributaria, no comercial societario. Alias al catch-all de reformas.
UPDATE documents SET parent_topic_key = 'reformas_tributarias' WHERE relative_path = 'CORE ya Arriba/COMERCIAL_SOCIETARIO/Ley-223-1994.md';

-- Row #4: comercial_societario -> otros_sectoriales
-- Rationale: Ley 1480/2011 es Estatuto del Consumidor (SIC), no societario — corrección de parent_topic + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/consolidado/Ley-1480-2011.md';

-- Row #7: comercial_societario -> otros_sectoriales
-- Rationale: Ley 1480/2011 es Estatuto del Consumidor (SIC), no societario — corrección de parent_topic + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/EXPERTOS/EXPERTOS_Ley-1480-2011.md';

-- Row #11: comercial_societario -> presupuesto_hacienda
-- Rationale: Ley 1151/2007 es el Plan Nacional de Desarrollo 2006-2010 — parent correcto es presupuesto_hacienda.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/LOGGRO/PRACTICA_Ley-1151-2007.md';

-- Row #12: comercial_societario -> otros_sectoriales
-- Rationale: Ley 1480/2011 es Estatuto del Consumidor (SIC), no societario — corrección de parent_topic + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/LOGGRO/PRACTICA_Ley-1480-2011.md';

-- Row #15: comercial_societario -> otros_sectoriales
-- Rationale: Ley 1480/2011 es Estatuto del Consumidor (SIC), no societario — corrección de parent_topic + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/NORMATIVA/Ley-1480-2011.md';

-- Row #22: datos_tecnologia -> declaracion_renta
-- Rationale: Sección 28 de casos prácticos es parte de la guía LOGGRO de declaración de renta PJ; PASO 1 la enrutó mal.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/LOGGRO/seccion-28-casos-practicos.md';

-- Row #59: estados_financieros_niif -> presupuesto_hacienda
-- Rationale: Ley 1530/2012 = Sistema General de Regalías. No es NIIF; parent correcto es presupuesto_hacienda.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/LEYES/NIIF_CONTABLE/consolidado/Ley-1530-2012.md';

-- Row #60: estados_financieros_niif -> presupuesto_hacienda
-- Rationale: Ley 1530/2012 = Sistema General de Regalías. No es NIIF; parent correcto es presupuesto_hacienda.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/LEYES/NIIF_CONTABLE/EXPERTOS/EXPERTOS_Ley-1530-2012.md';

-- Row #61: estados_financieros_niif -> presupuesto_hacienda
-- Rationale: Ley 1530/2012 = Sistema General de Regalías. No es NIIF; parent correcto es presupuesto_hacienda.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/LEYES/NIIF_CONTABLE/NORMATIVA/Ley-1530-2012.md';

-- Row #64: ica -> impuesto_patrimonio_personas_naturales
-- Rationale: No es ICA — es impuesto al patrimonio PN. Corrección de parent_topic + alias al catch-all PN.
UPDATE documents SET parent_topic_key = 'impuesto_patrimonio_personas_naturales' WHERE relative_path = 'CORE ya Arriba/IMPUESTO_PATRIMONIO_PN/LOGGRO/PAT-L01-guia-practica-declaracion-patrimonio-PN-2026.md';

-- Row #65: ica -> presupuesto_hacienda
-- Rationale: Ley 1530/2012 SGR — parent correcto es presupuesto_hacienda, no ICA.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/LEYES/NIIF_CONTABLE/LOGGRO/PRACTICA_Ley-1530-2012.md';

-- Row #66: ica -> declaracion_renta
-- Rationale: Sección 08 sobre clasificación y depuración de ingresos es de renta PJ, no ICA.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/LOGGRO/seccion-08-clasificacion-y-depuracion-de-ingresos.md';

-- Row #67: ica -> facturacion_electronica
-- Rationale: Sección 19 es facturación electrónica, no ICA.
UPDATE documents SET parent_topic_key = 'facturacion_electronica' WHERE relative_path = 'CORE ya Arriba/RENTA/LOGGRO/seccion-19-facturacion-electronica-documento-soporte-nomina-electronica.md';

-- Row #68: ica -> declaracion_renta
-- Rationale: Depreciación fiscal = declaración de renta PJ + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'to upload/AGGRANDIZEMENT-ABRIL-2026/DEPRECIACION_FISCAL/LOGGRO/DEP-L01-guia-practica-depreciacion-fiscal-PYME.md';

-- Row #69: ica -> informacion_exogena
-- Rationale: Recurso contra sanción exógena = informacion_exogena. Corrección de parent + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'informacion_exogena' WHERE relative_path = 'to upload/AGGRANDIZEMENT-ABRIL-2026/PROCEDIMIENTO_RECURSO_EXOGENA/LOGGRO/PRO-L01-guia-practica-recurso-sancion-no-presentar-exogena.md';

-- Row #93: iva -> datos_tecnologia
-- Rationale: DT-1221-2008 = Datos/Tecnología Ley 1221/2008 Teletrabajo. PASO 1 falsa coincidencia con "IVA".
UPDATE documents SET parent_topic_key = 'datos_tecnologia' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/DT-1221-2008-NORMATIVA.md';

-- Row #94: iva -> inversiones_incentivos
-- Rationale: II-1429-2010 = Inversiones Incentivos Ley 1429. Corrección parent + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'inversiones_incentivos' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/II-1429-2010-NORMATIVA.md';

-- Row #95: iva -> inversiones_incentivos
-- Rationale: II-1715-2014 = Inversiones Incentivos Ley 1715 FNCE.
UPDATE documents SET parent_topic_key = 'inversiones_incentivos' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/II-1715-2014-NORMATIVA.md';

-- Row #96: iva -> inversiones_incentivos
-- Rationale: II-2099-2021 = Inversiones Incentivos Ley 2099.
UPDATE documents SET parent_topic_key = 'inversiones_incentivos' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/II-2099-2021-NORMATIVA.md';

-- Row #97: iva -> inversiones_incentivos
-- Rationale: II-218-1995 = Inversiones Incentivos Ley Páez.
UPDATE documents SET parent_topic_key = 'inversiones_incentivos' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/II-218-1995-NORMATIVA.md';

-- Row #98: iva -> presupuesto_hacienda
-- Rationale: NC-1530-2012 = NIIF/Contable Ley 1530 SGR. Parent correcto = presupuesto_hacienda.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/NC-1530-2012-NORMATIVA.md';

-- Row #99: iva -> procedimiento_tributario
-- Rationale: PF-1437-2011 = Procedimiento Fiscal CPACA. Corrección de parent + subtopic dedicado.
UPDATE documents SET parent_topic_key = 'procedimiento_tributario' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/PF-1437-2011-NORMATIVA.md';

-- Row #100: iva -> otros_sectoriales
-- Rationale: PF-1438-2011 = Ley 1438 reforma salud. NO es procedimiento tributario — es sectorial (salud).
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/PF-1438-2011-NORMATIVA.md';

-- Row #101: iva -> otros_sectoriales
-- Rationale: PF-1474-2011 = Estatuto Anticorrupción. NO es procedimiento tributario — base SAGRILAFT/PTEE.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/PF-1474-2011-NORMATIVA.md';

-- Row #102: iva -> procedimiento_tributario
-- Rationale: PF-1564-2012 = Código General del Proceso.
UPDATE documents SET parent_topic_key = 'procedimiento_tributario' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/PF-1564-2012-NORMATIVA.md';

-- Row #103: iva -> presupuesto_hacienda
-- Rationale: PH-225-1995 = Presupuesto/Hacienda Ley Orgánica de Presupuesto.
UPDATE documents SET parent_topic_key = 'presupuesto_hacienda' WHERE relative_path = 'CORE ya Arriba/NORMATIVA_LEYES/PH-225-1995-NORMATIVA.md';

-- Row #104: iva -> declaracion_renta
-- Rationale: Archivos NORMATIVA de Libros del ET — parent correcto es declaracion_renta.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/NORMATIVA/Normativa/01_Libro1_T1_Sujetos_Pasivos.md';

-- Row #105: iva -> declaracion_renta
-- Rationale: Archivos NORMATIVA de Libros del ET — parent correcto es declaracion_renta.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/NORMATIVA/Normativa/12_Libro1_T4_Remesas.md';

-- Row #106: iva -> declaracion_renta
-- Rationale: Archivos NORMATIVA de Libros del ET — parent correcto es declaracion_renta.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/NORMATIVA/Normativa/21_Libro7_ECE_CHC.md';

-- Row #107: iva -> facturacion_electronica
-- Rationale: FE_OPERATIVA = Facturación Electrónica operativa.
UPDATE documents SET parent_topic_key = 'facturacion_electronica' WHERE relative_path = 'to upload/BRECHAS-SEMANA1-ABRIL-2026/FE_OPERATIVA/LOGGRO/FE-L07-habilitacion-contingencia-operativa.md';

-- Row #135: normas_internacionales_auditoria -> estados_financieros_niif
-- Rationale: NIA (Normas Internacionales de Auditoría) — parent correcto es estados_financieros_niif.
UPDATE documents SET parent_topic_key = 'estados_financieros_niif' WHERE relative_path = 'CORE ya Arriba/Corpus de Contabilidad/EXPERTOS/T-NIA-normas-internacionales-auditoria-interpretaciones-expertos.md';

-- Row #501: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1438/2011 reforma salud — NO es procedimiento tributario, parent correcto = otros_sectoriales.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/EXPERTOS/EXPERTOS_Ley-1438-2011.md';

-- Row #502: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1474/2011 Estatuto Anticorrupción — parent correcto = otros_sectoriales, subtopic SAGRILAFT/PTEE.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/EXPERTOS/EXPERTOS_Ley-1474-2011.md';

-- Row #504: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1438/2011 reforma salud — NO es procedimiento tributario, parent correcto = otros_sectoriales.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/LOGGRO/PRACTICA_Ley-1438-2011.md';

-- Row #505: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1474/2011 Estatuto Anticorrupción — parent correcto = otros_sectoriales, subtopic SAGRILAFT/PTEE.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/LOGGRO/PRACTICA_Ley-1474-2011.md';

-- Row #507: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1438/2011 reforma salud — NO es procedimiento tributario, parent correcto = otros_sectoriales.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/NORMATIVA/Ley-1438-2011.md';

-- Row #508: procedimiento_tributario -> otros_sectoriales
-- Rationale: Ley 1474/2011 Estatuto Anticorrupción — parent correcto = otros_sectoriales, subtopic SAGRILAFT/PTEE.
UPDATE documents SET parent_topic_key = 'otros_sectoriales' WHERE relative_path = 'CORE ya Arriba/LEYES/PROCEDIMIENTO_FISCAL/NORMATIVA/Ley-1474-2011.md';

-- Row #513: procedimiento_tributario -> declaracion_renta
-- Rationale: Normativa Libro 1 T1 Cap3 Renta Bruta — parent correcto = declaracion_renta.
UPDATE documents SET parent_topic_key = 'declaracion_renta' WHERE relative_path = 'CORE ya Arriba/RENTA/NORMATIVA/Normativa/04_Libro1_T1_Cap3_Renta_Bruta.md';

