import "@/styles/main.css";
import { renderFormGuideShell } from "@/app/form-guide/shell";
import { mountFormGuideApp } from "@/features/form-guide/formGuideApp";
import { bootstrapShellPage } from "@/shared/app/bootstrap";

bootstrapShellPage({
  missingRootMessage: "Missing #app root for form-guide page.",
  mountApp: mountFormGuideApp,
  renderShell: renderFormGuideShell,
  title: (i18n) => i18n.t("app.title.formGuide") || "LIA - Guia de Formulario",
});
