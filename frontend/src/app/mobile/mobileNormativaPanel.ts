import type { MobileSheet } from "./mobileSheet";
import {
  renderMobileCitationCards,
  type MobileCitationCardViewModel,
} from "@/shared/ui/organisms/citationList";
import {
  fetchCitationProfileInstant,
  fetchCitationProfileLlm,
} from "@/features/chat/normative/profileRenderer";
import type {
  CitationProfileResponse,
  CitationProfileFact,
  CitationProfileOriginalText,
  CitationProfileAdditionalDepthSection,
  CitationProfileAdditionalDepthItem,
  CitationProfileExpertComment,
  CitationProfileBanner,
} from "@/features/chat/normative/types";
import { openArticleReader } from "@/features/chat/normative/articleReader";
import { sanitizeHref, isRenderableEvidenceStatus } from "@/features/chat/normative/citationParsing";
import { createLinkAction } from "@/shared/ui/atoms/button";
import { createBadge } from "@/shared/ui/atoms/badge";
import { icons } from "@/shared/ui/icons";

export interface MobileNormativaPanel {
  setCitations(citations: MobileCitationCardViewModel[]): void;
  clear(): void;
}

/**
 * Renders mobile-friendly citation cards from shared citation view models.
 * When tapped, fetches the citation profile directly from the API (Supabase corpus)
 * and renders the same rich content that the desktop modal shows.
 */
