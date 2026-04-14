/**
 * Bogotá (America/Bogota, UTC-5) timezone utilities.
 *
 * All user-facing timestamps in the app display in Bogotá time.
 * Backend stores UTC; this module handles display conversion.
 */

/** IANA timezone for Colombia. */
export const TZ_CO = "America/Bogota" as const;

const _partsFmt = new Intl.DateTimeFormat("en-US", {
  timeZone: TZ_CO,
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  hour12: false,
  weekday: "short",
});

export interface BogotaParts {
  year: number;
  /** 0-indexed (0 = January). */
  month: number;
  day: number;
  /** 0-23. */
  hour: number;
  minute: number;
  /** 0 = Sunday, 1 = Monday, ... 6 = Saturday. */
  weekday: number;
}

const _WEEKDAY_MAP: Record<string, number> = {
  Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6,
};

/** Extract date/time components for a Date in Bogotá timezone. */
export function bogotaParts(date: Date): BogotaParts {
  const raw = Object.fromEntries(
    _partsFmt.formatToParts(date).map((p) => [p.type, p.value]),
  );
  return {
    year: Number(raw.year),
    month: Number(raw.month) - 1,
    day: Number(raw.day),
    hour: Number(raw.hour === "24" ? 0 : raw.hour),
    minute: Number(raw.minute),
    weekday: _WEEKDAY_MAP[raw.weekday] ?? 0,
  };
}

/**
 * Return a Date representing midnight in Bogotá for the given Bogotá-local
 * year/month/day.  Colombia is UTC-5 with no DST.
 */
export function bogotaMidnight(year: number, month: number, day: number): Date {
  return new Date(Date.UTC(year, month, day, 5, 0, 0));
}

/** Start of today in Bogotá, as a UTC Date (for API `since` queries). */
export function bogotaStartOfToday(now: Date = new Date()): Date {
  const p = bogotaParts(now);
  return bogotaMidnight(p.year, p.month, p.day);
}

/** Start of the current ISO week (Monday) in Bogotá. */
export function bogotaStartOfWeek(now: Date = new Date()): Date {
  const p = bogotaParts(now);
  const diff = p.weekday === 0 ? 6 : p.weekday - 1; // Monday = 0 offset
  const d = new Date(bogotaMidnight(p.year, p.month, p.day));
  d.setUTCDate(d.getUTCDate() - diff);
  return d;
}

/** Start of the current month in Bogotá. */
export function bogotaStartOfMonth(now: Date = new Date()): Date {
  const p = bogotaParts(now);
  return bogotaMidnight(p.year, p.month, 1);
}
