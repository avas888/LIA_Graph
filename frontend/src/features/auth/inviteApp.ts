// @ts-nocheck

import type { I18nRuntime } from "@/shared/i18n";
import { createButton } from "@/shared/ui/atoms/button";
import { createFormField } from "@/shared/ui/molecules/formField";
import { icons } from "@/shared/ui/icons";

function createPasswordToggle(inputId: string, card: HTMLElement): { trailingAction: any } {
  let visible = false;
  return {
    trailingAction: {
      iconHtml: icons.eyeOpen,
      label: "",
      tone: "ghost" as const,
      dataComponent: `password-toggle-${inputId}`,
      attrs: {
        "aria-label": "Mostrar contraseña",
        "title": "Mostrar contraseña",
        "aria-pressed": "false",
      },
      onClick: () => {
        const input = document.getElementById(inputId) as HTMLInputElement | null;
        const toggle = card.querySelector(`[data-lia-component="password-toggle-${inputId}"]`);
        if (!input || !toggle) return;
        visible = !visible;
        input.type = visible ? "text" : "password";
        const iconSpan = toggle.querySelector(".lia-btn__icon");
        if (iconSpan) iconSpan.innerHTML = visible ? icons.eyeClosed : icons.eyeOpen;
        toggle.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
        toggle.setAttribute("title", visible ? "Ocultar contraseña" : "Mostrar contraseña");
        toggle.setAttribute("aria-pressed", visible ? "true" : "false");
      },
    },
  };
}

export function mountInviteApp(root: HTMLElement, opts: { i18n: I18nRuntime }) {
  root.innerHTML = "";

  const shell = document.createElement("div");
  shell.className = "lia-auth-shell";

  const card = document.createElement("div");
  card.className = "lia-auth-card lia-auth-card--wide";

  const h1 = document.createElement("h1");
  h1.textContent = "Bienvenido a LIA";

  const subtitle = document.createElement("p");
  subtitle.className = "lia-auth-subtitle";
  subtitle.textContent = "Complete su registro o resetee su acceso con una contraseña propia.";

  const help = document.createElement("p");
  help.className = "lia-auth-help";
  help.textContent = "La contraseña debe tener al menos 12 caracteres e incluir mayúscula, minúscula, número y símbolo.";

  const form = document.createElement("form");
  form.id = "invite-form";

  // ── Name field ──
  const nameField = createFormField({
    label: "Nombre completo",
    input: {
      id: "display_name",
      name: "display_name",
      type: "text",
      placeholder: "Ej: Ana García",
      required: true,
      minlength: 2,
      maxlength: 100,
      attrs: { autofocus: "" },
    },
  });

  // ── Password fields ──
  const pwToggle = createPasswordToggle("password", card);
  const passwordField = createFormField({
    label: "Contraseña",
    input: {
      id: "password",
      name: "password",
      type: "password",
      placeholder: "Cree una contraseña segura",
      required: true,
      minlength: 12,
      maxlength: 256,
    },
    ...pwToggle,
  });

  const confirmToggle = createPasswordToggle("password_confirm", card);
  const confirmField = createFormField({
    label: "Confirmar contraseña",
    input: {
      id: "password_confirm",
      name: "password_confirm",
      type: "password",
      placeholder: "Repita la contraseña",
      required: true,
      minlength: 12,
      maxlength: 256,
    },
    ...confirmToggle,
  });

  // ── Submit button ──
  const submitBtn = createButton({
    label: "Activar acceso",
    tone: "primary",
    type: "submit",
  });

  // ── Messages ──
  const errorEl = document.createElement("p");
  errorEl.className = "lia-auth-error";
  errorEl.id = "error-msg";

  const successEl = document.createElement("p");
  successEl.className = "lia-auth-success";
  successEl.id = "success-msg";

  form.append(nameField, passwordField, confirmField, submitBtn, errorEl, successEl);
  card.append(h1, subtitle, help, form);
  shell.appendChild(card);
  root.appendChild(shell);

  // ── Validate invite token ──
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (!token) {
    errorEl.textContent = "Enlace de invitación inválido.";
    errorEl.style.display = "block";
    submitBtn.disabled = true;
    return;
  }

  // ── Form submit handler ──
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pw = (document.getElementById("password") as HTMLInputElement).value;
    const confirm = (document.getElementById("password_confirm") as HTMLInputElement).value;

    if (pw !== confirm) {
      errorEl.textContent = "Las contraseñas no coinciden.";
      errorEl.style.display = "block";
      return;
    }

    submitBtn.disabled = true;
    const labelSpan = submitBtn.querySelector(".lia-btn__label");
    if (labelSpan) labelSpan.textContent = "Procesando...";
    errorEl.style.display = "none";
    successEl.style.display = "none";

    try {
      const res = await fetch("/api/auth/accept-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          display_name: (document.getElementById("display_name") as HTMLInputElement).value.trim(),
          password: pw,
        }),
      });
      const data = await res.json();

      if (data.ok) {
        if (data.access_token) {
          localStorage.setItem("lia_platform_access_token", data.access_token);
        }
        const displayName = String(data.me?.display_name || "").trim();
        if (displayName) localStorage.setItem("lia_display_name", displayName);
        successEl.textContent = data.message || "Acceso activado. Redireccionando...";
        successEl.style.display = "block";
        setTimeout(() => { window.location.href = "/"; }, 1500);
        return;
      }
      errorEl.textContent = data.error || "No se pudo completar el registro.";
      errorEl.style.display = "block";
    } catch {
      errorEl.textContent = "Error de conexión.";
      errorEl.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      const label = submitBtn.querySelector(".lia-btn__label");
      if (label) label.textContent = "Activar acceso";
    }
  });
}