export function mountMobileNormativaPanel(
  root: HTMLElement,
  sheet: MobileSheet,
  options: {
    onOpenCitation?: (citationId: string) => void;
  } = {},
): MobileNormativaPanel {
  const listEl = root.querySelector<HTMLElement>("#mobile-normativa-list")!;
  const emptyEl = root.querySelector<HTMLElement>("#mobile-normativa-empty")!;
  let currentCitations: MobileCitationCardViewModel[] = [];

  function setCitations(citations: MobileCitationCardViewModel[]): void {
    currentCitations = [...citations];
    if (currentCitations.length === 0) {
      listEl.replaceChildren();
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    renderMobileCitationCards(listEl, currentCitations);
  }

  function clear(): void {
    currentCitations = [];
    listEl.replaceChildren();
    emptyEl.hidden = false;
  }

  listEl.addEventListener("click", (event: Event) => {
    const card = (event.target as HTMLElement).closest<HTMLElement>(".mobile-citation-card");
    if (!card) return;
    if ((event.target as HTMLElement).closest("a")) return;

    const index = parseInt(card.dataset.citationIndex ?? "-1", 10);
    const citation = currentCitations[index];
    if (!citation) return;

    void openNormaSheet(citation);
  });

  // Delegated click handler for depth items (related content links)
  document.addEventListener("click", (e: Event) => {
    const link = (e.target as HTMLElement).closest<HTMLAnchorElement>(".mobile-depth-item-link");
    if (!link) return;
    e.preventDefault();
    const docId = link.dataset.docId || "";
    const label = link.dataset.docLabel || "";
    const klass = link.dataset.knowledgeClass || "practica_erp";
    if (docId) openArticleReader(docId, label, klass);
  });

  // Depth sections use native <details> accordion — no JS handler needed.

  function buildLoaderHtml(): string {
    return `
      <div class="mobile-sheet-loader">
        <span class="lia-thinking-eye-pair">
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
        </span>
        <span class="mobile-sheet-loader-text">Consultando...</span>
      </div>
    `;
  }

  function buildMentionHtml(citation: MobileCitationCardViewModel): string {
    const linkBtn = citation.externalUrl
      ? `<div class="mobile-sheet-actions">
           ${createLinkAction({ href: citation.externalUrl, iconHtml: icons.link, label: "Abrir en Normograma DIAN", className: "mobile-sheet-action-btn" }).outerHTML}
         </div>`
      : "";

    return `
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          <strong>${escapeHtml(citation.title)}</strong> fue mencionada en la respuesta de LIA como soporte normativo.
          ${!citation.externalUrl ? '<br><br>Esta normativa no está incluida aún en el corpus de LIA. Puedes buscarla directamente en fuentes oficiales.' : ''}
        </div>
      </div>
      ${linkBtn}
    `;
  }

  function buildErrorHtml(citation: MobileCitationCardViewModel): string {
    const linkBtn = citation.externalUrl
      ? createLinkAction({ href: citation.externalUrl, iconHtml: icons.link, label: "Abrir fuente", className: "mobile-sheet-action-btn" }).outerHTML
      : "";

    return `
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          No fue posible cargar el detalle de esta referencia normativa.
        </div>
      </div>
      ${linkBtn ? `<div class="mobile-sheet-actions">${linkBtn}</div>` : ""}
    `;
  }

  // ── Rich profile HTML builder from CitationProfileResponse ──────────

  function buildProfileHtmlFromResponse(
    profile: CitationProfileResponse,
    citation: MobileCitationCardViewModel,
  ): string {
    const parts: string[] = [];

    // 1. Caution banner
    const cautionHtml = buildCautionBannerHtml(profile.caution_banner);
    if (cautionHtml) parts.push(cautionHtml);

    // 2. Binding force badge
    //    The backend returns taxonomy labels like "Decreto reglamentario" or
    //    "Ley o estatuto". Prefix with "Fuerza vinculante:" so the badge reads
    //    as an authority statement instead of a bare classification. The tone
    //    is derived from `binding_force_rank` (numeric hierarchy position)
    //    rather than string-matching the label.
    const bf = String(profile.binding_force || "").trim();
    const bfRank = typeof profile.binding_force_rank === "number" ? profile.binding_force_rank : 0;
    if (bf) {
      parts.push(`
        <div class="mobile-sheet-section">
          <span class="mobile-sheet-badge" data-tone="${bindingForceTone(bf, bfRank)}">${escapeHtml(formatBindingForceText(bf))}</span>
        </div>
      `);
    }

    // 3. Summary: lead text (always shown)
    const lead = String(profile.lead || "").trim();
    if (lead) {
      parts.push(`
        <div class="mobile-sheet-section">
          <div class="mobile-sheet-excerpt">${escapeHtml(lead)}</div>
        </div>
      `);
    }

    // 4. Original text (ET articles — quoted article)
    const originalHtml = buildOriginalTextHtml(profile.original_text, lead);
    if (originalHtml) parts.push(originalHtml);

    // 5. Facts (compact metadata)
    const facts = collectFacts(profile);
    const factsHtml = buildFactsHtml(facts);
    if (factsHtml) parts.push(factsHtml);

    // 6. Implicaciones para el contador (sections)
    const sectionsHtml = buildSectionsHtml(profile.sections, profile);
    if (sectionsHtml) parts.push(sectionsHtml);

    // 7. Contenido relacionado (flat list with badges)
    const depthHtml = buildAdditionalDepthHtml(profile.additional_depth_sections);
    if (depthHtml) parts.push(depthHtml);

    // 8. Action buttons
    const actionsHtml = buildActionsHtml(profile, citation);
    if (actionsHtml) parts.push(actionsHtml);

    return parts.join("");
  }

  function buildCautionBannerHtml(banner: CitationProfileBanner | null | undefined): string {
    const title = String(banner?.title || "").trim();
    const body = String(banner?.body || "").trim();
    if (!title && !body) return "";
    return `
      <div class="mobile-sheet-caution" data-tone="${String(banner?.tone || "").trim()}">
        ${title ? `<strong>${escapeHtml(title)}</strong>` : ""}
        ${body ? `<p>${escapeHtml(body)}</p>` : ""}
      </div>
    `;
  }

  function buildOriginalTextHtml(
    original: CitationProfileOriginalText | null | undefined,
    introText: string,
  ): string {
    if (!original) return "";
    const status = String(original.evidence_status || "").trim();
    if (status && status !== "verified" && status !== "missing") return "";
    const title = String(original.title || "").trim();
    const quote = String(original.quote || "").trim();
    if (!title) return "";

    const intro = introText ? `<p class="mobile-sheet-intro">${escapeHtml(introText)}</p>` : "";
    const sourceUrl = sanitizeHref(original.source_url);
    const sourceLink = sourceUrl
      ? `<a class="mobile-sheet-source-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">Ver fuente del artículo</a>`
      : "";

    if (!quote) {
      return `
        <div class="mobile-sheet-section mobile-sheet-original-text">
          ${intro}
          <h4 class="mobile-sheet-section-title">${escapeHtml(title)}</h4>
          ${sourceLink}
        </div>
      `;
    }

    const quoteParagraphs = quote
      .replace(/\r\n/g, "\n")
      .split(/\n{2,}/)
      .map((p) => p.trim())
      .filter(Boolean)
      .map((p) => `<p>${escapeHtml(p)}</p>`)
      .join("");

    return `
      <div class="mobile-sheet-section mobile-sheet-original-text">
        ${intro}
        <h4 class="mobile-sheet-section-title">${escapeHtml(title)}</h4>
        <blockquote class="mobile-sheet-quote">${quoteParagraphs}</blockquote>
        ${sourceLink}
      </div>
    `;
  }

  function collectFacts(profile: CitationProfileResponse): CitationProfileFact[] {
    // Mobile keeps all facts visible (including for ET articles)
    // unlike desktop which suppresses base facts for ET articles.
    const rows = Array.isArray(profile.facts) ? [...profile.facts] : [];
    const vigencia = profile.vigencia_detail;
    if (
      vigencia &&
      isRenderableEvidenceStatus(vigencia.evidence_status) &&
      String(vigencia.label || "").trim()
    ) {
      const summaryText = String(vigencia.summary || "").trim();
      const value = summaryText || [
        String(vigencia.label || "").trim(),
        String(vigencia.basis || "").trim(),
        String(vigencia.notes || "").trim(),
        String(vigencia.last_verified_date || "").trim()
          ? `Última verificación del corpus: ${String(vigencia.last_verified_date || "").trim()}`
          : "",
      ].filter(Boolean).join("\n");
      const existingIdx = rows.findIndex((fact) => /vigencia/i.test(String(fact?.label || "")));
      const entry: CitationProfileFact = { label: "Vigencia específica", value };
      if (existingIdx >= 0) {
        rows.splice(existingIdx, 1, entry);
      } else {
        rows.push(entry);
      }
    }
    return rows;
  }

  function buildFactsHtml(facts: CitationProfileFact[]): string {
    const validFacts = facts.filter(
      (f) => f && String(f.label || "").trim() && String(f.value || "").trim(),
    );
    if (validFacts.length === 0) return "";
    const items = validFacts
      .map(
        (f) => `
        <div class="mobile-sheet-fact">
          <span class="mobile-sheet-fact-label">${escapeHtml(String(f.label || "").trim())}</span>
          <div class="mobile-sheet-fact-value">${formatTextContent(String(f.value || "").trim())}</div>
        </div>`,
      )
      .join("");

    return `
      <div class="mobile-sheet-section">
        <h4 class="mobile-sheet-section-title">Datos clave</h4>
        <div class="mobile-sheet-facts">${items}</div>
      </div>
    `;
  }

  function buildSectionsHtml(
    sections: CitationProfileResponse["sections"],
    profile: CitationProfileResponse,
  ): string {
    if (!Array.isArray(sections)) return "";
    const filtered = sections.filter((s) => {
      if (!s || !String(s.title || "").trim() || !String(s.body || "").trim()) return false;
      const sectionId = String(s.id || "").trim();
      if (sectionId === "texto_original_relevante" && profile.original_text) return false;
      if (sectionId === "comentario_experto_relevante" && profile.expert_comment) return false;
      if (/instrumento de diligenciamiento/i.test(String(s.title || "").trim())) return false;
      return true;
    });
    if (filtered.length === 0) return "";

    const items = filtered
      .map(
        (s) => `
        <article class="mobile-sheet-section-card">
          <h4 class="mobile-sheet-section-title">${escapeHtml(String(s.title || "").trim())}</h4>
          <div class="mobile-sheet-section-body">${formatTextContent(String(s.body || "").trim())}</div>
        </article>`,
      )
      .join("");

    return `<div class="mobile-sheet-section">${items}</div>`;
  }

  function _kindBadge(kind: string): { label: string; tone: string } {
    switch (kind) {
      case "normative_base":
        return { label: "Normativa", tone: "info" };
      case "interpretative_guidance":
        return { label: "Expertos", tone: "warning" };
      case "practica_erp":
        return { label: "Práctico", tone: "success" };
      default:
        return { label: "", tone: "neutral" };
    }
  }

  function _renderDepthItem(item: CitationProfileAdditionalDepthItem): string {
    const label = escapeHtml(String(item.label || "").trim());
    const kind = String(item.kind || "").trim();
    const docId = String(item.doc_id || "").trim();
    const badge = _kindBadge(kind);
    const badgeHtml = badge.label
      ? createBadge({ label: badge.label, tone: badge.tone as any }).outerHTML + " "
      : "";

    if (docId) {
      return `<li><a href="#" class="mobile-depth-item-link" data-doc-id="${escapeHtml(docId)}" data-doc-label="${label}" data-knowledge-class="${escapeHtml(kind)}">${badgeHtml}${label}</a></li>`;
    }
    const href = sanitizeHref(item.url);
    if (href) {
      return `<li><a href="${href}" target="_blank" rel="noopener noreferrer">${badgeHtml}${label}</a></li>`;
    }
    return `<li>${badgeHtml}${label}</li>`;
  }

  function buildAdditionalDepthHtml(
    sections: CitationProfileAdditionalDepthSection[] | null | undefined,
  ): string {
    if (!Array.isArray(sections)) return "";

    // Sort open sections first (e.g. "Contenido relacionado"), then closed
    const sorted = [...sections].filter(Boolean).sort((a, b) => {
      const aOpen = String(a!.accordion_default || "closed") === "open" ? 0 : 1;
      const bOpen = String(b!.accordion_default || "closed") === "open" ? 0 : 1;
      return aOpen - bOpen;
    });

    const cards: string[] = [];
    for (const s of sorted) {
      if (!s) continue;
      const title = String(s.title || "").trim() || "Contenido relacionado de posible utilidad";
      const items = Array.isArray(s.items)
        ? s.items.filter((item) => String(item?.label || "").trim())
        : [];
      if (!items.length) continue;

      const isClosed = String(s.accordion_default || "closed") === "closed";
      const bullets = items.map((item) => _renderDepthItem(item)).join("");
      const listHtml = `<ul class="mobile-sheet-bullet-list mobile-depth-list">${bullets}</ul>`;

      if (isClosed) {
        // Closed sections use native <details> accordion — starts collapsed
        cards.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card mobile-sheet-accordion">
              <details>
                <summary class="mobile-sheet-accordion-summary">${escapeHtml(title)}</summary>
                ${listHtml}
              </details>
            </article>
          </div>
        `);
      } else {
        // Open sections render with visible list
        cards.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card">
              <h4 class="mobile-sheet-section-title">${escapeHtml(title)}</h4>
              ${listHtml}
            </article>
          </div>
        `);
      }
    }
    return cards.join("");
  }

  function buildExpertCommentHtml(expert: CitationProfileExpertComment | null | undefined): string {
    if (!expert) return "";
    const status = String(expert.evidence_status || "").trim();
    if (status && status !== "verified" && status !== "missing") return "";
    const body = String(expert.body || "").trim();
    if (!body) return "";

    const isOpen = String(expert.accordion_default || "closed").trim() === "open";
    const topicLabel = String(expert.topic_label || expert.source_label || "Detalle").trim();

    const sourceUrl = sanitizeHref(expert.source_url);
    const sourceLabel = String(expert.source_label || "").trim();
    const sourceMeta = sourceUrl
      ? `<a class="mobile-sheet-source-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(sourceLabel || "Fuente experta")}</a>`
      : sourceLabel
        ? `<p class="mobile-sheet-expert-source">${escapeHtml(sourceLabel)}</p>`
        : "";

    return `
      <div class="mobile-sheet-section">
        <article class="mobile-sheet-section-card mobile-sheet-accordion">
          <h4 class="mobile-sheet-section-title">Comentario experto relevante</h4>
          <details${isOpen ? " open" : ""}>
            <summary class="mobile-sheet-accordion-summary">${escapeHtml(topicLabel)}</summary>
            <div class="mobile-sheet-section-body">${formatTextContent(body)}</div>
            ${sourceMeta}
          </details>
        </article>
      </div>
    `;
  }

  function buildActionsHtml(
    profile: CitationProfileResponse,
    citation: MobileCitationCardViewModel,
  ): string {
    const actions: string[] = [];

    const sourceAction = profile.source_action;
    if (sourceAction && String(sourceAction.state || "").trim() !== "not_applicable") {
      const href = sanitizeHref(sourceAction.url);
      const label = String(sourceAction.label || "Ir a documento original").trim();
      if (href) {
        actions.push(createLinkAction({ href, iconHtml: icons.link, label, className: "mobile-sheet-action-btn" }).outerHTML);
      }
    }

    const analysisAction = profile.analysis_action;
    if (analysisAction && String(analysisAction.state || "").trim() === "available") {
      const href = sanitizeHref(analysisAction.url);
      const label = String(analysisAction.label || "Análisis profundo").trim();
      if (href) {
        actions.push(createLinkAction({ href, iconHtml: icons.search, label, className: "mobile-sheet-action-btn" }).outerHTML);
      }
    }

    const companionAction = profile.companion_action;
    if (companionAction && String(companionAction.state || "").trim() === "available") {
      const href = sanitizeHref(companionAction.url);
      const label = String(companionAction.label || "Guía de formulario").trim();
      if (href) {
        actions.push(createLinkAction({ href, iconHtml: icons.bookOpen, label, className: "mobile-sheet-action-btn" }).outerHTML);
      }
    }

    if (actions.length === 0 && citation.externalUrl) {
      actions.push(createLinkAction({ href: citation.externalUrl, iconHtml: icons.link, label: "Abrir fuente", className: "mobile-sheet-action-btn" }).outerHTML);
    }

    return actions.length > 0
      ? `<div class="mobile-sheet-actions">${actions.join("")}</div>`
      : "";
  }

  // ── Main sheet opener — calls API directly ──────────────────────────

  async function openNormaSheet(citation: MobileCitationCardViewModel): Promise<void> {
    // Non-modal citations: show mention view
    if (citation.action !== "modal") {
      sheet.open({
        title: citation.title,
        subtitle: citation.meta,
        html: buildMentionHtml(citation),
      });
      return;
    }

    // No raw citation data: fall back to mention view
    if (!citation.rawCitation) {
      sheet.open({
        title: citation.title,
        subtitle: citation.meta,
        html: buildMentionHtml(citation),
      });
      return;
    }

    // Show loader while fetching
    sheet.open({
      title: citation.title,
      subtitle: citation.meta,
      html: buildLoaderHtml(),
    });

    // Also trigger the desktop flow (in background) so the desktop modal DOM
    // stays populated if user switches views. But we don't scrape from it.
    options.onOpenCitation?.(citation.id);
    hideDesktopModal(root);

    try {
      // Phase 1: Instant profile from corpus (Supabase)
      const profile = await fetchCitationProfileInstant(citation.rawCitation);

      if (!sheet.isOpen()) return;

      // If the profile came back skipped or empty, fall back to mention
      if (profile.skipped) {
        sheet.open({
          title: citation.title,
          subtitle: citation.meta,
          html: buildMentionHtml(citation),
        });
        return;
      }

      // Render the rich profile content
      const profileTitle = String(profile.title || "").trim();
      const displayTitle = profileTitle || citation.title;
      const rawBindingForce = String(profile.binding_force || "").trim();
      const subtitle = rawBindingForce
        ? formatBindingForceText(rawBindingForce)
        : String(citation.meta || "").trim();

      sheet.open({
        title: displayTitle,
        subtitle,
        html: buildProfileHtmlFromResponse(profile, citation),
      });

      // Phase 2: LLM enrichment (if needed)
      if (profile.needs_llm) {
        try {
          const llmResult = await fetchCitationProfileLlm(citation.rawCitation);
          if (!sheet.isOpen()) return;

          // Merge LLM enrichment into the base profile
          const enriched: CitationProfileResponse = {
            ...profile,
            lead: String(llmResult.lead || "").trim() || profile.lead,
            facts: Array.isArray(llmResult.facts) && llmResult.facts.length > 0
              ? llmResult.facts
              : profile.facts,
            sections: Array.isArray(llmResult.sections) && llmResult.sections.length > 0
              ? llmResult.sections
              : profile.sections,
            vigencia_detail: llmResult.vigencia_detail ?? profile.vigencia_detail,
          };

          sheet.open({
            title: displayTitle,
            subtitle,
            html: buildProfileHtmlFromResponse(enriched, citation),
          });
        } catch {
          // LLM enrichment failed — keep the instant profile, it's still useful
        }
      }
    } catch {
      if (!sheet.isOpen()) return;
      // API call failed — fall back to error/mention
      sheet.open({
        title: citation.title,
        subtitle: citation.meta,
        html: buildErrorHtml(citation),
      });
    }
  }

  return { setCitations, clear };
}

