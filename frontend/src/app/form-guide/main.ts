import "@/styles/main.css";
import { renderFormGuideShell } from "@/app/form-guide/shell";
import { mountFormGuideApp } from "@/features/form-guide/formGuideApp";
import { createPageContext } from "@/shared/app/bootstrap";

// Form guides are public-readable content: a public visitor who clicks a
// "guía gráfica sobre cómo llenarlo" link from the module must reach the
// page without being redirected to /login. The backend form-guides
// endpoints (`/api/form-guides/catalog`, `/api/form-guides/content`) do
// not require auth, so we deliberately skip `requireAuth()` here — the
// Authorization header is still attached if a platform token happens to
// be present in localStorage.
const page = createPageContext({
  missingRootMessage: "Missing #app root for form-guide page.",
});
page.setTitle(page.i18n.t("app.title.formGuide") || "LIA - Guia de Formulario");
if (new URLSearchParams(window.location.search).get("embed") === "1") {
  document.body.classList.add("form-guide-embedded");
}
page.mountShell(renderFormGuideShell(page.i18n));
mountFormGuideApp(page.root, { i18n: page.i18n });
