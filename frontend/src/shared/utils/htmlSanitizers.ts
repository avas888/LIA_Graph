/**
 * Minimal HTML escaping utilities.
 *
 * Single concern: render user-ish text safely into strings of HTML. Kept
 * tiny on purpose — any logic beyond "escape chars / split paragraphs"
 * belongs in a dedicated formatter module.
 */

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

export function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/"/g, "&quot;");
}

/**
 * Splits a text block on blank lines and wraps each non-empty chunk in a
 * `<p>` with escaped content. CR/LF normalized to LF first.
 */
export function formatTextContent(text: string): string {
  return String(text ?? "")
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${escapeHtml(p)}</p>`)
    .join("");
}
