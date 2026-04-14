/**
 * Atom: centralized color dictionary.
 *
 * Single source of truth for programmatic color usage in TypeScript.
 * Mirrors the 3-tier structure in styles/tokens.css:
 *
 *   Tier 1 — primitives  : raw hex values (for canvas, SVG, non-CSS contexts)
 *   Tier 2 — semantic     : CSS variable references (for inline styles)
 *   Tier 3 — component    : domain-scoped CSS variable references
 *
 * IMPORTANT: when updating a primitive value here, update styles/tokens.css
 * to match (and vice-versa).  The CSS file is the rendering authority;
 * this dictionary is the programmatic authority.
 */

// ── Tier 1: Primitive Palette ─────────────────────────────────

export const palette = {
  neutral: {
    50:  "#f8fbff",
    100: "#edf4fd",
    150: "#e0eaf6",
    200: "#d1deeb",
    300: "#b6c8d8",
    400: "#8ea2b7",
    500: "#667a91",
    600: "#4c6178",
    700: "#32475f",
    800: "#203348",
    900: "#132235",
  },
  green: {
    50:  "#edf8ff",
    100: "#d7ebfb",
    200: "#b9dbf3",
    300: "#91c3e6",
    400: "#5aa3cf",
    500: "#2f84b2",
    600: "#226b93",
    700: "#1b5272",
    800: "#123a51",
  },
  navy: {
    50:  "#eef2f7",
    100: "#dde5f0",
    200: "#bccadc",
    400: "#607591",
    500: "#334760",
    600: "#26384f",
    700: "#1c2c40",
    800: "#131f31",
    900: "#0b1321",
  },
  success: {
    50:  "#eff9f4",
    100: "#d7eee1",
    200: "#afd9bf",
    400: "#50986d",
    600: "#2f6d4d",
    700: "#24533b",
  },
  actionGreen: {
    500: "#16a34a",
    600: "#15803d",
    700: "#166534",
  },
  amber: {
    50:  "#fff8ee",
    100: "#ffe7c8",
    200: "#efcca0",
    400: "#c98a4a",
    600: "#915c1e",
  },
  red: {
    50:  "#fff3f5",
    100: "#ffd9de",
    200: "#ebb3bb",
    400: "#be6170",
    600: "#8c3d49",
    700: "#6f2e38",
  },
  blue: {
    500: "#2d6fa4",
    600: "#245985",
    800: "#173d62",
  },
  white: "#ffffff",
  black: "#000000",
} as const;

// ── Tier 2: Semantic Tokens (CSS variable refs) ───────────────
//
// Use these for inline styles — they resolve at render time via
// the CSS custom properties defined in tokens.css.

export const semantic = {
  text: {
    primary:   "var(--text-primary)",
    secondary: "var(--text-secondary)",
    tertiary:  "var(--text-tertiary)",
    inverse:   "var(--text-inverse)",
  },
  surface: {
    base:        "var(--surface-base)",
    raised:      "var(--surface-raised)",
    tint:        "var(--surface-tint)",
    tintStrong:  "var(--surface-tint-strong)",
  },
  border: {
    default: "var(--border-default)",
    strong:  "var(--border-strong)",
    focus:   "var(--border-focus)",
  },
  interactive: {
    primary:      "var(--interactive-primary)",
    primaryHover: "var(--interactive-primary-hover)",
  },
  status: {
    success:     "var(--status-success)",
    successSoft: "var(--status-success-soft)",
    warning:     "var(--status-warning)",
    warningSoft: "var(--status-warning-soft)",
    error:       "var(--status-error)",
    errorSoft:   "var(--status-error-soft)",
  },
  chrome: {
    bg:    "var(--chrome-bg)",
    tabFg: "var(--chrome-tab-fg)",
  },
  field: {
    bg:          "var(--field-bg)",
    border:      "var(--field-border)",
    placeholder: "var(--field-placeholder)",
  },
  card: {
    bg:     "var(--card-bg)",
    hover:  "var(--card-hover-bg)",
    border: "var(--card-border)",
  },
  panel: {
    bg:       "var(--panel-bg)",
    bgStrong: "var(--panel-bg-strong)",
  },
  overlay: {
    scrim: "var(--overlay-scrim)",
  },
} as const;

// ── Tier 3: Component Tokens (CSS variable refs) ──────────────

