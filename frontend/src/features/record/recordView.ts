/**
 * DOM rendering for the Record (conversation history) tab.
 */

import type { ConversationSummary, TenantOption } from "./recordState";
import { extractUserLogin } from "./recordState";
import { groupByDate } from "./dateGrouping";
import { isAdmin } from "@/shared/auth/authContext";
import { TZ_CO } from "@/shared/dates";
import type { I18nRuntime } from "@/shared/i18n";
import {
  renderRecordConversationGroups,
  renderRecordFilterBar,
  renderUserFilter as renderSharedUserFilter,
  renderLoadMoreButton,
  topicColorClass,
  topicDisplayName,
  type RecordConversationViewModel,
  type UserFilterGroup,
} from "@/shared/ui/organisms/recordCollections";

export { TENANT_FILTER_PREFIX } from "@/shared/ui/organisms/recordCollections";

function formatTime(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleTimeString("es-CO", { hour: "numeric", minute: "2-digit", hour12: true, timeZone: TZ_CO });
  } catch {
    return "";
  }
}

function isExpiringSoon(dateStr: string): boolean {
  const date = new Date(dateStr);
  const monthsAgo = (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24 * 30);
  return monthsAgo >= 22;
}

function toConversationViewModel(
  session: ConversationSummary,
  i18n: I18nRuntime,
): RecordConversationViewModel {
  const answersCount = Math.floor((session.turn_count || 0) / 2);
  const turnsLabel = `${answersCount} ${answersCount === 1 ? i18n.t("record.answer") : i18n.t("record.answers")}`;
  return {
    expiresSoon: isExpiringSoon(session.updated_at),
    question: session.first_question || "...",
    resumeLabel: i18n.t("record.resume"),
    sessionId: session.session_id,
    tenantId: session.tenant_id,
    timeLabel: formatTime(session.updated_at),
    topicClassName: session.topic ? topicColorClass(session.topic) : "topic-default",
    topicLabel: session.topic ? topicDisplayName(session.topic) : "",
    turnsLabel,
    userLabel: isAdmin() && session.user_id ? (session.user_display_name || session.user_id) : "",
  };
}

export function renderUserFilterDropdown(
  tenants: TenantOption[],
  activeUserId: string | null,
): HTMLSelectElement | null {
  if (!isAdmin() || tenants.length === 0) return null;
  const groups: UserFilterGroup[] = tenants.map((tenant) => ({
    tenantLabel: tenant.display_name,
    users: (tenant.members || []).map((m) => ({
      userId: m.user_id,
      login: extractUserLogin(m.email),
      displayName: m.display_name || extractUserLogin(m.email),
    })),
  })).filter((g) => g.users.length > 0);
  return renderSharedUserFilter(groups, activeUserId, { includePublic: true });
}

export function renderFilterPills(
  topics: string[],
  activeFilter: string | null,
  i18n: I18nRuntime,
): HTMLDivElement {
  return renderRecordFilterBar(topics, activeFilter, i18n);
}

export function renderConversationList(
  sessions: ConversationSummary[],
  i18n: I18nRuntime,
): DocumentFragment {
  if (sessions.length === 0) {
    return renderRecordConversationGroups([], i18n.t("record.empty"));
  }

  const updatedAtBySession = new Map(
    sessions.map((session) => [session.session_id, session.updated_at]),
  );
  const groups = groupByDate(
    sessions.map((session) => toConversationViewModel(session, i18n)),
    (session) => updatedAtBySession.get(session.sessionId) || "",
  );

  return renderRecordConversationGroups(groups, i18n.t("record.empty"));
}

export function renderLoadMore(
  hasMore: boolean,
  loading: boolean,
  i18n: I18nRuntime,
): DocumentFragment {
  return renderLoadMoreButton(hasMore, loading, i18n.t("record.loadMore"));
}
