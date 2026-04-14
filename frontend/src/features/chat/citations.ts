// @ts-nocheck

const NORM_REFERENCE_RE =
  /\b((?:estatuto\s+tributario(?:\s*\(ET\))?|ET)(?:\s*[:,-]?\s*art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?)?|art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?(?:\s*(?:del?\s*)?(?:ET|estatuto\s+tributario|DUR\s*1625|decreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?))?|(?:decreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?(?:\s*\(DUR\s*1625\))?|DUR\s*1625(?:\s+de\s+2016)?)(?:\s*[:,-]?\s*(?:parte|t[íi]tulo|cap[íi]tulo|libro|secci[oó]n)[^.;\n]{0,120})?|ley\s*\d+(?:\s*(?:\/|de)\s*\d{4})?|decreto(?!\s+[uú]nico\s+reglamentario)\s*\d+(?:\s*(?:\/|de)\s*\d{4})?|circular\s*\d+(?:\s*(?:\/|de)\s*\d{4})?|resoluci[oó]n(?:\s*DIAN)?\s*\d+(?:\s*(?:\/|de)\s*\d{4})?|concepto(?:\s*DIAN)?\s*\d+(?:\s*(?:\/|de)\s*\d{4})?|(?:formulario|formato)\s*\d{2,6}(?![\.\-\/]\d)|f\.?\s*\d{2,6}(?![\.\-\/]\d))\b/gi;
const FORM_REFERENCE_SERIES_RE =
  /\b(formulario|formato|f)\.?\b([^\n]{0,90}?\d{2,6}(?:\s*(?:,|\/|o|u|y)\s*\d{2,6}){1,6})/gi;

function canonicalizeEtArticleNumber(value) {
  const clean = String(value || "").trim();
  if (!clean) return "";
  return /^\d+(?:\.\d+)+$/.test(clean) ? clean.replace(/\./g, "-") : clean;
}

function canonicalizeEtLocatorText(value) {
  const clean = String(value || "").trim();
  if (!clean) return "";
  return clean
    .replace(/\s+/g, " ")
    .replace(/[–—]/g, "-")
    .replace(/\b\d+(?:\.\d+)+\b/g, (match) => canonicalizeEtArticleNumber(match))
    .replace(/^arts?\.?\s*/i, "Artículos ")
    .replace(/^art[íi]culos?\s*/i, "Artículos ");
}

function canonicalizeEtLocatorKind(value) {
  const clean = String(value || "").trim().toLowerCase();
  if (!clean) return "";
  if (clean === "article" || clean === "articles") return "articles";
  return clean;
}

export function asCitationArray(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.filter((item) => item && typeof item === "object").map((item) => ({ ...item }));
}

export function boldGroupedFormReferences(text) {
  const raw = String(text || "");
  if (!raw) return "";
  FORM_REFERENCE_SERIES_RE.lastIndex = 0;
  const matches = [...raw.matchAll(FORM_REFERENCE_SERIES_RE)];
  if (matches.length === 0) return raw;

  let output = raw;
  matches.forEach((match) => {
    const block = String(match[0] || "");
    if (!block) return;
    const numbers = [...block.matchAll(/\d{1,6}/g)].map((item) => String(item[0] || ""));
    const uniqueNumbers = [...new Set(numbers.filter(Boolean))];
    if (uniqueNumbers.length < 2) return;
    let decorated = block;
    uniqueNumbers.forEach((number) => {
      const numberRegex = new RegExp(`\\b${number}\\b`, "g");
      decorated = decorated.replace(numberRegex, `**${number}**`);
    });
    if (decorated !== block) {
      output = output.replace(block, decorated);
    }
  });
  return output;
}

export function boldNormativeReferencesMarkdown(text) {
  const raw = String(text || "");
  if (!raw) return "";
  const withGroupedForms = boldGroupedFormReferences(raw);
  NORM_REFERENCE_RE.lastIndex = 0;
  return withGroupedForms.replace(NORM_REFERENCE_RE, (match, _ref, offset, source) => {
    const start = Number(offset) || 0;
    const before = source.slice(Math.max(0, start - 2), start);
    const after = source.slice(start + match.length, start + match.length + 2);
    if (before === "**" && after === "**") return match;
    return `**${match}**`;
  });
}

