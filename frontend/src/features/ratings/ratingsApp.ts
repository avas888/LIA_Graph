// @ts-nocheck

import "@/styles/ratings/ratings.css";
import { getJson } from "@/shared/api/client";
import { renderMarkdown } from "@/content/markdown";
import { createButton, createIconButton } from "@/shared/ui/atoms/button";
import { createButtonChip } from "@/shared/ui/atoms/chip";
import { icons } from "@/shared/ui/icons";
import { createGooglyLoader, type GooglyLoader } from "@/shared/ui/googlyLoader";
import { renderUserFilter, TENANT_FILTER_PREFIX, type UserFilterGroup } from "@/shared/ui/organisms/recordCollections";
import { TZ_CO, bogotaParts, bogotaStartOfToday, bogotaStartOfWeek, bogotaStartOfMonth } from "@/shared/dates";
import type { I18nRuntime } from "@/shared/i18n";

interface RatingEntry {
  trace_id: string;
  session_id: string | null;
  user_id: string;
  rating: number;
  comment: string;
  question_text: string;
  answer_text: string;
  timestamp: string;
  tenant_id: string;
}

interface TenantOption {
  tenant_id: string;
  display_name: string;
  members?: { user_id: string; email: string; display_name: string }[];
}

type TimeFilterKey = "" | "today" | "week" | "month";

interface RatingsState {
  entries: RatingEntry[];
  loading: boolean;
  errorMessage: string;
  userFilter: string;
  ratingFilter: Set<number>;
  timeFilter: TimeFilterKey;
  offset: number;
  hasMore: boolean;
}

function escapeHtml(s: string): string {
  const el = document.createElement("span");
  el.textContent = s;
  return el.innerHTML;
}

function renderStars(rating: number): string {
  const filled = Math.max(0, Math.min(5, rating));
  return "\u2605".repeat(filled) + "\u2606".repeat(5 - filled);
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const p = bogotaParts(d);
  const ampm = p.hour >= 12 ? "p.m." : "a.m.";
  const h = p.hour % 12 || 12;
  return `${p.day} ${months[p.month]} ${p.year}, ${h}:${String(p.minute).padStart(2, "0")} ${ampm}`;
}

function computeSince(key: TimeFilterKey): string | null {
  if (!key) return null;
  if (key === "today") return bogotaStartOfToday().toISOString();
  if (key === "week") return bogotaStartOfWeek().toISOString();
  if (key === "month") return bogotaStartOfMonth().toISOString();
  return null;
}

const PAGE_SIZE = 50;

