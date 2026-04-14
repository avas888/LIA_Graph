// @ts-nocheck

/**
 * Request timers, token usage formatting, runtime panel, telemetry milestones.
 * Extracted from requestController.ts during decouple-v1 Phase 4.
 */

import { getJson, postJson } from "@/shared/api/client";
import { getLocalStorage } from "@/shared/browser/storage";

// ── Pure exported helpers ─────────────────────────────────────

export function normalizeTokenUsage(raw: unknown): {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
} {
  const payload = raw && typeof raw === "object" ? raw : {};
  const inputTokens = Number((payload as Record<string, unknown>).input_tokens || 0);
  const outputTokens = Number((payload as Record<string, unknown>).output_tokens || 0);
  const totalTokens = Number((payload as Record<string, unknown>).total_tokens || inputTokens + outputTokens);
  return {
    input_tokens: Number.isFinite(inputTokens) ? Math.max(0, Math.trunc(inputTokens)) : 0,
    output_tokens: Number.isFinite(outputTokens) ? Math.max(0, Math.trunc(outputTokens)) : 0,
    total_tokens: Number.isFinite(totalTokens) ? Math.max(0, Math.trunc(totalTokens)) : 0,
  };
}

export function formatTokenUsage(usage: { input_tokens: number; output_tokens: number; total_tokens: number }): string {
  return `in=${usage.input_tokens} | out=${usage.output_tokens} | total=${usage.total_tokens}`;
}

export function formatDurationSeconds(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "-";
  return `${(ms / 1000).toFixed(2)} s`;
}

// ── Metrics controller factory ────────────────────────────────

export interface MetricsControllerDeps {
  i18n: any;
  state: any;
  debugInput: HTMLInputElement | null;
  diagnosticsNode: HTMLElement | null;
  runtimeRequestTimerNode: HTMLElement | null;
  runtimeLatencyNode: HTMLElement | null;
  runtimeModelNode: HTMLElement | null;
  runtimeTurnTokensNode: HTMLElement | null;
  runtimeConversationTokensNode: HTMLElement | null;
  devBootCacheKey: string;
  resetConversationUi: () => void;
  persistActiveSessionSnapshot?: () => void;
}

