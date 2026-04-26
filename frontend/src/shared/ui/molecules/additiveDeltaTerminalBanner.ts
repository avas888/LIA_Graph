/**
 * Additive-corpus-v1 terminal banner (Phase 8).
 *
 * Rendered once a job reaches a terminal stage (completed / failed /
 * cancelled). For completed runs with new chunks awaiting embedding
 * (Decision I1 reviewer amendment), surfaces the exact
 * ``make phase2-embed-backfill`` command with copy-to-clipboard.
 */

import { createButton } from "@/shared/ui/atoms/button";

export type AdditiveDeltaTerminalStage = "completed" | "failed" | "cancelled";

export interface AdditiveDeltaTerminalViewModel {
  stage: AdditiveDeltaTerminalStage;
  deltaId: string;
  report?: {
    documents_added?: number;
    documents_modified?: number;
    documents_retired?: number;
    chunks_written?: number;
    chunks_deleted?: number;
    edges_written?: number;
    edges_deleted?: number;
    new_chunks_count?: number;
  } | null;
  classifierSummary?: {
    classified_new_count?: number;
    prematched_count?: number;
    degraded_n1_only?: number;
  } | null;
  errorClass?: string | null;
  errorMessage?: string | null;
}

interface ToneSpec {
  variant: "success" | "warning" | "danger" | "navy";
  title: string;
  icon: string;
}

function toneForStage(
  vm: AdditiveDeltaTerminalViewModel,
): ToneSpec {
  if (vm.stage === "cancelled") {
    return { variant: "navy", title: "Delta cancelado", icon: "✕" };
  }
  if (vm.stage === "failed") {
    return { variant: "danger", title: "Delta falló", icon: "!" };
  }
  const needsEmbed =
    (vm.report?.new_chunks_count ?? vm.report?.chunks_written ?? 0) > 0;
  return {
    variant: needsEmbed ? "warning" : "success",
    title: needsEmbed ? "Delta completado — pendiente embeddings" : "Delta completado",
    icon: "✓",
  };
}

function summarySentence(vm: AdditiveDeltaTerminalViewModel): string {
  const r = vm.report ?? {};
  const added = Number(r.documents_added ?? 0);
  const modified = Number(r.documents_modified ?? 0);
  const retired = Number(r.documents_retired ?? 0);
  return (
    `Se procesaron ${added} nuevos, ${modified} modificados y ` +
    `${retired} retirados. Ediciones de chunks: ` +
    `+${r.chunks_written ?? 0} / -${r.chunks_deleted ?? 0}. ` +
    `Aristas: +${r.edges_written ?? 0} / -${r.edges_deleted ?? 0}.`
  );
}

function writeToClipboard(text: string): Promise<boolean> {
  if (!navigator.clipboard) return Promise.resolve(false);
  return navigator.clipboard
    .writeText(text)
    .then(() => true)
    .catch(() => false);
}

export function createAdditiveDeltaTerminalBanner(
  vm: AdditiveDeltaTerminalViewModel,
): HTMLElement {
  const tone = toneForStage(vm);
  const root = document.createElement("section");
  root.className = `lia-adelta-terminal lia-adelta-terminal--${tone.variant}`;
  root.setAttribute("data-lia-component", "additive-delta-terminal");
  root.setAttribute("data-stage", vm.stage);
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");

  const header = document.createElement("header");
  header.className = "lia-adelta-terminal__header";
  const iconEl = document.createElement("span");
  iconEl.className = "lia-adelta-terminal__icon";
  iconEl.textContent = tone.icon;
  iconEl.setAttribute("aria-hidden", "true");
  const title = document.createElement("h3");
  title.className = "lia-adelta-terminal__title";
  title.textContent = tone.title;
  const deltaIdEl = document.createElement("code");
  deltaIdEl.className = "lia-adelta-terminal__delta-id";
  deltaIdEl.textContent = vm.deltaId;
  header.append(iconEl, title, deltaIdEl);
  root.appendChild(header);

  if (vm.stage === "completed") {
    const summary = document.createElement("p");
    summary.className = "lia-adelta-terminal__summary";
    summary.textContent = summarySentence(vm);
    root.appendChild(summary);

    const degraded = Number(vm.classifierSummary?.degraded_n1_only ?? 0);
    const classifiedNew = Number(vm.classifierSummary?.classified_new_count ?? 0);
    if (degraded > 0) {
      const degradedNote = document.createElement("p");
      degradedNote.className = "lia-adelta-terminal__degraded";
      degradedNote.setAttribute("data-degraded-count", String(degraded));
      const denominator = classifiedNew > 0 ? classifiedNew : degraded;
      degradedNote.textContent =
        `${degraded} de ${denominator} documentos clasificados quedaron con ` +
        `requires_subtopic_review=true (verdicto N1 solamente). ` +
        `Causa típica: backpressure de TPM en Gemini o casos genuinamente ambiguos. ` +
        `Revisa esos doc_ids antes de dar el ingest por cerrado.`;
      root.appendChild(degradedNote);
    }

    const needsEmbed =
      (vm.report?.new_chunks_count ?? vm.report?.chunks_written ?? 0) > 0;
    if (needsEmbed) {
      const callout = document.createElement("div");
      callout.className = "lia-adelta-terminal__callout";

      const copy = document.createElement("p");
      copy.className = "lia-adelta-terminal__callout-body";
      const n = vm.report?.new_chunks_count ?? vm.report?.chunks_written ?? 0;
      copy.textContent =
        `${n} chunks nuevos pendientes de embedding — la calidad de retrieval ` +
        `está degradada hasta que corras la actualización.`;

      const cmd = document.createElement("code");
      cmd.className = "lia-adelta-terminal__cmd";
      cmd.textContent = "make phase2-embed-backfill";

      const copyBtn = createButton({
        label: "Copiar comando",
        tone: "secondary",
        onClick: () => {
          void writeToClipboard("make phase2-embed-backfill").then((ok) => {
            copyBtn.classList.toggle("is-copied", ok);
            copyBtn.querySelector(".lia-btn__label")!.textContent = ok
              ? "Copiado ✓"
              : "Copiar comando";
          });
        },
      });

      callout.append(copy, cmd, copyBtn);
      root.appendChild(callout);
    }
  } else if (vm.stage === "failed") {
    const summary = document.createElement("p");
    summary.className = "lia-adelta-terminal__summary";
    summary.textContent =
      "La aplicación del delta se detuvo. La parity con Falkor puede estar " +
      "desfasada; revisa los eventos antes de reintentar.";
    const err = document.createElement("pre");
    err.className = "lia-adelta-terminal__error";
    err.textContent =
      `${vm.errorClass ?? "unknown_error"}: ${vm.errorMessage ?? "(sin mensaje)"}`;
    root.append(summary, err);
  } else {
    const summary = document.createElement("p");
    summary.className = "lia-adelta-terminal__summary";
    summary.textContent =
      "El operador canceló el delta en un punto seguro. Los cambios parciales " +
      "no se revierten automáticamente; inspecciona el reporte antes de continuar.";
    root.appendChild(summary);
  }

  return root;
}
