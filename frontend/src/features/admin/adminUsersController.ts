import { getJson, postJson } from "@/shared/api/client";
import { semantic } from "@/shared/ui/colors";
import {
  createAdminUserRow,
  createAdminUsersFeedbackRow,
  type AdminUserActionViewModel,
  type AdminUserRowViewModel,
} from "@/shared/ui/organisms/adminUserRows";

type TenantUser = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  created_at: string;
};

type UsersResponse = { ok: boolean; users: TenantUser[] };
type InviteResponse = { ok: boolean; invite?: { token_id: string; invite_url: string; email: string; role: string; expires_at: string }; error?: string };
type ActionResponse = { ok: boolean; error?: string };

let _container: HTMLElement | null = null;
let _tenantId = "";

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "Activo",
    suspended: "Suspendido",
    invited: "Invitado",
  };
  return labels[status] || status;
}

function roleLabel(role: string): string {
  return role === "tenant_admin" ? "Admin" : "Usuario";
}

async function loadUsers(): Promise<void> {
  if (!_container || !_tenantId) return;
  const tableBody = _container.querySelector<HTMLElement>("#users-tbody");
  if (!tableBody) return;

  tableBody.replaceChildren(createAdminUsersFeedbackRow("Cargando...", "loading"));

  try {
    const data = await getJson<UsersResponse>(`/api/admin/users?tenant_id=${_tenantId}`);
    const users = data.users || [];
    if (users.length === 0) {
      tableBody.replaceChildren(createAdminUsersFeedbackRow("Sin usuarios", "empty"));
      return;
    }
    const fragment = document.createDocumentFragment();
    users
      .map<AdminUserRowViewModel>((user) => {
        const actions: AdminUserActionViewModel[] = [];
        const userName = user.display_name || user.email;
        if (user.status === "active") {
          actions.push({ kind: "suspend", label: "Suspender", userId: user.user_id, userName });
        } else if (user.status === "suspended") {
          actions.push({ kind: "reactivate", label: "Reactivar", userId: user.user_id, userName });
        }
        actions.push({ kind: "delete", label: "Eliminar", userId: user.user_id, userName });
        return {
          actions,
          displayName: user.display_name || user.email.split("@")[0],
          email: user.email,
          roleLabel: roleLabel(user.role),
          statusLabel: statusLabel(user.status),
          statusTone:
            user.status === "active"
              ? "success"
              : user.status === "suspended"
                ? "warning"
                : "neutral",
          userId: user.user_id,
        };
      })
      .forEach((rowModel) => {
        fragment.appendChild(
          createAdminUserRow(rowModel, {
            delete: (action) => void handleDelete(action.userId, action.userName),
            reactivate: (action) => void handleReactivate(action.userId, action.userName),
            suspend: (action) => void handleSuspend(action.userId, action.userName),
          }),
        );
      });
    tableBody.replaceChildren(fragment);
  } catch (err) {
    tableBody.replaceChildren(
      createAdminUsersFeedbackRow(
        err instanceof Error ? err.message : "Error al cargar usuarios",
        "error",
      ),
    );
  }
}

async function handleSuspend(userId: string, name: string): Promise<void> {
  if (!confirm(`¿Suspender al usuario ${name}?`)) return;
  try {
    await postJson<ActionResponse>(`/api/admin/users/${userId}/suspend`, {});
    await loadUsers();
  } catch {
    alert("Error al suspender usuario.");
  }
}

async function handleReactivate(userId: string, name: string): Promise<void> {
  if (!confirm(`¿Reactivar al usuario ${name}?`)) return;
  try {
    await postJson<ActionResponse>(`/api/admin/users/${userId}/reactivate`, {});
    await loadUsers();
  } catch {
    alert("Error al reactivar usuario.");
  }
}

async function handleDelete(userId: string, name: string): Promise<void> {
  if (!confirm(`¿Eliminar al usuario ${name}? Esta acción no se puede deshacer.`)) return;
  try {
    await postJson<ActionResponse>(`/api/admin/users/${userId}/delete`, { confirm: true });
    await loadUsers();
  } catch {
    alert("Error al eliminar usuario.");
  }
}

function renderInviteError(resultDiv: HTMLElement, message: string): void {
  resultDiv.replaceChildren();
  const text = document.createElement("p");
  text.textContent = message;
  text.style.color = semantic.status.error;
  resultDiv.appendChild(text);
  resultDiv.style.display = "block";
}

