const ARTICLE_REF_RE =
  /\b(?:art(?:[ií]culo)?\.?\s*(\d{1,4}(?:\s*[-–]\s*\d{1,4})?))\b/gi;

export function extractArticleRefs(text: string): string[] {
  if (!text) return [];
  const refs = new Set<string>();
  let match: RegExpExecArray | null;
  // biome-ignore lint/suspicious/noAssignInExpressions: standard regex loop
  while ((match = ARTICLE_REF_RE.exec(text)) !== null) {
    const num = (match[1] || "").replace(/\s+/g, "").trim();
    if (num) refs.add(`art_${num}`);
  }
  return Array.from(refs);
}
