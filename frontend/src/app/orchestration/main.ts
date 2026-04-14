import "@/styles/main.css";
import { renderOrchestrationShell } from "@/app/orchestration/shell";
import { mountOrchestrationApp } from "@/features/orchestration/orchestrationApp";
import { bootstrapShellPage } from "@/shared/app/bootstrap";

bootstrapShellPage({
  missingRootMessage: "Missing #app root for orchestration page.",
  mountApp: mountOrchestrationApp,
  renderShell: renderOrchestrationShell,
  title: (i18n) => i18n.t("app.title.orchestration") || "LIA - Orquestacion de Pipelines",
});