export function normalizeMentionReference(raw) {
  const clean = String(raw || "").replace(/\s+/g, " ").trim();
  if (!clean) return null;

  const etDirectMatch =
    /^(?:estatuto tributario(?:\s*\(ET\))?|ET)(?:\s*[:,-]?\s*(art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?))?$/i.exec(
      clean
    ) || /^(art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?)(?:\s*(?:del?\s*)?(?:ET|estatuto tributario))$/i.exec(clean);
  if (etDirectMatch) {
    const articleMatch = /art(?:[íi]culos?|s?)?\.?\s*(\d+(?:[.\-]\d+)*)(?:\s*(?:a|al|hasta|–)\s*(\d+(?:[.\-]\d+)*))?/i.exec(
      String(etDirectMatch[1] || clean)
    );
    if (articleMatch) {
      const start = canonicalizeEtArticleNumber(String(articleMatch[1] || "").trim());
      const end = canonicalizeEtArticleNumber(String(articleMatch[2] || "").trim());
      const locatorText = end ? `Artículos ${start} a ${end}` : `Artículos ${start}`;
      const sourceLabel = end ? `ET arts. ${start} a ${end}` : `ET art. ${start}`;
      return {
        reference_key: "et",
        reference_type: "et",
        source_label: sourceLabel,
        locator_text: locatorText,
        locator_kind: "articles",
        locator_start: start,
        locator_end: end || undefined,
      };
    }
    return {
      reference_key: "et",
      reference_type: "et",
      source_label: "Estatuto Tributario",
    };
  }

  const durMatch =
    /^(?:decreto único reglamentario 1625(?:\s*de\s*2016)?(?:\s*\(DUR\s*1625\))?|DUR\s*1625(?:\s*de\s*2016)?)(?:\s*[:,-]?\s*(.+))?$/i.exec(
      clean
    ) ||
    /^(art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?)(?:\s*(?:del?\s*)?(?:DUR\s*1625|decreto único reglamentario 1625(?:\s*de\s*2016)?))$/i.exec(
      clean
    );
  if (durMatch) {
    const articleMatch = /art(?:[íi]culos?|s?)?\.?\s*(\d+(?:[.\-]\d+)*)(?:\s*(?:a|al|hasta|–)\s*(\d+(?:[.\-]\d+)*))?/i.exec(
      String(durMatch[1] || clean)
    );
    if (articleMatch) {
      const start = String(articleMatch[1] || "").trim();
      const end = String(articleMatch[2] || "").trim();
      const locatorText = end ? `Artículos ${start} a ${end}` : `Artículos ${start}`;
      return {
        reference_key: "dur:1625:2016",
        reference_type: "dur",
        source_label: "DUR 1625 de 2016",
        locator_text: locatorText,
        locator_kind: "articles",
        locator_start: start,
        locator_end: end || undefined,
      };
    }
    const structureText = String(durMatch[1] || "").trim();
    return {
      reference_key: "dur:1625:2016",
      reference_type: "dur",
      source_label: "DUR 1625 de 2016",
      locator_text: structureText || undefined,
      locator_kind: structureText ? "structure" : undefined,
    };
  }

  const lawMatch = /^(ley|decreto|circular)\s*(\d{1,6})(?:\s*(?:\/|de)\s*(\d{4}))?$/i.exec(clean);
  if (lawMatch) {
    const refType = lawMatch[1].toLowerCase();
    const number = String(parseInt(lawMatch[2], 10));
    const year = lawMatch[3] ? String(lawMatch[3]) : "";
    const labelType = refType.charAt(0).toUpperCase() + refType.slice(1);
    return {
      reference_key: year ? `${refType}:${number}:${year}` : `${refType}:${number}`,
      reference_type: refType,
      source_label: year ? `${labelType} ${number} de ${year}` : `${labelType} ${number}`,
    };
  }

  const formMatch = /^(formulario|formato|f)\.?\s*(\d{2,6})(?![\.\-\/]\d)$/i.exec(clean);
  if (formMatch) {
    const alias = formMatch[1].toLowerCase();
    const number = String(parseInt(formMatch[2], 10));
    return {
      reference_key: `formulario:${number}`,
      reference_type: "formulario",
      source_label: alias === "formato" ? `Formato ${number}` : `Formulario ${number}`,
    };
  }

  const dianMatch = /^(resoluci[oó]n|concepto)(?:\s*(DIAN))?\s*(\d{1,10})(?:\s*(?:\/|de)\s*(\d{4}))?$/i.exec(clean);
  if (dianMatch) {
    const rawType = dianMatch[1].toLowerCase();
    const provider = dianMatch[2] ? "dian" : "";
    const number = String(parseInt(dianMatch[3], 10));
    const year = dianMatch[4] ? String(dianMatch[4]) : "";
    const normalizedType = provider ? `${rawType}_dian` : rawType;
    const labelType = rawType === "resolución" || rawType === "resolucion" ? "Resolución" : "Concepto";
    const providerLabel = provider ? " DIAN" : "";
    return {
      reference_key: year ? `${normalizedType}:${number}:${year}` : `${normalizedType}:${number}`,
      reference_type: normalizedType,
      source_label: `${labelType}${providerLabel} ${number}${year ? ` de ${year}` : ""}`,
    };
  }

  // Bare "artículo N" without explicit ET/Estatuto Tributario context —
  // in Colombian tax domain, bare article references default to ET.
  const bareArticleMatch = /^art(?:[íi]culos?|s?)?\.?\s*(\d+(?:[.\-]\d+)*)(?:\s*(?:a|al|hasta|–)\s*(\d+(?:[.\-]\d+)*))?$/i.exec(clean);
  if (bareArticleMatch) {
    const start = canonicalizeEtArticleNumber(String(bareArticleMatch[1] || "").trim());
    const end = canonicalizeEtArticleNumber(String(bareArticleMatch[2] || "").trim());
    const locatorText = end ? `Artículos ${start} a ${end}` : `Artículos ${start}`;
    const sourceLabel = end ? `ET arts. ${start} a ${end}` : `ET art. ${start}`;
    return {
      reference_key: "et",
      reference_type: "et",
      source_label: sourceLabel,
      locator_text: locatorText,
      locator_kind: "articles",
      locator_start: start,
      locator_end: end || undefined,
    };
  }

  return null;
}

