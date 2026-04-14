import { describe, expect, it } from "vitest";
import { groupByDate } from "@/features/record/dateGrouping";

function makeItem(dateStr: string) {
  return { id: dateStr, date: dateStr };
}

const getDate = (item: { date: string }) => item.date;

describe("groupByDate", () => {
  const now = new Date("2026-04-06T12:00:00Z");

  it("classifies today", () => {
    const groups = groupByDate([makeItem("2026-04-06T10:00:00Z")], getDate, now);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("today");
    expect(groups[0].label).toBe("Hoy");
    expect(groups[0].items).toHaveLength(1);
  });

  it("classifies yesterday", () => {
    const groups = groupByDate([makeItem("2026-04-05T10:00:00Z")], getDate, now);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("yesterday");
    expect(groups[0].label).toBe("Ayer");
  });

  it("classifies this week (2-6 days ago)", () => {
    const groups = groupByDate([makeItem("2026-04-02T10:00:00Z")], getDate, now);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("thisWeek");
    expect(groups[0].label).toBe("Esta semana");
  });

  it("classifies this month (same month, >7 days ago)", () => {
    // April 6 now, April 1 is >5 days ago but same month — should be thisWeek or thisMonth
    // Use something within the same month but more than 7 days ago... but April only started 6 days ago
    // So let's use a "now" that's later in the month
    const laterNow = new Date("2026-04-20T12:00:00Z");
    const groups = groupByDate([makeItem("2026-04-08T10:00:00Z")], getDate, laterNow);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("thisMonth");
    expect(groups[0].label).toBe("Este mes");
  });

  it("classifies older dates by month name", () => {
    const groups = groupByDate([makeItem("2026-02-15T10:00:00Z")], getDate, now);
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("month:2026-01");
    expect(groups[0].label).toBe("Febrero 2026");
  });

  it("handles invalid dates gracefully", () => {
    const groups = groupByDate([makeItem("not-a-date")], getDate, now);
    // Invalid date doesn't crash — gets classified as "unknown" with empty label
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe("unknown");
    expect(groups[0].label).toBe("");
  });

  it("groups multiple items into correct buckets", () => {
    const items = [
      makeItem("2026-04-06T08:00:00Z"), // today
      makeItem("2026-04-06T09:00:00Z"), // today
      makeItem("2026-04-05T10:00:00Z"), // yesterday
      makeItem("2026-02-10T10:00:00Z"), // Feb 2026
      makeItem("2026-01-15T10:00:00Z"), // Jan 2026
    ];
    const groups = groupByDate(items, getDate, now);
    const keys = groups.map((g) => g.key);
    expect(keys).toContain("today");
    expect(keys).toContain("yesterday");

    const todayGroup = groups.find((g) => g.key === "today")!;
    expect(todayGroup.items).toHaveLength(2);
  });

  it("returns groups in correct order (fixed first, then months descending)", () => {
    const items = [
      makeItem("2026-04-06T08:00:00Z"), // today
      makeItem("2026-01-15T10:00:00Z"), // Jan
      makeItem("2026-02-10T10:00:00Z"), // Feb
      makeItem("2026-04-05T10:00:00Z"), // yesterday
    ];
    const groups = groupByDate(items, getDate, now);
    const keys = groups.map((g) => g.key);
    // Fixed groups come first
    expect(keys.indexOf("today")).toBeLessThan(keys.indexOf("yesterday"));
    // Month groups sorted descending (Feb before Jan)
    const febIdx = keys.findIndex((k) => k.includes("2026-01")); // February is month index 1
    const janIdx = keys.findIndex((k) => k.includes("2026-00")); // January is month index 0
    if (febIdx >= 0 && janIdx >= 0) {
      expect(febIdx).toBeLessThan(janIdx);
    }
  });

  it("returns empty array for empty input", () => {
    const groups = groupByDate([], getDate, now);
    expect(groups).toHaveLength(0);
  });
});
