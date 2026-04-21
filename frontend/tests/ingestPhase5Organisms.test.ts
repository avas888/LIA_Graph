/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createIntakeDropZone,
  isAcceptedIntakeFile,
  type IntakeDropZoneResponse,
} from "@/shared/ui/organisms/intakeDropZone";
import { createRunProgressTimeline } from "@/shared/ui/organisms/runProgressTimeline";
import { createRunLogConsole } from "@/shared/ui/organisms/runLogConsole";
import { createRunTriggerCard } from "@/shared/ui/organisms/runTriggerCard";
import { createIngestController } from "@/features/ingest/ingestController";
import { renderIngestShellMarkup } from "@/app/ingest/ingestShell";

// ── Helpers ─────────────────────────────────────────────────────────

function makeFile(name: string, body = "hello", type = "text/plain"): File {
  return new File([body], name, { type });
}

interface EntryStub {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  file?: (cb: (f: File) => void) => void;
  createReader?: () => { readEntries: (cb: (entries: EntryStub[]) => void) => void };
}

function fileEntry(file: File): EntryStub {
  return {
    isFile: true,
    isDirectory: false,
    name: file.name,
    file: (cb) => cb(file),
  };
}

function dirEntry(name: string, children: EntryStub[]): EntryStub {
  let drained = false;
  return {
    isFile: false,
    isDirectory: true,
    name,
    createReader: () => ({
      readEntries: (cb) => {
        if (drained) {
          cb([]);
          return;
        }
        drained = true;
        cb(children);
      },
    }),
  };
}

function buildDragEvent(items: Array<{ entry: EntryStub | null; file?: File }>): Event {
  const event = new Event("drop", { bubbles: true, cancelable: true });
  const dt = {
    items: items.map((item) => ({
      webkitGetAsEntry: () => item.entry,
    })),
    files: items
      .filter((i) => !!i.file)
      .map((i) => i.file as File),
  };
  Object.defineProperty(event, "dataTransfer", { value: dt, writable: false });
  return event;
}

async function flushAsync(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
}

async function flushMicrotasks(): Promise<void> {
  for (let i = 0; i < 6; i += 1) {
    await Promise.resolve();
  }
}

// ── intakeDropZone ──────────────────────────────────────────────────

