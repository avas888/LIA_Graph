import { createButton } from "@/shared/ui/atoms/button";
import { createBadge } from "@/shared/ui/atoms/badge";
import { createStateBlock } from "@/shared/ui/molecules/stateBlock";

export interface AdminUserActionViewModel {
  kind: "suspend" | "reactivate" | "delete";
  label: string;
  userId: string;
  userName: string;
}

export interface AdminUserRowViewModel {
  actions: AdminUserActionViewModel[];
  displayName: string;
  email: string;
  roleLabel: string;
  statusLabel: string;
  statusTone: "success" | "warning" | "neutral";
  userId: string;
}

export function createAdminUsersFeedbackRow(
  message: string,
  tone: "loading" | "empty" | "error",
): HTMLTableRowElement {
  const row = document.createElement("tr");
  row.setAttribute("data-lia-component", "admin-users-feedback-row");
  const cell = document.createElement("td");
  cell.colSpan = 5;
  cell.appendChild(
    createStateBlock({
      className: "admin-users-feedback",
      compact: true,
      message,
      tone,
    }),
  );
  row.appendChild(cell);
  return row;
}

export function createAdminUserRow(
  rowModel: AdminUserRowViewModel,
  handlers: Record<AdminUserActionViewModel["kind"], (action: AdminUserActionViewModel) => void>,
): HTMLTableRowElement {
  const row = document.createElement("tr");
  row.dataset.uid = rowModel.userId;
  row.setAttribute("data-lia-component", "admin-user-row");

  const name = document.createElement("td");
  name.textContent = rowModel.displayName;

  const email = document.createElement("td");
  email.textContent = rowModel.email;

  const role = document.createElement("td");
  role.textContent = rowModel.roleLabel;

  const status = document.createElement("td");
  status.appendChild(
    createBadge({
      className: `admin-user-status-pill admin-user-status-pill--${rowModel.statusTone}`,
      label: rowModel.statusLabel,
      tone: rowModel.statusTone === "neutral" ? "neutral" : rowModel.statusTone,
    }),
  );

  const actions = document.createElement("td");
  actions.className = "admin-users-actions";

  rowModel.actions.forEach((actionModel) => {
    const tone = actionModel.kind === "delete"
      ? "destructive"
      : actionModel.kind === "reactivate"
        ? "secondary"
        : "ghost";
    const button = createButton({
      className: `btn-action btn-${actionModel.kind}`,
      dataComponent: "admin-user-action",
      label: actionModel.label,
      tone,
      type: "button",
    });
    button.dataset.uid = actionModel.userId;
    button.dataset.name = actionModel.userName;
    button.addEventListener("click", () => handlers[actionModel.kind](actionModel));
    actions.appendChild(button);
  });

  row.append(name, email, role, status, actions);
  return row;
}
