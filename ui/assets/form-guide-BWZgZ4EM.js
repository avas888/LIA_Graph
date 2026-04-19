import"./main-DICslklM.js";import{p as W,g as U}from"./client-OE0sHIIg.js";import{p as Z,r as V}from"./format-CYFfBTRg.js";import{c as ee}from"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./authGate-Bb2S6efH.js";function te(e){return`
    <main class="form-guide-shell">
      <header class="form-guide-header">
        <div class="form-guide-header-info">
          <p id="form-guide-profile" class="form-guide-eyebrow"></p>
          <h1 id="form-guide-title">Cargando guía...</h1>
          <p id="form-guide-version" class="form-guide-meta"></p>
          <p id="form-guide-verified" class="form-guide-meta"></p>
        </div>
        <div class="form-guide-header-actions">
          <button id="form-guide-sources-btn" class="secondary-btn" type="button">Ver fuentes</button>
          <button id="form-guide-pdf-btn" class="primary-btn" type="button">Descargar PDF oficial</button>
          <a href="/" class="nav-link form-guide-back-link">Volver al chat</a>
        </div>
        <div class="form-guide-mobile-controls">
          <button class="form-guide-hamburger" type="button" aria-label="Menú">
            <span></span><span></span><span></span>
          </button>
          <a href="/" class="form-guide-close-btn" aria-label="Cerrar">×</a>
          <div class="form-guide-mobile-menu" hidden>
            <button id="form-guide-sources-btn-mobile" class="form-guide-mobile-menu-item" type="button">Ver fuentes</button>
            <button id="form-guide-pdf-btn-mobile" class="form-guide-mobile-menu-item" type="button">Descargar PDF oficial</button>
          </div>
        </div>
      </header>

      <div id="form-guide-loading" class="form-guide-loading">
        <p>Cargando guía del formulario...</p>
      </div>

      <div id="form-guide-error" class="form-guide-error" hidden>
        <p id="form-guide-error-message">Esta guía aún no está disponible.</p>
        <a href="/" class="primary-btn">Volver al chat principal</a>
      </div>

      <div id="form-guide-content" class="form-guide-layout" hidden>
        <section class="form-guide-main">
          <div class="form-guide-view-toggle" role="tablist" aria-label="Cambiar vista de la guía">
            <button id="view-interactive-btn" class="view-toggle-btn view-toggle-active" type="button" role="tab" aria-selected="true">Guía gráfica</button>
            <button id="view-structured-btn" class="view-toggle-btn" type="button" role="tab" aria-selected="false">Guía texto</button>
          </div>

          <section id="form-guide-interactive-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header">
              <div>
                <p class="form-guide-panel-kicker">Guía visual</p>
                <h2>Guía gráfica del formulario</h2>
              </div>
              <p class="form-guide-panel-note">Haz clic en cualquier campo para abrir una ficha completa con el mismo nivel de detalle de la guía textual.</p>
            </header>
            <div id="interactive-pages" class="interactive-pages"></div>
          </section>

          <section id="form-guide-structured-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header">
              <div>
                <p class="form-guide-panel-kicker">Guía textual</p>
                <h2>Guía texto del formulario</h2>
              </div>
              <p class="form-guide-panel-note">Resumen completo por secciones para revisar antes de diligenciar y presentar.</p>
            </header>
            <div id="structured-sections" class="structured-sections"></div>
          </section>

          <button id="mobile-show-graphic-btn" class="mobile-show-graphic-btn" type="button" hidden>Ver guía gráfica del formulario</button>
        </section>

        <aside class="form-guide-chat">
          <header class="form-guide-chat-header">
            <h2>Chatea sobre este formulario</h2>
            <p id="form-guide-chat-context" class="form-guide-chat-context"></p>
          </header>
          <div id="form-guide-chat-log" class="form-guide-chat-log"></div>
          <form id="form-guide-chat-form" class="form-guide-chat-form">
            <textarea id="form-guide-chat-input" rows="2" placeholder="Pregunta sobre este formulario..." required></textarea>
            <button type="submit" class="primary-btn">Enviar</button>
          </form>
          <p id="form-guide-disclaimer" class="form-guide-disclaimer" hidden></p>
        </aside>
      </div>

      <div id="form-guide-profile-selector" class="form-guide-profile-selector" hidden>
        <h2>Selecciona un perfil tributario</h2>
        <p>Esta guía varía según el perfil del contribuyente. Selecciona el que aplica:</p>
        <div id="profile-options" class="profile-options"></div>
      </div>

      <dialog id="form-guide-sources-dialog" class="form-guide-sources-dialog">
        <header>
          <h3>Fuentes de la guía</h3>
          <button id="close-sources-dialog" type="button" class="modal-close">&times;</button>
        </header>
        <div id="sources-list" class="sources-list"></div>
      </dialog>

      <dialog id="form-guide-field-dialog" class="form-guide-field-dialog">
        <div class="form-guide-field-dialog-shell">
          <header class="form-guide-field-dialog-header">
            <div class="form-guide-field-dialog-heading">
              <p id="field-dialog-eyebrow" class="form-guide-eyebrow"></p>
              <h3 id="field-dialog-title">Campo seleccionado</h3>
              <div id="field-dialog-meta" class="field-dialog-meta"></div>
            </div>
            <button id="close-field-dialog" type="button" class="modal-close" aria-label="Cerrar detalle del campo">&times;</button>
          </header>

          <p id="field-dialog-summary" class="field-dialog-summary" hidden></p>
          <div id="field-dialog-body" class="field-dialog-grid"></div>

        </div>
      </dialog>
    </main>
  `}function q(e){const l=String(e||"").trim();return l&&(l.startsWith("/")||/^https?:\/\//i.test(l))?l:""}function ie(e){for(const l of e){const g=q(l.url);if(g&&String(l.source_type||"").trim().toLowerCase()==="formulario_oficial_pdf")return{url:g,authority:String(l.authority||"").trim()}}return{url:"",authority:""}}function c(e){return Z(String(e??"").trim())}function j(e){if(typeof e.showModal=="function"){e.open||e.showModal();return}e.setAttribute("open","true")}function F(e){if(typeof e.close=="function"&&e.open){e.close();return}e.removeAttribute("open")}function ne(e){return e.open||e.hasAttribute("open")}function L(e){const l=document.getElementById("view-structured-btn"),g=document.getElementById("view-interactive-btn");if(!l||!g)return;const E=e==="interactive"&&!g.hasAttribute("disabled");g.classList.toggle("view-toggle-active",E),l.classList.toggle("view-toggle-active",!E),g.setAttribute("aria-selected",E?"true":"false"),l.setAttribute("aria-selected",E?"false":"true")}function oe(e){return String(e.label||(e.casilla?`Casilla ${e.casilla}`:"este campo")).trim()}function re(e){return e.casilla?String(e.casilla):e.label?e.label:"Campo"}function ae(e){if(!Array.isArray(e.marker_bbox)||e.marker_bbox.length!==4)return null;const l=e.marker_bbox.map(g=>Number(g));return l.every(g=>Number.isFinite(g))?l:null}function le(e){const l=ae(e);return l?{left:l[0]+l[2]/2,top:l[1]+l[3]/2,centered:!0,markerCenterX:l[0]+l[2]/2,markerCenterY:l[1]+l[3]/2}:{left:e.bbox[0],top:e.bbox[1],centered:!1,markerCenterX:null,markerCenterY:null}}function s(e){const l=document.createElement("div");return l.appendChild(document.createTextNode(e)),l.innerHTML}function ce({state:e}){function l(p,d,f,_=""){const w=document.createElement("div");w.className=`form-guide-chat-bubble form-guide-chat-${d} ${_}`.trim();const B=document.createElement("p");B.className="chat-bubble-role",B.textContent=d==="user"?"Tú":"LIA",w.appendChild(B);const $=document.createElement("div");$.className="chat-bubble-body",d==="assistant"?V($,f):$.textContent=c(f),w.appendChild($),p.appendChild(w),p.scrollTop=p.scrollHeight,e.chatMessages.push({role:d,text:f})}function g(p,d){const f=document.createElement("div");f.className="form-guide-chat-handoff";const _=document.createElement("p");_.className="form-guide-chat-handoff-helper",_.textContent="Esta pregunta se abrirá en el chat general y quedará como borrador para que la continúes allá.";const w=document.createElement("a");w.className="secondary-btn",w.href=d,w.target="_blank",w.rel="noopener noreferrer",w.textContent="Continuar en el chat general",f.append(_,w),p.appendChild(f),p.scrollTop=p.scrollHeight}function E(p){const d=document.createElement("div");return d.className="form-guide-chat-bubble form-guide-chat-thinking",d.setAttribute("aria-live","polite"),d.setAttribute("aria-label","Pensando"),d.innerHTML=`
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
    `,p.appendChild(d),p.scrollTop=p.scrollHeight,d}function I(){const p=document.getElementById("form-guide-chat-form"),d=document.getElementById("form-guide-chat-input"),f=document.getElementById("form-guide-chat-log");!p||!d||!f||(p.onsubmit=async _=>{var $;_.preventDefault();const w=d.value.trim();if(!w)return;l(f,"user",w),d.value="",d.disabled=!0;const B=E(f);try{const{data:k}=await W("/api/form-guides/chat",{reference_key:e.currentReferenceKey,profile:e.currentProfile,message:w,selected_field_id:e.selectedFieldId,selected_page:null,active_section:e.selectedSection});if(B.remove(),k&&k.ok){const G=k.answer_mode==="pedagogical"?"":"chat-refusal";if(l(f,"assistant",k.answer_markdown,G),k.answer_mode==="out_of_scope_refusal"){const x=q(($=k.grounding)==null?void 0:$.handoff_url);x&&g(f,x)}if(k.suggested_followups&&k.suggested_followups.length>0){const x=k.suggested_followups.map(A=>`<button class="followup-btn" type="button">${s(c(A))}</button>`).join(""),S=document.createElement("div");S.className="chat-followups",S.innerHTML=x,S.addEventListener("click",A=>{const M=A.target.closest(".followup-btn");M&&(d.value=M.textContent||"",p.dispatchEvent(new Event("submit",{bubbles:!0,cancelable:!0})))}),f.appendChild(S)}}else l(f,"assistant","Error procesando tu pregunta. Intenta de nuevo.")}catch{B.remove(),l(f,"assistant","Error de conexión. Intenta de nuevo.")}finally{d.disabled=!1,d.focus()}})}return{bindChatForm:I}}function se(e,l){return e.guide?e.guide:e.reference_key&&Array.isArray(e.available_profiles)?{reference_key:e.reference_key,title:e.title||"",form_version:e.form_version||"",available_profiles:e.available_profiles,supported_views:e.supported_views||[],last_verified_date:e.last_verified_date||"",download_available:!!e.download_available,disclaimer:e.disclaimer||""}:Array.isArray(e.guides)&&e.guides.length>0?e.guides.find(g=>g.reference_key===l)||e.guides[0]:null}function de({state:e,onContentLoaded:l,onError:g,showLoading:E,showProfileSelector:I}){async function p(){try{const f=await U(`/api/form-guides/content?reference_key=${encodeURIComponent(e.currentReferenceKey)}&profile=${encodeURIComponent(e.currentProfile)}&view=structured`);if(!f.ok){g("No se pudo cargar el contenido de la guía.");return}e.guideSources=f.sources||[],e.guidePageAssets=f.page_assets||[];const _=ie(e.guideSources);e.guideOfficialPdfUrl=q(f.official_pdf_url)||_.url,e.guideOfficialPdfAuthority=String(f.official_pdf_authority||_.authority||"").trim(),l(f)}catch{g("Error cargando el contenido de la guía.")}}async function d(){try{const f=await U(`/api/form-guides/catalog?reference_key=${encodeURIComponent(e.currentReferenceKey)}`),_=se(f,e.currentReferenceKey);if(!f.ok||!_){g("Esta guía aún no está disponible.");return}if(_.available_profiles.length>1&&!e.currentProfile){I(_,w=>{e.currentProfile=w,E(),p()});return}!e.currentProfile&&_.available_profiles.length===1&&(e.currentProfile=_.available_profiles[0].profile_id),await p()}catch{g("Error cargando la guía. Intenta de nuevo.")}}return{loadCatalog:d,loadContent:p}}function ue(){return{currentReferenceKey:"",currentProfile:"",selectedFieldId:null,selectedSection:null,chatMessages:[],guideSources:[],guidePageAssets:[],guideOfficialPdfUrl:"",guideOfficialPdfAuthority:"",guideSectionsById:new Map,guideHotspotsById:new Map,guideViewObserver:null}}function fe({state:e}){function l(t){const i=document.createElement("div");return V(i,t),c(i.textContent||"")}function g(t){return l(t).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/gi," ").trim().toLowerCase()}function E(t,i){const r=g(t.instruction_md||"");if(!r)return!0;const n=g((i==null?void 0:i.title)||""),a=!!(t.casilla&&r.includes(`casilla ${t.casilla}`))&&!!(n&&r.includes(n)),m=r.includes("revise la casilla")||r.includes("verifique la casilla")||r.includes("dentro de la seccion")||r.includes("antes de presentar"),b=!c(t.what_to_review_before_filling||"")&&!c(t.common_errors||"")&&!c(t.warnings||"");return m&&a&&b}function I(t,i){const r=g(t),n=g(i);return!r||!n?!1:r.includes(n)||n.includes(r)}function p(){if(document.querySelectorAll(".guide-hotspot-active").forEach(t=>t.classList.remove("guide-hotspot-active")),document.querySelectorAll(".guide-section-active").forEach(t=>t.classList.remove("guide-section-active")),e.selectedFieldId){const t=document.querySelector(`.guide-hotspot[data-field-id="${e.selectedFieldId}"]`);t==null||t.classList.add("guide-hotspot-active")}if(e.selectedSection){const t=document.querySelector(`.guide-section[data-section-id="${e.selectedSection}"]`);t==null||t.classList.add("guide-section-active")}}function d(){const t=document.getElementById("form-guide-chat-context");if(t){if(e.selectedFieldId){const i=e.guideHotspotsById.get(e.selectedFieldId),r=e.selectedSection?e.guideSectionsById.get(e.selectedSection):void 0,n=i!=null&&i.casilla?`Casilla ${i.casilla} — ${c(i.label)}`:c((i==null?void 0:i.label)||e.selectedFieldId);t.textContent=r?`Contexto: ${n} · ${c(r.title)}`:`Contexto: ${n}`;return}if(e.selectedSection){const i=e.guideSectionsById.get(e.selectedSection);t.textContent=`Contexto: ${c((i==null?void 0:i.title)||e.selectedSection)}`;return}t.textContent=""}}function f(t){const i=document.getElementById("form-guide-field-dialog"),r=document.getElementById("field-dialog-title"),n=document.getElementById("field-dialog-eyebrow"),a=document.getElementById("field-dialog-meta"),m=document.getElementById("field-dialog-summary"),b=document.getElementById("field-dialog-body");if(!i||!r||!n||!a||!m||!b)return;const o=e.guideSectionsById.get(t.section),u=c(oe(t)),h=c(t.official_dian_instruction||""),v=String(t.instruction_md||"").trim();c(v);const T=!!v&&!E(t,o)&&(!h||!I(h,v)),D=c(t.what_to_review_before_filling||"");i.dataset.fieldId=t.field_id,i.dataset.sectionId=t.section,r.textContent=t.casilla?`Casilla ${t.casilla} — ${c(t.label)}`:c(t.label),n.textContent=c((o==null?void 0:o.title)||"Campo guiado"),a.innerHTML=[t.casilla?`<span class="field-dialog-chip">Casilla ${t.casilla}</span>`:"",t.año_gravable?`<span class="field-dialog-chip">AG ${s(t.año_gravable)}</span>`:"",`<span class="field-dialog-chip">Página ${t.page}</span>`,o!=null&&o.title?`<span class="field-dialog-chip field-dialog-chip-soft">${s(c(o.title))}</span>`:""].filter(Boolean).join(""),m.textContent=D,m.hidden=!D;const C=[];if(T){const H=(t.source_ids||[]).map(P=>e.guideSources.find(O=>O.source_id===P)).filter(Boolean).map(P=>P.authority).filter((P,O,Q)=>P&&Q.indexOf(P)===O),J=H.length>0?`<span class="field-dialog-source-badge">Fuente: ${s(H.join(", "))}</span>`:"";C.push(`
        <article class="field-dialog-card field-dialog-card-primary">
          <p class="guide-section-label">${h?"Cómo diligenciar":"Indicación principal"}: ${s(u)}</p>
          <div data-field-dialog-markdown="fallback" class="field-dialog-markdown"></div>
          ${J}
        </article>
      `)}if(h&&C.push(`
        <article class="field-dialog-card field-dialog-card-dian">
          <p class="guide-section-label dian-official-label">Instrucción DIAN para ${s(u)}</p>
          <p>${s(h)}</p>
          <span class="dian-official-badge">Recomendación Oficial DIAN</span>
        </article>
      `),t.what_to_review_before_filling&&C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Qué revisar en ${s(u)}</p>
          <p>${s(c(t.what_to_review_before_filling))}</p>
        </article>
      `),t.common_errors&&C.push(`
        <article class="field-dialog-card field-dialog-card-errors">
          <p class="guide-section-label">Errores frecuentes en ${s(u)}</p>
          <p>${s(c(t.common_errors))}</p>
        </article>
      `),t.warnings&&C.push(`
        <article class="field-dialog-card field-dialog-card-warnings">
          <p class="guide-section-label">Advertencias para ${s(u)}</p>
          <p>${s(c(t.warnings))}</p>
        </article>
      `),!T&&!h&&!t.what_to_review_before_filling&&!t.common_errors&&!t.warnings&&C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Detalle específico pendiente</p>
          <p>Esta casilla ya está ubicada y titulada, pero su comentario puntual aún no está curado con suficiente detalle.</p>
        </article>
      `),o!=null&&o.title||o!=null&&o.purpose||o!=null&&o.profile_differences){const H=[o!=null&&o.title?`<p><strong>Sección:</strong> ${s(c(o.title))}</p>`:"",o!=null&&o.purpose?`<p><strong>Para qué sirve:</strong> ${s(c(o.purpose))}</p>`:"",o!=null&&o.profile_differences?`<p><strong>Diferencias por perfil:</strong> ${s(c(o.profile_differences))}</p>`:""].filter(Boolean);C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Contexto de la sección</p>
          ${H.join("")}
        </article>
      `)}b.innerHTML=C.join("");const N=b.querySelector('[data-field-dialog-markdown="fallback"]');N&&v&&V(N,v),j(i)}function _(t,i){const r=t.filter(a=>a.section===i).sort((a,m)=>(a.casilla||0)-(m.casilla||0));if(r.length===0)return"";const n=r.map(a=>{const m=a.casilla?`<span class="campo-casilla">Cas. ${a.casilla}</span>`:"",b=s(c(a.label)),o=a.instruction_md?s(l(a.instruction_md).slice(0,160)):"",u=o.length>=160?o+"…":o;return`
          <li class="campo-item" data-campo-field-id="${a.field_id}" role="button" tabindex="0">
            <div class="campo-header">${m}<span class="campo-label">${b}</span></div>
            ${u?`<p class="campo-instruction">${u}</p>`:""}
          </li>
        `}).join("");return`
      <div class="guide-section-block guide-section-campos">
        <p class="guide-section-label">Campos de esta sección (${r.length})</p>
        <ul class="campo-list">${n}</ul>
      </div>
    `}function w(t,i){const r=document.getElementById("structured-sections");r&&(r.innerHTML=t.map(n=>`
        <article class="guide-section" data-section-id="${n.section_id}">
          <h3 class="guide-section-title">${s(c(n.title))}</h3>
          ${n.purpose?`<div class="guide-section-block"><p class="guide-section-label">Para qué sirve</p><p>${s(c(n.purpose))}</p></div>`:""}
          ${n.what_to_review?`<div class="guide-section-block"><p class="guide-section-label">Qué revisar antes de diligenciar</p><p>${s(c(n.what_to_review))}</p></div>`:""}
          ${n.profile_differences?`<div class="guide-section-block"><p class="guide-section-label">Diferencias por perfil</p><p>${s(c(n.profile_differences))}</p></div>`:""}
          ${_(i,n.section_id)}
          ${n.common_errors?`<div class="guide-section-block guide-section-errors"><p class="guide-section-label">Errores frecuentes</p><p>${s(c(n.common_errors))}</p></div>`:""}
          ${n.warnings?`<div class="guide-section-block guide-section-warnings"><p class="guide-section-label">Advertencias</p><p>${s(c(n.warnings))}</p></div>`:""}
        </article>
      `).join(""),r.onclick=n=>{const a=n.target.closest("[data-campo-field-id]");if(a){const b=a.dataset.campoFieldId||"",o=e.guideHotspotsById.get(b);o&&(e.selectedFieldId=b,e.selectedSection=o.section,p(),d(),f(o));return}const m=n.target.closest("[data-section-id]");m&&(e.selectedSection=m.dataset.sectionId||null,e.selectedFieldId=null,p(),d())})}function B(t){const i=document.getElementById("interactive-pages");i&&(i.innerHTML=`
      <section class="guide-page-card guide-page-card-empty">
        <div class="guide-page-header">
          <div>
            <h3 class="interactive-page-title">Guía gráfica no disponible</h3>
            <p>Este formulario aún no tiene mapa de campos publicado.</p>
          </div>
        </div>
        <div class="guide-document-fallback">${s(t)}</div>
      </section>
    `)}function $(t,i){const r=new Map;t.forEach(o=>{const u=r.get(o.page)||[];u.push(o),r.set(o.page,u)});const n=document.getElementById("interactive-pages");if(!n)return;const a=new Map;i.forEach(o=>{a.set(o.page,o)});const m=(r.size>0?Array.from(r.keys()):Array.from(a.keys())).sort((o,u)=>o-u);n.innerHTML=m.map(o=>{const u=a.get(o),h=r.get(o)||[];return`
          <section class="guide-page-card" data-guide-page="${o}">
            <div class="guide-page-header">
              <div>
                <h3 class="interactive-page-title">Página ${o}</h3>
                <p>${h.length} campo(s) guiado(s)</p>
              </div>
              <div class="guide-page-helper">Haz clic en un campo para abrir o cerrar la ficha.</div>
            </div>
            <div class="guide-document-frame">
              ${u?`<img class="guide-document-image" src="${s(u.url)}" alt="Vista exacta página ${o} del formulario" />`:'<div class="guide-document-fallback">No hay asset publicado para esta página.</div>'}
              <div class="guide-hotspot-layer">
                ${h.map(v=>{const y=le(v);return`
                      <button
                        class="guide-hotspot"
                        type="button"
                        data-field-id="${v.field_id}"
                        data-casilla="${v.casilla||""}"
                        data-section="${v.section}"
                        data-page="${v.page}"
                        data-marker-x="${y.markerCenterX??""}"
                        data-marker-y="${y.markerCenterY??""}"
                        data-marker-centered="${y.centered?"true":"false"}"
                        aria-label="Abrir o cerrar detalle de ${s(c(v.label))}"
                        style="left:${y.left}%;top:${y.top}%;--guide-hotspot-translate-x:${y.centered?"-50%":"0"};--guide-hotspot-translate-y:${y.centered?"-50%":"0"};"
                      >
                        <span class="guide-hotspot-pill">${s(re(v))}</span>
                      </button>
                    `}).join("")}
              </div>
            </div>
          </section>
        `}).join("");const b=Array.from(r.values()).flat();n.onclick=o=>{const u=o.target.closest("[data-field-id]");if(!u)return;const h=u.dataset.fieldId||"",v=b.find(D=>D.field_id===h);if(!v)return;const y=document.getElementById("form-guide-field-dialog"),T=!!(y&&y.dataset.fieldId===h&&ne(y));if(e.selectedFieldId=h,e.selectedSection=v.section,p(),d(),T&&y){F(y);return}f(v)}}function k(){var m;const t=document.getElementById("view-structured-btn"),i=document.getElementById("view-interactive-btn"),r=document.getElementById("form-guide-structured-view"),n=document.getElementById("form-guide-interactive-view"),a=document.querySelector(".form-guide-main");!t||!i||!r||!n||(t.onclick=()=>{L("structured"),r.scrollIntoView({block:"start",behavior:"smooth"})},i.onclick=()=>{i.hasAttribute("disabled")||(L("interactive"),n.scrollIntoView({block:"start",behavior:"smooth"}))},(m=e.guideViewObserver)==null||m.disconnect(),typeof IntersectionObserver=="function"&&(e.guideViewObserver=new IntersectionObserver(b=>{const u=b.filter(h=>h.isIntersecting).sort((h,v)=>v.intersectionRatio-h.intersectionRatio)[0];if(u){if(u.target===n&&!i.hasAttribute("disabled")){L("interactive");return}u.target===r&&L("structured")}},{root:a,threshold:[.35,.6,.85],rootMargin:"-12% 0px -45% 0px"}),e.guideViewObserver.observe(n),e.guideViewObserver.observe(r)))}function G(){const t=document.getElementById("form-guide-field-dialog"),i=document.getElementById("close-field-dialog");t&&(i&&(i.onclick=()=>F(t)),t.onclick=r=>{r.defaultPrevented||F(t)})}function x(){const t=document.getElementById("form-guide-sources-btn"),i=document.getElementById("form-guide-sources-dialog"),r=document.getElementById("close-sources-dialog"),n=document.getElementById("sources-list");!t||!i||!n||(t.onclick=()=>{n.innerHTML=e.guideSources.map(a=>`
          <div class="source-card ${a.is_primary?"source-primary":"source-secondary"}">
            <p class="source-title">${s(c(a.title))}</p>
            <p class="source-authority">${s(c(a.authority))} · ${a.is_primary?"Fuente primaria":"Fuente secundaria"}</p>
            ${a.url?`<a href="${s(a.url)}" target="_blank" rel="noopener noreferrer" class="source-link">Ver fuente</a>`:""}
            ${a.notes?`<p class="source-notes">${s(c(a.notes))}</p>`:""}
            <p class="source-checked">Verificada: ${s(a.last_checked_date)}</p>
          </div>
        `).join(""),j(i)},r&&(r.onclick=()=>F(i)),i.onclick=a=>{a.target===i&&F(i)})}function S(){const t=document.getElementById("form-guide-pdf-btn");t&&(t.disabled=!e.guideOfficialPdfUrl,t.title=e.guideOfficialPdfUrl?e.guideOfficialPdfAuthority?`Abre el PDF oficial publicado por ${e.guideOfficialPdfAuthority}`:"Abre el PDF oficial del formulario.":"Este formulario aún no tiene un PDF oficial publicado en la guía.",t.onclick=()=>{e.guideOfficialPdfUrl&&window.open(e.guideOfficialPdfUrl,"_blank","noopener,noreferrer")})}function A(){const t=document.getElementById("mobile-show-graphic-btn"),i=document.getElementById("form-guide-interactive-view");!t||!i||t.addEventListener("click",()=>{i.style.display="",t.hidden=!0,i.scrollIntoView({block:"start",behavior:"smooth"})})}function M(){const t=document.querySelector(".form-guide-hamburger"),i=document.querySelector(".form-guide-mobile-menu");if(!t||!i)return;t.addEventListener("click",()=>{i.hidden=!i.hidden}),document.addEventListener("click",b=>{!i.hidden&&!i.contains(b.target)&&b.target!==t&&!t.contains(b.target)&&(i.hidden=!0)});const r=document.getElementById("form-guide-sources-btn-mobile"),n=document.getElementById("form-guide-sources-btn");r&&n&&r.addEventListener("click",()=>{i.hidden=!0,n.click()});const a=document.getElementById("form-guide-pdf-btn-mobile"),m=document.getElementById("form-guide-pdf-btn");a&&m&&a.addEventListener("click",()=>{i.hidden=!0,m.click()})}function z(){const t=document.getElementById("form-guide-loading"),i=document.getElementById("form-guide-profile-selector"),r=document.getElementById("form-guide-error"),n=document.getElementById("form-guide-content");t&&(t.hidden=!1),i&&(i.hidden=!0),r&&(r.hidden=!0),n&&(n.hidden=!0)}function K(t,i){const r=document.getElementById("form-guide-loading"),n=document.getElementById("form-guide-profile-selector"),a=document.getElementById("profile-options");r&&(r.hidden=!0),!(!n||!a)&&(n.hidden=!1,a.innerHTML=t.available_profiles.map(m=>`
          <button class="profile-option-btn" type="button" data-profile="${m.profile_id}">
            <strong>${c(m.profile_label)}</strong>
          </button>
        `).join(""),a.onclick=m=>{const b=m.target.closest("[data-profile]");b&&(n.hidden=!0,i(b.dataset.profile||""))})}function X(t){const i=document.getElementById("form-guide-loading"),r=document.getElementById("form-guide-error"),n=document.getElementById("form-guide-error-message");i&&(i.hidden=!0),r&&(r.hidden=!1),n&&(n.textContent=c(t))}function Y(t){const i=document.getElementById("form-guide-loading"),r=document.getElementById("form-guide-content"),n=document.getElementById("form-guide-disclaimer");e.guideSectionsById=new Map(t.structured_sections.map(y=>[y.section_id,y])),e.guideHotspotsById=new Map(t.interactive_map.map(y=>[y.field_id,y])),i&&(i.hidden=!0),r&&(r.hidden=!1);const a=document.getElementById("form-guide-title"),m=document.getElementById("form-guide-profile"),b=document.getElementById("form-guide-version"),o=document.getElementById("form-guide-verified");a&&(a.textContent=c(t.manifest.title)),m&&(m.textContent=c(t.manifest.profile_label)),b&&(b.textContent=c(t.manifest.form_version)),o&&(o.textContent=`Última verificación: ${t.manifest.last_verified_date}`),n&&t.disclaimer&&(n.textContent=c(t.disclaimer),n.hidden=!1),w(t.structured_sections,t.interactive_map);const u=document.getElementById("view-interactive-btn"),h=t.interactive_map.length>0&&e.guidePageAssets.length>0;!h&&u?(u.setAttribute("disabled","true"),u.title="Guía gráfica no disponible para esta guía",B("La guía textual sigue disponible mientras se publica el mapa gráfico certificado.")):u?(u.removeAttribute("disabled"),u.title="",$(t.interactive_map,e.guidePageAssets)):h&&$(t.interactive_map,e.guidePageAssets),k(),G(),x(),S(),M(),A();const v=window.matchMedia("(max-width: 640px)").matches;L(v?"structured":h?"interactive":"structured"),p(),d()}return{renderGuide:Y,showError:X,showLoading:z,showProfileSelector:K}}function ge(e,l){const g=new URLSearchParams(window.location.search),E=ue();E.currentReferenceKey=g.get("reference_key")||"",E.currentProfile=g.get("profile")||"";const I=fe({state:E}),p=ce({state:E}),d=de({state:E,onContentLoaded:I.renderGuide,onError:I.showError,showLoading:I.showLoading,showProfileSelector:I.showProfileSelector});if(!E.currentReferenceKey){I.showError("No se especificó un formulario.");return}p.bindChatForm(),d.loadCatalog()}const R=ee({missingRootMessage:"Missing #app root for form-guide page."});R.setTitle(R.i18n.t("app.title.formGuide")||"LIA - Guia de Formulario");R.mountShell(te());ge();
