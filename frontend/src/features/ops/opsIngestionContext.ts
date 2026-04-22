/**
 * Shared context object passed between the ops ingestion controller factories
 * (api, upload, intake, autoPilot, renderers, events). Introduced in the
 * decouplingv1 Phase 7 split so every factory sees the same DOM bag, i18n
 * runtime, state controller, and wheel/flash callbacks without rebuilding
 * them per factory.
 *
 * `render` and `trace` start as no-op placeholders and get rebound by the
 * controller once the renderers factory is built. Factories capture `ctx`
 * (not destructured members), so the late binding is transparent.
 */

import type { I18nRuntime } from "@/shared/i18n";
import type { ToastController } from "@/shared/ui/toasts";
import { getToastController } from "@/shared/ui/toasts";

import type {
  AsyncTaskRunner,
  CreateOpsIngestionControllerOptions,
  OpsIngestionDom,
} from "@/features/ops/opsIngestionTypes";
import type { OpsStateController } from "@/features/ops/opsState";

export interface OpsControllerCtx {
  dom: OpsIngestionDom;
  i18n: I18nRuntime;
  stateController: OpsStateController;
  withThinkingWheel: AsyncTaskRunner;
  setFlash: CreateOpsIngestionControllerOptions["setFlash"];
  toast: ToastController;
  /** Live getter for the current OpsStateData — always reflects the latest state. */
  get state(): OpsStateController["state"];
  /** Bound lazily by the controller once renderers are built. Safe to call before binding (no-op). */
  render: () => void;
  /** Bound lazily by the controller once the trace helper is built. Safe to call before binding (no-op). */
  trace: (msg: string) => void;
}

export function createOpsControllerCtx(
  options: CreateOpsIngestionControllerOptions,
): OpsControllerCtx {
  const { i18n, stateController, dom, withThinkingWheel, setFlash } = options;
  const toast = getToastController(i18n);
  const ctx: OpsControllerCtx = {
    dom,
    i18n,
    stateController,
    withThinkingWheel,
    setFlash,
    toast,
    get state() {
      return stateController.state;
    },
    render: () => {},
    trace: () => {},
  };
  return ctx;
}
