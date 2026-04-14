import { getJson } from "@/shared/api/client";
import type { I18nRuntime } from "@/shared/i18n";
import {
  formatOpsError,
  statusTone,
  type OpsCascadeStep,
  type OpsRun,
  type OpsRunCascadeResponse,
  type OpsTabKey,
  type OpsTimelineEvent,
  type OpsWaterfall,
} from "@/features/ops/opsTypes";
import type { OpsStateController } from "@/features/ops/opsState";

type AsyncTaskRunner = <T>(task: () => Promise<T>) => Promise<T>;

interface OpsMonitorDom {
  monitorTabBtn: HTMLButtonElement | null;
  ingestionTabBtn: HTMLButtonElement | null;
  controlTabBtn: HTMLButtonElement | null;
  embeddingsTabBtn: HTMLButtonElement | null;
  reindexTabBtn: HTMLButtonElement | null;
  monitorPanel: HTMLElement | null;
  ingestionPanel: HTMLElement | null;
  controlPanel: HTMLElement | null;
  embeddingsPanel: HTMLElement | null;
  reindexPanel: HTMLElement | null;
  runsBody: HTMLTableSectionElement;
  timelineNode: HTMLUListElement;
  timelineMeta: HTMLParagraphElement;
  cascadeNote: HTMLParagraphElement;
  userCascadeNode: HTMLOListElement;
  userCascadeSummary: HTMLParagraphElement;
  technicalCascadeNode: HTMLOListElement;
  technicalCascadeSummary: HTMLParagraphElement;
  refreshRunsBtn: HTMLButtonElement;
}

interface CreateOpsMonitorControllerOptions {
  i18n: I18nRuntime;
  stateController: OpsStateController;
  dom: OpsMonitorDom;
  withThinkingWheel: AsyncTaskRunner;
  setFlash: (message?: string, tone?: "success" | "error") => void;
}

function finiteMs(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return parsed;
}