// ── Helpers ───────────────────────────────────────────────────────────

function hideDesktopModal(root: HTMLElement): void {
  const layer = root.querySelector<HTMLElement>("#modal-layer");
  if (layer) layer.hidden = true;
  const norma = root.querySelector<HTMLElement>("#modal-norma");
  if (norma) {
    norma.classList.remove("is-open");
    norma.setAttribute("aria-hidden", "true");
  }
}

/**
 * Map a normative document's binding force to a badge tone.
 *
 * Prefers the numeric `binding_force_rank` emitted by `normative_taxonomy.py`
 * (1000 = constitutional, 100 = generic support). When the rank is absent
 * (legacy test fixtures, missing field), falls back to pattern-matching the
 * label — including the stale alta/media vocabulary so old fixtures still
 * light up correctly.
 *
 * Rank thresholds:
 *   - ≥ 700 → "success"  (constitucional, ley, et_dur, decreto,
 *                         jurisprudencia, resolución DIAN — binding norms)
 *   - ≥ 300 → "warning"  (formulario, doctrina administrativa, circular —
 *                         prescriptive or orientative, read with caveats)
 *   - <  300 → "neutral" (generic support documents)
 */
function bindingForceTone(value: string, rank: number = 0): string {
  if (rank >= 700) return "success";
  if (rank >= 300) return "warning";
  if (rank > 0) return "neutral";

  // Fallback: no rank provided. Try to recover a tone from the label itself.
  const normalized = value.toLowerCase();
  if (normalized.includes("alta")) return "success";
  if (normalized.includes("media")) return "warning";
  if (/(rango constitucional|ley o estatuto|compilaci[oó]n tributaria|decreto reglamentario|precedente judicial|resoluci[oó]n dian)/.test(normalized)) {
    return "success";
  }
  if (/(instrumento operativo|doctrina administrativa|circular administrativa)/.test(normalized)) {
    return "warning";
  }
  return "neutral";
}

/**
 * Wrap a raw `binding_force` string from the backend taxonomy
 * (`normative_taxonomy.py`) with the "Fuerza vinculante:" prefix. Idempotent
 * if the value already carries the prefix — mirrors the desktop logic in
 * `profileRenderer.ts` so both surfaces render the eyebrow consistently.
 */
function formatBindingForceText(raw: string): string {
  const value = String(raw || "").trim();
  if (!value) return "";
  return /^fuerza\s+vinculante\b/i.test(value) ? value : `Fuerza vinculante: ${value}`;
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatTextContent(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${escapeHtml(p)}</p>`)
    .join("");
}