describe("organism: intakeDropZone", () => {
  it("(c) filters hidden files (start with dot)", () => {
    expect(isAcceptedIntakeFile(".DS_Store", ".DS_Store")).toBe(false);
    expect(isAcceptedIntakeFile("notes.txt", ".hidden/notes.txt")).toBe(false);
    expect(isAcceptedIntakeFile("ley.md", "carpeta/ley.md")).toBe(true);
  });

  it("(d) filters __MACOSX/ tree", () => {
    expect(isAcceptedIntakeFile("ley.md", "__MACOSX/ley.md")).toBe(false);
    expect(isAcceptedIntakeFile("ley.md", "nested/__MACOSX/ley.md")).toBe(false);
  });

  it("(e) filters unsupported extensions (.exe)", () => {
    expect(isAcceptedIntakeFile("virus.exe", "virus.exe")).toBe(false);
    expect(isAcceptedIntakeFile("a.png", "a.png")).toBe(false);
    expect(isAcceptedIntakeFile("a.pdf", "a.pdf")).toBe(true);
  });

  it("(a) accepts a single-file drop and calls onIntake", async () => {
    const onIntake = vi.fn(async () => ({
      ok: true,
      batch_id: "batch-1",
      summary: { received: 1, placed: 1, deduped: 0, rejected: 0 },
      files: [
        {
          filename: "ley.md",
          detected_topic: "tributario",
          topic_label: "Tributario",
          combined_confidence: 0.9,
          requires_review: false,
        },
      ],
    }));
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;

    const file = makeFile("ley.md", "# hi", "text/markdown");
    const event = buildDragEvent([{ entry: fileEntry(file) }]);
    zone.dispatchEvent(event);
    await flushAsync();

    expect(onIntake).toHaveBeenCalledTimes(1);
    const arg = onIntake.mock.calls[0]?.[0] as Array<{ filename: string; relativePath: string }>;
    expect(arg.length).toBe(1);
    expect(arg[0].filename).toBe("ley.md");
    document.body.removeChild(node);
  });

  it("(b) folder drop walks webkitGetAsEntry recursively", async () => {
    const f1 = makeFile("a.md");
    const f2 = makeFile("b.txt");
    const f3 = makeFile("c.json", "{}", "application/json");
    const tree = dirEntry("root", [
      fileEntry(f1),
      dirEntry("nested", [fileEntry(f2), fileEntry(f3)]),
    ]);

    const onIntake = vi.fn(async () => ({
      ok: true,
      batch_id: "batch-2",
      summary: { received: 3, placed: 3, deduped: 0, rejected: 0 },
      files: [],
    }));
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;

    zone.dispatchEvent(buildDragEvent([{ entry: tree }]));
    await flushAsync();

    expect(onIntake).toHaveBeenCalledTimes(1);
    const files = onIntake.mock.calls[0]?.[0] as Array<{ filename: string; relativePath: string }>;
    expect(files.map((f) => f.filename).sort()).toEqual(["a.md", "b.txt", "c.json"]);
    // Relative paths include the folder chain.
    const paths = files.map((f) => f.relativePath).sort();
    expect(paths).toContain("root/a.md");
    expect(paths).toContain("root/nested/b.txt");
    document.body.removeChild(node);
  });

  it("(f) drop fires onIntake with normalized file list (filtered)", async () => {
    const good = makeFile("ok.md");
    const exe = makeFile("bad.exe");
    const hidden = makeFile(".DS_Store");
    const tree = dirEntry("root", [fileEntry(good), fileEntry(exe), fileEntry(hidden)]);

    const onIntake = vi.fn(async () => ({
      ok: true,
      batch_id: "b",
      summary: { received: 1, placed: 1, deduped: 0, rejected: 0 },
      files: [],
    }));
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;

    zone.dispatchEvent(buildDragEvent([{ entry: tree }]));
    await flushAsync();

    expect(onIntake).toHaveBeenCalledTimes(1);
    const files = onIntake.mock.calls[0]?.[0] as Array<{ filename: string }>;
    expect(files.map((f) => f.filename)).toEqual(["ok.md"]);
    document.body.removeChild(node);
  });

  it("(g) Aprobar button is disabled until intake returns with placed > 0", async () => {
    let resolve: (v: IntakeDropZoneResponse) => void = () => undefined;
    const onIntake = vi.fn(
      () =>
        new Promise<IntakeDropZoneResponse>((res) => {
          resolve = res;
        }),
    );
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const approve = node.querySelector<HTMLButtonElement>(
      ".lia-intake-drop-zone__approve",
    )!;
    expect(approve.disabled).toBe(true);

    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;
    zone.dispatchEvent(buildDragEvent([{ entry: fileEntry(makeFile("a.md")) }]));
    await flushAsync();
    // Pending — still disabled.
    expect(approve.disabled).toBe(true);

    resolve({
      ok: true,
      batch_id: "b-ok",
      summary: { received: 1, placed: 1, deduped: 0, rejected: 0 },
      files: [{ filename: "a.md" }],
    });
    await flushAsync();
    expect(approve.disabled).toBe(false);
    document.body.removeChild(node);
  });

  it("(h) renders one intakeFileRow per returned file", async () => {
    const onIntake = vi.fn(async () => ({
      ok: true,
      batch_id: "bx",
      summary: { received: 2, placed: 2, deduped: 0, rejected: 0 },
      files: [
        { filename: "a.md", topic_label: "Renta", combined_confidence: 0.92 },
        { filename: "b.md", topic_label: "IVA", combined_confidence: 0.8 },
      ],
    }));
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;
    zone.dispatchEvent(
      buildDragEvent([
        { entry: fileEntry(makeFile("a.md")) },
        { entry: fileEntry(makeFile("b.md")) },
      ]),
    );
    await flushAsync();

    const rows = node.querySelectorAll(".lia-intake-file-row");
    expect(rows).toHaveLength(2);
    document.body.removeChild(node);
  });

  it("(p) low-confidence response surfaces requires_review marker in the row", async () => {
    const onIntake = vi.fn(async () => ({
      ok: true,
      batch_id: "b-rev",
      summary: { received: 1, placed: 1, deduped: 0, rejected: 0 },
      files: [
        {
          filename: "ley.md",
          topic_label: "Incierto",
          combined_confidence: 0.4,
          requires_review: true,
        },
      ],
    }));
    const node = createIntakeDropZone({ onIntake });
    document.body.appendChild(node);
    const zone = node.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;
    zone.dispatchEvent(buildDragEvent([{ entry: fileEntry(makeFile("ley.md")) }]));
    await flushAsync();

    const marker = node.querySelector(".lia-intake-file-row__review");
    expect(marker).toBeTruthy();
    expect(marker?.textContent).toContain("revisión");
    document.body.removeChild(node);
  });
});

// ── runProgressTimeline ─────────────────────────────────────────────