export function mountRatingsApp(
  container: HTMLElement,
  { i18n }: { i18n: I18nRuntime },
): void {
  const state: RatingsState = {
    entries: [],
    loading: false,
    errorMessage: "",
    userFilter: "",
    ratingFilter: new Set<number>(),
    timeFilter: "",
    offset: 0,
    hasMore: true,
  };

  let tenants: TenantOption[] = [];

  container.innerHTML = `
    <div class="ratings-shell">
      <header class="ratings-header">
        <h1 class="ratings-title">Calificaciones de usuarios</h1>
        <div class="ratings-filters">
          <div class="ratings-user-dropdown"></div>
          <div class="ratings-time-chips" aria-label="Filtrar por periodo"></div>
          <div class="ratings-rating-chips" aria-label="Filtrar por calificacion"></div>
        </div>
      </header>
      <div class="ratings-list"></div>
      <div class="ratings-footer"></div>
      <dialog class="ratings-detail-dialog"></dialog>
    </div>
  `;

  const listEl = container.querySelector<HTMLElement>(".ratings-list")!;
  const footerEl = container.querySelector<HTMLElement>(".ratings-footer")!;
  const googlyLoader: GooglyLoader = createGooglyLoader("Cargando calificaciones...");
  const dialog = container.querySelector<HTMLDialogElement>(".ratings-detail-dialog")!;
  const userDropdownEl = container.querySelector<HTMLElement>(".ratings-user-dropdown")!;
  const timeChipsEl = container.querySelector<HTMLElement>(".ratings-time-chips")!;
  const ratingChipsEl = container.querySelector<HTMLElement>(".ratings-rating-chips")!;

  // ── Data loading ──

  async function load(append = false): Promise<void> {
    state.loading = true;
    render();

    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(state.offset),
    });
    if (state.userFilter && state.userFilter.startsWith(TENANT_FILTER_PREFIX)) {
      params.set("tenant_id", state.userFilter.slice(TENANT_FILTER_PREFIX.length));
    } else if (state.userFilter) {
      params.set("user_id", state.userFilter);
    }
    if (state.ratingFilter.size > 0) {
      const vals = [...state.ratingFilter];
      params.set("rating_min", String(Math.min(...vals)));
      params.set("rating_max", String(Math.max(...vals)));
    }
    const since = computeSince(state.timeFilter);
    if (since) params.set("since", since);

    try {
      const data = await getJson<{ ok: boolean; ratings: RatingEntry[]; error?: string }>(
        `/api/admin/ratings?${params}`,
      );
      let newEntries = data?.ratings || [];
      if (state.ratingFilter.size > 0) {
        newEntries = newEntries.filter((e) => state.ratingFilter.has(e.rating));
      }
      state.entries = append ? [...state.entries, ...newEntries] : newEntries;
      state.hasMore = newEntries.length >= PAGE_SIZE;
      state.errorMessage = "";
    } catch (err: unknown) {
      console.error("Error loading ratings:", err);
      state.hasMore = false;
      if (!append) state.entries = [];
      const apiErr = err as { status?: number; message?: string };
      if (apiErr.status === 401 || apiErr.status === 403) {
        state.errorMessage = "No tiene permisos para ver calificaciones. Verifique su sesion.";
      } else {
        state.errorMessage = apiErr.message || "Error al cargar calificaciones.";
      }
    }

    state.loading = false;
    render();
  }

  // ── Rendering ──

  function render(): void {
    if (state.loading && state.entries.length === 0) {
      listEl.innerHTML = "";
      listEl.appendChild(googlyLoader.el);
      googlyLoader.show();
      footerEl.innerHTML = "";
      return;
    }
    googlyLoader.hide();

    if (!state.loading && state.entries.length === 0) {
      if (state.errorMessage) {
        listEl.innerHTML = `<p class="ratings-error">${escapeHtml(state.errorMessage)}</p>`;
      } else {
        listEl.innerHTML = `<p class="ratings-empty">No se encontraron calificaciones.</p>`;
      }
      footerEl.innerHTML = "";
      return;
    }

    listEl.innerHTML = state.entries.map(renderCard).join("");

    if (state.hasMore) {
      footerEl.replaceChildren(createButton({ label: "Cargar mas", tone: "ghost", className: "ratings-load-more" }));
    } else {
      footerEl.replaceChildren();
    }
  }

  function renderCard(entry: RatingEntry): string {
    const date = formatShortDate(entry.timestamp);
    const stars = renderStars(entry.rating);
    const question = escapeHtml((entry.question_text || "").slice(0, 120));
    const hasMore = (entry.question_text || "").length > 120;
    const commentHtml = entry.comment
      ? `<p class="rating-card-comment">${escapeHtml(entry.comment)}</p>`
      : "";

    const tenantBadge = entry.tenant_id ? `<span class="rating-card-tenant">${escapeHtml(entry.tenant_id)}</span>` : "";

    return `
      <div class="rating-card" data-trace-id="${escapeHtml(entry.trace_id)}">
        <div class="rating-card-header">
          <span class="rating-card-stars" aria-label="${entry.rating} de 5">${stars}</span>
          <span class="rating-card-user">${escapeHtml(entry.user_id || "Anonimo")}</span>
          ${tenantBadge}
          <span class="rating-card-date">${date}</span>
        </div>
        <p class="rating-card-question">${question}${hasMore ? "..." : ""}</p>
        ${commentHtml}
      </div>
    `;
  }

  function showDetail(entry: RatingEntry): void {
    const stars = renderStars(entry.rating);
    const question = escapeHtml(entry.question_text || "(sin pregunta)");
    const comment = entry.comment
      ? `<div class="rating-detail-section">
           <h3>Comentario</h3>
           <p>${escapeHtml(entry.comment)}</p>
         </div>`
      : "";

    dialog.innerHTML = `
      <div class="ratings-detail">
        <header class="rating-detail-header">
          <span class="rating-detail-stars" aria-label="${entry.rating} de 5">${stars}</span>
          <span class="rating-detail-actions" id="rating-detail-actions"></span>
        </header>
        <div class="rating-detail-section">
          <h3>Consulta</h3>
          <p>${question}</p>
        </div>
        <div class="rating-detail-section">
          <h3>Respuesta</h3>
          <div class="rating-detail-answer bubble-content"></div>
        </div>
        ${comment}
        <div class="rating-detail-meta">
          <span>Usuario: ${escapeHtml(entry.user_id || "Anonimo")}</span>
          <span>Sesion: ${escapeHtml(entry.session_id || "\u2014")}</span>
          <span>${formatShortDate(entry.timestamp)}</span>
        </div>
      </div>
    `;

    const answerEl = dialog.querySelector<HTMLElement>(".rating-detail-answer")!;
    void renderMarkdown(answerEl, entry.answer_text || "(sin respuesta)", { animate: false });

    const actionsEl = dialog.querySelector<HTMLElement>("#rating-detail-actions")!;

    const copyBtn = createIconButton({
      iconHtml: icons.copy,
      tone: "ghost",
      className: "rating-detail-copy",
      attrs: { "aria-label": "Copiar contenido", title: "Copiar" },
      onClick: async () => {
        const text = `CONSULTA:\n${entry.question_text || ""}\n\nRESPUESTA:\n${entry.answer_text || ""}`;
        await navigator.clipboard.writeText(text);
        const iconEl = copyBtn.querySelector("svg")?.parentElement ?? copyBtn;
        iconEl.innerHTML = icons.checkCircle;
        copyBtn.setAttribute("title", "Copiado!");
        setTimeout(() => {
          iconEl.innerHTML = icons.copy;
          copyBtn.setAttribute("title", "Copiar");
        }, 1500);
      },
    });
    actionsEl.appendChild(copyBtn);

    const closeBtn = createIconButton({
      iconHtml: icons.close,
      tone: "ghost",
      className: "rating-detail-close",
      attrs: { "aria-label": "Cerrar" },
      onClick: () => dialog.close(),
    });
    actionsEl.appendChild(closeBtn);

    dialog.showModal();
  }

  // ── Event handlers ──

  listEl.addEventListener("click", (e) => {
    const card = (e.target as HTMLElement).closest<HTMLElement>(".rating-card");
    if (!card) return;
    const traceId = card.dataset.traceId;
    const entry = state.entries.find((en) => en.trace_id === traceId);
    if (entry) showDetail(entry);
  });

  userDropdownEl.addEventListener("change", (e) => {
    const select = (e.target as HTMLElement).closest<HTMLSelectElement>("select");
    if (!select) return;
    state.userFilter = select.value;
    state.offset = 0;
    void load();
  });

  // ── Time filter chips ──

  const timeOptions: { key: TimeFilterKey; label: string }[] = [
    { key: "", label: "Todos" },
    { key: "today", label: "Hoy" },
    { key: "week", label: "Esta semana" },
    { key: "month", label: "Este mes" },
  ];
  const timeChips: HTMLButtonElement[] = [];

  timeOptions.forEach(({ key, label }) => {
    const chip = createButtonChip({
      label,
      tone: key === "" ? "brand" : "neutral",
      emphasis: key === "" ? "solid" : "soft",
      className: "ratings-chip-toggle",
      onClick: () => {
        state.timeFilter = key;
        state.offset = 0;
        syncTimeChipStyles();
        void load();
      },
    });
    timeChips.push(chip);
    timeChipsEl.appendChild(chip);
  });

  function syncTimeChipStyles(): void {
    timeChips.forEach((chip, i) => {
      const active = state.timeFilter === timeOptions[i].key;
      chip.classList.toggle("lia-chip--solid", active);
      chip.classList.toggle("lia-chip--soft", !active);
      chip.classList.toggle("lia-chip--brand", active);
      chip.classList.toggle("lia-chip--neutral", !active);
    });
  }

  // ── Rating chip toggles ──

  const ratingLabels = ["1 — Malo", "2", "3", "4", "5 — Bueno"];
  const ratingChips: HTMLButtonElement[] = [];

  for (let r = 1; r <= 5; r++) {
    const chip = createButtonChip({
      label: ratingLabels[r - 1],
      tone: "neutral",
      emphasis: "soft",
      className: "ratings-chip-toggle",
      onClick: () => {
        if (state.ratingFilter.has(r)) {
          state.ratingFilter.delete(r);
        } else {
          state.ratingFilter.add(r);
        }
        syncChipStyles();
        state.offset = 0;
        void load();
      },
    });
    ratingChips.push(chip);
    ratingChipsEl.appendChild(chip);
  }

  function syncChipStyles(): void {
    ratingChips.forEach((chip, i) => {
      const active = state.ratingFilter.has(i + 1);
      chip.classList.toggle("lia-chip--solid", active);
      chip.classList.toggle("lia-chip--soft", !active);
      chip.classList.toggle("lia-chip--brand", active);
      chip.classList.toggle("lia-chip--neutral", !active);
    });
  }

  footerEl.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest(".ratings-load-more")) {
      state.offset += PAGE_SIZE;
      void load(true);
    }
  });

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  // ── Load tenants for user dropdown, then load ratings ──
  void getJson<{ ok: boolean; tenants: TenantOption[] }>("/api/admin/tenants")
    .then((data) => {
      tenants = (data?.tenants || []).sort((a, b) => a.display_name.localeCompare(b.display_name));
      const groups: UserFilterGroup[] = tenants
        .map((t) => ({
          tenantLabel: t.display_name,
          users: (t.members || []).map((m) => ({
            userId: m.user_id,
            login: (m.email || "").split("@")[0] || m.user_id,
            displayName: m.display_name || m.user_id,
          })),
        }))
        .filter((g) => g.users.length > 0);
      const select = renderUserFilter(groups, null, { includePublic: true });
      select.className = "ratings-tenant-filter";
      userDropdownEl.replaceChildren(select);
    })
    .catch(() => { userDropdownEl.style.display = "none"; })
    .finally(() => void load());
}