export function createMetricsController(deps: MetricsControllerDeps) {
  const {
    state, debugInput, diagnosticsNode,
    runtimeRequestTimerNode, runtimeLatencyNode, runtimeModelNode,
    runtimeTurnTokensNode, runtimeConversationTokensNode,
    devBootCacheKey, resetConversationUi, persistActiveSessionSnapshot,
  } = deps;
  const localStore = getLocalStorage();

  function startRequestTimer(): void {
    stopRequestTimer();
    state.requestStartedAtMs = performance.now();
    state.latestTurnStartedAtMs = state.requestStartedAtMs;
    if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = "0.00 s";
    state.requestTimerInterval = window.setInterval(() => {
      if (state.requestStartedAtMs === null) return;
      const elapsed = performance.now() - state.requestStartedAtMs;
      if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = formatDurationSeconds(elapsed);
    }, 100);
  }

  function stopRequestTimer(): number | null {
    let elapsedMs: number | null = null;
    if (state.requestStartedAtMs !== null) {
      elapsedMs = Math.max(0, performance.now() - state.requestStartedAtMs);
    }
    if (state.requestTimerInterval !== null) {
      window.clearInterval(state.requestTimerInterval);
      state.requestTimerInterval = null;
    }
    state.requestStartedAtMs = null;
    if (elapsedMs !== null) {
      if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = formatDurationSeconds(elapsedMs);
    }
    return elapsedMs;
  }

  function setConversationTotals(
    usageRaw: unknown,
    { persistSnapshot = false }: { persistSnapshot?: boolean } = {},
  ): void {
    const usage = normalizeTokenUsage(usageRaw);
    state.conversationTokenTotals.input_tokens = usage.input_tokens;
    state.conversationTokenTotals.output_tokens = usage.output_tokens;
    state.conversationTokenTotals.total_tokens = usage.total_tokens;
    if (runtimeConversationTokensNode) runtimeConversationTokensNode.textContent = formatTokenUsage(state.conversationTokenTotals);
    if (persistSnapshot) persistActiveSessionSnapshot?.();
  }

  async function recordUserMilestone(
    milestone: string,
    {
      source = "", status = "ok", details = {},
    }: { source?: string; status?: string; details?: Record<string, unknown> } = {},
  ): Promise<void> {
    const chatRunId = String(state.activeChatRunId || "").trim();
    const startedAtMs = Number(state.latestTurnStartedAtMs);
    if (!chatRunId || !Number.isFinite(startedAtMs)) return;
    const elapsedMs = Math.max(0, performance.now() - startedAtMs);
    try {
      await postJson(`/api/chat/runs/${encodeURIComponent(chatRunId)}/milestones`, {
        milestone,
        elapsed_ms: elapsedMs,
        source: String(source || "").trim() || undefined,
        status: String(status || "").trim() || undefined,
        details: details && typeof details === "object" ? details : {},
      });
    } catch (_error) { /* telemetry should never block UI */ }
  }

  function updateRuntimePanel(responseData: Record<string, unknown>, fallbackLatencyMs: number | null): void {
    const metrics = responseData && typeof responseData.metrics === "object" ? responseData.metrics : {};
    const llmRuntime =
      (metrics as Record<string, unknown>).llm_runtime &&
      typeof (metrics as Record<string, unknown>).llm_runtime === "object"
        ? ((metrics as Record<string, unknown>).llm_runtime as Record<string, unknown>)
        : responseData && typeof responseData.llm_runtime === "object"
          ? (responseData.llm_runtime as Record<string, unknown>)
          : {};
    const model = llmRuntime.model || "n/a";
    const provider = llmRuntime.selected_provider || "n/a";
    const providerType = llmRuntime.selected_type || "n/a";
    if (runtimeModelNode) runtimeModelNode.textContent = `${model} | ${providerType} | ${provider}`;

    const latencyMs = Number((metrics as Record<string, unknown>).latency_ms);
    if (runtimeLatencyNode) {
      if (Number.isFinite(latencyMs) && latencyMs >= 0) {
        runtimeLatencyNode.textContent = formatDurationSeconds(latencyMs);
      } else if (Number.isFinite(fallbackLatencyMs) && (fallbackLatencyMs as number) >= 0) {
        runtimeLatencyNode.textContent = formatDurationSeconds(fallbackLatencyMs as number);
      } else {
        runtimeLatencyNode.textContent = "-";
      }
    }

    const tokenUsage =
      (metrics as Record<string, unknown>).token_usage &&
      typeof (metrics as Record<string, unknown>).token_usage === "object"
        ? ((metrics as Record<string, unknown>).token_usage as Record<string, unknown>)
        : responseData && typeof responseData.token_usage === "object"
          ? (responseData.token_usage as Record<string, unknown>)
          : {};
    const llmUsage = normalizeTokenUsage(tokenUsage.llm);
    const turnUsage = llmUsage.total_tokens > 0 ? llmUsage : normalizeTokenUsage(tokenUsage.turn);
    if (runtimeTurnTokensNode) runtimeTurnTokensNode.textContent = formatTokenUsage(turnUsage);

    const conversationUsage =
      (metrics as Record<string, unknown>).conversation &&
      typeof (metrics as Record<string, unknown>).conversation === "object"
        ? ((metrics as Record<string, unknown>).conversation as Record<string, unknown>).token_usage_total
        : null;
    if (conversationUsage) {
      setConversationTotals(conversationUsage, { persistSnapshot: true });
    } else {
      setConversationTotals({
        input_tokens: state.conversationTokenTotals.input_tokens + turnUsage.input_tokens,
        output_tokens: state.conversationTokenTotals.output_tokens + turnUsage.output_tokens,
        total_tokens: state.conversationTokenTotals.total_tokens + turnUsage.total_tokens,
      }, { persistSnapshot: true });
    }
  }

  async function hydrateRuntimeModelFromStatus(): Promise<void> {
    try {
      const data = await getJson<Record<string, unknown>>("/api/llm/status");
      const runtime = data && typeof data.llm_runtime === "object" ? (data.llm_runtime as Record<string, unknown>) : null;
      if (!runtime) return;
      const model = runtime.model || "n/a";
      const providerType = runtime.selected_type || "n/a";
      const provider = runtime.selected_provider || "n/a";
      if (runtimeModelNode) runtimeModelNode.textContent = `${model} | ${providerType} | ${provider}`;
    } catch (_error) { /* keep defaults */ }
  }

  function syncDevBootFreshness(buildInfo: Record<string, unknown>): boolean {
    if (!buildInfo.reset_chat_on_dev_boot) return false;
    const nonce = String(buildInfo.dev_boot_nonce || "").trim();
    if (!nonce) return false;
    let previousNonce = "";
    try { previousNonce = String(localStore.getItem(devBootCacheKey) || "").trim(); } catch (_e) { previousNonce = ""; }
    try { localStore.setItem(devBootCacheKey, nonce); } catch (_e) { /* ignore */ }
    if (!previousNonce || previousNonce === nonce) return false;
    resetConversationUi();
    return true;
  }

  async function loadBuildInfo(): Promise<boolean> {
    try {
      const data = await getJson<Record<string, unknown>>("/api/build-info");
      const info =
        data && data.build_info && typeof data.build_info === "object"
          ? (data.build_info as Record<string, unknown>)
          : {};
      const commit = String(info.git_commit || "unknown").trim();
      const startedAt = String(info.server_started_at || "").trim();
      const assetMtime = String(info.ui_asset_mtime || "").trim();
      state.buildInfoLine = `Build: commit=${commit} | server_started_at=${startedAt || "n/a"} | ui_asset_mtime=${assetMtime || "n/a"}`;
      if (diagnosticsNode) {
        diagnosticsNode.textContent = debugInput?.checked
          ? `${state.buildInfoLine}\n\n${diagnosticsNode.textContent}`
          : state.buildInfoLine;
      }
      return syncDevBootFreshness(info);
    } catch (_error) {
      return false;
    }
  }

  return {
    startRequestTimer,
    stopRequestTimer,
    setConversationTotals,
    recordUserMilestone,
    updateRuntimePanel,
    hydrateRuntimeModelFromStatus,
    loadBuildInfo,
  };
}
