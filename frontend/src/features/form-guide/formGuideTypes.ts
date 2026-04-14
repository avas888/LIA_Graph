import { publishedSpanishText } from "@/shared/utils/format";

export interface FormGuideSource {
  source_id: string;
  title: string;
  url: string;
  source_type: string;
  authority: string;
  is_primary: boolean;
  last_checked_date: string;
  notes: string;
}

export interface StructuredSection {
  section_id: string;
  title: string;
  purpose: string;
  what_to_review: string;
  profile_differences: string;
  common_errors: string;
  warnings: string;
  source_ids: string[];
}

export interface FieldHotspot {
  field_id: string;
  label: string;
  page: number;
  bbox: [number, number, number, number];
  marker_bbox?: [number, number, number, number] | null;
  section: string;
  casilla?: number;
  año_gravable?: string;
  profiles?: string[];
  instruction_md: string;
  official_dian_instruction?: string;
  what_to_review_before_filling: string;
  common_errors: string;
  warnings: string;
  source_ids?: string[];
  last_verified_date?: string;
}

export type GuideViewMode = "interactive" | "structured";

export interface GuideManifest {
  reference_key: string;
  title: string;
  form_version: string;
  profile_id: string;
  profile_label: string;
  supported_views: string[];
  last_verified_date: string;
  disclaimer: string;
}

export interface GuidePageAsset {
  name: string;
  page: number;
  url: string;
}

export interface GuideContentResponse {
  ok: boolean;
  manifest: GuideManifest;
  pages: string[];
  page_assets: GuidePageAsset[];
  interactive_map: FieldHotspot[];
  structured_sections: StructuredSection[];
  sources: FormGuideSource[];
  official_pdf_url?: string;
  official_pdf_authority?: string;
  disclaimer: string;
}

export interface GuideCatalogEntry {
  reference_key: string;
  title: string;
  form_version: string;
  available_profiles: Array<{ profile_id: string; profile_label: string }>;
  supported_views: string[];
  last_verified_date: string;
  download_available: boolean;
  disclaimer: string;
}

export interface GuideCatalogResponse extends Partial<GuideCatalogEntry> {
  ok: boolean;
  guide?: GuideCatalogEntry;
  guides?: GuideCatalogEntry[];
}

export interface GuideChatMessageResponse {
  ok: boolean;
  answer_markdown: string;
  answer_mode: string;
  grounding: Record<string, unknown> & {
    handoff_url?: string;
    handoff_target?: string;
  };
  suggested_followups: string[];
}

export function sanitizeAppHref(raw: unknown): string {
  const value = String(raw || "").trim();
  if (!value) return "";
  if (value.startsWith("/")) return value;
  if (/^https?:\/\//i.test(value)) return value;
  return "";
}

export function findOfficialFormPdfUrl(sources: FormGuideSource[]): { url: string; authority: string } {
  for (const source of sources) {
    const url = sanitizeAppHref(source.url);
    if (!url) continue;
    if (String(source.source_type || "").trim().toLowerCase() !== "formulario_oficial_pdf") continue;
    return {
      url,
      authority: String(source.authority || "").trim(),
    };
  }
  return { url: "", authority: "" };
}

export function uiText(value: unknown): string {
  return publishedSpanishText(String(value ?? "").trim());
}

export function openDialogSafely(dialog: HTMLDialogElement): void {
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) {
      dialog.showModal();
    }
    return;
  }
  dialog.setAttribute("open", "true");
}

export function closeDialogSafely(dialog: HTMLDialogElement): void {
  if (typeof dialog.close === "function" && dialog.open) {
    dialog.close();
    return;
  }
  dialog.removeAttribute("open");
}

export function isDialogOpen(dialog: HTMLDialogElement): boolean {
  return dialog.open || dialog.hasAttribute("open");
}

export function setGuideView(mode: GuideViewMode): void {
  const structuredBtn = document.getElementById("view-structured-btn");
  const interactiveBtn = document.getElementById("view-interactive-btn");
  if (!structuredBtn || !interactiveBtn) return;

  const interactiveSelected = mode === "interactive" && !interactiveBtn.hasAttribute("disabled");
  interactiveBtn.classList.toggle("view-toggle-active", interactiveSelected);
  structuredBtn.classList.toggle("view-toggle-active", !interactiveSelected);
  interactiveBtn.setAttribute("aria-selected", interactiveSelected ? "true" : "false");
  structuredBtn.setAttribute("aria-selected", interactiveSelected ? "false" : "true");
}

export function fieldDisplayName(field: FieldHotspot): string {
  return String(field.label || (field.casilla ? `Casilla ${field.casilla}` : "este campo")).trim();
}

export function renderHotspotBadge(field: FieldHotspot): string {
  if (field.casilla) return String(field.casilla);
  return field.label ? field.label : "Campo";
}

function parseMarkerBox(field: FieldHotspot): [number, number, number, number] | null {
  if (!Array.isArray(field.marker_bbox) || field.marker_bbox.length !== 4) {
    return null;
  }
  const values = field.marker_bbox.map((value) => Number(value)) as [number, number, number, number];
  return values.every((value) => Number.isFinite(value)) ? values : null;
}

export function resolveHotspotAnchor(field: FieldHotspot): {
  left: number;
  top: number;
  centered: boolean;
  markerCenterX: number | null;
  markerCenterY: number | null;
} {
  const markerBox = parseMarkerBox(field);
  if (markerBox) {
    return {
      left: markerBox[0] + markerBox[2] / 2,
      top: markerBox[1] + markerBox[3] / 2,
      centered: true,
      markerCenterX: markerBox[0] + markerBox[2] / 2,
      markerCenterY: markerBox[1] + markerBox[3] / 2,
    };
  }

  return {
    left: field.bbox[0],
    top: field.bbox[1],
    centered: false,
    markerCenterX: null,
    markerCenterY: null,
  };
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
