import { createChip, type LiaChipTone } from "@/shared/ui/atoms/chip";

/**
 * fixplan_v3 §0.4 — the 11-state vigencia taxonomy. Each state has a chip
 * variant rendered to the right of a citation in the chat surface (Fix 1D).
 *
 * V is a no-op (the default vigente state has no chip).
 */
export type VigenciaState =
  | "V"
  | "VM"
  | "DE"
  | "DT"
  | "SP"
  | "IE"
  | "EC"
  | "VC"
  | "VL"
  | "DI"
  | "RV";

export interface VigenciaChipOptions {
  /** Required: the canonical state code (one of the 11 from §0.4). */
  state: VigenciaState;
  /** Optional: the source norm_id that caused the state transition. */
  sourceNormId?: string | null;
  /** Optional: the source norm's display label (rendered in tooltip). */
  sourceLabel?: string | null;
  /** Optional: state_from / fecha de efectos for chips that show a date. */
  stateFrom?: string | null;
  /** Optional: state_until — used by VL/DI countdowns. */
  stateUntil?: string | null;
  /** Optional: literal Court text for EC/VC (rendered on hover/expand). */
  interpretiveConstraintText?: string | null;
  /** Optional: rige_desde for VL/DI variants. */
  rigeDesde?: string | null;
  /** Optional: revives_text_version for RV. */
  revivesTextVersion?: string | null;
  /** Optional: triggering sentencia for RV. */
  revivedTriggerNormId?: string | null;
  /** Optional CSS class extension. */
  className?: string;
}

interface VariantSpec {
  tone: LiaChipTone;
  variantClass: string; // e.g. "lia-vigencia-chip--di"
  label: (opts: VigenciaChipOptions) => string;
  ariaLabel: (opts: VigenciaChipOptions) => string;
  showsConstraint: boolean;
}

