// @ts-nocheck

import type { I18nRuntime } from "@/shared/i18n";
import { createButton } from "@/shared/ui/atoms/button";
import { createFormField } from "@/shared/ui/molecules/formField";
import { icons } from "@/shared/ui/icons";

export function mountLoginApp(root: HTMLElement, opts: { i18n: I18nRuntime }) {
  root.innerHTML = "";

  const shell = document.createElement("div");
  shell.className = "lia-auth-shell";

  const card = document.createElement("div");
  card.className = "lia-auth-card";

  // ── Brand block (logo + tagline) ──
  const brand = document.createElement("div");
  brand.className = "lia-auth-brand";

  const logo = document.createElement("img");
  logo.src = "/assets/lia-logo.png";
  logo.alt = "LIA";
  logo.className = "lia-auth-logo";
  logo.draggable = false;

  const tagline = document.createElement("p");
  tagline.className = "lia-auth-tagline";
  tagline.textContent = "Inteligencia Especializada para Contadores";

  brand.append(logo, tagline);

  // ── Divider ──
  const divider = document.createElement("hr");
  divider.className = "lia-auth-divider";

  // ── Session-expired banner (shown after token expiry redirect) ──
  const expiredFlag = localStorage.getItem("lia_session_expired");
  let expiredBanner: HTMLElement | null = null;
  if (expiredFlag) {
    localStorage.removeItem("lia_session_expired");
    expiredBanner = document.createElement("div");
    expiredBanner.className = "lia-auth-expired-banner";
    expiredBanner.textContent =
      "Tu sesi\u00f3n de login expir\u00f3 (dura 24 horas). Por seguridad vu\u00e9lve a hacer login.";
  }

  const form = document.createElement("form");
  form.id = "login-form";

  // ── Email field ──
  const emailField = createFormField({
    label: "Correo electr\u00f3nico",
    input: {
      id: "email",
      name: "email",
      type: "email",
      placeholder: "usuario@correo.com",
      required: true,
      attrs: { autofocus: "" },
    },
  });

  // ── Password field with eye toggle ──
  let passwordVisible = false;
  const passwordField = createFormField({
    label: "Contrase\u00f1a",
    input: {
      id: "password",
      name: "password",
      type: "password",
      placeholder: "Ingrese su contrase\u00f1a",
      required: true,
      minlength: 8,
      maxlength: 256,
    },
    trailingAction: {
      iconHtml: icons.eyeOpen,
      label: "",
      tone: "ghost",
      dataComponent: "password-toggle",
      attrs: {
        "aria-label": "Mostrar contrase\u00f1a",
        "title": "Mostrar contrase\u00f1a",
        "aria-pressed": "false",
      },
      onClick: () => {
        const input = document.getElementById("password") as HTMLInputElement | null;
        const toggle = card.querySelector('[data-lia-component="password-toggle"]');
        if (!input || !toggle) return;
        passwordVisible = !passwordVisible;
        input.type = passwordVisible ? "text" : "password";
        const iconSpan = toggle.querySelector(".lia-btn__icon");
        if (iconSpan) iconSpan.innerHTML = passwordVisible ? icons.eyeClosed : icons.eyeOpen;
        toggle.setAttribute("aria-label", passwordVisible ? "Ocultar contrase\u00f1a" : "Mostrar contrase\u00f1a");
        toggle.setAttribute("title", passwordVisible ? "Ocultar contrase\u00f1a" : "Mostrar contrase\u00f1a");
        toggle.setAttribute("aria-pressed", passwordVisible ? "true" : "false");
      },
    },
  });

  // ── Tenant picker (hidden by default) ──
  const tenantPicker = document.createElement("div");
  tenantPicker.id = "tenant-picker";
  tenantPicker.hidden = true;

  const tenantLabel = document.createElement("label");
  tenantLabel.className = "lia-form-field__label";
  tenantLabel.htmlFor = "tenant_id";
  tenantLabel.textContent = "Tenant";

  const tenantSelect = document.createElement("select");
  tenantSelect.id = "tenant_id";
  tenantSelect.name = "tenant_id";
  tenantSelect.className = "lia-input";

  tenantPicker.append(tenantLabel, tenantSelect);

  // ── Submit button ──
  const submitBtn = createButton({
    label: "Entrar",
    tone: "primary",
    type: "submit",
  });

  // ── Error message ──
  const errorEl = document.createElement("p");
  errorEl.className = "lia-auth-error";
  errorEl.id = "error-msg";

  form.append(emailField, passwordField, tenantPicker, submitBtn, errorEl);

  // ── Help text in footer ──
  const footer = document.createElement("div");
  footer.className = "lia-auth-footer";

  const footerDivider = document.createElement("hr");
  footerDivider.className = "lia-auth-divider";

  const help = document.createElement("p");
  help.className = "lia-auth-help";
  help.textContent = "Si es su primer ingreso o necesita resetear acceso, use el enlace de invitaci\u00f3n enviado por el administrador.";

  footer.append(footerDivider, help);

  card.append(brand, divider, ...(expiredBanner ? [expiredBanner] : []), form, footer);
  shell.appendChild(card);
  root.appendChild(shell);

  // ── Form submit handler ──
  function setTenants(tenants: Array<{ tenant_id: string; display_name?: string; role: string }>) {
    tenantSelect.innerHTML = "";
    tenants.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.tenant_id;
      option.textContent = `${item.display_name || item.tenant_id} (${item.role})`;
      tenantSelect.appendChild(option);
    });
    tenantPicker.hidden = !tenants.length;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    const labelSpan = submitBtn.querySelector(".lia-btn__label");
    if (labelSpan) labelSpan.textContent = "Verificando...";
    errorEl.style.display = "none";

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: (document.getElementById("email") as HTMLInputElement).value.trim(),
          password: (document.getElementById("password") as HTMLInputElement).value,
          tenant_id: tenantSelect.value || "",
        }),
      });
      const data = await res.json();

      if (data.ok && data.access_token) {
        localStorage.setItem("lia_platform_access_token", data.access_token);
        const displayName = String(data.me?.display_name || "").trim();
        if (displayName) localStorage.setItem("lia_display_name", displayName);
        window.location.href = "/";
        return;
      }
      if (data.code === "auth_tenant_selection_required" && Array.isArray(data.tenants) && data.tenants.length) {
        setTenants(data.tenants);
      }
      errorEl.textContent = data.error || "Credenciales inválidas.";
      errorEl.style.display = "block";
    } catch {
      errorEl.textContent = "Error de conexión.";
      errorEl.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      const label = submitBtn.querySelector(".lia-btn__label");
      if (label) label.textContent = "Entrar";
    }
  });
}
