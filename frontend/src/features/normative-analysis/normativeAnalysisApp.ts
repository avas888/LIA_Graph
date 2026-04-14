// @ts-nocheck

import { renderMarkdown } from "@/content/markdown";
import { getJson } from "@/shared/api/client";
import type { I18nRuntime } from "@/shared/i18n";
import { createChip } from "@/shared/ui/atoms/chip";
import { createLinkAction } from "@/shared/ui/atoms/button";
import { createFactCard } from "@/shared/ui/molecules/factCard";
import { createNormativeSection } from "@/shared/ui/molecules/normativeSection";
import { createTimelineItem } from "@/shared/ui/molecules/timelineItem";
import { createRelationLink } from "@/shared/ui/molecules/relationLink";
import { visibleText } from "@/shared/utils/format";

// ── Response DTOs ──────────────────────────────────────────────────

interface FactRow {
  label: string;
  value: string;
}

interface SectionRow {
  id: string;
  title: string;
  body: string;
}

interface BannerRow {
  title?: string;
  body?: string;
  tone?: string;
}

interface TimelineEventRow {
  id: string;
  label: string;
  date?: string;
  detail?: string;
}

interface RelatedDocumentRow {
  doc_id?: string;
  title?: string;
  relation_type?: string;
  relation_label?: string;
  helper_text?: string;
  url?: string;
}

interface RecommendedActionRow {
  id: string;
  kind?: string;
  label?: string;
  url?: string;
  helper_text?: string;
}

interface NormativeAnalysisResponse {
  ok: boolean;
  title: string;
  document_family: string;
  family_subtype?: string;
  hierarchy_tier?: string;
  binding_force?: string;
  ui_surface?: string;
  lead?: string;
  preview_facts?: FactRow[];
  caution_banner?: BannerRow | null;
  sections?: SectionRow[];
  timeline_events?: TimelineEventRow[];
  related_documents?: RelatedDocumentRow[];
  allowed_secondary_overlays?: string[];
  recommended_actions?: RecommendedActionRow[];
}

// ── Label humanization ─────────────────────────────────────────────

const FAMILY_LABELS: Record<string, string> = {
  decreto: "Decreto",
  ley: "Ley",
  resolucion: "Resolución",
  et_dur: "Estatuto Tributario / DUR",
  formulario: "Formulario",
  concepto: "Concepto",
  circular: "Circular",
  jurisprudencia: "Jurisprudencia",
  constitucion: "Constitución",
};

const SUBTYPE_LABELS: Record<string, string> = {
  decreto_reglamentario: "Decreto reglamentario",
  decreto_ordinario: "Decreto ordinario",
  decreto_legislativo: "Decreto legislativo",
  resolucion_dian: "Resolución DIAN",
  resolucion_parametrica: "Resolución paramétrica",
  resolucion_general: "Resolución general",
  concepto_general: "Concepto general",
  concepto_unificado: "Concepto unificado",
  sentencia_corte_constitucional: "Sentencia Corte Constitucional",
  sentencia_consejo_estado: "Sentencia Consejo de Estado",
  documento_general: "",
};

function humanizeFamily(family: string, subtype: string): string {
  const familyLabel = FAMILY_LABELS[family] || family.replace(/_/g, " ");
  const subtypeLabel = SUBTYPE_LABELS[subtype] || subtype.replace(/_/g, " ");
  return [familyLabel, subtypeLabel].filter(Boolean).join(" / ");
}

// ── Mount ──────────────────────────────────────────────────────────

export function mountNormativeAnalysisApp(_root: HTMLElement, opts: { i18n: I18nRuntime }) {
  const params = new URLSearchParams(window.location.search);
  const docId = params.get("doc_id") || "";
  if (!docId) {
    showError(opts.i18n.t("normativeAnalysis.missingDoc"));
    return;
  }
  void loadAnalysis(docId, params, opts.i18n);
}

async function loadAnalysis(docId: string, pageParams: URLSearchParams, i18n: I18nRuntime) {
  try {
    const params = new URLSearchParams();
    params.set("doc_id", docId);
    for (const field of ["locator_text", "locator_kind", "locator_start", "locator_end"]) {
      const value = pageParams.get(field);
      if (value) {
        params.set(field, value);
      }
    }
    const response = await getJson<NormativeAnalysisResponse>(`/api/normative-analysis?${params.toString()}`);
    if (!response.ok) {
      showError(i18n.t("normativeAnalysis.error"));
      return;
    }
    await renderAnalysis(response, i18n);
  } catch {
    showError(i18n.t("normativeAnalysis.error"));
  }
}

function showError(message: string) {
  const loadingEl = document.getElementById("normative-analysis-loading");
  const contentEl = document.getElementById("normative-analysis-content");
  const errorEl = document.getElementById("normative-analysis-error");
  const msgEl = document.getElementById("normative-analysis-error-message");
  if (loadingEl) loadingEl.hidden = true;
  if (contentEl) contentEl.hidden = true;
  if (errorEl) errorEl.hidden = false;
  if (msgEl) msgEl.textContent = message;
}

// ── Render helpers (compose from atoms/molecules) ──────────────────

function renderFactRows(node: HTMLElement, rows: FactRow[]) {
  node.replaceChildren(
    ...rows
      .filter((item) => item?.label?.trim() && item?.value?.trim())
      .map((item) =>
        createFactCard({
          label: String(item.label).trim(),
          value: String(item.value).trim(),
        }),
      ),
  );
}

