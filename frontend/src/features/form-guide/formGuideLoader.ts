import { getJson } from "@/shared/api/client";
import type { FormGuideState } from "@/features/form-guide/formGuideState";
import {
  findOfficialFormPdfUrl,
  sanitizeAppHref,
  type GuideCatalogEntry,
  type GuideCatalogResponse,
  type GuideContentResponse,
} from "@/features/form-guide/formGuideTypes";

interface CreateFormGuideLoaderOptions {
  state: FormGuideState;
  onContentLoaded: (data: GuideContentResponse) => void;
  onError: (message: string) => void;
  showLoading: () => void;
  showProfileSelector: (catalog: GuideCatalogEntry, onSelect: (profileId: string) => void) => void;
}

function selectCatalogEntry(response: GuideCatalogResponse, referenceKey: string): GuideCatalogEntry | null {
  if (response.guide) {
    return response.guide;
  }

  if (response.reference_key && Array.isArray(response.available_profiles)) {
    return {
      reference_key: response.reference_key,
      title: response.title || "",
      form_version: response.form_version || "",
      available_profiles: response.available_profiles,
      supported_views: response.supported_views || [],
      last_verified_date: response.last_verified_date || "",
      download_available: Boolean(response.download_available),
      disclaimer: response.disclaimer || "",
    };
  }

  if (Array.isArray(response.guides) && response.guides.length > 0) {
    return response.guides.find((guide) => guide.reference_key === referenceKey) || response.guides[0];
  }

  return null;
}

export function createFormGuideLoader({
  state,
  onContentLoaded,
  onError,
  showLoading,
  showProfileSelector,
}: CreateFormGuideLoaderOptions) {
  async function loadContent(): Promise<void> {
    try {
      const response = await getJson<GuideContentResponse>(
        `/api/form-guides/content?reference_key=${encodeURIComponent(state.currentReferenceKey)}&profile=${encodeURIComponent(state.currentProfile)}&view=structured`
      );

      if (!response.ok) {
        onError("No se pudo cargar el contenido de la guía.");
        return;
      }

      state.guideSources = response.sources || [];
      state.guidePageAssets = response.page_assets || [];
      const officialPdf = findOfficialFormPdfUrl(state.guideSources);
      state.guideOfficialPdfUrl = sanitizeAppHref(response.official_pdf_url) || officialPdf.url;
      state.guideOfficialPdfAuthority = String(response.official_pdf_authority || officialPdf.authority || "").trim();
      onContentLoaded(response);
    } catch {
      onError("Error cargando el contenido de la guía.");
    }
  }

  async function loadCatalog(): Promise<void> {
    try {
      const response = await getJson<GuideCatalogResponse>(
        `/api/form-guides/catalog?reference_key=${encodeURIComponent(state.currentReferenceKey)}`
      );

      const catalog = selectCatalogEntry(response, state.currentReferenceKey);
      if (!response.ok || !catalog) {
        onError("Esta guía aún no está disponible.");
        return;
      }

      if (catalog.available_profiles.length > 1 && !state.currentProfile) {
        showProfileSelector(catalog, (profileId) => {
          state.currentProfile = profileId;
          showLoading();
          void loadContent();
        });
        return;
      }

      if (!state.currentProfile && catalog.available_profiles.length === 1) {
        state.currentProfile = catalog.available_profiles[0].profile_id;
      }

      await loadContent();
    } catch {
      onError("Error cargando la guía. Intenta de nuevo.");
    }
  }

  return {
    loadCatalog,
    loadContent,
  };
}