export function extractGroupedFormReferences(text) {
  const value = String(text || "");
  if (!value) return [];
  FORM_REFERENCE_SERIES_RE.lastIndex = 0;
  const grouped = [...value.matchAll(FORM_REFERENCE_SERIES_RE)];
  if (grouped.length === 0) return [];

  const extracted = [];
  grouped.forEach((match) => {
    const alias = String(match[1] || "").toLowerCase();
    const chunk = String(match[2] || "");
    if (!alias || !chunk) return;
    const numbers = [...chunk.matchAll(/\d{1,6}/g)].map((item) => String(parseInt(item[0], 10)));
    const uniqueNumbers = [...new Set(numbers.filter(Boolean))];
    uniqueNumbers.forEach((number) => {
      extracted.push(`${alias} ${number}`);
    });
  });
  return extracted;
}

const _NORMOGRAMA_BASES = [
  "https://normograma.dian.gov.co/dian/compilacion/docs",
  "https://normograma.mintic.gov.co/mintic/compilacion/docs",
] as const;

// Prefer MinTIC mirror: honors fragment anchors (#807 etc.) unlike the DIAN host.
const _NORMOGRAMA_BASE = _NORMOGRAMA_BASES[1];

function _mirrorUrl(path: string): string {
  return `${_NORMOGRAMA_BASES[0]}/${path}`;
}

export interface NormogramaUrls {
  primary: string;
  fallback: string | null;
}

