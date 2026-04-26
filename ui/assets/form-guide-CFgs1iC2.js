import"./main-pJxnhjdJ.js";import{p as J,g as z}from"./client-OE0sHIIg.js";import{p as W,r as O}from"./format-CYFfBTRg.js";import{i as Z}from"./icons-BZwBwwSI.js";import{c as ee}from"./bootstrap-BApbUZ11.js";import"./index-DF3uq1vv.js";import"./authGate-Bb2S6efH.js";function te(e){return`
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
            <header class="form-guide-panel-header form-guide-panel-header--with-demo">
              <div class="form-guide-panel-header-intro">
                <p class="form-guide-panel-kicker">Guía visual</p>
                <h2>Guía gráfica del formulario</h2>
                <p class="form-guide-panel-note">Toca cualquier <strong>número</strong> sobre el formulario para abrir una <strong>ficha completa</strong> del campo, con el mismo detalle de la guía textual.</p>
              </div>
              <div class="form-guide-panel-demo" aria-hidden="true">
                <svg class="form-guide-panel-illustration" viewBox="0 0 200 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustración: un dedo toca un número pequeño sobre el formulario para abrir la ficha del campo">
                  <defs>
                    <radialGradient id="fg-panel-illu-glow-graphic" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="rgba(20, 115, 83, 0.3)"/>
                      <stop offset="100%" stop-color="rgba(20, 115, 83, 0)"/>
                    </radialGradient>
                  </defs>
                  <circle cx="26" cy="52" r="26" fill="url(#fg-panel-illu-glow-graphic)"/>
                  <rect x="14" y="10" width="124" height="96" rx="9" fill="#ffffff" stroke="rgba(22,49,41,0.14)" stroke-width="1"/>
                  <path d="M23 10 H129 Q138 10 138 19 V30 H14 V19 Q14 10 23 10 Z" fill="#163129"/>
                  <rect x="22" y="15.5" width="56" height="2.8" rx="1.4" fill="rgba(255,255,255,0.92)"/>
                  <rect x="22" y="21.5" width="36" height="2.2" rx="1.1" fill="rgba(255,255,255,0.55)"/>
                  <circle cx="26" cy="40" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.55)" stroke-width="0.85"/>
                  <text x="26" y="41.6" text-anchor="middle" fill="rgba(20,115,83,0.9)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">1</text>
                  <rect x="34" y="38.6" width="82" height="2.9" rx="1.45" fill="rgba(22,49,41,0.26)"/>
                  <circle cx="26" cy="52" r="4.1" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.95)" stroke-width="1.15"/>
                  <text x="26" y="53.7" text-anchor="middle" fill="rgba(20,115,83,1)" font-family="ui-sans-serif, system-ui" font-size="4.2" font-weight="700">2</text>
                  <rect x="34" y="50.55" width="94" height="2.9" rx="1.45" fill="rgba(22,49,41,0.42)"/>
                  <circle cx="26" cy="64" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.55)" stroke-width="0.85"/>
                  <text x="26" y="65.6" text-anchor="middle" fill="rgba(20,115,83,0.9)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">3</text>
                  <rect x="34" y="62.6" width="70" height="2.9" rx="1.45" fill="rgba(22,49,41,0.26)"/>
                  <circle cx="26" cy="76" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.42)" stroke-width="0.85"/>
                  <text x="26" y="77.6" text-anchor="middle" fill="rgba(20,115,83,0.72)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">4</text>
                  <rect x="34" y="74.6" width="76" height="2.9" rx="1.45" fill="rgba(22,49,41,0.2)"/>
                  <circle cx="26" cy="88" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.3)" stroke-width="0.85"/>
                  <text x="26" y="89.6" text-anchor="middle" fill="rgba(20,115,83,0.55)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">5</text>
                  <rect x="34" y="86.6" width="60" height="2.9" rx="1.45" fill="rgba(22,49,41,0.14)"/>
                  <g class="form-guide-panel-illu-ripple">
                    <circle cx="26" cy="52" r="9" fill="none" stroke="rgba(20,115,83,0.5)" stroke-width="1.2"/>
                    <circle cx="26" cy="52" r="5.5" fill="none" stroke="rgba(20,115,83,0.72)" stroke-width="1.2"/>
                  </g>
                  <g transform="translate(7.6 47.2) scale(1.6)">
                    <g class="form-guide-panel-illu-hand">
                      <path fill="#163129" stroke="#ffffff" stroke-width="0.6" stroke-linejoin="round" d="M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z"/>
                    </g>
                  </g>
                </svg>
              </div>
            </header>
            <div id="interactive-pages" class="interactive-pages"></div>
          </section>

          <section id="form-guide-structured-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header form-guide-panel-header--with-demo">
              <div class="form-guide-panel-header-intro">
                <p class="form-guide-panel-kicker">Guía textual</p>
                <h2>Guía texto del formulario</h2>
                <p class="form-guide-panel-note">Toca cualquier fila con <strong>Cas. N</strong> para abrir una <strong>ficha completa</strong> del campo. Resumen completo por secciones para revisar antes de diligenciar y presentar.</p>
              </div>
              <div class="form-guide-panel-demo" aria-hidden="true">
                <svg class="form-guide-panel-illustration" viewBox="0 0 200 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustración: un dedo toca una fila de la lista para abrir la ficha del campo">
                  <defs>
                    <radialGradient id="fg-panel-illu-glow" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="rgba(20, 115, 83, 0.32)"/>
                      <stop offset="100%" stop-color="rgba(20, 115, 83, 0)"/>
                    </radialGradient>
                  </defs>
                  <circle cx="108" cy="60" r="30" fill="url(#fg-panel-illu-glow)"/>
                  <rect x="14" y="10" width="124" height="86" rx="9" fill="#ffffff" stroke="rgba(22,49,41,0.14)" stroke-width="1"/>
                  <rect x="26" y="20" width="46" height="3.5" rx="1.75" fill="rgba(22,49,41,0.38)"/>
                  <rect x="26" y="27" width="28" height="3" rx="1.5" fill="rgba(22,49,41,0.18)"/>
                  <rect x="26" y="40" width="12" height="8" rx="2" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.4)" stroke-width="0.7"/>
                  <rect x="42" y="42" width="64" height="3.5" rx="1.75" fill="rgba(22,49,41,0.2)"/>
                  <rect x="22" y="54" width="108" height="18" rx="5" fill="rgba(20,115,83,0.14)" stroke="rgba(20,115,83,0.55)" stroke-width="1.2"/>
                  <rect x="28" y="60" width="14" height="8" rx="2.2" fill="rgba(20,115,83,0.92)"/>
                  <text x="35" y="66" text-anchor="middle" fill="#ffffff" font-family="ui-sans-serif, system-ui" font-size="5.6" font-weight="700">2</text>
                  <rect x="46" y="59.2" width="58" height="3.5" rx="1.75" fill="rgba(20,115,83,0.55)"/>
                  <rect x="46" y="64.8" width="38" height="3" rx="1.5" fill="rgba(20,115,83,0.35)"/>
                  <rect x="26" y="80" width="12" height="8" rx="2" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.4)" stroke-width="0.7"/>
                  <rect x="42" y="82" width="50" height="3.5" rx="1.75" fill="rgba(22,49,41,0.2)"/>
                  <g class="form-guide-panel-illu-ripple">
                    <circle cx="108" cy="62.5" r="10" fill="none" stroke="rgba(20,115,83,0.5)" stroke-width="1.3"/>
                    <circle cx="108" cy="62.5" r="5.5" fill="none" stroke="rgba(20,115,83,0.72)" stroke-width="1.3"/>
                  </g>
                  <g transform="translate(87 56.5) scale(1.8)">
                    <g class="form-guide-panel-illu-hand">
                      <path fill="#163129" stroke="#ffffff" stroke-width="0.6" stroke-linejoin="round" d="M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z"/>
                    </g>
                  </g>
                </svg>
              </div>
            </header>
            <div id="structured-sections" class="structured-sections"></div>
          </section>
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
  `}function q(e){const c=String(e||"").trim();return c&&(c.startsWith("/")||/^https?:\/\//i.test(c))?c:""}function ie(e){for(const c of e){const u=q(c.url);if(u&&String(c.source_type||"").trim().toLowerCase()==="formulario_oficial_pdf")return{url:u,authority:String(c.authority||"").trim()}}return{url:"",authority:""}}function l(e){return W(String(e??"").trim())}function j(e){if(typeof e.showModal=="function"){e.open||e.showModal();return}e.setAttribute("open","true")}function F(e){if(typeof e.close=="function"&&e.open){e.close();return}e.removeAttribute("open")}function re(e){return e.open||e.hasAttribute("open")}function M(e){const c=document.getElementById("view-structured-btn"),u=document.getElementById("view-interactive-btn");if(!c||!u)return;const v=e==="interactive"&&!u.hasAttribute("disabled");u.classList.toggle("view-toggle-active",v),c.classList.toggle("view-toggle-active",!v),u.setAttribute("aria-selected",v?"true":"false"),c.setAttribute("aria-selected",v?"false":"true")}function oe(e){return String(e.label||(e.casilla?`Casilla ${e.casilla}`:"este campo")).trim()}function ae(e){return e.casilla?String(e.casilla):e.label?e.label:"Campo"}function ne(e){if(!Array.isArray(e.marker_bbox)||e.marker_bbox.length!==4)return null;const c=e.marker_bbox.map(u=>Number(u));return c.every(u=>Number.isFinite(u))?c:null}function le(e){const c=ne(e);if(c){const[u,v,_,f]=c,s=e.bbox,x=Array.isArray(s)&&s.length===4&&s.every(E=>Number.isFinite(Number(E)))&&Math.abs(u-Number(s[0]))<.05&&Math.abs(v-Number(s[1]))<.05&&Math.abs(f-Number(s[3]))<.05&&_<Number(s[2])*.7,h=u+_/2;if(x)return{left:h,top:v,translateX:"-50%",translateY:"0",markerCenterX:h,markerCenterY:v+f/2};const I=v+f/2;return{left:h,top:I,translateX:"-50%",translateY:"-50%",markerCenterX:h,markerCenterY:I}}return{left:e.bbox[0],top:e.bbox[1],translateX:"0",translateY:"0",markerCenterX:null,markerCenterY:null}}function d(e){const c=document.createElement("div");return c.appendChild(document.createTextNode(e)),c.innerHTML}function se({state:e}){function c(f,s,g,x=""){const h=document.createElement("div");h.className=`form-guide-chat-bubble form-guide-chat-${s} ${x}`.trim();const I=document.createElement("p");I.className="chat-bubble-role",I.textContent=s==="user"?"Tú":"LIA",h.appendChild(I);const E=document.createElement("div");E.className="chat-bubble-body",s==="assistant"?O(E,g):E.textContent=l(g),h.appendChild(E),f.appendChild(h),f.scrollTop=f.scrollHeight,e.chatMessages.push({role:s,text:g})}function u(f,s){const g=document.createElement("div");g.className="form-guide-chat-handoff";const x=document.createElement("p");x.className="form-guide-chat-handoff-helper",x.textContent="Esta pregunta se abrirá en el chat general y quedará como borrador para que la continúes allá.";const h=document.createElement("a");h.className="secondary-btn",h.href=s,h.target="_blank",h.rel="noopener noreferrer",h.textContent="Continuar en el chat general",g.append(x,h),f.appendChild(g),f.scrollTop=f.scrollHeight}function v(f){const s=document.createElement("div");return s.className="form-guide-chat-bubble form-guide-chat-thinking",s.setAttribute("aria-live","polite"),s.setAttribute("aria-label","Pensando"),s.innerHTML=`
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
    `,f.appendChild(s),f.scrollTop=f.scrollHeight,s}function _(){const f=document.getElementById("form-guide-chat-form"),s=document.getElementById("form-guide-chat-input"),g=document.getElementById("form-guide-chat-log");!f||!s||!g||(f.onsubmit=async x=>{var E;x.preventDefault();const h=s.value.trim();if(!h)return;c(g,"user",h),s.value="",s.disabled=!0;const I=v(g);try{const{data:$}=await J("/api/form-guides/chat",{reference_key:e.currentReferenceKey,profile:e.currentProfile,message:h,selected_field_id:e.selectedFieldId,selected_page:null,active_section:e.selectedSection});if(I.remove(),$&&$.ok){const G=$.answer_mode==="pedagogical"?"":"chat-refusal";if(c(g,"assistant",$.answer_markdown,G),$.answer_mode==="out_of_scope_refusal"){const B=q((E=$.grounding)==null?void 0:E.handoff_url);B&&u(g,B)}if($.suggested_followups&&$.suggested_followups.length>0){const B=$.suggested_followups.map(P=>`<button class="followup-btn" type="button">${d(l(P))}</button>`).join(""),S=document.createElement("div");S.className="chat-followups",S.innerHTML=B,S.addEventListener("click",P=>{const L=P.target.closest(".followup-btn");L&&(s.value=L.textContent||"",f.dispatchEvent(new Event("submit",{bubbles:!0,cancelable:!0})))}),g.appendChild(S)}}else c(g,"assistant","Error procesando tu pregunta. Intenta de nuevo.")}catch{I.remove(),c(g,"assistant","Error de conexión. Intenta de nuevo.")}finally{s.disabled=!1,s.focus()}})}return{bindChatForm:_}}function ce(e,c){return e.guide?e.guide:e.reference_key&&Array.isArray(e.available_profiles)?{reference_key:e.reference_key,title:e.title||"",form_version:e.form_version||"",available_profiles:e.available_profiles,supported_views:e.supported_views||[],last_verified_date:e.last_verified_date||"",download_available:!!e.download_available,disclaimer:e.disclaimer||""}:Array.isArray(e.guides)&&e.guides.length>0?e.guides.find(u=>u.reference_key===c)||e.guides[0]:null}function de({state:e,onContentLoaded:c,onError:u,showLoading:v,showProfileSelector:_}){async function f(){try{const g=await z(`/api/form-guides/content?reference_key=${encodeURIComponent(e.currentReferenceKey)}&profile=${encodeURIComponent(e.currentProfile)}&view=structured`);if(!g.ok){u("No se pudo cargar el contenido de la guía.");return}e.guideSources=g.sources||[],e.guidePageAssets=g.page_assets||[];const x=ie(e.guideSources);e.guideOfficialPdfUrl=q(g.official_pdf_url)||x.url,e.guideOfficialPdfAuthority=String(g.official_pdf_authority||x.authority||"").trim(),c(g)}catch{u("Error cargando el contenido de la guía.")}}async function s(){try{const g=await z(`/api/form-guides/catalog?reference_key=${encodeURIComponent(e.currentReferenceKey)}`),x=ce(g,e.currentReferenceKey);if(!g.ok||!x){u("Esta guía aún no está disponible.");return}if(x.available_profiles.length>1&&!e.currentProfile){_(x,h=>{e.currentProfile=h,v(),f()});return}!e.currentProfile&&x.available_profiles.length===1&&(e.currentProfile=x.available_profiles[0].profile_id),await f()}catch{u("Error cargando la guía. Intenta de nuevo.")}}return{loadCatalog:s,loadContent:f}}function ue(){return{currentReferenceKey:"",currentProfile:"",selectedFieldId:null,selectedSection:null,chatMessages:[],guideSources:[],guidePageAssets:[],guideOfficialPdfUrl:"",guideOfficialPdfAuthority:"",guideSectionsById:new Map,guideHotspotsById:new Map,guideViewObserver:null}}function fe({state:e}){function c(t){const i=document.createElement("div");return O(i,t),l(i.textContent||"")}function u(t){return c(t).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/gi," ").trim().toLowerCase()}function v(t,i){const a=u(t.instruction_md||"");if(!a)return!0;const r=u((i==null?void 0:i.title)||""),n=!!(t.casilla&&a.includes(`casilla ${t.casilla}`))&&!!(r&&a.includes(r)),p=a.includes("revise la casilla")||a.includes("verifique la casilla")||a.includes("dentro de la seccion")||a.includes("antes de presentar"),b=!l(t.what_to_review_before_filling||"")&&!l(t.common_errors||"")&&!l(t.warnings||"");return p&&n&&b}function _(t,i){const a=u(t),r=u(i);return!a||!r?!1:a.includes(r)||r.includes(a)}function f(){if(document.querySelectorAll(".guide-hotspot-active").forEach(t=>t.classList.remove("guide-hotspot-active")),document.querySelectorAll(".guide-section-active").forEach(t=>t.classList.remove("guide-section-active")),e.selectedFieldId){const t=document.querySelector(`.guide-hotspot[data-field-id="${e.selectedFieldId}"]`);t==null||t.classList.add("guide-hotspot-active")}if(e.selectedSection){const t=document.querySelector(`.guide-section[data-section-id="${e.selectedSection}"]`);t==null||t.classList.add("guide-section-active")}}function s(){const t=document.getElementById("form-guide-chat-context");if(t){if(e.selectedFieldId){const i=e.guideHotspotsById.get(e.selectedFieldId),a=e.selectedSection?e.guideSectionsById.get(e.selectedSection):void 0,r=i!=null&&i.casilla?`Casilla ${i.casilla} — ${l(i.label)}`:l((i==null?void 0:i.label)||e.selectedFieldId);t.textContent=a?`Contexto: ${r} · ${l(a.title)}`:`Contexto: ${r}`;return}if(e.selectedSection){const i=e.guideSectionsById.get(e.selectedSection);t.textContent=`Contexto: ${l((i==null?void 0:i.title)||e.selectedSection)}`;return}t.textContent=""}}function g(t){const i=document.getElementById("form-guide-field-dialog"),a=document.getElementById("field-dialog-title"),r=document.getElementById("field-dialog-eyebrow"),n=document.getElementById("field-dialog-meta"),p=document.getElementById("field-dialog-summary"),b=document.getElementById("field-dialog-body");if(!i||!a||!r||!n||!p||!b)return;const o=e.guideSectionsById.get(t.section),m=l(oe(t)),y=l(t.official_dian_instruction||""),w=String(t.instruction_md||"").trim();l(w);const T=!!w&&!v(t,o)&&(!y||!_(y,w)),H=l(t.what_to_review_before_filling||"");i.dataset.fieldId=t.field_id,i.dataset.sectionId=t.section,a.textContent=t.casilla?`Casilla ${t.casilla} — ${l(t.label)}`:l(t.label),r.textContent=l((o==null?void 0:o.title)||"Campo guiado"),n.innerHTML=[t.casilla?`<span class="field-dialog-chip">Casilla ${t.casilla}</span>`:"",t.año_gravable?`<span class="field-dialog-chip">AG ${d(t.año_gravable)}</span>`:"",`<span class="field-dialog-chip">Página ${t.page}</span>`,o!=null&&o.title?`<span class="field-dialog-chip field-dialog-chip-soft">${d(l(o.title))}</span>`:""].filter(Boolean).join(""),p.textContent=H,p.hidden=!H;const C=[];if(T){const D=(t.source_ids||[]).map(A=>e.guideSources.find(V=>V.source_id===A)).filter(Boolean).map(A=>A.authority).filter((A,V,Q)=>A&&Q.indexOf(A)===V),K=D.length>0?`<span class="field-dialog-source-badge">Fuente: ${d(D.join(", "))}</span>`:"";C.push(`
        <article class="field-dialog-card field-dialog-card-primary">
          <p class="guide-section-label">${y?"Cómo diligenciar":"Indicación principal"}: ${d(m)}</p>
          <div data-field-dialog-markdown="fallback" class="field-dialog-markdown"></div>
          ${K}
        </article>
      `)}if(y&&C.push(`
        <article class="field-dialog-card field-dialog-card-dian">
          <p class="guide-section-label dian-official-label">Instrucción DIAN para ${d(m)}</p>
          <p>${d(y)}</p>
          <span class="dian-official-badge">Recomendación Oficial DIAN</span>
        </article>
      `),t.what_to_review_before_filling&&C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Qué revisar en ${d(m)}</p>
          <p>${d(l(t.what_to_review_before_filling))}</p>
        </article>
      `),t.common_errors&&C.push(`
        <article class="field-dialog-card field-dialog-card-errors">
          <p class="guide-section-label">Errores frecuentes en ${d(m)}</p>
          <p>${d(l(t.common_errors))}</p>
        </article>
      `),t.warnings&&C.push(`
        <article class="field-dialog-card field-dialog-card-warnings">
          <p class="guide-section-label">Advertencias para ${d(m)}</p>
          <p>${d(l(t.warnings))}</p>
        </article>
      `),!T&&!y&&!t.what_to_review_before_filling&&!t.common_errors&&!t.warnings&&C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Detalle específico pendiente</p>
          <p>Esta casilla ya está ubicada y titulada, pero su comentario puntual aún no está curado con suficiente detalle.</p>
        </article>
      `),o!=null&&o.title||o!=null&&o.purpose||o!=null&&o.profile_differences){const D=[o!=null&&o.title?`<p><strong>Sección:</strong> ${d(l(o.title))}</p>`:"",o!=null&&o.purpose?`<p><strong>Para qué sirve:</strong> ${d(l(o.purpose))}</p>`:"",o!=null&&o.profile_differences?`<p><strong>Diferencias por perfil:</strong> ${d(l(o.profile_differences))}</p>`:""].filter(Boolean);C.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Contexto de la sección</p>
          ${D.join("")}
        </article>
      `)}b.innerHTML=C.join("");const R=b.querySelector('[data-field-dialog-markdown="fallback"]');R&&w&&O(R,w),j(i)}function x(t,i){const a=t.filter(n=>n.section===i).sort((n,p)=>(n.casilla||0)-(p.casilla||0));if(a.length===0)return"";const r=a.map(n=>{const p=n.casilla?`<span class="campo-casilla">Cas. ${n.casilla}</span>`:"",b=d(l(n.label)),o=n.instruction_md?d(c(n.instruction_md).slice(0,160)):"",m=o.length>=160?o+"…":o;return`
          <li class="campo-item" data-campo-field-id="${n.field_id}" role="button" tabindex="0">
            <div class="campo-header">${p}<span class="campo-label">${b}</span></div>
            ${m?`<p class="campo-instruction">${m}</p>`:""}
            <span class="campo-open-icon" aria-hidden="true" title="Ver ficha completa">${Z.externalLink}</span>
          </li>
        `}).join("");return`
      <div class="guide-section-block guide-section-campos">
        <p class="guide-section-label">Campos de esta sección (${a.length})</p>
        <ul class="campo-list">${r}</ul>
      </div>
    `}function h(t,i){const a=document.getElementById("structured-sections");a&&(a.innerHTML=t.map(r=>`
        <article class="guide-section" data-section-id="${r.section_id}">
          <h3 class="guide-section-title">${d(l(r.title))}</h3>
          ${r.purpose?`<div class="guide-section-block"><p class="guide-section-label">Para qué sirve</p><p>${d(l(r.purpose))}</p></div>`:""}
          ${r.what_to_review?`<div class="guide-section-block"><p class="guide-section-label">Qué revisar antes de diligenciar</p><p>${d(l(r.what_to_review))}</p></div>`:""}
          ${r.profile_differences?`<div class="guide-section-block"><p class="guide-section-label">Diferencias por perfil</p><p>${d(l(r.profile_differences))}</p></div>`:""}
          ${x(i,r.section_id)}
          ${r.common_errors?`<div class="guide-section-block guide-section-errors"><p class="guide-section-label">Errores frecuentes</p><p>${d(l(r.common_errors))}</p></div>`:""}
          ${r.warnings?`<div class="guide-section-block guide-section-warnings"><p class="guide-section-label">Advertencias</p><p>${d(l(r.warnings))}</p></div>`:""}
        </article>
      `).join(""),a.onclick=r=>{const n=r.target.closest("[data-campo-field-id]");if(n){const b=n.dataset.campoFieldId||"",o=e.guideHotspotsById.get(b);o&&(e.selectedFieldId=b,e.selectedSection=o.section,f(),s(),g(o));return}const p=r.target.closest("[data-section-id]");p&&(e.selectedSection=p.dataset.sectionId||null,e.selectedFieldId=null,f(),s())})}function I(t){const i=document.getElementById("interactive-pages");i&&(i.innerHTML=`
      <section class="guide-page-card guide-page-card-empty">
        <div class="guide-page-header">
          <div>
            <h3 class="interactive-page-title">Guía gráfica no disponible</h3>
            <p>Este formulario aún no tiene mapa de campos publicado.</p>
          </div>
        </div>
        <div class="guide-document-fallback">${d(t)}</div>
      </section>
    `)}function E(t,i){const a=new Map;t.forEach(o=>{const m=a.get(o.page)||[];m.push(o),a.set(o.page,m)});const r=document.getElementById("interactive-pages");if(!r)return;const n=new Map;i.forEach(o=>{n.set(o.page,o)});const p=(a.size>0?Array.from(a.keys()):Array.from(n.keys())).sort((o,m)=>o-m);r.innerHTML=p.map(o=>{const m=n.get(o),y=a.get(o)||[];return`
          <section class="guide-page-card" data-guide-page="${o}">
            <div class="guide-page-header">
              <div>
                <h3 class="interactive-page-title">Página ${o}</h3>
                <p>${y.length} campo(s) guiado(s)</p>
              </div>
              <div class="guide-page-helper">Haz clic en un campo para abrir o cerrar la ficha.</div>
            </div>
            <div class="guide-document-frame">
              ${m?`<img class="guide-document-image" src="${d(m.url)}" alt="Vista exacta página ${o} del formulario" />`:'<div class="guide-document-fallback">No hay asset publicado para esta página.</div>'}
              <div class="guide-hotspot-layer">
                ${y.map(w=>{const k=le(w);return`
                      <button
                        class="guide-hotspot"
                        type="button"
                        data-field-id="${w.field_id}"
                        data-casilla="${w.casilla||""}"
                        data-section="${w.section}"
                        data-page="${w.page}"
                        data-marker-x="${k.markerCenterX??""}"
                        data-marker-y="${k.markerCenterY??""}"
                        data-anchor-mode="${k.translateY==="0"?"top":"center"}"
                        aria-label="Abrir o cerrar detalle de ${d(l(w.label))}"
                        style="left:${k.left}%;top:${k.top}%;--guide-hotspot-translate-x:${k.translateX};--guide-hotspot-translate-y:${k.translateY};"
                      >
                        <span class="guide-hotspot-pill">${d(ae(w))}</span>
                      </button>
                    `}).join("")}
              </div>
            </div>
          </section>
        `}).join("");const b=Array.from(a.values()).flat();r.onclick=o=>{const m=o.target.closest("[data-field-id]");if(!m)return;const y=m.dataset.fieldId||"",w=b.find(H=>H.field_id===y);if(!w)return;const k=document.getElementById("form-guide-field-dialog"),T=!!(k&&k.dataset.fieldId===y&&re(k));if(e.selectedFieldId=y,e.selectedSection=w.section,f(),s(),T&&k){F(k);return}g(w)}}function $(){var p;const t=document.getElementById("view-structured-btn"),i=document.getElementById("view-interactive-btn"),a=document.getElementById("form-guide-structured-view"),r=document.getElementById("form-guide-interactive-view"),n=document.querySelector(".form-guide-main");!t||!i||!a||!r||(t.onclick=()=>{M("structured"),a.scrollIntoView({block:"start",behavior:"smooth"})},i.onclick=()=>{i.hasAttribute("disabled")||(M("interactive"),r.scrollIntoView({block:"start",behavior:"smooth"}))},(p=e.guideViewObserver)==null||p.disconnect(),typeof IntersectionObserver=="function"&&(e.guideViewObserver=new IntersectionObserver(b=>{const m=b.filter(y=>y.isIntersecting).sort((y,w)=>w.intersectionRatio-y.intersectionRatio)[0];if(m){if(m.target===r&&!i.hasAttribute("disabled")){M("interactive");return}m.target===a&&M("structured")}},{root:n,threshold:[.35,.6,.85],rootMargin:"-12% 0px -45% 0px"}),e.guideViewObserver.observe(r),e.guideViewObserver.observe(a)))}function G(){const t=document.getElementById("form-guide-field-dialog"),i=document.getElementById("close-field-dialog");t&&(i&&(i.onclick=()=>F(t)),t.onclick=a=>{a.defaultPrevented||F(t)})}function B(){const t=document.getElementById("form-guide-sources-btn"),i=document.getElementById("form-guide-sources-dialog"),a=document.getElementById("close-sources-dialog"),r=document.getElementById("sources-list");!t||!i||!r||(t.onclick=()=>{r.innerHTML=e.guideSources.map(n=>`
          <div class="source-card ${n.is_primary?"source-primary":"source-secondary"}">
            <p class="source-title">${d(l(n.title))}</p>
            <p class="source-authority">${d(l(n.authority))} · ${n.is_primary?"Fuente primaria":"Fuente secundaria"}</p>
            ${n.url?`<a href="${d(n.url)}" target="_blank" rel="noopener noreferrer" class="source-link">Ver fuente</a>`:""}
            ${n.notes?`<p class="source-notes">${d(l(n.notes))}</p>`:""}
            <p class="source-checked">Verificada: ${d(n.last_checked_date)}</p>
          </div>
        `).join(""),j(i)},a&&(a.onclick=()=>F(i)),i.onclick=n=>{n.target===i&&F(i)})}function S(){const t=document.getElementById("form-guide-pdf-btn");t&&(t.disabled=!e.guideOfficialPdfUrl,t.title=e.guideOfficialPdfUrl?e.guideOfficialPdfAuthority?`Abre el PDF oficial publicado por ${e.guideOfficialPdfAuthority}`:"Abre el PDF oficial del formulario.":"Este formulario aún no tiene un PDF oficial publicado en la guía.",t.onclick=()=>{e.guideOfficialPdfUrl&&window.open(e.guideOfficialPdfUrl,"_blank","noopener,noreferrer")})}function P(){const t=document.querySelector(".form-guide-hamburger"),i=document.querySelector(".form-guide-mobile-menu");if(!t||!i)return;t.addEventListener("click",()=>{i.hidden=!i.hidden}),document.addEventListener("click",b=>{!i.hidden&&!i.contains(b.target)&&b.target!==t&&!t.contains(b.target)&&(i.hidden=!0)});const a=document.getElementById("form-guide-sources-btn-mobile"),r=document.getElementById("form-guide-sources-btn");a&&r&&a.addEventListener("click",()=>{i.hidden=!0,r.click()});const n=document.getElementById("form-guide-pdf-btn-mobile"),p=document.getElementById("form-guide-pdf-btn");n&&p&&n.addEventListener("click",()=>{i.hidden=!0,p.click()})}function L(){const t=document.getElementById("form-guide-loading"),i=document.getElementById("form-guide-profile-selector"),a=document.getElementById("form-guide-error"),r=document.getElementById("form-guide-content");t&&(t.hidden=!1),i&&(i.hidden=!0),a&&(a.hidden=!0),r&&(r.hidden=!0)}function U(t,i){const a=document.getElementById("form-guide-loading"),r=document.getElementById("form-guide-profile-selector"),n=document.getElementById("profile-options");a&&(a.hidden=!0),!(!r||!n)&&(r.hidden=!1,n.innerHTML=t.available_profiles.map(p=>`
          <button class="profile-option-btn" type="button" data-profile="${p.profile_id}">
            <strong>${l(p.profile_label)}</strong>
          </button>
        `).join(""),n.onclick=p=>{const b=p.target.closest("[data-profile]");b&&(r.hidden=!0,i(b.dataset.profile||""))})}function Y(t){const i=document.getElementById("form-guide-loading"),a=document.getElementById("form-guide-error"),r=document.getElementById("form-guide-error-message");i&&(i.hidden=!0),a&&(a.hidden=!1),r&&(r.textContent=l(t))}function X(t){const i=document.getElementById("form-guide-loading"),a=document.getElementById("form-guide-content"),r=document.getElementById("form-guide-disclaimer");e.guideSectionsById=new Map(t.structured_sections.map(k=>[k.section_id,k])),e.guideHotspotsById=new Map(t.interactive_map.map(k=>[k.field_id,k])),i&&(i.hidden=!0),a&&(a.hidden=!1);const n=document.getElementById("form-guide-title"),p=document.getElementById("form-guide-profile"),b=document.getElementById("form-guide-version"),o=document.getElementById("form-guide-verified");n&&(n.textContent=l(t.manifest.title)),p&&(p.textContent=l(t.manifest.profile_label)),b&&(b.textContent=l(t.manifest.form_version)),o&&(o.textContent=`Última verificación: ${t.manifest.last_verified_date}`),r&&t.disclaimer&&(r.textContent=l(t.disclaimer),r.hidden=!1),h(t.structured_sections,t.interactive_map);const m=document.getElementById("view-interactive-btn"),y=t.interactive_map.length>0&&e.guidePageAssets.length>0;!y&&m?(m.setAttribute("disabled","true"),m.title="Guía gráfica no disponible para esta guía",I("La guía textual sigue disponible mientras se publica el mapa gráfico certificado.")):m?(m.removeAttribute("disabled"),m.title="",E(t.interactive_map,e.guidePageAssets)):y&&E(t.interactive_map,e.guidePageAssets),$(),G(),B(),S(),P();const w=window.matchMedia("(max-width: 640px)").matches;M(w?"structured":y?"interactive":"structured"),f(),s()}return{renderGuide:X,showError:Y,showLoading:L,showProfileSelector:U}}function ge(e,c){const u=new URLSearchParams(window.location.search),v=ue();v.currentReferenceKey=u.get("reference_key")||"",v.currentProfile=u.get("profile")||"";const _=fe({state:v}),f=se({state:v}),s=de({state:v,onContentLoaded:_.renderGuide,onError:_.showError,showLoading:_.showLoading,showProfileSelector:_.showProfileSelector});if(!v.currentReferenceKey){_.showError("No se especificó un formulario.");return}f.bindChatForm(),s.loadCatalog()}const N=ee({missingRootMessage:"Missing #app root for form-guide page."});N.setTitle(N.i18n.t("app.title.formGuide")||"LIA - Guia de Formulario");new URLSearchParams(window.location.search).get("embed")==="1"&&document.body.classList.add("form-guide-embedded");N.mountShell(te());ge();
