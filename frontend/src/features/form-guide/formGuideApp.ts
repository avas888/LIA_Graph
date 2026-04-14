import type { I18nRuntime } from "@/shared/i18n";
import { createFormGuideChatController } from "@/features/form-guide/formGuideChatController";
import { createFormGuideLoader } from "@/features/form-guide/formGuideLoader";
import { createFormGuideState } from "@/features/form-guide/formGuideState";
import { createFormGuideSurfaceController } from "@/features/form-guide/formGuideSurfaceController";

export function mountFormGuideApp(_root: HTMLElement, _opts: { i18n: I18nRuntime }) {
  const params = new URLSearchParams(window.location.search);
  const state = createFormGuideState();
  state.currentReferenceKey = params.get("reference_key") || "";
  state.currentProfile = params.get("profile") || "";

  const surfaceController = createFormGuideSurfaceController({ state });
  const chatController = createFormGuideChatController({ state });
  const loader = createFormGuideLoader({
    state,
    onContentLoaded: surfaceController.renderGuide,
    onError: surfaceController.showError,
    showLoading: surfaceController.showLoading,
    showProfileSelector: surfaceController.showProfileSelector,
  });

  if (!state.currentReferenceKey) {
    surfaceController.showError("No se especificó un formulario.");
    return;
  }

  chatController.bindChatForm();
  void loader.loadCatalog();
}