export function resolveExternalNormativeUrls(referenceKey, referenceType, locatorStart): NormogramaUrls | null {
  const key = String(referenceKey || "").trim().toLowerCase();
  if (!key) return null;

  if (key === "et") {
    const article = String(locatorStart || "").trim().replace(/\./g, "-");
    const path = article ? `estatuto_tributario.htm#${article}` : "estatuto_tributario.htm";
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  if (key === "dur:1625:2016" || key === "dur:1625") {
    const path = "decreto_1625_2016.htm";
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  const leyMatch = key.match(/^ley:(\d+):(\d{4})$/);
  if (leyMatch) {
    const path = `ley_${leyMatch[1]}_${leyMatch[2]}.htm`;
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  const decretoMatch = key.match(/^decreto:(\d+):(\d{4})$/);
  if (decretoMatch) {
    const num = decretoMatch[1].padStart(4, "0");
    const path = `decreto_${num}_${decretoMatch[2]}.htm`;
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  const resMatch = key.match(/^resoluci[oó]n(?:_dian)?:(\d+):(\d{4})$/);
  if (resMatch) {
    const path = `resolucion_dian_${resMatch[1].padStart(4, "0")}_${resMatch[2]}.htm`;
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  const conceptoMatch = key.match(/^concepto(?:_dian)?:(\d+):(\d{4})$/);
  if (conceptoMatch) {
    const path = `oficio_dian_${conceptoMatch[1]}_${conceptoMatch[2]}.htm#INICIO`;
    return { primary: `${_NORMOGRAMA_BASE}/${path}`, fallback: _mirrorUrl(path) };
  }

  return null;
}

export function resolveExternalNormativeUrl(referenceKey, referenceType, locatorStart) {
  const urls = resolveExternalNormativeUrls(referenceKey, referenceType, locatorStart);
  return urls ? urls.primary : null;
}

export function normogramaMirrorUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const s = String(url).trim();
  for (let i = 0; i < _NORMOGRAMA_BASES.length; i++) {
    if (s.startsWith(_NORMOGRAMA_BASES[i])) {
      const altIndex = (i + 1) % _NORMOGRAMA_BASES.length;
      return _NORMOGRAMA_BASES[altIndex] + s.slice(_NORMOGRAMA_BASES[i].length);
    }
  }
  return null;
}

export function buildMentionOnlyCitation(normalized) {
  const urls = resolveExternalNormativeUrls(
    normalized.reference_key,
    normalized.reference_type,
    normalized.locator_start,
  );
  const externalUrl = urls?.primary ?? null;
  const fallbackUrl = urls?.fallback ?? null;
  const isFormulario = normalized.reference_type === "formulario";
  const isEtWithLocator = normalized.reference_key === "et" && normalized.locator_start;
  let sourceProvider;
  if (isFormulario) {
    sourceProvider = "Guía de formulario";
  } else if (isEtWithLocator) {
    sourceProvider = "Corpus normativo";
  } else if (externalUrl) {
    sourceProvider = "Normograma DIAN";
  } else {
    sourceProvider = "Sin documento en corpus";
  }
  return {
    mention_only: true,
    reference_key: normalized.reference_key,
    reference_type: normalized.reference_type,
    source_label: normalized.source_label,
    legal_reference: normalized.source_label,
    locator_text: normalized.locator_text,
    locator_kind: normalized.locator_kind,
    locator_start: normalized.locator_start,
    locator_end: normalized.locator_end,
    source_tier: sourceProvider,
    source_provider: sourceProvider,
    usage_context: "Referencia normativa detectada en la respuesta de LIA.",
    external_url: externalUrl || undefined,
    external_fallback_url: fallbackUrl || undefined,
  };
}

export function extractMentionCitations(text) {
  const value = String(text || "");
  if (!value) return [];
  NORM_REFERENCE_RE.lastIndex = 0;
  const matches = [...value.matchAll(NORM_REFERENCE_RE)];
  const groupedFormReferences = extractGroupedFormReferences(value);
  if (matches.length === 0 && groupedFormReferences.length === 0) return [];

  const seen = new Set();
  const citations = [];
  matches.forEach((match) => {
    const normalized = normalizeMentionReference(match[1] || match[0]);
    if (!normalized) return;
    const mentionCitation = buildMentionOnlyCitation(normalized);
    const identity = [...citationIdentityCandidates(mentionCitation)][0] || `key:${normalized.reference_key}`;
    if (seen.has(identity)) return;
    seen.add(identity);
    citations.push(mentionCitation);
  });
  groupedFormReferences.forEach((reference) => {
    const normalized = normalizeMentionReference(reference);
    if (!normalized) return;
    const mentionCitation = buildMentionOnlyCitation(normalized);
    const identity = [...citationIdentityCandidates(mentionCitation)][0] || `key:${normalized.reference_key}`;
    if (seen.has(identity)) return;
    seen.add(identity);
    citations.push(mentionCitation);
  });
  return citations;
}

export function extractUserFormMentionCitations(text) {
  return extractMentionCitations(text).filter((citation) =>
    /^formulario:\d{2,6}[a-z]?$/i.test(String(citation?.reference_key || "").trim())
  );
}

export function logicalDocIdFromDocId(docId) {
  return String(docId || "").trim().replace(/_part_[0-9]+$/i, "");
}

function normalizeCitationIdentityComponent(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function citationLocatorIdentity(citation) {
  if (!citation || typeof citation !== "object") return "";
  const key = normalizeCitationIdentityComponent(citation.reference_key);
  if (!key) return "";
  const locatorKind = normalizeCitationIdentityComponent(
    key === "et" ? canonicalizeEtLocatorKind(citation.locator_kind) : citation.locator_kind
  );
  const locatorStart = normalizeCitationIdentityComponent(
    key === "et" && locatorKind === "articles" ? canonicalizeEtArticleNumber(citation.locator_start) : citation.locator_start
  );
  const locatorEnd = normalizeCitationIdentityComponent(
    key === "et" && locatorKind === "articles" ? canonicalizeEtArticleNumber(citation.locator_end) : citation.locator_end
  );
  const includeLocatorText = !(key === "et" && locatorKind === "articles" && (locatorStart || locatorEnd));
  const locatorText = normalizeCitationIdentityComponent(
    key === "et" && locatorKind === "articles" && includeLocatorText
      ? canonicalizeEtLocatorText(citation.locator_text)
      : includeLocatorText
        ? citation.locator_text
        : ""
  );
  if (!locatorKind && !locatorStart && !locatorEnd && !locatorText) return "";
  return `locator:${key}::${locatorKind}::${locatorStart}::${locatorEnd}::${locatorText}`;
}

export function citationIdentityCandidates(citation) {
  const candidates = new Set();
  if (!citation || typeof citation !== "object") return candidates;
  const locatorIdentity = citationLocatorIdentity(citation);
  if (locatorIdentity) {
    candidates.add(locatorIdentity);
    return candidates;
  }
  const logicalDocId = String(citation.logical_doc_id || logicalDocIdFromDocId(citation.doc_id || "")).trim().toLowerCase();
  if (logicalDocId) candidates.add(`logical:${logicalDocId}`);
  const key = String(citation.reference_key || "").trim().toLowerCase();
  if (key) candidates.add(`key:${key}`);
  const docId = String(citation.doc_id || "").trim().toLowerCase();
  if (docId) candidates.add(`doc:${docId}`);
  const ref = String(citation.legal_reference || citation.source_label || "").replace(/\s+/g, " ").trim().toLowerCase();
  if (ref) candidates.add(`ref:${ref}`);
  return candidates;
}

export function citationQualityScore(citation) {
  if (!citation || typeof citation !== "object") return 0;
  let score = 0;
  if (String(citation.doc_id || "").trim()) score += 8;
  if (String(citation.logical_doc_id || "").trim()) score += 4;
  if (String(citation.reference_key || "").trim()) score += 4;
  if (String(citation.usage_context || "").trim()) score += 2;
  if (!citation.mention_only && !citation.mention_detected) score += 1;
  return score;
}

export function mergeCitationPair(left, right) {
  const leftScore = citationQualityScore(left);
  const rightScore = citationQualityScore(right);
  const winner = rightScore > leftScore ? right : left;
  const loser = winner === left ? right : left;
  return {
    ...loser,
    ...winner,
    mention_only: Boolean(left?.mention_only) && Boolean(right?.mention_only),
    mention_detected:
      Boolean(left?.mention_detected) ||
      Boolean(right?.mention_detected) ||
      Boolean(left?.mention_only) ||
      Boolean(right?.mention_only),
  };
}

export function citationsShareIdentity(left, right) {
  const leftKeys = citationIdentityCandidates(left);
  const rightKeys = citationIdentityCandidates(right);
  if (leftKeys.size === 0 || rightKeys.size === 0) return false;
  for (const key of leftKeys) {
    if (rightKeys.has(key)) return true;
  }
  return false;
}

export function isPrimaryNormativeHelperCitation(citation) {
  if (!citation || typeof citation !== "object") return false;
  const knowledgeClass = String(citation.knowledge_class || "").trim().toLowerCase();
  if (knowledgeClass === "normative_base") return true;
  if (knowledgeClass) return false;
  const sourceType = String(citation.source_type || "").trim().toLowerCase();
  if (sourceType === "official_primary" || sourceType === "official_secondary" || sourceType === "norma") {
    return true;
  }
  const sourceTier = String(citation.source_tier || "").trim().toLowerCase();
  return sourceTier.startsWith("fuente primaria");
}

export function dedupeCitations(citations) {
  const rows = asCitationArray(citations);
  const deduped = [];
  rows.forEach((item) => {
    const matches = [];
    for (let index = 0; index < deduped.length; index += 1) {
      if (citationsShareIdentity(deduped[index], item)) {
        matches.push(index);
      }
    }
    if (matches.length === 0) {
      deduped.push(item);
      return;
    }
    let merged = item;
    matches.forEach((index) => {
      merged = mergeCitationPair(deduped[index], merged);
    });
    deduped[matches[0]] = merged;
    for (let cursor = matches.length - 1; cursor >= 1; cursor -= 1) {
      deduped.splice(matches[cursor], 1);
    }
  });
  const locatorKeys = new Set(
    deduped
      .filter((citation) => citationLocatorIdentity(citation))
      .map((citation) => String(citation.reference_key || "").trim().toLowerCase())
      .filter(Boolean)
  );
  if (locatorKeys.size === 0) {
    return deduped;
  }
  return deduped.filter((citation) => {
    const key = String(citation?.reference_key || "").trim().toLowerCase();
    if (!key || !locatorKeys.has(key)) return true;
    return Boolean(citationLocatorIdentity(citation));
  });
}

export function filterNormativeHelperBaseCitations(citations) {
  return dedupeCitations(asCitationArray(citations).filter((citation) => isPrimaryNormativeHelperCitation(citation)));
}

export function mergeCitations(primary, mentions) {
  const base = asCitationArray(primary);
  const mentionRows = asCitationArray(mentions);
  return pruneCitationsShadowedByMentionLocators(dedupeCitations([...base, ...mentionRows]));
}

export function filterCitedOnly(citations) {
  return asCitationArray(citations).filter((citation) =>
    citation.usage_context || citation.mention_only || citation.mention_detected
  );
}

function pruneCitationsShadowedByMentionLocators(citations) {
  const rows = asCitationArray(citations);
  const mentionedLocatorsByKey = new Map();
  rows.forEach((citation) => {
    const key = String(citation?.reference_key || "").trim().toLowerCase();
    const locatorIdentity = citationLocatorIdentity(citation);
    const mentioned = Boolean(citation?.mention_only) || Boolean(citation?.mention_detected);
    if (!key || !locatorIdentity || !mentioned) return;
    let locators = mentionedLocatorsByKey.get(key);
    if (!locators) {
      locators = new Set();
      mentionedLocatorsByKey.set(key, locators);
    }
    locators.add(locatorIdentity);
  });
  if (mentionedLocatorsByKey.size === 0) return rows;
  return rows.filter((citation) => {
    const key = String(citation?.reference_key || "").trim().toLowerCase();
    if (!key) return true;
    const mentionedLocators = mentionedLocatorsByKey.get(key);
    if (!mentionedLocators || mentionedLocators.size === 0) return true;
    const locatorIdentity = citationLocatorIdentity(citation);
    if (!locatorIdentity) return true;
    return mentionedLocators.has(locatorIdentity);
  });
}
// @ts-nocheck
