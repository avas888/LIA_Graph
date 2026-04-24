import "@/styles/main.css";
import "@/styles/admin/api.css";
import { requireAuth } from "@/shared/auth/authGate";
import { renderChatShell } from "@/app/chat/shell";
import { renderBackstageShell } from "@/app/ops/shell";
import { mountChatApp } from "@/features/chat/chatApp";
import { mountBackstageApp } from "@/features/ops/opsApp";
import { createPageContext } from "@/shared/app/bootstrap";
import { mountTemplate, queryRequired } from "@/shared/dom/template";
import {
  renderBrowserChrome,
  mountBrowserTabs,
  readStoredBrowserTab,
  type BrowserTabId,
  type BrowserTabConfig,
} from "@/shared/dom/browserTabs";
import { getVisibleTabs } from "@/shared/auth/tabAccess";
import { getAuthContext } from "@/shared/auth/authContext";
import { isMobile } from "@/app/mobile/detectMobile";

// ── Auth gate: redirect to /login if not authenticated ──
if (!requireAuth()) {
  // Browser will redirect; nothing to render.
} else if (isMobile()) {
  initMobileApp();
} else {
  initApp();
}

// ── Mobile bootstrap ──────────────────────────────────────

async function initMobileApp(): Promise<void> {
  // iOS Safari: set shell height to window.innerHeight (accounts for toolbar)
  function syncShellHeight(): void {
    document.documentElement.style.setProperty("--app-height", `${window.innerHeight}px`);
  }
  syncShellHeight();
  window.addEventListener("resize", syncShellHeight);

  const page = createPageContext({ missingRootMessage: "Missing #app root." });
  const { i18n, root } = page;

  // Load mobile CSS
  await import("@/styles/mobile/index.css");

  // Render mobile shell (embeds desktop chat DOM for chatApp compatibility)
  const { renderMobileShell } = await import("@/app/mobile/shell-mobile");
  page.mountShell(renderMobileShell(i18n));
  page.setTitle(i18n.t("app.title.chat"));

  // Mount chatApp on the chat panel (contains full desktop DOM)
  const chatPanel = queryRequired<HTMLElement>(root, "#mobile-panel-chat");
  const chatApp = mountChatApp(chatPanel, { i18n });

  // Mount mobile controllers
  const { mountMobileNav } = await import("@/app/mobile/mobileNav");
  const { mountMobileSheet } = await import("@/app/mobile/mobileSheet");
  const { mountMobileNormativaPanel } = await import("@/app/mobile/mobileNormativaPanel");
  const { mountMobileInterpPanel } = await import("@/app/mobile/mobileInterpPanel");
  const { mountMobileChatAdapter } = await import("@/app/mobile/mobileChatAdapter");
  const { mountMobileDrawer } = await import("@/app/mobile/mobileDrawer");
  const { mountMobileHistorial } = await import("@/app/mobile/mobileHistorial");

  const { getToastController } = await import("@/shared/ui/toasts");
  const toastController = getToastController(i18n);

  const chatLog = root.querySelector<HTMLElement>("#chat-log")!;
  const newThreadBtn = root.querySelector<HTMLButtonElement>("#new-thread-btn");

  const nav = mountMobileNav(root, {
    onChatTabReclick: async () => {
      const hasBubbles = chatLog.querySelector(".bubble") !== null;
      if (!hasBubbles) return;
      const confirmed = await toastController.confirm({
        message: i18n.t("chat.newChat.caution"),
        tone: "caution",
        confirmLabel: i18n.t("chat.newChat.confirmAction"),
        cancelLabel: i18n.t("chat.newChat.cancelAction"),
      });
      if (confirmed) newThreadBtn?.click();
    },
  });
  const mobileSheet = mountMobileSheet(root);
  const { setMobileSheet } = await import("@/features/chat/normative/articleReader");
  setMobileSheet(mobileSheet);
  const normativaPanel = mountMobileNormativaPanel(root, mobileSheet, {
    onOpenCitation: (citationId: string) => {
      if (chatApp && typeof chatApp.openCitationById === "function") {
        chatApp.openCitationById(citationId);
      }
    },
  });
  const interpPanel = mountMobileInterpPanel(root, mobileSheet, {
    onOpenCard: (cardId: string) => {
      if (chatApp && typeof chatApp.openExpertCardById === "function") {
        chatApp.openExpertCardById(cardId);
      }
    },
  });

  mountMobileChatAdapter({ root, nav, normativaPanel, interpPanel });

  const historial = mountMobileHistorial(root, {
    onBack: () => nav.switchTab("chat"),
    onResumeConversation: (sessionId: string) => {
      nav.switchTab("chat");
      if (chatApp && typeof chatApp.loadExternalSession === "function") {
        chatApp.loadExternalSession(sessionId);
      }
    },
  });

  mountMobileDrawer(root, {
    onNewConversation: () => {
      nav.switchTab("chat");
      const newThreadBtn = root.querySelector<HTMLButtonElement>("#new-thread-btn");
      newThreadBtn?.click();
    },
    onHistorial: () => {
      historial.show();
    },
  });
}

