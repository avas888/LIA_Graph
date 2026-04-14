/**
 * State container for the Record (conversation history) tab.
 */

import { getJson } from "@/shared/api/client";
import { getAuthContext } from "@/shared/auth/authContext";
import { TENANT_FILTER_PREFIX } from "@/shared/ui/organisms/recordCollections";

export interface ConversationSummary {
  session_id: string;
  first_question: string;
  topic: string | null;
  tenant_id: string;
  user_id: string;
  user_display_name?: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
  status: string;
}

interface ConversationsResponse {
  ok: boolean;
  sessions: ConversationSummary[];
}

export interface TenantMember {
  user_id: string;
  email: string;
  display_name: string;
}

export interface TenantOption {
  tenant_id: string;
  display_name: string;
  members?: TenantMember[];
}

export interface RecordState {
  sessions: ConversationSummary[];
  activeTopicFilter: string | null;
  activeUserFilter: string | null;
  loading: boolean;
  offset: number;
  hasMore: boolean;
  error: string | null;
}

const PAGE_SIZE = 50;

export function createInitialState(): RecordState {
  return {
    sessions: [],
    activeTopicFilter: null,
    activeUserFilter: null,
    loading: false,
    offset: 0,
    hasMore: true,
    error: null,
  };
}

function buildUrl(state: RecordState): string {
  const params = new URLSearchParams();
  const ctx = getAuthContext();

  // When the user picks "Público (testing)", scope to that tenant directly.
  if (state.activeUserFilter?.startsWith(TENANT_FILTER_PREFIX)) {
    params.set("tenant_id", state.activeUserFilter.slice(TENANT_FILTER_PREFIX.length));
  } else {
    // platform_admin always queries across all tenants; user filter narrows by user_id.
    const tenantId = ctx.role === "platform_admin" ? "__all__" : (ctx.tenantId || "public");
    params.set("tenant_id", tenantId);
    if (state.activeUserFilter) {
      params.set("user_id", state.activeUserFilter);
    }
  }

  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(state.offset));
  params.set("status", "active");
  return `/api/conversations?${params.toString()}`;
}

/**
 * Fetch conversations from the API and update state.
 * If `append` is true, adds to existing sessions (pagination).
 */
export async function fetchConversations(
  state: RecordState,
  append: boolean,
): Promise<RecordState> {
  const url = buildUrl(state);
  try {
    const data = await getJson<ConversationsResponse>(url);
    const sessions = data.sessions ?? [];
    return {
      ...state,
      sessions: append ? [...state.sessions, ...sessions] : sessions,
      hasMore: sessions.length >= PAGE_SIZE,
      loading: false,
      error: null,
    };
  } catch (err) {
    return {
      ...state,
      loading: false,
      error: err instanceof Error ? err.message : "Error cargando conversaciones",
    };
  }
}

/**
 * Extract unique topic values from loaded sessions.
 */
export function extractTopics(sessions: ConversationSummary[]): string[] {
  const topics = new Set<string>();
  for (const s of sessions) {
    if (s.topic) topics.add(s.topic);
  }
  return Array.from(topics).sort();
}

interface TenantsResponse {
  ok: boolean;
  tenants: TenantOption[];
}

/** Extract "usuario01" style login name from an email like "usuario1@lia.dev". */
export function extractUserLogin(email: string): string {
  const local = (email || "").split("@")[0] || "";
  return local;
}

/**
 * Fetch all tenants (admin only).
 */
export async function fetchTenants(): Promise<TenantOption[]> {
  try {
    const data = await getJson<TenantsResponse>("/api/admin/tenants");
    return (data.tenants ?? []).sort((a, b) => a.display_name.localeCompare(b.display_name));
  } catch {
    return [];
  }
}

interface TopicsResponse {
  ok: boolean;
  topics: string[];
}

/**
 * Fetch all distinct topics across the tenant's entire conversation history.
 */
export async function fetchDistinctTopics(): Promise<string[]> {
  const ctx = getAuthContext();
  const params = new URLSearchParams();
  params.set("tenant_id", ctx.role === "platform_admin" ? "__all__" : (ctx.tenantId || "public"));
  params.set("status", "active");
  try {
    const data = await getJson<TopicsResponse>(`/api/conversations/topics?${params.toString()}`);
    return (data.topics ?? []).sort();
  } catch {
    return [];
  }
}
