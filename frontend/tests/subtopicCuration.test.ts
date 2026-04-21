/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/shared/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/shared/api/client")>(
    "@/shared/api/client",
  );
  return {
    ...actual,
    getJson: vi.fn(),
    postJson: vi.fn(),
  };
});

import { getJson, postJson } from "@/shared/api/client";
import { createSubtopicController } from "@/features/subtopics/subtopicController";
import { renderSubtopicShellMarkup } from "@/app/subtopics/subtopicShell";
import {
  createSubtopicCurationBoard,
} from "@/shared/ui/organisms/subtopicCurationBoard";
import { createSubtopicProposalCard } from "@/shared/ui/molecules/subtopicProposalCard";

const mockGetJson = vi.mocked(getJson);
const mockPostJson = vi.mocked(postJson);

function mountShell(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = renderSubtopicShellMarkup();
  document.body.replaceChildren(root);
  const shell = root.querySelector<HTMLElement>("#lia-subtopic-shell");
  if (!shell) throw new Error("shell not rendered");
  return shell;
}

function makeProposalRow(overrides: Record<string, unknown> = {}) {
  return {
    proposal_id: "laboral::001",
    parent_topic: "laboral",
    proposed_key: "aportes_parafiscales",
    proposed_label: "Aportes parafiscales",
    candidate_labels: ["aportes_parafiscales", "parafiscales_aportes"],
    evidence_doc_ids: ["sha256:aaa", "sha256:bbb"],
    evidence_count: 7,
    intra_similarity_min: 0.82,
    intra_similarity_max: 0.91,
    decided: false,
    latest_decision: null,
    ...overrides,
  };
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((r) => setTimeout(r, 0));
  await Promise.resolve();
  await new Promise((r) => setTimeout(r, 0));
}

beforeEach(() => {
  mockGetJson.mockReset();
  mockPostJson.mockReset();
  vi.restoreAllMocks();
});

afterEach(() => {
  document.body.replaceChildren();
});

// ---------------------------------------------------------------------------
// (a) board renders one column per parent with ≥1 proposal
// ---------------------------------------------------------------------------

describe("subtopic curation board — rendering", () => {
  it("(a) renders one column per parent_topic", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return {
          ok: true,
          exists: false,
          taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} },
        };
      }
      return {
        ok: true,
        source_path: "artifacts/subtopic_proposals_x.json",
        proposals: [
          makeProposalRow({ proposal_id: "laboral::001", parent_topic: "laboral" }),
          makeProposalRow({ proposal_id: "iva::001", parent_topic: "iva", proposed_key: "iva_exento", proposed_label: "IVA exento" }),
        ],
        decided_count: 0,
      };
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const columns = shell.querySelectorAll("[data-parent-topic]");
    expect(columns.length).toBeGreaterThanOrEqual(2);
  });

  it("(b) renders empty state when no proposals", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return { ok: true, source_path: null, proposals: [], decided_count: 0 };
    });
    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const empty = shell.querySelector(".lia-subtopic-board__empty");
    expect(empty).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// (c) accept button POSTs the correct payload
// ---------------------------------------------------------------------------

