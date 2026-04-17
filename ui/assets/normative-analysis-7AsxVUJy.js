import"./main-DICslklM.js";import{v as b,r as C}from"./format-CYFfBTRg.js";import{g as A}from"./client-OE0sHIIg.js";import{c as S}from"./chip-Bjq03GaS.js";import{b as I}from"./button-1yFzSXrY.js";import{c as B}from"./factCard-Cu0UJHPY.js";import{b as N}from"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./authGate-Bb2S6efH.js";function x(t){return`
    <main class="normative-analysis-shell">
      <header class="normative-analysis-header">
        <div class="normative-analysis-header-info">
          <p id="normative-analysis-family" class="form-guide-eyebrow"></p>
          <h1 id="normative-analysis-title">${t.t("normativeAnalysis.loadingTitle")}</h1>
          <p id="normative-analysis-binding" class="normative-analysis-binding" hidden></p>
        </div>
        <div class="normative-analysis-header-actions">
          <a href="/" class="nav-link form-guide-back-link">${t.t("common.backToChat")}</a>
        </div>
      </header>

      <div id="normative-analysis-loading" class="form-guide-loading">
        <p>${t.t("normativeAnalysis.loading")}</p>
      </div>

      <div id="normative-analysis-error" class="form-guide-error" hidden>
        <p id="normative-analysis-error-message">${t.t("normativeAnalysis.error")}</p>
        <a href="/" class="primary-btn">${t.t("common.backToChat")}</a>
      </div>

      <div id="normative-analysis-content" class="normative-analysis-layout" hidden>
        <section class="normative-analysis-main">
          <div id="normative-analysis-caution" class="normative-analysis-caution" hidden>
            <strong id="normative-analysis-caution-title"></strong>
            <p id="normative-analysis-caution-body"></p>
          </div>

          <p id="normative-analysis-lead" class="normative-analysis-lead"></p>
          <div id="normative-analysis-facts" class="normative-analysis-facts"></div>
          <div id="normative-analysis-sections" class="normative-analysis-sections"></div>
        </section>

        <aside class="normative-analysis-sidebar">
          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${t.t("normativeAnalysis.timelineTitle")}</h2>
              <p>${t.t("normativeAnalysis.timelineSubtitle")}</p>
            </div>
            <div id="normative-analysis-timeline" class="normative-analysis-timeline"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${t.t("normativeAnalysis.relationsTitle")}</h2>
              <p>${t.t("normativeAnalysis.relationsSubtitle")}</p>
            </div>
            <div id="normative-analysis-relations" class="normative-analysis-relations"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${t.t("normativeAnalysis.overlaysTitle")}</h2>
              <p>${t.t("normativeAnalysis.overlaysSubtitle")}</p>
            </div>
            <div id="normative-analysis-overlays" class="normative-analysis-overlays"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${t.t("normativeAnalysis.actionsTitle")}</h2>
              <p>${t.t("normativeAnalysis.actionsSubtitle")}</p>
            </div>
            <div id="normative-analysis-actions" class="normative-analysis-actions"></div>
          </section>
        </aside>
      </div>
    </main>
  `}function k({id:t,title:a,body:e},n){const i=document.createElement("article");i.className="lia-normative-section",i.setAttribute("data-lia-component","normative-section"),i.dataset.sectionId=t;const o=document.createElement("h2");o.className="lia-normative-section__title",o.textContent=a;const s=document.createElement("div");return s.className="lia-normative-section__body",i.append(o,s),n?n(s,e):s.textContent=e,i}function $({id:t,label:a,date:e,detail:n},i=""){const o=document.createElement("article");o.className="lia-timeline-item",o.setAttribute("data-lia-component","timeline-item"),o.dataset.eventId=t;const s=document.createElement("h3");s.className="lia-timeline-item__label",s.textContent=a;const r=document.createElement("p");if(r.className="lia-timeline-item__meta",r.textContent=(e==null?void 0:e.trim())||i,o.append(s,r),n!=null&&n.trim()){const l=document.createElement("p");l.className="lia-timeline-item__detail",l.textContent=n,o.appendChild(l)}return o}function w({docId:t,title:a,relationLabel:e,helperText:n,url:i}){const o=document.createElement("article");if(o.className="lia-relation-link",o.setAttribute("data-lia-component","relation-link"),t&&(o.dataset.docId=t),e!=null&&e.trim()){const r=document.createElement("p");r.className="lia-relation-link__meta",r.textContent=e,o.appendChild(r)}const s=document.createElement("a");if(s.className="lia-relation-link__title",s.href=(i==null?void 0:i.trim())||"#",s.textContent=a,o.appendChild(s),n!=null&&n.trim()){const r=document.createElement("p");r.className="lia-relation-link__helper",r.textContent=n,o.appendChild(r)}return o}const R={decreto:"Decreto",ley:"Ley",resolucion:"Resolución",et_dur:"Estatuto Tributario / DUR",formulario:"Formulario",concepto:"Concepto",circular:"Circular",jurisprudencia:"Jurisprudencia",constitucion:"Constitución"},L={decreto_reglamentario:"Decreto reglamentario",decreto_ordinario:"Decreto ordinario",decreto_legislativo:"Decreto legislativo",resolucion_dian:"Resolución DIAN",resolucion_parametrica:"Resolución paramétrica",resolucion_general:"Resolución general",concepto_general:"Concepto general",concepto_unificado:"Concepto unificado",sentencia_corte_constitucional:"Sentencia Corte Constitucional",sentencia_consejo_estado:"Sentencia Consejo de Estado",documento_general:""};function T(t,a){const e=R[t]||t.replace(/_/g," "),n=L[a]||a.replace(/_/g," ");return[e,n].filter(Boolean).join(" / ")}function D(t,a){const e=new URLSearchParams(window.location.search),n=e.get("doc_id")||"";if(!n){m(a.i18n.t("normativeAnalysis.missingDoc"));return}F(n,e,a.i18n)}async function F(t,a,e){try{const n=new URLSearchParams;n.set("doc_id",t);for(const o of["locator_text","locator_kind","locator_start","locator_end"]){const s=a.get(o);s&&n.set(o,s)}const i=await A(`/api/normative-analysis?${n.toString()}`);if(!i.ok){m(e.t("normativeAnalysis.error"));return}await z(i,e)}catch{m(e.t("normativeAnalysis.error"))}}function m(t){const a=document.getElementById("normative-analysis-loading"),e=document.getElementById("normative-analysis-content"),n=document.getElementById("normative-analysis-error"),i=document.getElementById("normative-analysis-error-message");a&&(a.hidden=!0),e&&(e.hidden=!0),n&&(n.hidden=!1),i&&(i.textContent=t)}function j(t,a){t.replaceChildren(...a.filter(e=>{var n,i;return((n=e==null?void 0:e.label)==null?void 0:n.trim())&&((i=e==null?void 0:e.value)==null?void 0:i.trim())}).map(e=>B({label:String(e.label).trim(),value:String(e.value).trim()})))}async function M(t,a){t.replaceChildren();for(const e of a.filter(n=>{var i,o;return((i=n==null?void 0:n.title)==null?void 0:i.trim())&&((o=n==null?void 0:n.body)==null?void 0:o.trim())}))t.appendChild(k({id:e.id,title:String(e.title).trim(),body:String(e.body).trim()},async(n,i)=>{await C(n,i,{})}))}function P(t,a,e){t.replaceChildren(...a.filter(n=>{var i;return(i=n==null?void 0:n.label)==null?void 0:i.trim()}).map(n=>$({id:n.id,label:String(n.label).trim(),date:n.date,detail:n.detail},(e==null?void 0:e.t("normativeAnalysis.unconfirmedDate"))||"")))}function U(t,a){t.replaceChildren(...a.filter(e=>{var n;return(n=e==null?void 0:e.title)==null?void 0:n.trim()}).map(e=>w({docId:e.doc_id,title:String(e.title).trim(),relationLabel:String(e.relation_label||e.relation_type||"").trim(),helperText:e.helper_text,url:e.url})))}function J(t,a){t.replaceChildren(...a.filter(Boolean).map(e=>S({label:String(e).replace(/_/g," ").trim(),tone:"neutral",emphasis:"soft"})))}function Y(t,a){t.replaceChildren(...a.filter(e=>{var n,i;return((n=e==null?void 0:e.label)==null?void 0:n.trim())&&((i=e==null?void 0:e.url)==null?void 0:i.trim())}).map(e=>{var o;const n=document.createElement("div");n.className="normative-analysis-action";const i=/^https?:\/\//i.test(String(e.url||""));if(n.appendChild(I({href:String(e.url).trim(),label:String(e.label).trim(),tone:e.kind==="source"?"primary":"secondary",target:i?"_blank":"_self"})),(o=e.helper_text)!=null&&o.trim()){const s=document.createElement("p");s.className="normative-analysis-action__helper",s.textContent=e.helper_text,n.appendChild(s)}return n}))}async function z(t,a){var h,_,E;const e=document.getElementById("normative-analysis-loading"),n=document.getElementById("normative-analysis-content"),i=document.getElementById("normative-analysis-title"),o=document.getElementById("normative-analysis-family"),s=document.getElementById("normative-analysis-binding"),r=document.getElementById("normative-analysis-lead"),l=document.getElementById("normative-analysis-caution"),c=document.getElementById("normative-analysis-caution-title"),d=document.getElementById("normative-analysis-caution-body");e&&(e.hidden=!0),n&&(n.hidden=!1),i&&(i.textContent=String(t.title||"").trim()),document.title=`${String(t.title||"").trim()||a.t("app.title.normativeAnalysis")} | ${a.t("app.title.normativeAnalysis")}`,o&&(o.textContent=T(t.document_family||"",t.family_subtype||"")),s&&(s.textContent=String(t.binding_force||"").trim(),s.hidden=!s.textContent),r&&(r.textContent=String(t.lead||"").trim(),r.hidden=!r.textContent),l&&c&&d&&(c.textContent=b((h=t.caution_banner)==null?void 0:h.title),d.textContent=b((_=t.caution_banner)==null?void 0:_.body),l.hidden=!(c.textContent&&d.textContent),l.setAttribute("data-tone",l.hidden?"":String(((E=t.caution_banner)==null?void 0:E.tone)||"").trim()));const v=document.getElementById("normative-analysis-facts"),u=document.getElementById("normative-analysis-sections"),y=document.getElementById("normative-analysis-timeline"),p=document.getElementById("normative-analysis-relations"),g=document.getElementById("normative-analysis-overlays"),f=document.getElementById("normative-analysis-actions");v&&j(v,t.preview_facts||[]),u&&await M(u,t.sections||[]),y&&P(y,t.timeline_events||[],a),p&&U(p,t.related_documents||[]),g&&J(g,t.allowed_secondary_overlays||[]),f&&Y(f,t.recommended_actions||[])}N({missingRootMessage:"Missing #app root for normative-analysis page.",mountApp:D,renderShell:x,title:t=>t.t("app.title.normativeAnalysis")||"LIA - Analisis Normativo"});
