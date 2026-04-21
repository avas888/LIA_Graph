import { createPipelineFlow } from "@/shared/ui/molecules/pipelineFlow";
import { createRunStatusBadge, type RunStatus } from "@/shared/ui/molecules/runStatusBadge";

export interface RunTriggerOptions {
  /** Currently dispatched job id, if any. */
  activeJobId: string | null;
  /** Most recent run status surfaced to the user. */
  lastRunStatus: RunStatus | null;
  /** Disable trigger while a job is running. */
  disabled: boolean;
  onTrigger: (params: { suinScope: string; supabaseTarget: "wip" | "production" }) => void;
}

export function createRunTriggerCard(opts: RunTriggerOptions): HTMLElement {
  const { activeJobId, lastRunStatus, disabled, onTrigger } = opts;

  const root = document.createElement("section");
  root.className = "lia-run-trigger";
  root.setAttribute("data-lia-component", "run-trigger-card");

  const header = document.createElement("header");
  header.className = "lia-run-trigger__header";

  const title = document.createElement("h2");
  title.className = "lia-run-trigger__title";
  title.textContent = "Iniciar nueva ingesta";
  header.appendChild(title);

  const subtitle = document.createElement("p");
  subtitle.className = "lia-run-trigger__subtitle";
  subtitle.textContent =
    "Ejecuta make phase2-graph-artifacts-supabase contra knowledge_base/. Por defecto escribe a WIP (Supabase local + FalkorDB local). Cuando WIP esté validado, promueve a Cloud desde la pestaña Promoción.";
  header.appendChild(subtitle);

  root.appendChild(header);

  root.appendChild(createPipelineFlow({ activeStage: "wip" }));

  // Form
  const form = document.createElement("form");
  form.className = "lia-run-trigger__form";
  form.setAttribute("novalidate", "");

  const targetField = _renderRadioField({
    name: "supabase_target",
    legend: "Destino Supabase",
    options: [
      {
        value: "wip",
        label: "WIP (local)",
        hint: "Supabase docker + FalkorDB docker — ciclo seguro",
        defaultChecked: true,
      },
      {
        value: "production",
        label: "Producción (cloud)",
        hint: "Supabase cloud + FalkorDB cloud — afecta runtime servido",
      },
    ],
  });
  form.appendChild(targetField);

  const suinField = _renderTextField({
    name: "suin_scope",
    label: "Scope SUIN-Juriscol",
    placeholder: "vacío para omitir, ej: et",
    hint: "Cuando es vacío, sólo se reingiere el corpus base. Pasa el scope (et, tributario, laboral, jurisprudencia) para incluir SUIN.",
  });
  form.appendChild(suinField);

  // Submit row
  const submitRow = document.createElement("div");
  submitRow.className = "lia-run-trigger__submit-row";

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "lia-button lia-button--primary lia-run-trigger__submit";
  submit.textContent = activeJobId ? "Ejecutando…" : "Iniciar ingesta";
  submit.disabled = disabled;
  submitRow.appendChild(submit);

  if (lastRunStatus) {
    submitRow.appendChild(createRunStatusBadge({ status: lastRunStatus }));
  }

  if (activeJobId) {
    const idEl = document.createElement("code");
    idEl.className = "lia-run-trigger__job-id";
    idEl.textContent = activeJobId;
    submitRow.appendChild(idEl);
  }

  form.appendChild(submitRow);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (disabled) return;
    const fd = new FormData(form);
    const supabaseTarget = (fd.get("supabase_target") as string) || "wip";
    const suinScope = String(fd.get("suin_scope") || "").trim();
    onTrigger({
      suinScope,
      supabaseTarget: supabaseTarget === "production" ? "production" : "wip",
    });
  });

  root.appendChild(form);

  return root;
}

interface RadioOption {
  value: string;
  label: string;
  hint?: string;
  defaultChecked?: boolean;
}

function _renderRadioField(opts: {
  name: string;
  legend: string;
  options: RadioOption[];
}): HTMLFieldSetElement {
  const fs = document.createElement("fieldset");
  fs.className = "lia-run-trigger__field lia-run-trigger__field--radio";

  const legend = document.createElement("legend");
  legend.className = "lia-run-trigger__legend";
  legend.textContent = opts.legend;
  fs.appendChild(legend);

  opts.options.forEach((option) => {
    const wrap = document.createElement("label");
    wrap.className = "lia-run-trigger__radio-row";

    const input = document.createElement("input");
    input.type = "radio";
    input.name = opts.name;
    input.value = option.value;
    if (option.defaultChecked) input.defaultChecked = true;
    wrap.appendChild(input);

    const text = document.createElement("span");
    text.className = "lia-run-trigger__radio-text";
    const labelLine = document.createElement("span");
    labelLine.className = "lia-run-trigger__radio-label";
    labelLine.textContent = option.label;
    text.appendChild(labelLine);
    if (option.hint) {
      const hintEl = document.createElement("span");
      hintEl.className = "lia-run-trigger__radio-hint";
      hintEl.textContent = option.hint;
      text.appendChild(hintEl);
    }
    wrap.appendChild(text);

    fs.appendChild(wrap);
  });

  return fs;
}

function _renderTextField(opts: {
  name: string;
  label: string;
  placeholder?: string;
  hint?: string;
}): HTMLDivElement {
  const wrap = document.createElement("div");
  wrap.className = "lia-run-trigger__field lia-run-trigger__field--text";

  const labelEl = document.createElement("label");
  labelEl.className = "lia-run-trigger__label";
  labelEl.htmlFor = `lia-run-trigger-${opts.name}`;
  labelEl.textContent = opts.label;
  wrap.appendChild(labelEl);

  const input = document.createElement("input");
  input.type = "text";
  input.id = `lia-run-trigger-${opts.name}`;
  input.name = opts.name;
  input.className = "lia-input lia-run-trigger__input";
  input.autocomplete = "off";
  input.spellcheck = false;
  if (opts.placeholder) input.placeholder = opts.placeholder;
  wrap.appendChild(input);

  if (opts.hint) {
    const hintEl = document.createElement("p");
    hintEl.className = "lia-run-trigger__hint";
    hintEl.textContent = opts.hint;
    wrap.appendChild(hintEl);
  }

  return wrap;
}
