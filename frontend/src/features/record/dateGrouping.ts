/**
 * Date grouping logic for conversation history.
 *
 * All date classification uses Bogotá time (America/Bogota).
 * Recent groups: Hoy, Ayer, Esta semana, Este mes.
 * Older: actual month names — "Febrero 2026", "Enero 2026", etc.
 */

import { bogotaParts, bogotaMidnight } from "@/shared/dates";

export interface DateGroup<T> {
  key: string;
  label: string;
  items: T[];
}

const MONTH_NAMES_ES: string[] = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

/**
 * Classify a date into a group key using Bogotá timezone.
 * Recent dates get fixed keys; older dates get "month:YYYY-MM" keys.
 */
function classifyDate(dateStr: string, now: Date): { key: string; label: string } {
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return { key: "unknown", label: "" };

  const nowParts = bogotaParts(now);
  const dateParts = bogotaParts(date);

  const todayMidnight = bogotaMidnight(nowParts.year, nowParts.month, nowParts.day);
  const targetMidnight = bogotaMidnight(dateParts.year, dateParts.month, dateParts.day);

  const diffMs = todayMidnight.getTime() - targetMidnight.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return { key: "today", label: "Hoy" };
  if (diffDays === 1) return { key: "yesterday", label: "Ayer" };
  if (diffDays < 7) return { key: "thisWeek", label: "Esta semana" };

  // Same month & year as now (in Bogotá)
  if (dateParts.month === nowParts.month && dateParts.year === nowParts.year) {
    return { key: "thisMonth", label: "Este mes" };
  }

  // Older: group by actual month + year
  const monthKey = `month:${dateParts.year}-${String(dateParts.month).padStart(2, "0")}`;
  const monthLabel = `${MONTH_NAMES_ES[dateParts.month]} ${dateParts.year}`;
  return { key: monthKey, label: monthLabel };
}

/**
 * Group items by date, using a date extractor function.
 * Returns groups in chronological order (most recent first).
 * Empty groups are omitted.
 *
 * Fixed groups come first (today → yesterday → thisWeek → thisMonth),
 * then month groups sorted by recency (most recent month first).
 */
export function groupByDate<T>(
  items: T[],
  getDate: (item: T) => string,
  now: Date = new Date(),
): DateGroup<T>[] {
  const fixedOrder = ["today", "yesterday", "thisWeek", "thisMonth"];
  const fixedBuckets = new Map<string, DateGroup<T>>();
  const monthBuckets = new Map<string, DateGroup<T>>();

  for (const key of fixedOrder) {
    fixedBuckets.set(key, { key, label: "", items: [] });
  }

  for (const item of items) {
    const { key, label } = classifyDate(getDate(item), now);

    if (fixedOrder.includes(key)) {
      const bucket = fixedBuckets.get(key)!;
      bucket.label = label;
      bucket.items.push(item);
    } else {
      if (!monthBuckets.has(key)) {
        monthBuckets.set(key, { key, label, items: [] });
      }
      monthBuckets.get(key)!.items.push(item);
    }
  }

  // Fixed groups first (in order), then month groups sorted by key descending (most recent first)
  const fixed = fixedOrder
    .map((k) => fixedBuckets.get(k)!)
    .filter((g) => g.items.length > 0);

  const months = Array.from(monthBuckets.values())
    .sort((a, b) => b.key.localeCompare(a.key));

  return [...fixed, ...months];
}
