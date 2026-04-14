/**
 * Transcript detail modal — shows the full Q/A history for a conversation session.
 *
 * Reuses the existing `/api/conversation/:id` endpoint and the ratings-style
 * dialog pattern. Each turn pair gets its own copy button, plus a "copy all"
 * button in the header.
 */

import { getJson } from "@/shared/api/client";
import { getAuthContext } from "@/shared/auth/authContext";
import { renderMarkdown } from "@/content/markdown";
import { createIconButton } from "@/shared/ui/atoms/button";
import { icons } from "@/shared/ui/icons";
import { formatConversationCopyPayload } from "@/features/chat/transcriptController";
import type { I18nRuntime } from "@/shared/i18n";

interface SessionTurn {
  role: string;
  content: string;
  timestamp?: string;
}

interface SessionResponse {
  ok: boolean;
  session: {
    session_id: string;
    turns: SessionTurn[];
    topic?: string;
    created_at?: string;
  };
}

/** Pair of user question + assistant answer (one exchange). */
interface TurnPair {
  question: string;
  answer: string;
}

function extractPairs(turns: SessionTurn[]): TurnPair[] {
  const pairs: TurnPair[] = [];
  let pendingQuestion = "";
  for (const turn of turns) {
    if (turn.role === "user") {
      pendingQuestion = turn.content || "";
    } else if (turn.role === "assistant" && pendingQuestion) {
      pairs.push({ question: pendingQuestion, answer: turn.content || "" });
      pendingQuestion = "";
    }
  }
  return pairs;
}

function buildFullTranscript(pairs: TurnPair[], i18n: I18nRuntime): string {
  return pairs
    .map((p) => formatConversationCopyPayload(p.question, p.answer, i18n))
    .join("\n\n---\n\n");
}

function swapToCopied(btn: HTMLButtonElement): void {
  const iconEl = btn.querySelector("svg")?.parentElement ?? btn;
  iconEl.innerHTML = icons.checkCircle;
  btn.setAttribute("title", "Copiado!");
  setTimeout(() => {
    iconEl.innerHTML = icons.copy;
    btn.setAttribute("title", "Copiar");
  }, 1500);
}

export async function showTranscriptModal(
  dialog: HTMLDialogElement,
  sessionId: string,
  i18n: I18nRuntime,
  tenantId?: string,
): Promise<void> {
  // Show loader immediately
  dialog.innerHTML = `
    <div class="record-transcript">
      <header class="record-transcript-header">
        <span class="record-transcript-title">Conversacion</span>
        <span class="record-transcript-actions" id="transcript-actions-loading"></span>
      </header>
      <div class="record-transcript-body record-transcript-loading">Cargando...</div>
    </div>
  `;
  dialog.showModal();

  // Fetch session — prefer the conversation's own tenant_id over the auth context
  const ctx = getAuthContext();
  const tenantParam = tenantId || ctx.tenantId || "public";
  let data: SessionResponse;
  try {
    data = await getJson<SessionResponse>(
      `/api/conversation/${encodeURIComponent(sessionId)}?tenant_id=${encodeURIComponent(tenantParam)}`,
    );
  } catch {
    dialog.innerHTML = `
      <div class="record-transcript">
        <header class="record-transcript-header">
          <span class="record-transcript-title">Error</span>
          <span class="record-transcript-actions" id="transcript-actions-err"></span>
        </header>
        <div class="record-transcript-body">No se pudo cargar la conversacion.</div>
      </div>
    `;
    mountCloseButton(dialog, "#transcript-actions-err");
    return;
  }

  const session = data?.session;
  if (!session || !Array.isArray(session.turns) || session.turns.length === 0) {
    dialog.innerHTML = `
      <div class="record-transcript">
        <header class="record-transcript-header">
          <span class="record-transcript-title">Conversacion</span>
          <span class="record-transcript-actions" id="transcript-actions-empty"></span>
        </header>
        <div class="record-transcript-body">Sin turnos registrados.</div>
      </div>
    `;
    mountCloseButton(dialog, "#transcript-actions-empty");
    return;
  }

  const pairs = extractPairs(session.turns);

  // Build final dialog content
  dialog.innerHTML = `
    <div class="record-transcript">
      <header class="record-transcript-header">
        <span class="record-transcript-title">Conversacion</span>
        <span class="record-transcript-actions" id="transcript-actions"></span>
      </header>
      <div class="record-transcript-body" id="transcript-pairs"></div>
    </div>
  `;

  const actionsEl = dialog.querySelector<HTMLElement>("#transcript-actions")!;
  const pairsEl = dialog.querySelector<HTMLElement>("#transcript-pairs")!;

  // Copy-all button
  const copyAllBtn = createIconButton({
    iconHtml: icons.copy,
    tone: "ghost",
    className: "record-transcript-copy",
    attrs: { "aria-label": "Copiar toda la conversacion", title: "Copiar todo" },
    onClick: async () => {
      const text = buildFullTranscript(pairs, i18n);
      await navigator.clipboard.writeText(text);
      swapToCopied(copyAllBtn);
    },
  });
  actionsEl.appendChild(copyAllBtn);

  // Close button
  mountCloseButton(dialog, "#transcript-actions");

  // Render each Q/A pair
  for (let idx = 0; idx < pairs.length; idx++) {
    const pair = pairs[idx];
    const pairEl = document.createElement("div");
    pairEl.className = "record-transcript-pair";

    // Per-pair copy button
    const pairCopy = createIconButton({
      iconHtml: icons.copy,
      tone: "ghost",
      className: "record-transcript-pair-copy",
      attrs: { "aria-label": "Copiar este intercambio", title: "Copiar" },
      onClick: async () => {
        const text = formatConversationCopyPayload(pair.question, pair.answer, i18n);
        await navigator.clipboard.writeText(text);
        swapToCopied(pairCopy);
      },
    });

    pairEl.innerHTML = `
      <div class="record-transcript-question">
        <h3>Consulta</h3>
        <p></p>
      </div>
      <div class="record-transcript-answer">
        <h3>Respuesta</h3>
        <div class="record-transcript-answer-content bubble-content"></div>
      </div>
    `;

    // Set question text safely (no innerHTML injection)
    pairEl.querySelector<HTMLParagraphElement>(".record-transcript-question p")!.textContent = pair.question;

    // Render answer markdown
    const answerContent = pairEl.querySelector<HTMLElement>(".record-transcript-answer-content")!;
    void renderMarkdown(answerContent, pair.answer || "(sin respuesta)", { animate: false });

    // Attach copy button to the pair header
    pairEl.querySelector<HTMLElement>(".record-transcript-question")!.prepend(pairCopy);

    pairsEl.appendChild(pairEl);

    // Separator between pairs
    if (idx < pairs.length - 1) {
      const sep = document.createElement("hr");
      sep.className = "record-transcript-separator";
      pairsEl.appendChild(sep);
    }
  }
}

function mountCloseButton(dialog: HTMLDialogElement, actionsSelector: string): void {
  const actionsEl = dialog.querySelector<HTMLElement>(actionsSelector);
  if (!actionsEl) return;
  const closeBtn = createIconButton({
    iconHtml: icons.close,
    tone: "ghost",
    className: "record-transcript-close",
    attrs: { "aria-label": "Cerrar" },
    onClick: () => dialog.close(),
  });
  actionsEl.appendChild(closeBtn);
}
