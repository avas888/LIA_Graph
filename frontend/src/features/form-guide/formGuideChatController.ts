import { postJson } from "@/shared/api/client";
import { renderMarkdown } from "@/content/markdown";
import type { FormGuideState } from "@/features/form-guide/formGuideState";
import {
  escapeHtml,
  sanitizeAppHref,
  uiText,
  type GuideChatMessageResponse,
} from "@/features/form-guide/formGuideTypes";

interface CreateFormGuideChatControllerOptions {
  state: FormGuideState;
}

export function createFormGuideChatController({ state }: CreateFormGuideChatControllerOptions) {
  function appendChatMessage(log: HTMLElement, role: string, text: string, extraClass = ""): void {
    const bubble = document.createElement("div");
    bubble.className = `form-guide-chat-bubble form-guide-chat-${role} ${extraClass}`.trim();

    const roleLabel = document.createElement("p");
    roleLabel.className = "chat-bubble-role";
    roleLabel.textContent = role === "user" ? "Tú" : "LIA";
    bubble.appendChild(roleLabel);

    const body = document.createElement("div");
    body.className = "chat-bubble-body";

    if (role === "assistant") {
      renderMarkdown(body, text);
    } else {
      body.textContent = uiText(text);
    }

    bubble.appendChild(body);
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    state.chatMessages.push({ role, text });
  }

  function appendChatHandoff(log: HTMLElement, href: string): void {
    const wrapper = document.createElement("div");
    wrapper.className = "form-guide-chat-handoff";

    const helper = document.createElement("p");
    helper.className = "form-guide-chat-handoff-helper";
    helper.textContent =
      "Esta pregunta se abrirá en el chat general y quedará como borrador para que la continúes allá.";

    const link = document.createElement("a");
    link.className = "secondary-btn";
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Continuar en el chat general";

    wrapper.append(helper, link);
    log.appendChild(wrapper);
    log.scrollTop = log.scrollHeight;
  }

  function appendThinkingIndicator(log: HTMLElement): HTMLElement {
    const wrapper = document.createElement("div");
    wrapper.className = "form-guide-chat-bubble form-guide-chat-thinking";
    wrapper.setAttribute("aria-live", "polite");
    wrapper.setAttribute("aria-label", "Pensando");
    wrapper.innerHTML = `
      <p class="chat-bubble-role">LIA</p>
      <div class="guide-chat-thinking-googly">
        <div class="guide-chat-thinking-core">
          <span class="lia-thinking-eye-pair">
            <span class="lia-thinking-eye">
              <span class="lia-thinking-eye-pupil"></span>
            </span>
            <span class="lia-thinking-eye">
              <span class="lia-thinking-eye-pupil"></span>
            </span>
          </span>
        </div>
      </div>
    `;
    log.appendChild(wrapper);
    log.scrollTop = log.scrollHeight;
    return wrapper;
  }

  function bindChatForm(): void {
    const form = document.getElementById("form-guide-chat-form") as HTMLFormElement | null;
    const input = document.getElementById("form-guide-chat-input") as HTMLTextAreaElement | null;
    const log = document.getElementById("form-guide-chat-log");

    if (!form || !input || !log) return;

    form.onsubmit = async (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) return;

      appendChatMessage(log, "user", message);
      input.value = "";
      input.disabled = true;

      const thinkingEl = appendThinkingIndicator(log);

      try {
        const { data: response } = await postJson<GuideChatMessageResponse>("/api/form-guides/chat", {
          reference_key: state.currentReferenceKey,
          profile: state.currentProfile,
          message,
          selected_field_id: state.selectedFieldId,
          selected_page: null,
          active_section: state.selectedSection,
        });

        thinkingEl.remove();

        if (response && response.ok) {
          const modeClass = response.answer_mode === "pedagogical" ? "" : "chat-refusal";
          appendChatMessage(log, "assistant", response.answer_markdown, modeClass);
          if (response.answer_mode === "out_of_scope_refusal") {
            const handoffUrl = sanitizeAppHref(response.grounding?.handoff_url);
            if (handoffUrl) {
              appendChatHandoff(log, handoffUrl);
            }
          }

          if (response.suggested_followups && response.suggested_followups.length > 0) {
            const followupsHtml = response.suggested_followups
              .map((followup) => `<button class="followup-btn" type="button">${escapeHtml(uiText(followup))}</button>`)
              .join("");
            const wrapper = document.createElement("div");
            wrapper.className = "chat-followups";
            wrapper.innerHTML = followupsHtml;
            wrapper.addEventListener("click", (clickEvent) => {
              const btn = (clickEvent.target as HTMLElement).closest(".followup-btn") as HTMLElement | null;
              if (!btn) return;
              input.value = btn.textContent || "";
              form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            });
            log.appendChild(wrapper);
          }
        } else {
          appendChatMessage(log, "assistant", "Error procesando tu pregunta. Intenta de nuevo.");
        }
      } catch {
        thinkingEl.remove();
        appendChatMessage(log, "assistant", "Error de conexión. Intenta de nuevo.");
      } finally {
        input.disabled = false;
        input.focus();
      }
    };
  }

  return {
    bindChatForm,
  };
}