describe("organism: runProgressTimeline", () => {
  it("(i) renders all 6 stages on construction", () => {
    const { element } = createRunProgressTimeline();
    const items = element.querySelectorAll(".lia-run-progress-timeline__item");
    expect(items).toHaveLength(6);
    const names = Array.from(items).map((el) => el.getAttribute("data-stage"));
    expect(names).toEqual(["coerce", "audit", "chunk", "sink", "falkor", "embeddings"]);
  });

  it("(j) update() reflects stage status transitions", () => {
    const { element, update } = createRunProgressTimeline();
    update({
      stages: {
        coerce: { status: "done", counts: { docs: 3 } },
        audit: { status: "running" },
      },
    });
    const coerce = element.querySelector('[data-stage="coerce"] .lia-stage-progress-item')!;
    expect(coerce.className).toContain("lia-stage-progress-item--done");
    const audit = element.querySelector('[data-stage="audit"] .lia-stage-progress-item')!;
    expect(audit.className).toContain("lia-stage-progress-item--running");
    const chunk = element.querySelector('[data-stage="chunk"] .lia-stage-progress-item')!;
    expect(chunk.className).toContain("lia-stage-progress-item--pending");
  });

  it("(k) surfaces failed stage error in the DOM", () => {
    const { element, update } = createRunProgressTimeline();
    update({
      stages: {
        falkor: { status: "failed", error: "cypher BFS timeout" },
      },
    });
    const err = element.querySelector(
      '[data-stage="falkor"] .lia-stage-progress-item__error',
    );
    expect(err).toBeTruthy();
    expect(err?.textContent).toBe("cypher BFS timeout");
  });
});

// ── runLogConsole ───────────────────────────────────────────────────

describe("organism: runLogConsole", () => {
  it("(l) appends lines and scrolls to bottom", () => {
    const handle = createRunLogConsole({ initialLines: ["boot"] });
    document.body.appendChild(handle.element);
    const pre = handle.element.querySelector(".lia-log-tail-viewer__body") as HTMLPreElement;

    let scrollTop = 0;
    Object.defineProperty(pre, "scrollHeight", { configurable: true, get: () => 512 });
    Object.defineProperty(pre, "scrollTop", {
      configurable: true,
      get: () => scrollTop,
      set: (v: number) => {
        scrollTop = v;
      },
    });

    handle.appendLines(["line-a", "line-b"]);
    expect(pre.textContent).toBe("boot\nline-a\nline-b");
    expect(scrollTop).toBe(512);
    document.body.removeChild(handle.element);
  });

  it("(m) clear() empties the body", () => {
    const handle = createRunLogConsole({ initialLines: ["a", "b"] });
    handle.clear();
    const pre = handle.element.querySelector(".lia-log-tail-viewer__body");
    expect(pre?.textContent).toBe("");
  });
});

// ── controller wiring ───────────────────────────────────────────────

