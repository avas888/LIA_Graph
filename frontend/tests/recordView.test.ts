import { describe, expect, it } from "vitest";
import {
  renderConversationList,
  renderFilterPills,
} from "@/features/record/recordView";
import type { ConversationSummary } from "@/features/record/recordState";
import { renderFragmentToHtml, renderNodeToHtml } from "@/shared/ui/testing/render";

const i18n = {
  t: (key: string) => {
    const catalog: Record<string, string> = {
      "record.filterAll": "Todos",
      "record.resume": "Reanudar",
      "record.turns": "turnos",
      "record.answer": "respuesta",
      "record.answers": "respuestas",
      "record.empty": "No hay conversaciones registradas",
      "record.today": "Hoy",
      "record.yesterday": "Ayer",
      "record.thisWeek": "Esta semana",
      "record.thisMonth": "Este mes",
      "record.lastMonth": "Mes anterior",
      "record.older": "Más antiguo",
      "record.expiresSoon": "Expira pronto",
    };
    return catalog[key] ?? key;
  },
};

function makeSummary(overrides: Partial<ConversationSummary> = {}): ConversationSummary {
  return {
    session_id: "sess-1",
    first_question: "Test question",
    topic: "renta",
    turn_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: "active",
    ...overrides,
  };
}

describe("recordView topic display names", () => {
  it("displays standard topics with friendly names", () => {
    const html = renderFragmentToHtml(renderConversationList([makeSummary({ topic: "renta" })], i18n));
    expect(html).toContain(">Renta</span>");
  });

  it("displays informacion_exogena as Exógena", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "informacion_exogena" })],
      i18n,
    ));
    expect(html).toContain("Exógena");
    expect(html).not.toContain("informacion_exogena");
  });

  it("displays facturacion_electronica as Facturación", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "facturacion_electronica" })],
      i18n,
    ));
    expect(html).toContain("Facturación");
  });

  it("displays retencion_fuente as Retención", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "retencion_fuente" })],
      i18n,
    ));
    expect(html).toContain("Retención");
  });

  it("displays estados_financieros_niif as NIIF", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "estados_financieros_niif" })],
      i18n,
    ));
    expect(html).toContain("NIIF");
  });

  it("humanizes unknown topics by replacing underscores", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "regimen_cambiario" })],
      i18n,
    ));
    expect(html).toContain("Regimen Cambiario");
  });

  it("applies correct CSS class for informacion_exogena", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "informacion_exogena" })],
      i18n,
    ));
    expect(html).toContain("topic-iva");
  });

  it("applies correct CSS class for facturacion_electronica", () => {
    const html = renderFragmentToHtml(renderConversationList(
      [makeSummary({ topic: "facturacion_electronica" })],
      i18n,
    ));
    expect(html).toContain("topic-facturacion");
  });
});

describe("recordView filter pills", () => {
  it("shows Todos pill plus topic pills", () => {
    const html = renderNodeToHtml(renderFilterPills(["renta", "laboral"], null, i18n));
    expect(html).toContain("Todos");
    expect(html).toContain("Renta");
    expect(html).toContain("Laboral");
  });

  it("marks active filter with is-active class", () => {
    const html = renderNodeToHtml(renderFilterPills(["renta", "laboral"], "renta", i18n));
    // The Todos pill should NOT be active
    expect(html).toContain('data-topic-filter="">Todos');
    // The renta pill should be active
    expect(html).toContain('record-filter-pill is-active');
    expect(html).toContain('data-topic-filter="renta"');
  });

  it("displays informacion_exogena pill as Exógena", () => {
    const html = renderNodeToHtml(renderFilterPills(["informacion_exogena"], null, i18n));
    expect(html).toContain("Exógena");
  });
});
