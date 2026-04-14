import { createButtonChip } from "@/shared/ui/atoms/chip";
import { createButton } from "@/shared/ui/atoms/button";
import { createListSectionHeading } from "@/shared/ui/molecules/listSection";
import type { DateGroup } from "@/features/record/dateGrouping";
import type { I18nRuntime } from "@/shared/i18n";

export interface RecordConversationViewModel {
  expiresSoon?: boolean;
  question: string;
  resumeLabel: string;
  sessionId: string;
  tenantId?: string;
  timeLabel: string;
  topicClassName?: string;
  topicLabel?: string;
  turnsLabel: string;
  userLabel?: string;
}

export interface MobileHistoryConversationViewModel {
  question: string;
  sessionId: string;
  timeAgoLabel: string;
  topicClassName?: string;
  topicLabel?: string;
}

export interface RecordTenantOptionViewModel {
  label: string;
  selected: boolean;
  value: string;
}

export interface UserFilterGroup {
  tenantLabel: string;
  users: { userId: string; login: string; displayName: string }[];
}

const TOPIC_COLORS: Record<string, string> = {
  renta: "topic-renta",
  declaracion_renta: "topic-renta",
  iva: "topic-iva",
  niif: "topic-niif",
  laboral: "topic-laboral",
  facturacion: "topic-facturacion",
  facturacion_electronica: "topic-facturacion",
  retencion: "topic-retencion",
  retencion_fuente: "topic-retencion",
  regimen_sancionatorio: "topic-renta",
  exogena: "topic-iva",
  informacion_exogena: "topic-iva",
  calendario: "topic-calendario",
  calendario_obligaciones: "topic-calendario",
  estados_financieros_niif: "topic-niif",
  ica: "topic-iva",
};

export function topicColorClass(topic: string | null): string {
  if (!topic) return "topic-default";
  return TOPIC_COLORS[topic.toLowerCase()] ?? "topic-default";
}

export function topicDisplayName(topic: string | null): string {
  if (!topic) return "";
  const names: Record<string, string> = {
    renta: "Renta",
    declaracion_renta: "Renta",
    iva: "IVA",
    niif: "NIIF",
    estados_financieros_niif: "NIIF",
    laboral: "Laboral",
    facturacion: "Facturación",
    facturacion_electronica: "Facturación",
    retencion: "Retención",
    retencion_fuente: "Retención",
    regimen_sancionatorio: "Sanciones",
    exogena: "Exógena",
    informacion_exogena: "Exógena",
    calendario: "Calendario",
    calendario_obligaciones: "Calendario",
    ica: "ICA",
    impuesto_al_patrimonio: "Patrimonio",
    rst_regimen_simple: "Régimen Simple",
    perdidas_fiscales: "Pérdidas Fiscales",
    dividendos_utilidades: "Dividendos",
    precios_transferencia: "Precios Transf.",
    devoluciones_saldos_favor: "Devoluciones",
    reforma_pensional: "Pensional",
    obligaciones_profesionales_contador: "Obligaciones Prof.",
  };
  const key = topic.toLowerCase();
  if (names[key]) return names[key];
  return topic
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function renderRecordFilterBar(
  topics: string[],
  activeFilter: string | null,
  i18n: I18nRuntime,
): HTMLDivElement {
  const wrapper = document.createElement("div");
  wrapper.className = "record-filter-bar lia-filter-bar";
  wrapper.setAttribute("data-lia-component", "record-filter-bar");

  wrapper.appendChild(
    createButtonChip({
      className: ["record-filter-pill", !activeFilter ? "is-active" : ""].filter(Boolean).join(" "),
      dataComponent: "record-filter-pill",
      emphasis: !activeFilter ? "solid" : "soft",
      label: i18n.t("record.filterAll"),
      tone: !activeFilter ? "brand" : "neutral",
      onClick: null,
    }),
  );
  (wrapper.lastElementChild as HTMLButtonElement).dataset.topicFilter = "";

  topics.forEach((topic) => {
    const active = activeFilter === topic;
    const button = createButtonChip({
      className: ["record-filter-pill", active ? "is-active" : ""].filter(Boolean).join(" "),
      dataComponent: "record-filter-pill",
      emphasis: active ? "solid" : "soft",
      label: topicDisplayName(topic),
      tone: active ? "brand" : "neutral",
      onClick: null,
    });
    button.dataset.topicFilter = topic;
    wrapper.appendChild(button);
  });

  return wrapper;
}

export function renderTenantFilter(
  options: RecordTenantOptionViewModel[],
): HTMLSelectElement {
  const select = document.createElement("select");
  select.className = "record-tenant-filter";
  select.setAttribute("aria-label", "Filtrar por tenant");
  select.setAttribute("data-lia-component", "record-tenant-filter");

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Todos los tenants";
  placeholder.selected = !options.some((option) => option.selected);
  select.appendChild(placeholder);

  options.forEach((option) => {
    const node = document.createElement("option");
    node.value = option.value;
    node.textContent = option.label;
    node.selected = option.selected;
    select.appendChild(node);
  });

  return select;
}

/** Prefix used to encode a tenant-level filter inside the user dropdown value. */
export const TENANT_FILTER_PREFIX = "__tenant__:";

export function renderUserFilter(
  groups: UserFilterGroup[],
  activeUserId: string | null,
  { includePublic = false }: { includePublic?: boolean } = {},
): HTMLSelectElement {
  const select = document.createElement("select");
  select.className = "record-tenant-filter";
  select.setAttribute("aria-label", "Filtrar por usuario");
  select.setAttribute("data-lia-component", "record-user-filter");

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Todos";
  placeholder.selected = !activeUserId;
  select.appendChild(placeholder);

  // "Público (testing)" — anonymous / non-login traffic
  if (includePublic) {
    const pubOption = document.createElement("option");
    pubOption.value = `${TENANT_FILTER_PREFIX}public`;
    pubOption.textContent = "P\u00fablico (testing)";
    pubOption.selected = activeUserId === `${TENANT_FILTER_PREFIX}public`;
    select.appendChild(pubOption);
  }

  groups.forEach((group) => {
    const optgroup = document.createElement("optgroup");
    optgroup.label = group.tenantLabel;
    group.users.forEach((u) => {
      const option = document.createElement("option");
      option.value = u.userId;
      option.textContent = `${u.login} (${u.displayName})`;
      option.selected = activeUserId === u.userId;
      optgroup.appendChild(option);
    });
    select.appendChild(optgroup);
  });

  return select;
}

function createTopicPill(label: string, topicClassName: string): HTMLSpanElement {
  const pill = document.createElement("span");
  pill.className = `record-topic-pill ${topicClassName}`;
  pill.textContent = label;
  pill.setAttribute("data-lia-component", "record-topic-pill");
  return pill;
}

function createRecordCard(card: RecordConversationViewModel): HTMLElement {
  const article = document.createElement("article");
  article.className = "record-card";
  article.setAttribute("data-lia-component", "record-card");
  article.dataset.sessionId = card.sessionId;
  if (card.tenantId) article.dataset.tenantId = card.tenantId;

  const question = document.createElement("p");
  question.className = "record-card-question";
  question.textContent = card.question;
  article.appendChild(question);

  const meta = document.createElement("div");
  meta.className = "record-card-meta";

  const time = document.createElement("span");
  time.className = "record-card-time";
  time.textContent = card.timeLabel;
  meta.appendChild(time);

  const separator = document.createElement("span");
  separator.className = "record-card-separator";
  separator.textContent = "\u00B7";
  meta.appendChild(separator);

  const turns = document.createElement("span");
  turns.className = "record-card-turns";
  turns.textContent = card.turnsLabel;
  meta.appendChild(turns);

  if (card.topicLabel && card.topicClassName) {
    meta.appendChild(createTopicPill(card.topicLabel, card.topicClassName));
  }

  if (card.userLabel) {
    const user = document.createElement("span");
    user.className = "record-user-badge";
    user.textContent = card.userLabel;
    meta.appendChild(user);
  }

  if (card.expiresSoon) {
    const expire = document.createElement("span");
    expire.className = "record-expire-badge";
    expire.textContent = "Expira pronto";
    meta.appendChild(expire);
  }

  const button = createButton({
    className: "record-resume-btn",
    dataComponent: "record-resume-btn",
    label: card.resumeLabel,
    tone: "primary",
    type: "button",
  });
  button.dataset.resumeSession = card.sessionId;
  meta.appendChild(button);

  article.appendChild(meta);
  return article;
}

export function renderRecordConversationGroups(
  groups: DateGroup<RecordConversationViewModel>[],
  emptyLabel: string,
): DocumentFragment {
  const fragment = document.createDocumentFragment();
  if (groups.length === 0) {
    const empty = document.createElement("div");
    empty.className = "record-empty lia-state-block lia-state-block--empty lia-state-block--compact";
    empty.setAttribute("data-lia-component", "record-empty");
    empty.textContent = emptyLabel;
    fragment.appendChild(empty);
    return fragment;
  }

  groups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "record-date-group";
    section.setAttribute("data-lia-component", "record-date-group");
    section.appendChild(
      createListSectionHeading({
        className: "record-date-header",
        dataComponent: "record-date-header",
        label: group.label,
        tagName: "h3",
      }),
    );
    group.items.forEach((item) => section.appendChild(createRecordCard(item)));
    fragment.appendChild(section);
  });
  return fragment;
}