describe("subtopic curation controller — actions", () => {
  it("(c) accept sends the expected payload", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return {
        ok: true,
        source_path: "x",
        proposals: [makeProposalRow()],
        decided_count: 0,
      };
    });
    mockPostJson.mockResolvedValue({
      response: new Response(JSON.stringify({ ok: true, decision: {} }), { status: 200 }),
      data: { ok: true, decision: {} },
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const acceptBtn = shell.querySelector<HTMLButtonElement>(
      '[data-lia-component="subtopic-accept"]',
    );
    expect(acceptBtn).not.toBeNull();
    acceptBtn!.click();
    await flushUi();

    expect(mockPostJson).toHaveBeenCalledWith(
      "/api/subtopics/decision",
      expect.objectContaining({
        proposal_id: "laboral::001",
        action: "accept",
        final_key: "aportes_parafiscales",
        final_label: "Aportes parafiscales",
      }),
    );
  });

  it("(d) reject button prompts for reason before POST", async () => {
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("duplicate topic");
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return { ok: true, source_path: "x", proposals: [makeProposalRow()], decided_count: 0 };
    });
    mockPostJson.mockResolvedValue({
      response: new Response(JSON.stringify({ ok: true, decision: {} }), { status: 200 }),
      data: { ok: true, decision: {} },
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const rejectBtn = shell.querySelector<HTMLButtonElement>(
      '[data-lia-component="subtopic-reject"]',
    );
    rejectBtn!.click();
    await flushUi();

    expect(promptSpy).toHaveBeenCalled();
    expect(mockPostJson).toHaveBeenCalledWith(
      "/api/subtopics/decision",
      expect.objectContaining({
        action: "reject",
        reason: "duplicate topic",
      }),
    );
  });

  it("(e) merge opens a picker of siblings within same parent", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return {
        ok: true,
        source_path: "x",
        proposals: [
          makeProposalRow({ proposal_id: "laboral::001" }),
          makeProposalRow({ proposal_id: "laboral::002", proposed_key: "other", proposed_label: "Otra propuesta" }),
        ],
        decided_count: 0,
      };
    });
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("1");
    mockPostJson.mockResolvedValue({
      response: new Response(JSON.stringify({ ok: true, decision: {} }), { status: 200 }),
      data: { ok: true, decision: {} },
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const mergeBtn = shell.querySelector<HTMLButtonElement>(
      '[data-parent-topic="laboral"] [data-lia-component="subtopic-merge"]',
    );
    mergeBtn!.click();
    await flushUi();

    expect(promptSpy).toHaveBeenCalled();
    expect(mockPostJson).toHaveBeenCalledWith(
      "/api/subtopics/decision",
      expect.objectContaining({
        action: "merge",
        merged_into: "laboral::002",
      }),
    );
  });

  it("(f) rename inline-edits the label before POSTing", async () => {
    const promptSpy = vi.spyOn(window, "prompt");
    promptSpy.mockReturnValueOnce("Nuevo label renombrado"); // first prompt: label
    promptSpy.mockReturnValueOnce(""); // second prompt: key (blank → keep)
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return { ok: true, source_path: "x", proposals: [makeProposalRow()], decided_count: 0 };
    });
    mockPostJson.mockResolvedValue({
      response: new Response(JSON.stringify({ ok: true, decision: {} }), { status: 200 }),
      data: { ok: true, decision: {} },
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const renameBtn = shell.querySelector<HTMLButtonElement>(
      '[data-lia-component="subtopic-rename"]',
    );
    renameBtn!.click();
    await flushUi();

    expect(mockPostJson).toHaveBeenCalledWith(
      "/api/subtopics/decision",
      expect.objectContaining({
        action: "rename",
        final_label: "Nuevo label renombrado",
      }),
    );
  });
});

// ---------------------------------------------------------------------------
// (g) evidence list loads on card expand
// ---------------------------------------------------------------------------

describe("subtopic curation controller — evidence", () => {
  it("(g) expanding a card fetches evidence from the backend", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      if (url.includes("/evidence")) {
        return {
          ok: true,
          proposal_id: "laboral::001",
          parent_topic: "laboral",
          proposed_label: "Aportes parafiscales",
          evidence: [
            {
              doc_id: "sha256:aaa",
              filename: "doc_a.md",
              corpus_relative_path: "laboral/doc_a.md",
              autogenerar_label: "label a",
              autogenerar_rationale: "rationale a",
              parent_topic: "laboral",
            },
          ],
        };
      }
      return { ok: true, source_path: "x", proposals: [makeProposalRow()], decided_count: 0 };
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const evBtn = shell.querySelector<HTMLButtonElement>(
      '[data-lia-component="subtopic-evidence"]',
    );
    evBtn!.click();
    await flushUi();

    const evidenceList = shell.querySelector('[data-lia-component="subtopic-evidence-list"]');
    expect(evidenceList).not.toBeNull();
    expect(evidenceList?.textContent).toContain("doc_a.md");
  });
});

// ---------------------------------------------------------------------------
// (h) decided proposals visibly muted after submission
// ---------------------------------------------------------------------------

