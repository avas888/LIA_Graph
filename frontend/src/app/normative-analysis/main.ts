import "@/styles/main.css";
import { renderNormativeAnalysisShell } from "@/app/normative-analysis/shell";
import { mountNormativeAnalysisApp } from "@/features/normative-analysis/normativeAnalysisApp";
import { bootstrapShellPage } from "@/shared/app/bootstrap";

bootstrapShellPage({
  missingRootMessage: "Missing #app root for normative-analysis page.",
  mountApp: mountNormativeAnalysisApp,
  renderShell: renderNormativeAnalysisShell,
  title: (i18n) => i18n.t("app.title.normativeAnalysis") || "LIA - Analisis Normativo",
});