function renderInviteSuccess(resultDiv: HTMLElement, inviteUrl: string): HTMLButtonElement {
  resultDiv.replaceChildren();

  const message = document.createElement("p");
  message.textContent = "Invitación creada.";
  message.style.color = semantic.status.success;
  message.style.marginBottom = "0.5rem";

  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.gap = "0.5rem";
  row.style.alignItems = "center";

  const input = document.createElement("input");
  input.type = "text";
  input.readOnly = true;
  input.value = inviteUrl;
  input.style.flex = "1";
  input.style.padding = "0.375rem 0.5rem";
  input.style.border = `1px solid ${semantic.border.default}`;
  input.style.borderRadius = "6px";
  input.style.fontSize = "0.8125rem";

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "btn-copy lia-btn lia-btn--secondary";
  copyBtn.style.whiteSpace = "nowrap";
  copyBtn.textContent = "Copiar";

  row.append(input, copyBtn);
  resultDiv.append(message, row);
  resultDiv.style.display = "block";
  return copyBtn;
}

export async function handleInvite(tenantId: string): Promise<void> {
  const dialog = document.createElement("dialog");
  dialog.className = "invite-dialog";
  dialog.innerHTML = `
    <form method="dialog" class="invite-form">
      <h3>Invitar usuario</h3>
      <label for="invite-email">Correo electrónico</label>
      <input type="email" id="invite-email" name="email" required placeholder="usuario@ejemplo.com" autofocus>
      <label for="invite-role">Rol</label>
      <select id="invite-role" name="role">
        <option value="tenant_user">Usuario</option>
        <option value="tenant_admin">Administrador</option>
      </select>
      <div class="invite-actions">
        <button type="button" class="btn-cancel lia-btn lia-btn--ghost">Cancelar</button>
        <button type="submit" class="btn-submit lia-btn lia-btn--primary">Enviar invitación</button>
      </div>
      <div class="invite-result" style="display:none"></div>
    </form>
  `;

  document.body.appendChild(dialog);
  dialog.showModal();

  const form = dialog.querySelector("form")!;
  const resultDiv = dialog.querySelector<HTMLElement>(".invite-result")!;
  const cancelBtn = dialog.querySelector<HTMLButtonElement>(".btn-cancel")!;
  const submitBtn = dialog.querySelector<HTMLButtonElement>(".btn-submit")!;

  cancelBtn.addEventListener("click", () => {
    dialog.close();
    dialog.remove();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = (form.querySelector<HTMLInputElement>("#invite-email")!).value.trim();
    const role = (form.querySelector<HTMLSelectElement>("#invite-role")!).value;

    submitBtn.disabled = true;
    submitBtn.textContent = "Enviando...";
    resultDiv.style.display = "none";

    try {
      const { data } = await postJson<InviteResponse>("/api/admin/users/invite", {
        email,
        role,
        tenant_id: tenantId,
      });

      if (data?.ok && data.invite?.invite_url) {
        const copyBtn = renderInviteSuccess(resultDiv, data.invite.invite_url);
        copyBtn.addEventListener("click", async () => {
          await navigator.clipboard.writeText(data.invite!.invite_url);
          copyBtn.textContent = "Copiado";
          setTimeout(() => { copyBtn.textContent = "Copiar"; }, 2000);
        });
        submitBtn.textContent = "Listo";
        // Reload users list after short delay
        setTimeout(() => loadUsers(), 500);
      } else {
        renderInviteError(resultDiv, data?.error || "Error al crear invitación.");
        submitBtn.disabled = false;
        submitBtn.textContent = "Enviar invitación";
      }
    } catch {
      renderInviteError(resultDiv, "Error de conexión.");
      submitBtn.disabled = false;
      submitBtn.textContent = "Enviar invitación";
    }
  });

  dialog.addEventListener("close", () => dialog.remove());
}

export function mountAdminUsers(container: HTMLElement, tenantId: string): void {
  _container = container;
  _tenantId = tenantId;

  container.innerHTML = `
    <table class="admin-users-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Correo</th>
          <th>Rol</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody id="users-tbody">
        <tr><td colspan="5" style="text-align:center;color:${semantic.text.tertiary}">Cargando...</td></tr>
      </tbody>
    </table>
  `;

  void loadUsers();
}
