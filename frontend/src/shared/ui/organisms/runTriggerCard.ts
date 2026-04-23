import { createPipelineFlow } from "@/shared/ui/molecules/pipelineFlow";
import { createRunStatusBadge, type RunStatus } from "@/shared/ui/molecules/runStatusBadge";

export interface RunTriggerParams {
  suinScope: string;
  supabaseTarget: "wip" | "production";
  autoEmbed: boolean;
  autoPromote: boolean;
}

export interface RunTriggerOptions {
  /** Currently dispatched job id, if any. */
  activeJobId: string | null;
  /** Most recent run status surfaced to the user. */
  lastRunStatus: RunStatus | null;
  /** Disable trigger while a job is running. */
  disabled: boolean;
  onTrigger: (params: RunTriggerParams) => void;
}

export function createRunTriggerCard(opts: RunTriggerOptions): HTMLElement {
  const { activeJobId, lastRunStatus, disabled, onTrigger } = opts;

  const root = document.createElement("section");
  root.className = "lia-run-trigger";
  root.setAttribute("data-lia-component", "run-trigger-card");

  const header = document.createElement("header");
  header.className = "lia-run-trigger__header";

  const title = document.createElement("h3");
  title.className = "lia-run-trigger__title";
  title.textContent = "Ingesta completa";
  header.appendChild(title);

  const subtitle = document.createElement("p");
  subtitle.className = "lia-run-trigger__subtitle";
  subtitle.innerHTML =
    "Lee <code>knowledge_base/</code> en disco completo y lo reconstruye desde cero: re-audita, re-clasifica, re-parsea y re-publica los ~1.3k documentos. Tarda 30–40 minutos y cuesta aprox. US$ 6–16 en LLM. Úsala cuando cambie el clasificador, la taxonomía, o quieras un baseline limpio. Para cambios puntuales, prefiere Delta aditivo.";
  header.appendChild(subtitle);

  const safetyNote = document.createElement("p");
  safetyNote.className = "lia-run-trigger__safety";
  safetyNote.innerHTML =
    "<strong>Seguridad:</strong> por defecto escribe a la base local (WIP). " +
    "Solo promueve a la nube cuando el resultado esté validado — desde la pestaña Promoción.";
  header.appendChild(safetyNote);

  root.appendChild(header);

  root.appendChild(createPipelineFlow({ activeStage: "wip" }));

  // Form
  const form = document.createElement("form");
  form.className = "lia-run-trigger__form";
  form.setAttribute("novalidate", "");

  const targetField = _renderRadioField({
    name: "supabase_target",
    legend: "¿Dónde escribir?",
    options: [
      {
        value: "wip",
        label: "Base local (recomendado)",
        hint: "Escribe a Supabase y FalkorDB locales en Docker. Ciclo seguro: no afecta la base de producción.",
        defaultChecked: true,
      },
      {
        value: "production",
        label: "Producción (nube)",
        hint: "Escribe directo a Supabase y FalkorDB en la nube. Afecta lo que ven los usuarios hoy.",
      },
    ],
  });
  form.appendChild(targetField);

  const suinField = _renderTextField({
    name: "suin_scope",
    label: "Incluir jurisprudencia SUIN (opcional)",
    placeholder: "déjalo vacío si solo quieres re-ingerir la base",
    hint: "Además del corpus base, incluye documentos SUIN-Juriscol descargados. Valores válidos: et · tributario · laboral · jurisprudencia.",
  });
  form.appendChild(suinField);

  const optionsField = _renderCheckboxGroup([
    {
      name: "skip_embeddings",
      label: "Saltar embeddings",
      hint: "No recalcula los embeddings al final. Usa esto solo si vas a correrlos manualmente después.",
      defaultChecked: false,
    },
    {
      name: "auto_promote",
      label: "Promover a la nube al terminar",
      hint: "Si la ingesta local termina sin errores, encadena automáticamente una promoción a la nube.",
      defaultChecked: false,
    },
  ]);
  form.appendChild(optionsField);

  // Submit row
  const submitRow = document.createElement("div");
  submitRow.className = "lia-run-trigger__submit-row";

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "lia-button lia-button--primary lia-run-trigger__submit";
  submit.textContent = activeJobId ? "Ejecutando…" : "Reconstruir todo";
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
    const skipEmbeddings = fd.get("skip_embeddings") != null;
    const autoPromote = fd.get("auto_promote") != null;
    onTrigger({
      suinScope,
      supabaseTarget: supabaseTarget === "production" ? "production" : "wip",
      autoEmbed: !skipEmbeddings,
      autoPromote,
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

interface CheckboxOption {
  name: string;
  label: string;
  hint?: string;
  defaultChecked?: boolean;
}

function _renderCheckboxGroup(options: CheckboxOption[]): HTMLFieldSetElement {
  const fs = document.createElement("fieldset");
  fs.className = "lia-run-trigger__field lia-run-trigger__field--checkbox";

  const legend = document.createElement("legend");
  legend.className = "lia-run-trigger__legend";
  legend.textContent = "Opciones de corrida";
  fs.appendChild(legend);

  options.forEach((option) => {
    const wrap = document.createElement("label");
    wrap.className = "lia-run-trigger__checkbox-row";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = option.name;
    if (option.defaultChecked) input.defaultChecked = true;
    wrap.appendChild(input);

    const text = document.createElement("span");
    text.className = "lia-run-trigger__checkbox-text";
    const labelLine = document.createElement("span");
    labelLine.className = "lia-run-trigger__checkbox-label";
    labelLine.textContent = option.label;
    text.appendChild(labelLine);
    if (option.hint) {
      const hintEl = document.createElement("span");
      hintEl.className = "lia-run-trigger__checkbox-hint";
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
