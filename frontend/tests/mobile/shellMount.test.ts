import { describe, expect, it } from "vitest";
import { renderMobileShell } from "@/app/mobile/shell-mobile";

const i18n = {
  t: (key: string) => {
    const catalog: Record<string, string> = {
      "chat.hero.tagline": "Asistente tributario",
      "chat.panel.title": "Chat",
      "chat.workspace.newThread": "Nuevo hilo",
      "chat.workspace.reset": "Reiniciar",
      "chat.empty.message": "Escribe tu primera consulta",
      "chat.composer.label": "Consulta",
      "chat.composer.send": "Enviar",
      "chat.composer.cursor": "cursor",
      "chat.support.title": "Soporte Normativo",
      "chat.support.defer": "Pendiente",
      "chat.experts.title": "Interpretación",
      "chat.experts.defer": "Pendiente",
      "chat.experts.tooltip.trigger": "Info",
      "chat.experts.tooltip.body": "Info body",
      "chat.modal.norma.title": "Norma",
      "chat.modal.norma.original": "Original",
      "chat.modal.norma.deepAnalysis": "Análisis",
      "chat.modal.norma.loading": "Cargando...",
      "chat.modal.norma.guidePrompt": "Guía",
      "chat.modal.interpretations.title": "Interpretaciones",
      "chat.modal.interpretations.loading": "Cargando...",
      "chat.modal.summary.title": "Resumen",
      "chat.modal.summary.link": "Ver",
      "chat.modal.summary.select": "Seleccionar",
      "chat.experts.modal.title": "Detalle Experto",
      "chat.sessions.title": "Sesiones",
      "common.backstageOps": "Ops",
      "common.window2": "Ventana 2",
      "common.window3": "Ventana 3",
    };
    return catalog[key] ?? key;
  },
};

describe("renderMobileShell", () => {
  it("contains mobile-shell wrapper", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('class="mobile-shell"');
  });

  it("contains mobile topbar", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('class="mobile-topbar"');
    expect(html).toContain('class="mobile-hamburger-btn"');
  });

  it("contains bottom tab bar with 3 tabs", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('class="mobile-tab-bar"');
    expect(html).toContain('data-tab="chat"');
    expect(html).toContain('data-tab="normativa"');
    expect(html).toContain('data-tab="interpretacion"');
  });

  it("contains 4 mobile panels", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('id="mobile-panel-chat"');
    expect(html).toContain('id="mobile-panel-normativa"');
    expect(html).toContain('id="mobile-panel-interpretacion"');
    expect(html).toContain('id="mobile-panel-historial"');
  });

  it("contains drawer", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('class="mobile-drawer"');
    expect(html).toContain('data-drawer-action="new-conversation"');
    expect(html).toContain('data-drawer-action="historial"');
    expect(html).toContain('data-drawer-action="logout"');
  });

  it("contains bottom sheet", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('class="mobile-sheet-overlay"');
    expect(html).toContain('class="mobile-sheet-handle"');
    expect(html).toContain('class="mobile-sheet-content"');
  });

  it("uses desktop chat-log-empty hello message (no separate suggested questions)", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('id="chat-log-empty"');
    expect(html).not.toContain('id="mobile-suggested"');
  });

  it("embeds full desktop chat shell (with chat-form, chat-log, etc.)", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('id="chat-form"');
    expect(html).toContain('id="chat-log"');
    expect(html).toContain('id="message"');
    expect(html).toContain('id="send-btn"');
    expect(html).toContain('id="citations"');
    expect(html).toContain('id="expert-panel-content"');
    expect(html).toContain('id="bubble-template"');
  });

  it("contains empty state containers for normativa and interp", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('id="mobile-normativa-empty"');
    expect(html).toContain('id="mobile-interp-empty"');
  });

  it("contains historial search and pills", () => {
    const html = renderMobileShell(i18n as any);
    expect(html).toContain('id="mobile-historial-search-input"');
    expect(html).toContain('id="mobile-historial-pills"');
    expect(html).toContain('id="mobile-historial-list"');
  });
});