export function createOpsMonitorController({
  i18n,
  stateController,
  dom,
  withThinkingWheel,
  setFlash,
}: CreateOpsMonitorControllerOptions) {
  const {
    monitorTabBtn,
    ingestionTabBtn,
    controlTabBtn,
    embeddingsTabBtn,
    reindexTabBtn,
    monitorPanel,
    ingestionPanel,
    controlPanel,
    embeddingsPanel,
    reindexPanel,
    runsBody,
    timelineNode,
    timelineMeta,
    cascadeNote,
    userCascadeNode,
    userCascadeSummary,
    technicalCascadeNode,
    technicalCascadeSummary,
    refreshRunsBtn,
  } = dom;

  const { state } = stateController;

  function formatSeconds(ms: unknown): string {
    const value = finiteMs(ms);
    if (value === null) return "-";
    return `${i18n.formatNumber(value / 1000, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} s`;
  }

  function setActiveTab(tab: OpsTabKey): void {
    stateController.setActiveTab(tab);
    renderTabs();
  }

  function renderTabs(): void {
    if (!monitorTabBtn) return;
    const active = state.activeTab;

    monitorTabBtn.classList.toggle("is-active", active === "monitor");
    monitorTabBtn.setAttribute("aria-selected", String(active === "monitor"));
    ingestionTabBtn?.classList.toggle("is-active", active === "ingestion");
    ingestionTabBtn?.setAttribute("aria-selected", String(active === "ingestion"));
    controlTabBtn?.classList.toggle("is-active", active === "control");
    controlTabBtn?.setAttribute("aria-selected", String(active === "control"));
    embeddingsTabBtn?.classList.toggle("is-active", active === "embeddings");
    embeddingsTabBtn?.setAttribute("aria-selected", String(active === "embeddings"));
    reindexTabBtn?.classList.toggle("is-active", active === "reindex");
    reindexTabBtn?.setAttribute("aria-selected", String(active === "reindex"));

    if (monitorPanel) {
      monitorPanel.hidden = active !== "monitor";
      monitorPanel.classList.toggle("is-active", active === "monitor");
    }
    if (ingestionPanel) {
      ingestionPanel.hidden = active !== "ingestion";
      ingestionPanel.classList.toggle("is-active", active === "ingestion");
    }
    if (controlPanel) {
      controlPanel.hidden = active !== "control";
      controlPanel.classList.toggle("is-active", active === "control");
    }
    if (embeddingsPanel) {
      embeddingsPanel.hidden = active !== "embeddings";
      embeddingsPanel.classList.toggle("is-active", active === "embeddings");
    }
    if (reindexPanel) {
      reindexPanel.hidden = active !== "reindex";
      reindexPanel.classList.toggle("is-active", active === "reindex");
    }
  }

  function renderTimeline(events: OpsTimelineEvent[]): void {
    timelineNode.innerHTML = "";
    if (!Array.isArray(events) || events.length === 0) {
      timelineNode.innerHTML = `<li>${i18n.t("ops.timeline.empty")}</li>`;
      return;
    }

    events.forEach((event) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <strong>${event.stage || "-"}</strong> · <span class="status-${statusTone(String(event.status || ""))}">${event.status || "-"}</span><br/>
        <small>${event.at || "-"} · ${event.duration_ms || 0} ms</small>
        <pre>${JSON.stringify(event.details || {}, null, 2)}</pre>
      `;
      timelineNode.appendChild(li);
    });
  }

  function renderWaterfallSummary(node: HTMLElement, waterfall: OpsWaterfall | undefined, kind: "user" | "technical"): void {
    const totalMs = finiteMs(waterfall?.total_ms);
    const totalText = totalMs === null ? i18n.t("ops.timeline.summaryPending") : formatSeconds(totalMs);
    const suffix =
      kind === "user"
        ? String(waterfall?.chat_run_id || "").trim()
          ? ` · chat_run ${String(waterfall?.chat_run_id || "").trim()}`
          : ""
        : "";
    node.textContent = `${i18n.t("ops.timeline.totalLabel")} ${totalText}${suffix}`;
  }

  function buildStepDetailText(step: OpsCascadeStep): string {
    const parts: string[] = [];
    const source = String(step.details?.source || "").trim();
    const status = String(step.status || "").trim();
    if (source) parts.push(source);
    if (status && status !== "ok" && status !== "missing") parts.push(status);
    const citationsCount = Number(step.details?.citations_count || 0);
    if (Number.isFinite(citationsCount) && citationsCount > 0) {
      parts.push(`${citationsCount} refs`);
    }
    const panelStatus = String(step.details?.panel_status || "").trim();
    if (panelStatus) {
      parts.push(panelStatus);
    }
    return parts.join(" · ");
  }

  function renderWaterfall(node: HTMLOListElement, waterfall: OpsWaterfall | undefined, kind: "user" | "technical"): void {
    node.innerHTML = "";
    const steps = Array.isArray(waterfall?.steps) ? waterfall?.steps || [] : [];
    if (steps.length === 0) {
      node.innerHTML = `<li class="ops-cascade-step is-empty">${i18n.t("ops.timeline.waterfallEmpty")}</li>`;
      return;
    }

    const totalMs =
      finiteMs(waterfall?.total_ms) ??
      Math.max(
        1,
        ...steps.map((step) => finiteMs(step.cumulative_ms) ?? finiteMs(step.absolute_elapsed_ms) ?? 0)
      );

    steps.forEach((step) => {
      const durationMs = finiteMs(step.duration_ms);
      const offsetMs = finiteMs(step.offset_ms) ?? 0;
      const absoluteMs = finiteMs(step.absolute_elapsed_ms);
      const row = document.createElement("li");
      row.className = `ops-cascade-step ops-cascade-step--${kind}${durationMs === null ? " is-missing" : ""}`;

      const head = document.createElement("div");
      head.className = "ops-cascade-step-head";

      const titleWrap = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = step.label || "-";
      const meta = document.createElement("small");
      meta.className = "ops-cascade-step-meta";
      meta.textContent =
        durationMs === null
          ? i18n.t("ops.timeline.missingStep")
          : `${i18n.t("ops.timeline.stepLabel")} ${formatSeconds(durationMs)} · T+${formatSeconds(absoluteMs ?? step.cumulative_ms)}`;
      titleWrap.append(title, meta);

      const status = document.createElement("span");
      status.className = `meta-chip status-${statusTone(String(step.status || ""))}`;
      status.textContent = String(step.status || (durationMs === null ? "missing" : "ok"));

      head.append(titleWrap, status);

      row.appendChild(head);

      const track = document.createElement("div");
      track.className = "ops-cascade-track";

      const segment = document.createElement("span");
      segment.className = "ops-cascade-segment";
      const startPct = Math.max(0, Math.min(100, (offsetMs / totalMs) * 100));
      const durationPct = durationMs === null ? 0 : Math.max((durationMs / totalMs) * 100, durationMs > 0 ? 2.5 : 0);
      segment.style.left = `${startPct}%`;
      segment.style.width = `${durationPct}%`;
      segment.setAttribute(
        "aria-label",
        durationMs === null
          ? `${step.label}: ${i18n.t("ops.timeline.missingStep")}`
          : `${step.label}: ${formatSeconds(durationMs)}`
      );
      track.appendChild(segment);
      row.appendChild(track);

      const detailText = buildStepDetailText(step);
      if (detailText) {
        const detail = document.createElement("p");
        detail.className = "ops-cascade-step-detail";
        detail.textContent = detailText;
        row.appendChild(detail);
      }

      node.appendChild(row);
    });
  }

  async function fetchRuns(): Promise<OpsRun[]> {
    const data = await getJson<{ runs?: OpsRun[] }>("/api/ops/runs?limit=30");
    return data.runs || [];
  }

  async function fetchRunCascade(runId: string): Promise<OpsRunCascadeResponse> {
    return getJson<OpsRunCascadeResponse>(`/api/ops/runs/${encodeURIComponent(runId)}/timeline`);
  }

  function renderCascade(data: OpsRunCascadeResponse, runId: string): void {
    const run = (data.run || {}) as Record<string, unknown>;
    timelineMeta.textContent = i18n.t("ops.timeline.label", { id: runId });
    cascadeNote.textContent = i18n.t("ops.timeline.selectedRunMeta", {
      trace: String(run.trace_id || "-"),
      chatRun: String(data.user_waterfall?.chat_run_id || run.chat_run_id || "-"),
    });
    renderWaterfallSummary(userCascadeSummary, data.user_waterfall, "user");
    renderWaterfallSummary(technicalCascadeSummary, data.technical_waterfall, "technical");
    renderWaterfall(userCascadeNode, data.user_waterfall, "user");
    renderWaterfall(technicalCascadeNode, data.technical_waterfall, "technical");
    renderTimeline(Array.isArray(data.timeline) ? data.timeline : []);
  }

  function renderRuns(runs: OpsRun[]): void {
    runsBody.innerHTML = "";
    if (!Array.isArray(runs) || runs.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="4">${i18n.t("ops.runs.empty")}</td>`;
      runsBody.appendChild(tr);
      return;
    }

    runs.forEach((run) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><button type="button" class="link-btn" data-run-id="${run.run_id}">${run.run_id}</button></td>
        <td>${run.trace_id || "-"}</td>
        <td class="status-${statusTone(String(run.status || ""))}">${run.status || "-"}</td>
        <td>${run.started_at ? i18n.formatDateTime(run.started_at, { dateStyle: "short", timeStyle: "short", timeZone: "America/Bogota" }) : "-"}</td>
      `;
      runsBody.appendChild(tr);
    });

    runsBody.querySelectorAll<HTMLButtonElement>("button[data-run-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const runId = btn.getAttribute("data-run-id") || "";
        try {
          const cascade = await withThinkingWheel(async () => fetchRunCascade(runId));
          renderCascade(cascade, runId);
        } catch (error) {
          userCascadeNode.innerHTML = `<li class="ops-cascade-step is-empty status-error">${formatOpsError(error)}</li>`;
          technicalCascadeNode.innerHTML = `<li class="ops-cascade-step is-empty status-error">${formatOpsError(error)}</li>`;
          timelineNode.innerHTML = `<li class="status-error">${formatOpsError(error)}</li>`;
        }
      });
    });
  }

  async function refreshRuns({
    showWheel = true,
    reportError = true,
  }: {
    showWheel?: boolean;
    reportError?: boolean;
  } = {}): Promise<void> {
    const task = async () => {
      const runs = await fetchRuns();
      renderRuns(runs);
    };

    try {
      if (showWheel) {
        await withThinkingWheel(task);
      } else {
        await task();
      }
    } catch (error) {
      runsBody.innerHTML = `<tr><td colspan="4" class="status-error">${formatOpsError(error)}</td></tr>`;
      if (reportError) {
        setFlash(formatOpsError(error), "error");
      }
    }
  }

  function bindEvents(): void {
    monitorTabBtn?.addEventListener("click", () => {
      setActiveTab("monitor");
    });

    ingestionTabBtn?.addEventListener("click", () => {
      setActiveTab("ingestion");
    });

    controlTabBtn?.addEventListener("click", () => {
      setActiveTab("control");
    });

    embeddingsTabBtn?.addEventListener("click", () => {
      setActiveTab("embeddings");
    });

    reindexTabBtn?.addEventListener("click", () => {
      setActiveTab("reindex");
    });

    refreshRunsBtn.addEventListener("click", () => {
      setFlash();
      void refreshRuns({ showWheel: true, reportError: true });
    });
  }

  return {
    bindEvents,
    refreshRuns,
    renderTabs,
  };
}