export function renderLoadMoreButton(
  hasMore: boolean,
  loading: boolean,
  label: string,
): DocumentFragment {
  const fragment = document.createDocumentFragment();
  if (!hasMore) return fragment;

  const button = createButton({
    className: "record-load-more",
    dataComponent: "record-load-more",
    disabled: loading,
    label: loading ? "..." : label,
    tone: "ghost",
    type: "button",
  });
  fragment.appendChild(button);
  return fragment;
}

function createMobileHistoryCard(item: MobileHistoryConversationViewModel): HTMLDivElement {
  const card = document.createElement("div");
  card.className = "mobile-historial-card";
  card.setAttribute("data-lia-component", "mobile-history-card");
  card.dataset.sessionId = item.sessionId;
  card.setAttribute("role", "button");
  card.tabIndex = 0;

  const body = document.createElement("div");
  body.className = "mobile-historial-card-body";
  const title = document.createElement("p");
  title.className = "mobile-historial-card-title";
  title.textContent = item.question;
  body.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "mobile-historial-card-meta";
  if (item.topicLabel) {
    const pill = document.createElement("span");
    pill.className = `mobile-historial-card-topic ${item.topicClassName || "topic-default"}`;
    pill.textContent = item.topicLabel;
    meta.appendChild(pill);
  }
  const time = document.createElement("span");
  time.textContent = item.timeAgoLabel;
  meta.appendChild(time);
  body.appendChild(meta);

  card.appendChild(body);
  return card;
}

export function renderMobileHistoryGroups(
  groups: Array<{ label: string; items: MobileHistoryConversationViewModel[] }>,
): DocumentFragment {
  const fragment = document.createDocumentFragment();
  groups.forEach((group) => {
    const label = document.createElement("p");
    label.className = "mobile-historial-date-group";
    label.setAttribute("data-lia-component", "mobile-history-group");
    label.textContent = group.label;
    fragment.appendChild(label);
    group.items.forEach((item) => fragment.appendChild(createMobileHistoryCard(item)));
  });
  return fragment;
}