export const component = {
  chat: {
    bubbleBorder:        "var(--chat-bubble-border)",
    bubbleUserBg:        "var(--chat-bubble-user-bg)",
    bubbleUserBorder:    "var(--chat-bubble-user-border)",
    bubbleAssistantBg:   "var(--chat-bubble-assistant-bg)",
    bubbleAssistantBorder: "var(--chat-bubble-assistant-border)",
    followupFg:          "var(--chat-followup-fg)",
    followupBg:          "var(--chat-followup-bg)",
    link:                "var(--chat-bubble-link)",
  },
  ops: {
    flashSuccessBg:     "var(--ops-flash-success-bg)",
    flashSuccessBorder: "var(--ops-flash-success-border)",
    flashSuccessFg:     "var(--ops-flash-success-fg)",
    flashErrorBg:       "var(--ops-flash-error-bg)",
    flashErrorBorder:   "var(--ops-flash-error-border)",
    flashErrorFg:       "var(--ops-flash-error-fg)",
    progressTrack:      "var(--ops-progress-track)",
    progressFill:       "var(--ops-progress-fill)",
  },
  toast: {
    bg:                    "var(--toast-bg)",
    border:                "var(--toast-border)",
    titleFg:               "var(--toast-title-fg)",
    messageFg:             "var(--toast-message-fg)",
    dismissFg:             "var(--toast-dismiss-fg)",
    infoBorder:            "var(--toast-info-border)",
    infoBg:                "var(--toast-info-bg)",
    successBorder:         "var(--toast-success-border)",
    successBg:             "var(--toast-success-bg)",
    errorBorder:           "var(--toast-error-border)",
    errorBg:               "var(--toast-error-bg)",
    cautionBorder:         "var(--toast-caution-border)",
    cautionBg:             "var(--toast-caution-bg)",
    actionPrimaryBg:       "var(--toast-action-primary-bg)",
    actionPrimaryBorder:   "var(--toast-action-primary-border)",
    actionPrimaryFg:       "var(--toast-action-primary-fg)",
    actionSecondaryBg:     "var(--toast-action-secondary-bg)",
    actionSecondaryBorder: "var(--toast-action-secondary-border)",
    actionSecondaryFg:     "var(--toast-action-secondary-fg)",
  },
  orchestration: {
    canvasBg:    "var(--orch-canvas-bg)",
    gridLine:    "var(--orch-grid-line)",
    edgeColor:   "var(--orch-edge-color)",
    lanePlatform: "var(--orch-lane-plataforma)",
    laneMobile:   "var(--orch-lane-mobile)",
  },
  admin: {
    tableBorder:      "var(--admin-table-border)",
    tableHeaderFg:    "var(--admin-table-header-fg)",
    tableRowHover:    "var(--admin-table-row-hover)",
    btnSuspendFg:     "var(--admin-btn-suspend-fg)",
    btnReactivateFg:  "var(--admin-btn-reactivate-fg)",
    btnDeleteFg:      "var(--admin-btn-delete-fg)",
    submitBg:         "var(--admin-submit-bg)",
    copyFg:           "var(--admin-copy-fg)",
  },
  topic: {
    rentaBg:       "var(--topic-renta-bg)",
    rentaFg:       "var(--topic-renta-fg)",
    ivaBg:         "var(--topic-iva-bg)",
    ivaFg:         "var(--topic-iva-fg)",
    niifBg:        "var(--topic-niif-bg)",
    niifFg:        "var(--topic-niif-fg)",
    laboralBg:     "var(--topic-laboral-bg)",
    laboralFg:     "var(--topic-laboral-fg)",
    facturacionBg: "var(--topic-facturacion-bg)",
    facturacionFg: "var(--topic-facturacion-fg)",
    retencionBg:   "var(--topic-retencion-bg)",
    retencionFg:   "var(--topic-retencion-fg)",
    calendarioBg:  "var(--topic-calendario-bg)",
    calendarioFg:  "var(--topic-calendario-fg)",
  },
  hero: {
    taglineFg: "var(--hero-tagline-fg)",
  },
  expert: {
    concordanciaFg: "var(--expert-concordancia-fg)",
    divergenciaFg:  "var(--expert-divergencia-fg)",
    complementarioFg: "var(--expert-complementario-fg)",
    individualFg:   "var(--expert-individual-fg)",
    linkFg:         "var(--expert-link-fg)",
    openFg:         "var(--expert-open-fg)",
  },
  corpus: {
    toneGreenFg:  "var(--corpus-tone-green-fg)",
    toneYellowFg: "var(--corpus-tone-yellow-fg)",
    toneRedFg:    "var(--corpus-tone-red-fg)",
    dotOk:        "var(--corpus-dot-ok)",
    dotError:     "var(--corpus-dot-error)",
    logBg:        "var(--corpus-log-bg)",
    logFg:        "var(--corpus-log-fg)",
  },
} as const;

// ── Convenience re-export ─────────────────────────────────────

export const colors = { palette, semantic, component } as const;
