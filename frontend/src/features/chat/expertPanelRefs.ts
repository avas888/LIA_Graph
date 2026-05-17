// Capture both the article number AND optional code suffix (ET / CST) when
// adjacent (within ~12 chars before or after). Emits code-aware refs
// (`cst_art_N` / `et_art_N`) IN ADDITION to the bare `art_N` form so existing
// matchers in expertPanelSeed continue to work while the off-topic filter
// can distinguish labor (CST) from tax (ET) articles. See fix_v22_may.md §9 D6.

const ARTICLE_REF_RE =
  /(\b(?:CST|ET)\b[^.,;()\n]{0,12}?)?\bart(?:[ií]culo)?\.?\s*(\d{1,4}(?:\s*[-–]\s*\d{1,4})?)(\s*\b(?:CST|ET)\b)?/gi;

export function extractArticleRefs(text: string): string[] {
  if (!text) return [];
  const refs = new Set<string>();
  let match: RegExpExecArray | null;
  // biome-ignore lint/suspicious/noAssignInExpressions: standard regex loop
  while ((match = ARTICLE_REF_RE.exec(text)) !== null) {
    const num = (match[2] || "").replace(/\s+/g, "").trim();
    if (!num) continue;
    refs.add(`art_${num}`);
    const before = (match[1] || "").trim().toLowerCase();
    const after = (match[3] || "").trim().toLowerCase();
    const code =
      (after.includes("cst") || before.includes("cst"))
        ? "cst"
        : (after.includes("et") || before.includes("et"))
          ? "et"
          : "";
    if (code) refs.add(`${code}_art_${num}`);
  }
  return Array.from(refs);
}
