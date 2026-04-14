import { describe, expect, it, vi } from "vitest";
import { createButton, createLinkAction } from "@/shared/ui/atoms/button";
import { createStateBlock } from "@/shared/ui/molecules/stateBlock";
import {
  flattenCitationGroups,
  renderCitationList,
  renderMobileCitationCards,
  type CitationGroupViewModel,
} from "@/shared/ui/organisms/citationList";
import {
  renderExpertCardList,
  renderMobileExpertCards,
  type ExpertCardViewModel,
} from "@/shared/ui/organisms/expertCards";
import {
  renderMobileHistoryGroups,
  renderRecordConversationGroups,
  type MobileHistoryConversationViewModel,
  type RecordConversationViewModel,
} from "@/shared/ui/organisms/recordCollections";
import {
  createAdminUserRow,
  createAdminUsersFeedbackRow,
  type AdminUserRowViewModel,
} from "@/shared/ui/organisms/adminUserRows";
import { queryAllByComponent, renderFragmentToHtml } from "@/shared/ui/testing/render";

describe("shared UI atomic layer", () => {
  it("renders atoms and molecules with canonical component markers", () => {
    const clicks = vi.fn();
    const button = createButton({
      dataComponent: "save-button",
      label: "Guardar",
      onClick: clicks,
      tone: "primary",
      type: "button",
    });
    const link = createLinkAction({
      dataComponent: "docs-link",
      href: "https://example.com",
      label: "Ver documentación",
      tone: "secondary",
    });
    const state = createStateBlock({
      message: "Cargando componentes...",
      title: "UI compartida",
      tone: "loading",
    });

    button.click();

    expect(clicks).toHaveBeenCalledOnce();
    expect(button.getAttribute("data-lia-component")).toBe("save-button");
    expect(button.className).toContain("lia-btn--primary");
    expect(link.getAttribute("data-lia-component")).toBe("docs-link");
    expect(link.className).toContain("lia-btn--secondary");
    expect(state.getAttribute("data-lia-component")).toBe("state-block");
    expect(state.querySelector(".lia-state-block__spinner")).not.toBeNull();
  });

  it("renders citation desktop and mobile variants from the same view model ids", () => {
    const groups: CitationGroupViewModel[] = [
      {
        id: "current",
        label: "Actual",
        items: [
          {
            action: "modal",
            hint: "Abrir visor",
            id: "citation-1",
            meta: "Primaria | DIAN",
            title: "Artículo 240 ET",
          },
          {
            action: "external",
            externalHint: "Abrir fuente oficial",
            externalUrl: "https://example.com/ley",
            id: "citation-2",
            mentionOnly: true,
            meta: "Mención | Ley",
            title: "Ley 1819 de 2016",
          },
        ],
      },
    ];

    const desktop = document.createElement("ul");
    const mobile = document.createElement("div");

    renderCitationList(desktop, groups);
    renderMobileCitationCards(mobile, flattenCitationGroups(groups));

    const desktopIds = Array.from(
      desktop.querySelectorAll<HTMLElement>("[data-citation-id]"),
      (node) => node.dataset.citationId,
    );
    const mobileIds = Array.from(
      mobile.querySelectorAll<HTMLElement>("[data-citation-id]"),
      (node) => node.dataset.citationId,
    );

    expect(desktopIds).toEqual(["citation-1", "citation-2"]);
    expect(mobileIds).toEqual(desktopIds);
    expect(queryAllByComponent(mobile, "mobile-citation-card")).toHaveLength(2);
  });

  it("renders expert desktop and mobile variants from the same card ids", () => {
    const cards: ExpertCardViewModel[] = [
      {
        articleLabel: "Art. 147 ET",
        classification: "concordancia",
        classificationLabel: "Coinciden",
        heading: "Las pérdidas fiscales pueden compensarse si están soportadas.",
        id: "expert-147",
        nutshell: "La lectura práctica converge en la necesidad de soporte.",
        providerLabels: ["DIAN", "PwC"],
        signal: "permite",
        signalLabel: "Permite",
        sourceCountLabel: "2 fuentes",
      },
      {
        articleLabel: "Art. 240 ET",
        classification: "individual",
        classificationLabel: "Perspectiva individual",
        heading: "La tarifa depende del régimen activo.",
        id: "expert-240",
        providerLabels: ["Actualícese"],
        relevancia: "Revisar antes del cierre fiscal.",
        signal: "condiciona",
        signalLabel: "Condiciona",
        sourceCountLabel: "1 fuente",
      },
    ];

    const desktop = document.createElement("div");
    const mobile = document.createElement("div");

    renderExpertCardList(desktop, cards);
    renderMobileExpertCards(mobile, cards);

    const desktopIds = Array.from(
      desktop.querySelectorAll<HTMLElement>("[data-card-id]"),
      (node) => node.dataset.cardId,
    );
    const mobileIds = Array.from(
      mobile.querySelectorAll<HTMLElement>("[data-card-id]"),
      (node) => node.dataset.cardId,
    );

    expect(desktopIds).toEqual(["expert-147", "expert-240"]);
    expect(mobileIds).toEqual(desktopIds);
    expect(queryAllByComponent(desktop, "expert-card")).toHaveLength(2);
    expect(queryAllByComponent(mobile, "mobile-expert-card")).toHaveLength(2);
  });

  it("renders record and admin shared organisms with stable selectors", () => {
    const recordGroups = [
      {
        label: "Hoy",
        items: [
          {
            expiresSoon: false,
            question: "¿Cuál es el tratamiento del beneficio de auditoría?",
            resumeLabel: "Reanudar",
            sessionId: "session-1",
            timeLabel: "09:30",
            topicClassName: "topic-renta",
            topicLabel: "Renta",
            turnsLabel: "2 respuestas",
            userLabel: "contadora@lia.co",
          } satisfies RecordConversationViewModel,
        ],
      },
    ];
    const mobileGroups = [
      {
        label: "Hoy",
        items: [
          {
            question: "¿Cuál es el tratamiento del beneficio de auditoría?",
            sessionId: "session-1",
            timeAgoLabel: "Hace 5 min",
            topicClassName: "topic-renta",
            topicLabel: "Renta",
          } satisfies MobileHistoryConversationViewModel,
        ],
      },
    ];
    const adminRowModel: AdminUserRowViewModel = {
      actions: [
        { kind: "suspend", label: "Suspender", userId: "user-1", userName: "Ana" },
        { kind: "delete", label: "Eliminar", userId: "user-1", userName: "Ana" },
      ],
      displayName: "Ana Gómez",
      email: "ana@lia.co",
      roleLabel: "Admin",
      statusLabel: "Activo",
      statusTone: "success",
      userId: "user-1",
    };

    const recordHtml = renderFragmentToHtml(
      renderRecordConversationGroups(recordGroups, "Sin sesiones"),
    );
    const mobileHtml = renderFragmentToHtml(renderMobileHistoryGroups(mobileGroups));
    const adminRow = createAdminUserRow(adminRowModel, {
      delete: vi.fn(),
      reactivate: vi.fn(),
      suspend: vi.fn(),
    });
    const feedbackRow = createAdminUsersFeedbackRow("Cargando...", "loading");

    expect(recordHtml).toContain('data-lia-component="record-card"');
    expect(recordHtml).toContain('data-lia-component="record-date-group"');
    expect(mobileHtml).toContain('data-lia-component="mobile-history-card"');
    expect(mobileHtml).toContain('data-lia-component="mobile-history-group"');
    expect(queryAllByComponent(adminRow, "admin-user-action")).toHaveLength(2);
    expect(queryAllByComponent(feedbackRow, "state-block")).toHaveLength(1);
  });
});