function initApp(): void {
  const page = createPageContext({ missingRootMessage: "Missing #app root." });
  const { i18n, root } = page;

  // ── Define all tabs with categories ─────────────────────
  const allTabs: BrowserTabConfig[] = [
    { id: "chat", label: i18n.t("tabs.chat"), category: "user" },
    { id: "record", label: i18n.t("tabs.record"), category: "user" },
    { id: "backstage", label: i18n.t("tabs.backstage"), category: "admin" },
    { id: "activity", label: "Actividad", category: "admin" },
    { id: "ingestion", label: i18n.t("tabs.ingestion"), category: "admin" },
    { id: "orchestration", label: i18n.t("tabs.orchestration"), category: "admin" },
    { id: "ratings", label: i18n.t("tabs.ratings"), category: "admin" },
    { id: "api", label: "API", category: "admin" },
  ];

  const visibleTabs = getVisibleTabs(allTabs);
  const visibleIds = new Set(visibleTabs.map((t) => t.id));

  // Ensure stored tab is visible; fall back to chat
  let initialTab = readStoredBrowserTab();
  if (!visibleIds.has(initialTab)) initialTab = "chat";

  // ── Render browser chrome (one panel per visible tab) ───
  page.mountShell(
    renderBrowserChrome(visibleTabs, initialTab, {
      logoSrc: "/assets/lia-logo.png",
      logoAlt: "LIA",
      tagline: i18n.t("chat.hero.tagline"),
    }),
  );

  const chatPanel = queryRequired<HTMLElement>(root, "#tab-panel-chat");
  const tabBar = queryRequired<HTMLElement>(root, ".browser-tab-bar");

  // Optional panels — only exist if visible
  const recordPanel = root.querySelector<HTMLElement>("#tab-panel-record");
  const ingestionPanel = root.querySelector<HTMLElement>("#tab-panel-ingestion");
  const backstagePanel = root.querySelector<HTMLElement>("#tab-panel-backstage");
  const ratingsPanel = root.querySelector<HTMLElement>("#tab-panel-ratings");
  const activityPanel = root.querySelector<HTMLElement>("#tab-panel-activity");
  const apiPanel = root.querySelector<HTMLElement>("#tab-panel-api");

  // ── Mount backstage eagerly if visible ──────────────────
  if (backstagePanel) {
    mountTemplate(backstagePanel, renderBackstageShell(i18n));
    mountBackstageApp(backstagePanel, { i18n });
  }

  // ── Mount chat ──────────────────────────────────────────
  mountTemplate(chatPanel, renderChatShell(i18n));
  const chatApp = mountChatApp(chatPanel, { i18n });

  // ── Lazy-mount ops app on first visit to ingestion or backstage ──
  //
  // The Ingesta tab now hosts two level-1 sub-tabs ("Sesiones" and
  // "Promoción"). Sesiones contains the ingestion UI (mountOpsApp);
  // Promoción contains the WIP→Production lifecycle panel that used to
  // live as the standalone top-level "Operaciones" tab. Both controllers
  // mount eagerly on first visit so polling and event wiring start
  // immediately, regardless of which sub-tab the user opens first.

  let opsAppMounted = false;

  async function ensureOpsApp(): Promise<void> {
    if (opsAppMounted || !ingestionPanel) return;
    opsAppMounted = true;

    const [
      { renderIngestionShell, renderPromocionShell },
      { mountOpsApp },
      { createCorpusLifecycleController },
      { createOpsEmbeddingsController },
      { createOpsReindexController },
    ] = await Promise.all([
      import("@/app/ops/shell"),
      import("@/features/ops/opsApp"),
      import("@/features/ops/opsCorpusLifecycleController"),
      import("@/features/ops/opsEmbeddingsController"),
      import("@/features/ops/opsReindexController"),
    ]);

    // 1. Render the ingestion shell (which now embeds both sub-tab
    //    sections — Sesiones populated, Promoción empty) and bind the
    //    Sesiones controller against the panel as before.
    mountTemplate(ingestionPanel, renderIngestionShell(i18n));
    mountOpsApp(ingestionPanel, { i18n });

    // 1a. Wire the level-1 Sesiones / Promoción / Sub-temas switcher
    //     FIRST — before any async refreshes — so tab navigation works
    //     even if Supabase/Falkor polling later throws. Previously this
    //     wiring lived at the bottom of ensureOpsApp(), so a single
    //     rejected refresh would leave the tabs dead.
    const earlySubtabBtns = ingestionPanel.querySelectorAll<HTMLButtonElement>(
      ".ingestion-subtab",
    );
    const earlySections: Record<string, HTMLElement | null> = {
      sesiones: ingestionPanel.querySelector<HTMLElement>("#ingestion-section-sesiones"),
      promocion: ingestionPanel.querySelector<HTMLElement>("#ingestion-section-promocion"),
      subtopics: ingestionPanel.querySelector<HTMLElement>("#ingestion-section-subtopics"),
    };
    let subtopicsMountedEarly = false;
    async function ensureSubtopicsMountedEarly(): Promise<void> {
      if (subtopicsMountedEarly) return;
      const section = earlySections.subtopics;
      if (!section) return;
      subtopicsMountedEarly = true;
      const [
        { renderSubtopicShellMarkup },
        { createSubtopicController },
      ] = await Promise.all([
        import("@/app/subtopics/subtopicShell"),
        import("@/features/subtopics/subtopicController"),
      ]);
      mountTemplate(section, renderSubtopicShellMarkup());
      const shellRoot = section.querySelector<HTMLElement>("#lia-subtopic-shell");
      if (shellRoot) {
        const controller = createSubtopicController(shellRoot);
        void controller.refresh();
      }
    }
    earlySubtabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const section = btn.dataset.ingestionSection ?? "sesiones";
        earlySubtabBtns.forEach((b) => {
          const active = b === btn;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-selected", String(active));
        });
        for (const [key, el] of Object.entries(earlySections)) {
          if (el) el.hidden = key !== section;
        }
        if (section === "subtopics") {
          void ensureSubtopicsMountedEarly();
        }
      });
    });

    // 2. Inject the Promoción shell into its (currently hidden) section
    //    and bind the corpus-lifecycle / embeddings / re-index controllers
    //    exactly as the old top-level Operaciones tab did.
    const promocionSection = ingestionPanel.querySelector<HTMLElement>(
      "#ingestion-section-promocion",
    );
    if (promocionSection) {
      promocionSection.innerHTML = renderPromocionShell();

      const flashEl = promocionSection.querySelector<HTMLDivElement>("#operations-flash")!;
      function setFlash(message = "", tone: "success" | "error" = "success"): void {
        if (!message) {
          flashEl.hidden = true;
          flashEl.textContent = "";
          flashEl.removeAttribute("data-tone");
          return;
        }
        flashEl.hidden = false;
        flashEl.dataset.tone = tone;
        flashEl.textContent = message;
      }

      // Level-2 sub-tabs (Corpus / Embeddings / Re-index) — unchanged
      // from the prior Operaciones panel.
      const subtabBtns = promocionSection.querySelectorAll<HTMLButtonElement>(
        ".operations-subtab",
      );
      const sections = {
        corpus: promocionSection.querySelector<HTMLElement>("#ops-section-corpus")!,
        embeddings: promocionSection.querySelector<HTMLElement>("#ops-section-embeddings")!,
        reindex: promocionSection.querySelector<HTMLElement>("#ops-section-reindex")!,
      };
      subtabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          const section = btn.dataset.opsSection as keyof typeof sections;
          subtabBtns.forEach((b) => b.classList.toggle("is-active", b === btn));
          for (const [key, el] of Object.entries(sections)) {
            el.hidden = key !== section;
          }
        });
      });

      const corpusContainer = promocionSection.querySelector<HTMLElement>(
        "#operations-corpus-lifecycle",
      )!;
      const corpusController = createCorpusLifecycleController({
        dom: { container: corpusContainer },
        setFlash,
      });
      corpusController.bindEvents();

      const embeddingsContainer = promocionSection.querySelector<HTMLElement>(
        "#operations-embeddings-lifecycle",
      )!;
      const embeddingsController = createOpsEmbeddingsController({
        dom: { container: embeddingsContainer },
        setFlash,
      });
      embeddingsController.bindEvents();

      const reindexContainer = promocionSection.querySelector<HTMLElement>(
        "#operations-reindex-lifecycle",
      )!;
      const reindexController = createOpsReindexController({
        dom: { container: reindexContainer },
        setFlash,
        navigateToEmbeddings: () => {
          subtabBtns.forEach((b) =>
            b.classList.toggle("is-active", b.dataset.opsSection === "embeddings"),
          );
          for (const [key, el] of Object.entries(sections)) el.hidden = key !== "embeddings";
        },
      });
      reindexController.bindEvents();

      // Kick off the initial refreshes + polling, but swallow errors so
      // a backend outage never kills the outer ensureOpsApp() flow (which
      // would leave the level-1 subtabs dead — the bug the early-wire
      // block above now prevents, but we keep the safety net too).
      try {
        await Promise.all([
          corpusController.refresh(),
          embeddingsController.refresh(),
          reindexController.refresh(),
        ]);
      } catch (err) {
        console.warn("Promoción controllers initial refresh failed:", err);
      }
      window.setInterval(() => {
        void corpusController.refresh().catch(() => undefined);
        void embeddingsController.refresh().catch(() => undefined);
        void reindexController.refresh().catch(() => undefined);
      }, 5_000);
    }
    // Level-1 subtab wiring moved to step 1a above — don't re-attach here.
  }

  // ── Lazy-mount record tab on first visit ────────────────

  let recordAppMounted = false;
  let recordAppLoading = false;

  async function ensureRecordApp(): Promise<void> {
    if (recordAppMounted || recordAppLoading || !recordPanel) return;
    recordAppLoading = true;
    try {
      const { mountRecordApp } = await import("@/features/record/recordApp");
      mountRecordApp(recordPanel, { i18n });
      recordAppMounted = true;
    } finally {
      recordAppLoading = false;
    }
  }

  // ── Panel switching ─────────────────────────────────────

  function showPanel(id: BrowserTabId): void {
    chatPanel.classList.toggle("is-active", id === "chat");
    recordPanel?.classList.toggle("is-active", id === "record");
    ingestionPanel?.classList.toggle("is-active", id === "ingestion");
    backstagePanel?.classList.toggle("is-active", id === "backstage");
    ratingsPanel?.classList.toggle("is-active", id === "ratings");
    activityPanel?.classList.toggle("is-active", id === "activity");
    apiPanel?.classList.toggle("is-active", id === "api");
  }

  function updateTitle(id: BrowserTabId): void {
    if (id === "chat") {
      page.setTitle(i18n.t("app.title.chat"));
    } else if (id === "record") {
      page.setTitle(i18n.t("tabs.record"));
    } else {
      page.setTitle(i18n.t("app.title.ops"));
    }
  }

  let ratingsMounted = false;

  async function ensureRatingsPanel(): Promise<void> {
    if (ratingsMounted || !ratingsPanel) return;
    ratingsMounted = true;
    const { mountRatingsApp } = await import("@/features/ratings/ratingsApp");
    mountRatingsApp(ratingsPanel, { i18n });
  }

  let activityMounted = false;

  async function ensureActivityPanel(): Promise<void> {
    if (activityMounted || !activityPanel) return;
    activityMounted = true;
    const { mountActivityPanel } = await import("@/features/admin/activityController");
    mountActivityPanel(activityPanel);
  }

  let apiMounted = false;

  async function ensureApiPanel(): Promise<void> {
    if (apiMounted || !apiPanel) return;
    apiMounted = true;
    const { mountAdminApiTab } = await import("@/features/admin/adminApiController");
    const ctx = getAuthContext();
    mountAdminApiTab(apiPanel, ctx.tenant_id || "");
  }

  async function handleTabSwitch(id: BrowserTabId): Promise<void> {
    if (id === "orchestration") {
      window.location.href = "/orchestration";
      return;
    }
    try {
      if (id === "record") await ensureRecordApp();
      if ((id === "ingestion" || id === "backstage") && !opsAppMounted) await ensureOpsApp();
      if (id === "ratings" && !ratingsMounted) await ensureRatingsPanel();
      if (id === "activity" && !activityMounted) await ensureActivityPanel();
      if (id === "api" && !apiMounted) await ensureApiPanel();
    } catch (err) {
      console.error(`[LIA] Failed to mount "${id}" tab:`, err);
    }
    // Always switch panel — even if lazy-mount failed
    showPanel(id);
    updateTitle(id);
  }

  // ── Mount tab controller ────────────────────────────────

  const tabs = mountBrowserTabs(tabBar, (id) => {
    handleTabSwitch(id).catch((err) =>
      console.error("[LIA] Tab switch error:", err),
    );
  });

  // ── Resume conversation: Record tab → Chat tab ─────────

  document.addEventListener("resume-conversation", ((e: CustomEvent<{ sessionId: string }>) => {
    tabs.switchTo("chat");
    if (chatApp && typeof chatApp.loadExternalSession === "function") {
      chatApp.loadExternalSession(e.detail.sessionId);
    }
  }) as EventListener);

  // ── Initialize ──────────────────────────────────────────

  void handleTabSwitch(initialTab);
}
