import { createBadge } from "@/shared/ui/atoms/badge";
import { createFactCard } from "@/shared/ui/molecules/factCard";
import { createStateBlock } from "@/shared/ui/molecules/stateBlock";

// ── View Models ──────────────────────────────────────────────

export interface ActivitySummaryViewModel {
  loginsToday: number;
  activeUsers7d: number;
  totalInteractions7d: number;
}

export interface LoginEventRowViewModel {
  email: string;
  displayName: string;
  status: "success" | "failure";
  statusTone: "success" | "error";
  statusLabel: string;
  ipAddress: string;
  createdAt: string;
}

export interface UserStatsRowViewModel {
  userId: string;
  email: string;
  displayName: string;
  loginCount: number;
  interactionCount: number;
  lastActiveAt: string;
}

// ── Summary Cards ────────────────────────────────────────────

export function renderActivitySummary(model: ActivitySummaryViewModel): HTMLElement {
  const container = document.createElement("div");
  container.className = "activity-summary-cards";
  container.setAttribute("data-lia-component", "activity-summary");

  container.append(
    createFactCard({ label: "Logins hoy", value: String(model.loginsToday) }),
    createFactCard({ label: "Usuarios activos (7d)", value: String(model.activeUsers7d) }),
    createFactCard({ label: "Interacciones (7d)", value: String(model.totalInteractions7d) }),
  );

  return container;
}

// ── Login Event Row ──────────────────────────────────────────

export function createLoginEventRow(model: LoginEventRowViewModel): HTMLTableRowElement {
  const row = document.createElement("tr");
  row.setAttribute("data-lia-component", "login-event-row");

  const user = document.createElement("td");
  user.textContent = model.displayName || model.email;
  if (model.displayName) {
    user.title = model.email;
  }

  const status = document.createElement("td");
  status.appendChild(
    createBadge({
      label: model.statusLabel,
      tone: model.statusTone === "success" ? "success" : "error",
    }),
  );

  const ip = document.createElement("td");
  ip.textContent = model.ipAddress || "-";
  ip.className = "activity-ip-cell";

  const date = document.createElement("td");
  date.textContent = model.createdAt;

  row.append(user, status, ip, date);
  return row;
}

// ── User Stats Row ───────────────────────────────────────────

export function createUserStatsRow(model: UserStatsRowViewModel): HTMLTableRowElement {
  const row = document.createElement("tr");
  row.setAttribute("data-lia-component", "user-stats-row");

  const user = document.createElement("td");
  user.textContent = model.displayName || model.email;
  if (model.displayName) {
    user.title = model.email;
  }

  const logins = document.createElement("td");
  logins.textContent = String(model.loginCount);
  logins.className = "activity-numeric-cell";

  const interactions = document.createElement("td");
  interactions.textContent = String(model.interactionCount);
  interactions.className = "activity-numeric-cell";

  const lastActive = document.createElement("td");
  lastActive.textContent = model.lastActiveAt || "-";

  row.append(user, logins, interactions, lastActive);
  return row;
}

// ── Feedback Row (loading / empty / error) ───────────────────

export function createActivityFeedbackRow(
  message: string,
  tone: "loading" | "empty" | "error",
  colSpan = 4,
): HTMLTableRowElement {
  const row = document.createElement("tr");
  row.setAttribute("data-lia-component", "activity-feedback-row");
  const cell = document.createElement("td");
  cell.colSpan = colSpan;
  cell.appendChild(
    createStateBlock({ className: "activity-feedback", compact: true, message, tone }),
  );
  row.appendChild(cell);
  return row;
}