async function renderSections(node: HTMLElement, rows: SectionRow[]) {
  node.replaceChildren();
  for (const item of rows.filter((s) => s?.title?.trim() && s?.body?.trim())) {
    node.appendChild(
      createNormativeSection(
        { id: item.id, title: String(item.title).trim(), body: String(item.body).trim() },
        async (container, markdown) => {
          await renderMarkdown(container, markdown, { animate: false });
        },
      ),
    );
  }
}

function renderTimeline(node: HTMLElement, rows: TimelineEventRow[], i18n?: I18nRuntime) {
  node.replaceChildren(
    ...rows
      .filter((item) => item?.label?.trim())
      .map((item) =>
        createTimelineItem(
          {
            id: item.id,
            label: String(item.label).trim(),
            date: item.date,
            detail: item.detail,
          },
          i18n?.t("normativeAnalysis.unconfirmedDate") || "",
        ),
      ),
  );
}

function renderRelations(node: HTMLElement, rows: RelatedDocumentRow[]) {
  node.replaceChildren(
    ...rows
      .filter((item) => item?.title?.trim())
      .map((item) =>
        createRelationLink({
          docId: item.doc_id,
          title: String(item.title).trim(),
          relationLabel: String(item.relation_label || item.relation_type || "").trim(),
          helperText: item.helper_text,
          url: item.url,
        }),
      ),
  );
}

function renderOverlays(node: HTMLElement, items: string[]) {
  node.replaceChildren(
    ...items
      .filter(Boolean)
      .map((item) =>
        createChip({
          label: String(item).replace(/_/g, " ").trim(),
          tone: "neutral",
          emphasis: "soft",
        }),
      ),
  );
}

function renderActions(node: HTMLElement, rows: RecommendedActionRow[]) {
  node.replaceChildren(
    ...rows
      .filter((item) => item?.label?.trim() && item?.url?.trim())
      .map((item) => {
        const wrap = document.createElement("div");
        wrap.className = "normative-analysis-action";

        const isExternal = /^https?:\/\//i.test(String(item.url || ""));
        wrap.appendChild(
          createLinkAction({
            href: String(item.url).trim(),
            label: String(item.label).trim(),
            tone: item.kind === "source" ? "primary" : "secondary",
            target: isExternal ? "_blank" : "_self",
          }),
        );

        if (item.helper_text?.trim()) {
          const helper = document.createElement("p");
          helper.className = "normative-analysis-action__helper";
          helper.textContent = item.helper_text;
          wrap.appendChild(helper);
        }

        return wrap;
      }),
  );
}

// ── Main render orchestrator ───────────────────────────────────────

async function renderAnalysis(payload: NormativeAnalysisResponse, i18n: I18nRuntime) {
  const loadingEl = document.getElementById("normative-analysis-loading");
  const contentEl = document.getElementById("normative-analysis-content");
  const titleEl = document.getElementById("normative-analysis-title");
  const familyEl = document.getElementById("normative-analysis-family");
  const bindingEl = document.getElementById("normative-analysis-binding");
  const leadEl = document.getElementById("normative-analysis-lead");
  const cautionEl = document.getElementById("normative-analysis-caution");
  const cautionTitleEl = document.getElementById("normative-analysis-caution-title");
  const cautionBodyEl = document.getElementById("normative-analysis-caution-body");

  if (loadingEl) loadingEl.hidden = true;
  if (contentEl) contentEl.hidden = false;
  if (titleEl) titleEl.textContent = String(payload.title || "").trim();
  document.title = `${String(payload.title || "").trim() || i18n.t("app.title.normativeAnalysis")} | ${i18n.t("app.title.normativeAnalysis")}`;
  if (familyEl) {
    familyEl.textContent = humanizeFamily(payload.document_family || "", payload.family_subtype || "");
  }
  if (bindingEl) {
    bindingEl.textContent = String(payload.binding_force || "").trim();
    bindingEl.hidden = !bindingEl.textContent;
  }
  if (leadEl) {
    leadEl.textContent = String(payload.lead || "").trim();
    leadEl.hidden = !leadEl.textContent;
  }
  if (cautionEl && cautionTitleEl && cautionBodyEl) {
    cautionTitleEl.textContent = visibleText(payload.caution_banner?.title);
    cautionBodyEl.textContent = visibleText(payload.caution_banner?.body);
    cautionEl.hidden = !(cautionTitleEl.textContent && cautionBodyEl.textContent);
    cautionEl.setAttribute(
      "data-tone",
      cautionEl.hidden ? "" : String(payload.caution_banner?.tone || "").trim(),
    );
  }

  const factsNode = document.getElementById("normative-analysis-facts");
  const sectionsNode = document.getElementById("normative-analysis-sections");
  const timelineNode = document.getElementById("normative-analysis-timeline");
  const relationsNode = document.getElementById("normative-analysis-relations");
  const overlaysNode = document.getElementById("normative-analysis-overlays");
  const actionsNode = document.getElementById("normative-analysis-actions");

  if (factsNode) renderFactRows(factsNode, payload.preview_facts || []);
  if (sectionsNode) await renderSections(sectionsNode, payload.sections || []);
  if (timelineNode) renderTimeline(timelineNode, payload.timeline_events || [], i18n);
  if (relationsNode) renderRelations(relationsNode, payload.related_documents || []);
  if (overlaysNode) renderOverlays(overlaysNode, payload.allowed_secondary_overlays || []);
  if (actionsNode) renderActions(actionsNode, payload.recommended_actions || []);
}
