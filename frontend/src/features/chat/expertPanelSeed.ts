import { extractArticleRefs } from "@/features/chat/expertPanelRefs";
import { stripMarkdown } from "@/shared/utils/format";

export interface ExpertPanelSupportCitation {
  doc_id: string;
  logical_doc_id?: string;
  legal_reference?: string;
  source_label?: string;
  search_query?: string;
}

const COMMON_REFERENCE_WORDS = new Set([
  "articulo",
  "art",
  "estatuto",
  "tributario",
  "et",
  "de",
  "del",
  "la",
  "el",
  "los",
  "las",
  "y",
  "o",
  "para",
  "por",
  "con",
  "segun",
  "según",
  "ley",
  "decreto",
  "resolucion",
  "resolución",
  "concepto",
  "formulario",
]);

function normalizeText(value: unknown): string {
  return stripMarkdown(String(value || ""))
    .replace(/\s+/g, " ")
    .trim();
}

function clipText(value: string, maxChars: number): string {
  const clean = normalizeText(value);
  if (!clean || clean.length <= maxChars) return clean;
  const clipped = clean.slice(0, Math.max(0, maxChars - 1)).trimEnd();
  const lastSpace = clipped.lastIndexOf(" ");
  if (lastSpace >= Math.floor(maxChars * 0.6)) {
    return `${clipped.slice(0, lastSpace).trimEnd()}…`;
  }
  return `${clipped}…`;
}

function splitSentences(value: string): string[] {
  const clean = normalizeText(value);
  if (!clean) return [];
  return clean
    .replace(/\n+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function citationIdentity(citation: ExpertPanelSupportCitation): string {
  return (
    normalizeText(citation.logical_doc_id) ||
    normalizeText(citation.doc_id) ||
    normalizeText(citation.legal_reference) ||
    normalizeText(citation.source_label)
  ).toLowerCase();
}

function citationLabel(citation: ExpertPanelSupportCitation): string {
  return (
    normalizeText(citation.legal_reference) ||
    normalizeText(citation.source_label) ||
    normalizeText(citation.search_query) ||
    normalizeText(citation.doc_id)
  );
}

function citationKeywordSet(citation: ExpertPanelSupportCitation): Set<string> {
  const refs = extractArticleRefs(
    [
      citation.legal_reference,
      citation.source_label,
      citation.search_query,
    ]
      .map((value) => normalizeText(value))
      .filter(Boolean)
      .join(" "),
  );
  if (refs.length > 0) {
    return new Set(refs);
  }
  const label = citationLabel(citation).toLowerCase();
  return new Set(
    label
      .split(/[^a-z0-9áéíóúñ-]+/i)
      .map((token) => token.trim())
      .filter((token) => token.length > 3 && !COMMON_REFERENCE_WORDS.has(token)),
  );
}

function sentenceMatchesCitation(sentence: string, citation: ExpertPanelSupportCitation): boolean {
  const sentenceRefs = new Set(extractArticleRefs(sentence));
  const citationTokens = citationKeywordSet(citation);
  for (const token of citationTokens) {
    if (sentenceRefs.has(token)) return true;
  }
  const normalizedSentence = normalizeText(sentence).toLowerCase();
  for (const token of citationTokens) {
    if (normalizedSentence.includes(token.toLowerCase())) return true;
  }
  return false;
}

function pickAnswerGist(answer: string): string {
  const sentences = splitSentences(answer);
  if (sentences.length === 0) return clipText(answer, 280);
  let gist = "";
  for (const sentence of sentences) {
    const next = gist ? `${gist} ${sentence}` : sentence;
    if (next.length > 280 && gist) break;
    gist = next;
    if (gist.length >= 220) break;
  }
  return clipText(gist || sentences[0], 280);
}

function pickCitationClause(
  citation: ExpertPanelSupportCitation,
  {
    answerSentences,
    fallbackGist,
  }: {
    answerSentences: string[];
    fallbackGist: string;
  },
): string {
  for (const sentence of answerSentences) {
    if (sentenceMatchesCitation(sentence, citation)) {
      return clipText(sentence, 180);
    }
  }
  return clipText(fallbackGist, 180);
}

export function normalizeExpertPanelSupportCitations(raw: unknown): ExpertPanelSupportCitation[] {
  if (!Array.isArray(raw)) return [];
  const normalized: ExpertPanelSupportCitation[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const citation: ExpertPanelSupportCitation = {
      doc_id: normalizeText((item as Record<string, unknown>).doc_id),
      logical_doc_id: normalizeText((item as Record<string, unknown>).logical_doc_id) || undefined,
      legal_reference: normalizeText((item as Record<string, unknown>).legal_reference) || undefined,
      source_label: normalizeText((item as Record<string, unknown>).source_label) || undefined,
      search_query: normalizeText((item as Record<string, unknown>).search_query) || undefined,
    };
    const identity = citationIdentity(citation);
    if (!identity || seen.has(identity)) continue;
    seen.add(identity);
    normalized.push(citation);
  }
  return normalized;
}

export function expertPanelSupportCitationsFromSnapshot(snapshot: unknown): ExpertPanelSupportCitation[] {
  if (!snapshot || typeof snapshot !== "object") return [];
  const payload = snapshot as Record<string, unknown>;
  const preferred =
    Array.isArray(payload.cachedCitations) && payload.cachedCitations.length > 0
      ? payload.cachedCitations
      : payload.fallbackCitations;
  return normalizeExpertPanelSupportCitations(preferred).slice(0, 5);
}

export function buildExpertPanelSearchSeed({
  message,
  assistantAnswer,
  supportCitations,
  normativeArticleRefs,
}: {
  message: string;
  assistantAnswer: string;
  supportCitations?: ExpertPanelSupportCitation[];
  normativeArticleRefs?: string[];
}): string {
  const cleanMessage = clipText(message, 180);
  const gist = pickAnswerGist(assistantAnswer);
  const answerSentences = splitSentences(assistantAnswer);
  const citations = normalizeExpertPanelSupportCitations(supportCitations).slice(0, 5);

  const parts: string[] = [];
  if (cleanMessage) {
    parts.push(`Consulta: ${cleanMessage}`);
  }
  if (gist) {
    parts.push(`Tesis: ${gist}`);
  }

  if (citations.length > 0) {
    parts.push("Normas citadas:");
    for (const citation of citations) {
      const label = clipText(citationLabel(citation), 96);
      const clause = pickCitationClause(citation, {
        answerSentences,
        fallbackGist: gist,
      });
      parts.push(clause ? `- ${label}: ${clause}` : `- ${label}`);
    }
  } else if (Array.isArray(normativeArticleRefs) && normativeArticleRefs.length > 0) {
    const refs = Array.from(
      new Set(
        normativeArticleRefs
          .map((value) => normalizeText(value))
          .filter(Boolean),
      ),
    ).slice(0, 5);
    if (refs.length > 0) {
      parts.push(`Referencias priorizadas: ${refs.join(", ")}`);
    }
  }

  return clipText(parts.join("\n"), 900);
}