describe("ingestController — Phase 5 wiring", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let originalFetch: typeof fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    globalThis.fetch = originalFetch;
  });

  function mountShell(): { root: HTMLElement; cleanup: () => void } {
    const host = document.createElement("div");
    host.innerHTML = renderIngestShellMarkup();
    const root = host.querySelector<HTMLElement>("#lia-ingest-shell")!;
    document.body.appendChild(host);
    return {
      root,
      cleanup: () => {
        document.body.removeChild(host);
      },
    };
  }

  function jsonResponse(payload: unknown, status = 200): Response {
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  it("(n) _handleIntakeDrop posts base64 JSON to /api/ingest/intake", async () => {
    // Resolve initial overview/generations + the intake POST we care about.
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      const method = (init?.method || "GET").toUpperCase();
      if (url === "/api/ingest/intake" && method === "POST") {
        return jsonResponse({
          ok: true,
          batch_id: "b-123",
          summary: { received: 1, placed: 1, deduped: 0, rejected: 0 },
          files: [{ filename: "a.md" }],
        });
      }
      if (url.startsWith("/api/ingest/state")) {
        return jsonResponse({
          ok: true,
          corpus: {
            active_generation_id: "g1",
            activated_at: "",
            generated_at: "",
            documents: 0,
            chunks: 0,
            knowledge_class_counts: {},
            countries: [],
          },
          audit: {
            scanned: 0,
            include_corpus: 0,
            exclude_internal: 0,
            revision_candidates: 0,
            pending_revisions: 0,
            scanned_at: "",
            taxonomy_version: "",
          },
          graph: { ok: true, nodes: 0, edges: 0, validated_at: "" },
          inventory: {},
        });
      }
      if (url.startsWith("/api/ingest/generations")) {
        return jsonResponse({ ok: true, generations: [] });
      }
      return jsonResponse({ ok: true });
    });

    const { root, cleanup } = mountShell();
    const controller = createIngestController(root);
    await flushAsync();

    const zone = root.querySelector<HTMLElement>(".lia-intake-drop-zone__zone")!;
    zone.dispatchEvent(
      buildDragEvent([{ entry: fileEntry(makeFile("a.md", "hello")) }]),
    );
    await flushAsync();
    await flushAsync();

    const intakePost = fetchMock.mock.calls.find(
      ([url, init]) => url === "/api/ingest/intake" && (init as RequestInit | undefined)?.method === "POST",
    );
    expect(intakePost).toBeDefined();
    const body = JSON.parse(String((intakePost![1] as RequestInit).body));
    expect(body.files).toHaveLength(1);
    expect(body.files[0].filename).toBe("a.md");
    expect(typeof body.files[0].content_base64).toBe("string");
    expect(body.files[0].content_base64.length).toBeGreaterThan(0);
    // 'hello' -> 'aGVsbG8='
    expect(body.files[0].content_base64).toBe("aGVsbG8=");

    controller.destroy();
    cleanup();
  });

  it("(o) polling halts after status=done from the progress endpoint", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    let progressCalls = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      const method = (init?.method || "GET").toUpperCase();
      if (url.startsWith("/api/ingest/state")) {
        return jsonResponse({
          ok: true,
          corpus: {
            active_generation_id: "",
            activated_at: "",
            generated_at: "",
            documents: 0,
            chunks: 0,
            knowledge_class_counts: {},
            countries: [],
          },
          audit: {
            scanned: 0,
            include_corpus: 0,
            exclude_internal: 0,
            revision_candidates: 0,
            pending_revisions: 0,
            scanned_at: "",
            taxonomy_version: "",
          },
          graph: { ok: true, nodes: 0, edges: 0, validated_at: "" },
          inventory: {},
        });
      }
      if (url.startsWith("/api/ingest/generations")) {
        return jsonResponse({ ok: true, generations: [] });
      }
      if (url === "/api/ingest/run" && method === "POST") {
        return jsonResponse({ ok: true, job_id: "job-xyz" });
      }
      if (url.startsWith("/api/ingest/job/job-xyz/progress")) {
        progressCalls += 1;
        const status = progressCalls >= 2 ? "done" : "running";
        return jsonResponse({
          ok: true,
          job_id: "job-xyz",
          status,
          stages: {
            coerce: { status: "done" },
            audit: { status: "done" },
            chunk: { status: "done" },
            sink: { status: "done" },
            falkor: { status: "done" },
            embeddings: { status: status === "done" ? "done" : "running" },
          },
        });
      }
      if (url.startsWith("/api/ingest/job/job-xyz/log/tail")) {
        return jsonResponse({
          ok: true,
          lines: ["tick"],
          next_cursor: 10,
          total_lines: 10,
        });
      }
      return jsonResponse({ ok: true });
    });

    const { root, cleanup } = mountShell();
    const controller = createIngestController(root);
    await flushMicrotasks();

    // Kick a run by submitting the trigger form directly.
    const form = root.querySelector<HTMLFormElement>(".lia-run-trigger__form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushMicrotasks();

    // Drive the interval past the "done" transition.
    await vi.advanceTimersByTimeAsync(1600);
    await flushMicrotasks();
    await vi.advanceTimersByTimeAsync(1600);
    await flushMicrotasks();
    await vi.advanceTimersByTimeAsync(1600);
    await flushMicrotasks();
    const callsAfterDone = progressCalls;
    await vi.advanceTimersByTimeAsync(5000);
    await flushMicrotasks();
    expect(progressCalls).toBe(callsAfterDone);
    expect(progressCalls).toBeGreaterThanOrEqual(2);

    controller.destroy();
    cleanup();
  });

  it("(q) auto-embed checkbox default true sends auto_embed:true; toggling sends false", async () => {
    const onTrigger = vi.fn();
    const node = createRunTriggerCard({
      activeJobId: null,
      lastRunStatus: null,
      disabled: false,
      onTrigger,
    });
    document.body.appendChild(node);

    // Default submission → skip_embeddings NOT checked → autoEmbed true.
    const form = node.querySelector("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onTrigger).toHaveBeenCalledTimes(1);
    expect(onTrigger.mock.calls[0]?.[0]).toMatchObject({
      autoEmbed: true,
      autoPromote: false,
    });

    // Toggle skip_embeddings → autoEmbed:false.
    const skip = node.querySelector<HTMLInputElement>(
      "[name=skip_embeddings]",
    )!;
    skip.checked = true;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onTrigger.mock.calls[1]?.[0]).toMatchObject({ autoEmbed: false });

    // Toggle auto_promote → autoPromote:true.
    const promote = node.querySelector<HTMLInputElement>("[name=auto_promote]")!;
    promote.checked = true;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onTrigger.mock.calls[2]?.[0]).toMatchObject({
      autoEmbed: false,
      autoPromote: true,
    });

    document.body.removeChild(node);
  });
});