describe("subtopic proposal card — decided state", () => {
  it("(h) decided card renders with decided modifier + disabled buttons", () => {
    const host = document.createElement("div");
    host.appendChild(
      createSubtopicProposalCard({
        proposal: {
          proposalId: "x",
          parentTopic: "laboral",
          proposedKey: "k",
          proposedLabel: "Label",
          candidateLabels: [],
          evidenceCount: 1,
          intraSimilarityMin: 1,
          intraSimilarityMax: 1,
          decided: true,
          latestAction: "accept",
        },
        onAccept: () => undefined,
        onReject: () => undefined,
        onRenameRequest: () => undefined,
        onMergeRequest: () => undefined,
        onSplitRequest: () => undefined,
        onExpandEvidence: () => undefined,
      }),
    );
    const card = host.querySelector<HTMLElement>(".lia-subtopic-proposal");
    expect(card?.classList.contains("lia-subtopic-proposal--decided")).toBe(true);
    const acceptBtn = host.querySelector<HTMLButtonElement>(
      '[data-lia-component="subtopic-accept"]',
    );
    expect(acceptBtn?.disabled).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// (i) error toast on 5xx
// ---------------------------------------------------------------------------

describe("subtopic curation controller — error handling", () => {
  it("(i) surfaces a toast when the proposals endpoint fails", async () => {
    mockGetJson.mockRejectedValue(new Error("server exploded"));

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const toast = document.querySelector(".lia-subtopic-toast--error");
    expect(toast).not.toBeNull();
    expect(toast?.textContent).toContain("server exploded");
  });
});

// ---------------------------------------------------------------------------
// (j) controller.destroy tears down DOM state
// ---------------------------------------------------------------------------

describe("subtopic curation controller — lifecycle", () => {
  it("(j) destroy clears slot contents and in-flight state", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return { ok: true, exists: false, taxonomy: { version: null, generated_from: null, generated_at: null, subtopics: {} } };
      }
      return { ok: true, source_path: "x", proposals: [makeProposalRow()], decided_count: 0 };
    });
    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const boardSlot = shell.querySelector<HTMLElement>('[data-slot="curation-board"]');
    expect(boardSlot?.children.length).toBeGreaterThan(0);

    controller.destroy();
    expect(boardSlot?.children.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// (k) taxonomy sidebar refreshes after each decision
// ---------------------------------------------------------------------------

describe("subtopic curation board — sidebar", () => {
  it("(k) taxonomy sidebar lists curated subtopics from the API", async () => {
    mockGetJson.mockImplementation(async (url: string) => {
      if (url.includes("/taxonomy")) {
        return {
          ok: true,
          exists: true,
          taxonomy: {
            version: "2026-04-21-v1",
            generated_from: "x",
            generated_at: "2026-04-21T00:00:00Z",
            subtopics: {
              laboral: [
                {
                  key: "aportes_parafiscales",
                  label: "Aportes parafiscales",
                  aliases: [],
                  evidence_count: 5,
                  curated_at: "2026-04-21T00:00:00Z",
                  curator: "admin@lia.dev",
                },
              ],
            },
          },
        };
      }
      return { ok: true, source_path: "x", proposals: [], decided_count: 0 };
    });

    const shell = mountShell();
    const controller = createSubtopicController(shell);
    await controller.refresh();
    await flushUi();

    const sidebar = shell.querySelector('[data-lia-component="subtopic-taxonomy-sidebar"]');
    expect(sidebar).not.toBeNull();
    expect(sidebar?.textContent).toContain("Aportes parafiscales");
    expect(sidebar?.textContent).toContain("laboral");
  });
});

// ---------------------------------------------------------------------------
// (l) empty-state pure organism render
// ---------------------------------------------------------------------------

describe("subtopic curation board — organism direct", () => {
  it("(l) organism renders column per parent when proposals present", () => {
    const host = document.createElement("div");
    host.appendChild(
      createSubtopicCurationBoard({
        proposals: [
          {
            proposalId: "laboral::001",
            parentTopic: "laboral",
            proposedKey: "x",
            proposedLabel: "X",
            candidateLabels: ["x"],
            evidenceCount: 1,
            intraSimilarityMin: 1,
            intraSimilarityMax: 1,
            decided: false,
            latestAction: null,
          },
        ],
        currentTaxonomy: {},
        evidenceByProposalId: new Map(),
        evidenceLoadingIds: new Set(),
        expandedProposalIds: new Set(),
        onAccept: () => undefined,
        onReject: () => undefined,
        onRenameRequest: () => undefined,
        onMergeRequest: () => undefined,
        onSplitRequest: () => undefined,
        onExpandEvidence: () => undefined,
      }),
    );
    expect(host.querySelector('[data-parent-topic="laboral"]')).not.toBeNull();
  });
});
