import "@/styles/main.css";
import { renderOpsShell } from "@/app/ops/shell";
import { mountOpsApp } from "@/features/ops/opsApp";
import { bootstrapShellPage } from "@/shared/app/bootstrap";

bootstrapShellPage({
  missingRootMessage: "Missing #app root for ops page.",
  mountApp: mountOpsApp,
  renderShell: renderOpsShell,
  title: (i18n) => i18n.t("app.title.ops"),
});
