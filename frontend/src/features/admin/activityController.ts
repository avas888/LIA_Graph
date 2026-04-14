import { getJson } from "@/shared/api/client";
import { TZ_CO } from "@/shared/dates";
import { renderActivityShell } from "@/app/admin/activityShell";
import {
  renderActivitySummary,
  createLoginEventRow,
  createUserStatsRow,
  createActivityFeedbackRow,
  type ActivitySummaryViewModel,
  type LoginEventRowViewModel,
  type UserStatsRowViewModel,
} from "@/shared/ui/organisms/activityRows";

// ── API Response Types ───────────────────────────────────────

type ActivityResponse = {
  ok: boolean;
  activity: {
    recent_logins: {
      email: string;
      display_name: string;
      status: string;
      ip_address: string;
      created_at: string;
      failure_reason: string | null;
    }[];
    user_stats: {
      user_id: string;
      email: string;
      display_name: string;
      login_count: number;
      last_login_at: string;
      interaction_count: number;
      last_interaction_at: string;
    }[];
    summary: {
      logins_today: number;
      active_users_7d: number;
      total_interactions_7d: number;
    };
  };
};

// ── Helpers ──────────────────────────────────────────────────

function userLabel(displayName: string, email: string): string {
  const login = (email || "").split("@")[0] || "";
  if (!displayName) return login || email;
  return login ? `${displayName} (${login})` : displayName;
}

function formatRelativeTime(iso: string): string {
  if (!iso) return "-";
  try {
    const date = new Date(iso);
    const now = Date.now();
    const diff = now - date.getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return "ahora";
    if (mins < 60) return `hace ${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `hace ${hours}h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `hace ${days}d`;
    return date.toLocaleDateString("es-CO", { day: "numeric", month: "short", timeZone: TZ_CO });
  } catch {
    return iso;
  }
}

// ── Mount ────────────────────────────────────────────────────

export function mountActivityPanel(container: HTMLElement): void {
  container.innerHTML = renderActivityShell();
  loadActivity(container);
}

async function loadActivity(container: HTMLElement): Promise<void> {
  const loginsTbody = container.querySelector<HTMLElement>("#activity-logins-tbody");
  const statsTbody = container.querySelector<HTMLElement>("#activity-stats-tbody");
  const summaryNode = container.querySelector<HTMLElement>("#activity-summary");

  if (loginsTbody) {
    loginsTbody.replaceChildren(createActivityFeedbackRow("Cargando...", "loading"));
  }
  if (statsTbody) {
    statsTbody.replaceChildren(createActivityFeedbackRow("Cargando...", "loading"));
  }

  try {
    const data = await getJson<ActivityResponse>("/api/admin/activity?limit=100");
    const activity = data.activity;

    // Summary cards
    if (summaryNode) {
      const summaryModel: ActivitySummaryViewModel = {
        loginsToday: activity.summary.logins_today,
        activeUsers7d: activity.summary.active_users_7d,
        totalInteractions7d: activity.summary.total_interactions_7d,
      };
      summaryNode.replaceChildren(renderActivitySummary(summaryModel));
    }

    // Recent logins table
    if (loginsTbody) {
      const logins = activity.recent_logins || [];
      if (logins.length === 0) {
        loginsTbody.replaceChildren(createActivityFeedbackRow("Sin logins registrados", "empty"));
      } else {
        const rows = logins.map((login): LoginEventRowViewModel => ({
          email: login.email,
          displayName: userLabel(login.display_name, login.email),
          status: login.status === "success" ? "success" : "failure",
          statusTone: login.status === "success" ? "success" : "error",
          statusLabel: login.status === "success" ? "OK" : "Fallido",
          ipAddress: login.ip_address,
          createdAt: formatRelativeTime(login.created_at),
        }));
        loginsTbody.replaceChildren(...rows.map(createLoginEventRow));
      }
    }

    // User stats table
    if (statsTbody) {
      const stats = activity.user_stats || [];
      if (stats.length === 0) {
        statsTbody.replaceChildren(createActivityFeedbackRow("Sin datos de usuarios", "empty"));
      } else {
        const rows = stats.map((s): UserStatsRowViewModel => ({
          userId: s.user_id,
          email: s.email,
          displayName: userLabel(s.display_name, s.email),
          loginCount: s.login_count,
          interactionCount: s.interaction_count,
          lastActiveAt: formatRelativeTime(s.last_login_at || s.last_interaction_at),
        }));
        statsTbody.replaceChildren(...rows.map(createUserStatsRow));
      }
    }
  } catch (err) {
    console.error("[LIA] Failed to load activity:", err);
    if (loginsTbody) {
      loginsTbody.replaceChildren(createActivityFeedbackRow("Error al cargar actividad", "error"));
    }
    if (statsTbody) {
      statsTbody.replaceChildren(createActivityFeedbackRow("Error al cargar estadisticas", "error"));
    }
  }
}
