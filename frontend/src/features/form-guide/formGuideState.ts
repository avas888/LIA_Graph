import type {
  FieldHotspot,
  FormGuideSource,
  GuidePageAsset,
  StructuredSection,
} from "@/features/form-guide/formGuideTypes";

export interface FormGuideState {
  currentReferenceKey: string;
  currentProfile: string;
  selectedFieldId: string | null;
  selectedSection: string | null;
  chatMessages: Array<{ role: string; text: string }>;
  guideSources: FormGuideSource[];
  guidePageAssets: GuidePageAsset[];
  guideOfficialPdfUrl: string;
  guideOfficialPdfAuthority: string;
  guideSectionsById: Map<string, StructuredSection>;
  guideHotspotsById: Map<string, FieldHotspot>;
  guideViewObserver: IntersectionObserver | null;
}

export function createFormGuideState(): FormGuideState {
  return {
    currentReferenceKey: "",
    currentProfile: "",
    selectedFieldId: null,
    selectedSection: null,
    chatMessages: [],
    guideSources: [],
    guidePageAssets: [],
    guideOfficialPdfUrl: "",
    guideOfficialPdfAuthority: "",
    guideSectionsById: new Map(),
    guideHotspotsById: new Map(),
    guideViewObserver: null,
  };
}