const VARIANTS: Record<VigenciaState, VariantSpec | null> = {
  V: null, // no chip — vigente sin modificaciones
  VM: {
    tone: "info",
    variantClass: "lia-vigencia-chip--vm",
    label: (o) => `modificada por ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    ariaLabel: (o) =>
      `Vigente con modificaciones — modificada por ${shortLabel(
        o.sourceLabel || o.sourceNormId,
      )}`,
    showsConstraint: false,
  },
  DE: {
    tone: "error",
    variantClass: "lia-vigencia-chip--de",
    label: (o) =>
      `derogada por ${shortLabel(o.sourceLabel || o.sourceNormId)}${
        o.stateFrom ? ` desde ${o.stateFrom}` : ""
      }`,
    ariaLabel: (o) =>
      `Derogada expresa — ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    showsConstraint: false,
  },
  DT: {
    tone: "warning",
    variantClass: "lia-vigencia-chip--dt",
    label: () => "derogada tácitamente — verificar",
    ariaLabel: () =>
      "Derogada tácita — requiere verificación de pronunciamiento oficial",
    showsConstraint: false,
  },
  SP: {
    tone: "warning",
    variantClass: "lia-vigencia-chip--sp",
    label: (o) =>
      `suspendida por ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    ariaLabel: (o) =>
      `Suspensión provisional — ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    showsConstraint: false,
  },
  IE: {
    tone: "error",
    variantClass: "lia-vigencia-chip--ie",
    label: (o) =>
      `inexequible — ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    ariaLabel: (o) =>
      `Inexequible — declarado por ${shortLabel(o.sourceLabel || o.sourceNormId)}`,
    showsConstraint: false,
  },
  EC: {
    tone: "info",
    variantClass: "lia-vigencia-chip--ec",
    label: () => "exequibilidad condicionada — ver condicionamiento",
    ariaLabel: (o) =>
      `Exequibilidad condicionada — ${
        o.interpretiveConstraintText || "ver condicionamiento literal"
      }`,
    showsConstraint: true,
  },
  VC: {
    tone: "info",
    variantClass: "lia-vigencia-chip--vc",
    label: () => "vigente con modulación — ver detalle",
    ariaLabel: (o) =>
      `Vigente condicionada — ${
        o.interpretiveConstraintText || "modulación doctrinaria"
      }`,
    showsConstraint: true,
  },
  VL: {
    tone: "neutral",
    variantClass: "lia-vigencia-chip--vl",
    label: (o) =>
      `vacatio legis — rige desde ${o.rigeDesde || "fecha futura"}`,
    ariaLabel: (o) =>
      `Vacatio legis — entra en vigor el ${o.rigeDesde || "fecha futura"}`,
    showsConstraint: false,
  },
  DI: {
    tone: "warning",
    variantClass: "lia-vigencia-chip--di",
    label: (o) =>
      `exequibilidad diferida — vence ${o.rigeDesde || o.stateUntil || "?"}`,
    ariaLabel: (o) =>
      `Exequibilidad diferida — plazo Congreso vence ${
        o.rigeDesde || o.stateUntil || "fecha pendiente"
      }`,
    showsConstraint: false,
  },
  RV: {
    tone: "success",
    variantClass: "lia-vigencia-chip--rv",
    label: (o) =>
      `revivida tras ${shortLabel(o.revivedTriggerNormId || o.sourceNormId)}`,
    ariaLabel: (o) =>
      `Revivida — texto restaurado tras inexequibilidad de ${shortLabel(
        o.revivedTriggerNormId || o.sourceNormId,
      )}${o.revivesTextVersion ? ` (${o.revivesTextVersion})` : ""}`,
    showsConstraint: false,
  },
};


/**
 * Atom: chip representing the vigencia state of a citation in the chat
 * surface. Returns `null` for state="V" (the default vigente case has no
 * chip — keeps the cited norm visually quiet).
 */
export function createVigenciaChip(
  opts: VigenciaChipOptions,
): HTMLSpanElement | null {
  const variant = VARIANTS[opts.state];
  if (variant === null) return null;

  const chip = createChip({
    label: variant.label(opts),
    tone: variant.tone,
    emphasis: "soft",
    className: ["lia-vigencia-chip", variant.variantClass, opts.className || ""]
      .filter(Boolean)
      .join(" "),
    dataComponent: "vigencia-chip",
  });
  chip.setAttribute("data-vigencia-state", opts.state);
  if (opts.sourceNormId) {
    chip.setAttribute("data-source-norm-id", opts.sourceNormId);
  }
  chip.setAttribute("aria-label", variant.ariaLabel(opts));
  if (variant.showsConstraint && opts.interpretiveConstraintText) {
    // Stored as a data attribute so the molecule can pop it on hover/expand
    // without a separate fetch.
    chip.setAttribute(
      "data-interpretive-constraint",
      opts.interpretiveConstraintText,
    );
    chip.setAttribute("title", opts.interpretiveConstraintText);
  }
  return chip;
}


/**
 * Returns the chip variant + tone for a given state — useful for tests and
 * for higher-level molecules that need the colour without rendering the chip.
 */
export function getVigenciaVariantTone(
  state: VigenciaState,
): LiaChipTone | null {
  return VARIANTS[state]?.tone ?? null;
}


function shortLabel(value: string | null | undefined): string {
  if (!value) return "fuente";
  // Compact `ley.2277.2022.art.96` → "Ley 2277/2022 Art. 96"
  if (value.startsWith("ley.")) {
    const parts = value.split(".");
    if (parts.length >= 3) {
      const base = `Ley ${parts[1]}/${parts[2]}`;
      if (parts.length > 3 && parts[3] === "art") {
        return `${base} Art. ${parts.slice(4).join(".")}`;
      }
      return base;
    }
  }
  if (value.startsWith("decreto.")) {
    const parts = value.split(".");
    if (parts.length >= 3) {
      return `Decreto ${parts[1]}/${parts[2]}`;
    }
  }
  if (value.startsWith("sent.cc.")) {
    return value.slice("sent.cc.".length);
  }
  if (value.startsWith("sent.ce.")) {
    return `CE ${value.slice("sent.ce.".length)}`;
  }
  if (value.startsWith("auto.ce.")) {
    return `Auto CE ${value.slice("auto.ce.".length)}`;
  }
  if (value.startsWith("concepto.dian.")) {
    return `Concepto DIAN ${value.slice("concepto.dian.".length)}`;
  }
  return value;
}
