/**
 * Binding-force taxonomy helpers shared by desktop `profileRenderer.ts`
 * and mobile `mobileNormativaPanel.ts`.
 *
 * Single concern: map raw `binding_force` + numeric rank from the backend
 * taxonomy (`normative_taxonomy.py`) into (a) a user-facing label and
 * (b) a tone keyword the chip/badge components consume.
 */

export function formatBindingForceText(raw: string): string {
  const value = String(raw || "").trim();
  if (!value) return "";
  return /^fuerza\s+vinculante\b/i.test(value) ? value : `Fuerza vinculante: ${value}`;
}

/**
 * Tone thresholds mirror the taxonomy tiers:
 *   - ≥ 700 → "success"  (ley, estatuto, precedente, decreto reglamentario,
 *                         jurisprudencia, resolución DIAN)
 *   - ≥ 300 → "warning"  (formulario, doctrina administrativa, circular)
 *   - >   0 → "neutral"  (generic support documents)
 *   -   0   → label-based fallback
 */
export function bindingForceTone(value: string, rank: number = 0): string {
  if (rank >= 700) return "success";
  if (rank >= 300) return "warning";
  if (rank > 0) return "neutral";

  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("alta")) return "success";
  if (normalized.includes("media")) return "warning";
  if (
    /(rango constitucional|ley o estatuto|compilaci[oó]n tributaria|decreto reglamentario|precedente judicial|resoluci[oó]n dian)/.test(
      normalized,
    )
  ) {
    return "success";
  }
  if (/(instrumento operativo|doctrina administrativa|circular administrativa)/.test(normalized)) {
    return "warning";
  }
  return "neutral";
}
