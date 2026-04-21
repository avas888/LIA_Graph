import{o as W,f as X,d as L,e as Z,g as ee,h as te,s as E,j as ie,k as ne,l as se}from"./brandMark-DFbqTxjh.js";import{s as v,i as le}from"./format-CYFfBTRg.js";import{b as y}from"./button-1yFzSXrY.js";import{a as re}from"./stateBlock-CleM9k1B.js";import{i as h}from"./icons-BZwBwwSI.js";import"./bootstrap-DAARwiGO.js";import"./index-BAf9D_ld.js";import"./authGate-Bb2S6efH.js";import"./client-OE0sHIIg.js";import"./input-Byu2cnK9.js";import"./toasts-Dx3CUztl.js";import"./chip-Bjq03GaS.js";const T="mobile-form-guide-modal",ae="embed=1";function oe(l){return!l||/(^|[?&])embed=1(&|$)/.test(l)?l:l+(l.includes("?")?"&":"?")+ae}function q(){return document.getElementById(T)}function S(){const l=q();if(!l)return;l.classList.remove("is-open");const a=()=>{l.removeEventListener("transitionend",a),l.remove(),document.querySelector(".mobile-sheet-overlay.is-open")||(document.body.style.overflow="")};l.addEventListener("transitionend",a,{once:!0}),setTimeout(()=>{l.classList.contains("is-open")||(l.remove(),document.querySelector(".mobile-sheet-overlay.is-open")||(document.body.style.overflow=""))},400)}function ce(l,a){var b,f;if(!l)return;S();const m=document.createElement("div");m.id=T,m.className="mobile-form-guide-modal-overlay",m.innerHTML=`
    <div class="mfgm-scrim"></div>
    <div class="mfgm-dialog" role="dialog" aria-modal="true" aria-label="${_(a)}">
      <header class="mfgm-chrome">
        <span class="mfgm-title">${B(a)}</span>
        <button type="button" class="mfgm-close" aria-label="Cerrar guía">&times;</button>
      </header>
      <iframe class="mfgm-iframe" src="${_(oe(l))}" title="${_(a)}"></iframe>
    </div>
  `,document.body.appendChild(m),document.body.style.overflow="hidden",m.offsetHeight,m.classList.add("is-open"),(b=m.querySelector(".mfgm-close"))==null||b.addEventListener("click",S),(f=m.querySelector(".mfgm-scrim"))==null||f.addEventListener("click",S)}let I=!1;function de(){I||(I=!0,document.addEventListener("click",l=>{const a=l.target,m=a==null?void 0:a.closest("[data-mobile-form-guide-url]");if(!m)return;l.preventDefault();const b=m.getAttribute("data-mobile-form-guide-url")||"",f=m.getAttribute("data-mobile-form-guide-title")||"Guía";ce(b,f)}),document.addEventListener("keydown",l=>{l.key==="Escape"&&q()&&S()}))}function B(l){const a=document.createElement("div");return a.textContent=l,a.innerHTML}function _(l){return B(l).replace(/"/g,"&quot;")}function d(l){const a=document.createElement("div");return a.textContent=String(l??""),a.innerHTML}function C(l){return d(l).replace(/"/g,"&quot;")}function M(l){return String(l??"").replace(/\r\n/g,`
`).split(/\n{2,}/).map(a=>a.trim()).filter(Boolean).map(a=>`<p>${d(a)}</p>`).join("")}function Ae(l,a,m={}){const b=l.querySelector("#mobile-normativa-list"),f=l.querySelector("#mobile-normativa-empty");let g=[];de();function w(e){if(g=[...e],g.length===0){b.replaceChildren(),f.hidden=!1;return}f.hidden=!0,te(b,g)}function j(){g=[],b.replaceChildren(),f.hidden=!1}b.addEventListener("click",e=>{const i=e.target.closest(".mobile-citation-card");if(!i||e.target.closest("a"))return;const t=parseInt(i.dataset.citationIndex??"-1",10),s=g[t];s&&Q(s)}),document.addEventListener("click",e=>{const i=e.target.closest(".mobile-depth-item-link");if(!i)return;e.preventDefault();const t=i.dataset.docId||"",s=i.dataset.docLabel||"",n=i.dataset.knowledgeClass||"practica_erp";t&&W(t,s,n)}),document.addEventListener("click",e=>{const i=e.target.closest(".mobile-sheet-annot-tab");if(!i||!i.dataset.tabIndex)return;const t=i.closest(".mobile-sheet-annot");if(!t)return;e.preventDefault();const s=i.dataset.tabIndex,n=i.getAttribute("aria-selected")==="true";t.querySelectorAll(".mobile-sheet-annot-tab").forEach(r=>{const o=r.dataset.tabIndex===s,c=o&&!n;r.setAttribute("aria-selected",c?"true":"false"),r.tabIndex=o?0:-1}),t.querySelectorAll(".mobile-sheet-annot-panel").forEach(r=>{const o=r.dataset.tabIndex===s;r.hidden=n||!o})});function N(){return`
      <div class="mobile-sheet-loader">
        <span class="lia-thinking-eye-pair">
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
        </span>
        <span class="mobile-sheet-loader-text">Consultando...</span>
      </div>
    `}function k(e){const i=e.externalUrl?`<div class="mobile-sheet-actions">
           ${y({href:e.externalUrl,iconHtml:h.link,label:"Abrir en Normograma DIAN",className:"mobile-sheet-action-btn"}).outerHTML}
         </div>`:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          <strong>${d(e.title)}</strong> fue mencionada en la respuesta de LIA como soporte normativo.
          ${e.externalUrl?"":"<br><br>Esta normativa no está incluida aún en el corpus de LIA. Puedes buscarla directamente en fuentes oficiales."}
        </div>
      </div>
      ${i}
    `}function D(e){const i=e.externalUrl?y({href:e.externalUrl,iconHtml:h.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          No fue posible cargar el detalle de esta referencia normativa.
        </div>
      </div>
      ${i?`<div class="mobile-sheet-actions">${i}</div>`:""}
    `}function A(e,i){const t=[],s=F(e.caution_banner);s&&t.push(s);const n=String(e.binding_force||"").trim(),r=typeof e.binding_force_rank=="number"?e.binding_force_rank:0;n&&t.push(`
        <div class="mobile-sheet-section">
          <span class="mobile-sheet-badge" data-tone="${ee(n,r)}">${d(L(n))}</span>
        </div>
      `);const o=String(e.lead||"").trim();o&&t.push(`
        <div class="mobile-sheet-section">
          <div class="mobile-sheet-excerpt">${d(o)}</div>
        </div>
      `);const c=O(e.original_text,o);c&&t.push(c);const p=R(e),u=G(p);u&&t.push(u);const $=V(e.sections,e);$&&t.push($);const x=J(e.additional_depth_sections);x&&t.push(x);const H=K(e,i);return H&&t.push(H),t.join("")}function F(e){const i=String((e==null?void 0:e.title)||"").trim(),t=String((e==null?void 0:e.body)||"").trim();return!i&&!t?"":`
      <div class="mobile-sheet-caution" data-tone="${String((e==null?void 0:e.tone)||"").trim()}">
        ${i?`<strong>${d(i)}</strong>`:""}
        ${t?`<p>${d(t)}</p>`:""}
      </div>
    `}function O(e,i){if(!e)return"";const t=String(e.evidence_status||"").trim();if(t&&t!=="verified"&&t!=="missing")return"";const s=String(e.title||"").trim(),n=String(e.quote||"").trim();if(!s)return"";const r=i?`<p class="mobile-sheet-intro">${d(i)}</p>`:"",o=v(e.source_url),c=o?`<a class="mobile-sheet-source-link" href="${o}" target="_blank" rel="noopener noreferrer">Ver fuente del artículo</a>`:"";if(!n)return`
        <div class="mobile-sheet-section mobile-sheet-original-text">
          ${r}
          <h4 class="mobile-sheet-section-title">${d(s)}</h4>
          ${c}
        </div>
      `;const p=E(n).map($=>`<p>${d($)}</p>`).join(""),u=U(e.annotations);return`
      <div class="mobile-sheet-section mobile-sheet-original-text">
        ${r}
        <h4 class="mobile-sheet-section-title">${d(s)}</h4>
        <blockquote class="mobile-sheet-quote">${p}</blockquote>
        ${u}
        ${c}
      </div>
    `}function P(e){return E(e).map(i=>{const t=ie(i);return ne(t)?`<ul class="mobile-sheet-annot-list">${t.map(n=>`<li>${d(se(n))}</li>`).join("")}</ul>`:`<p>${d(t.join(" "))}</p>`}).join("")}function U(e){const i=Array.isArray(e)?e.map(n=>({label:String((n==null?void 0:n.label)||"").trim(),body:String((n==null?void 0:n.body)||"").trim()})).filter(n=>n.label&&n.body):[];if(i.length===0)return"";const t=i.map((n,r)=>`
        <button
          type="button"
          class="mobile-sheet-annot-tab"
          role="tab"
          data-tab-index="${r}"
          aria-selected="false"
          tabindex="${r===0?0:-1}"
        >${d(n.label)}</button>`).join(""),s=i.map((n,r)=>`
        <div
          class="mobile-sheet-annot-panel"
          role="tabpanel"
          data-tab-index="${r}"
          hidden
        >${P(n.body)}</div>`).join("");return`
      <div class="mobile-sheet-annot" data-count="${i.length}">
        <div class="mobile-sheet-annot-tabs" role="tablist">${t}</div>
        <div class="mobile-sheet-annot-panels">${s}</div>
      </div>
    `}function R(e){const i=Array.isArray(e.facts)?[...e.facts]:[],t=e.vigencia_detail;if(t&&le(t.evidence_status)&&String(t.label||"").trim()){const n=String(t.summary||"").trim()||[String(t.label||"").trim(),String(t.basis||"").trim(),String(t.notes||"").trim(),String(t.last_verified_date||"").trim()?`Última verificación del corpus: ${String(t.last_verified_date||"").trim()}`:""].filter(Boolean).join(`
`),r=i.findIndex(c=>/vigencia/i.test(String((c==null?void 0:c.label)||""))),o={label:"Vigencia específica",value:n};r>=0?i.splice(r,1,o):i.push(o)}return i}function G(e){const i=e.filter(s=>s&&String(s.label||"").trim()&&String(s.value||"").trim());return i.length===0?"":`
      <div class="mobile-sheet-section">
        <h4 class="mobile-sheet-section-title">Datos clave</h4>
        <div class="mobile-sheet-facts">${i.map(s=>`
        <div class="mobile-sheet-fact">
          <span class="mobile-sheet-fact-label">${d(String(s.label||"").trim())}</span>
          <div class="mobile-sheet-fact-value">${M(String(s.value||"").trim())}</div>
        </div>`).join("")}</div>
      </div>
    `}function V(e,i){if(!Array.isArray(e))return"";const t=e.filter(n=>{if(!n||!String(n.title||"").trim()||!String(n.body||"").trim())return!1;const r=String(n.id||"").trim();return!(r==="texto_original_relevante"&&i.original_text||r==="comentario_experto_relevante"&&i.expert_comment||/instrumento de diligenciamiento/i.test(String(n.title||"").trim()))});return t.length===0?"":`<div class="mobile-sheet-section">${t.map(n=>`
        <article class="mobile-sheet-section-card">
          <h4 class="mobile-sheet-section-title">${d(String(n.title||"").trim())}</h4>
          <div class="mobile-sheet-section-body">${M(String(n.body||"").trim())}</div>
        </article>`).join("")}</div>`}function z(e){switch(e){case"normative_base":return{label:"Normativa",tone:"info"};case"interpretative_guidance":return{label:"Expertos",tone:"warning"};case"practica_erp":return{label:"Práctico",tone:"success"};default:return{label:"",tone:"neutral"}}}function Y(e){const i=d(String(e.label||"").trim()),t=String(e.kind||"").trim(),s=String(e.doc_id||"").trim(),n=z(t),r=n.label?re({label:n.label,tone:n.tone}).outerHTML+" ":"";if(s)return`<li><a href="#" class="mobile-depth-item-link" data-doc-id="${d(s)}" data-doc-label="${i}" data-knowledge-class="${d(t)}">${r}${i}</a></li>`;const o=v(e.url);return o?`<li><a href="${o}" target="_blank" rel="noopener noreferrer">${r}${i}</a></li>`:`<li>${r}${i}</li>`}function J(e){if(!Array.isArray(e))return"";const i=[...e].filter(Boolean).sort((s,n)=>{const r=String(s.accordion_default||"closed")==="open"?0:1,o=String(n.accordion_default||"closed")==="open"?0:1;return r-o}),t=[];for(const s of i){if(!s)continue;const n=String(s.title||"").trim()||"Contenido relacionado de posible utilidad",r=Array.isArray(s.items)?s.items.filter(u=>String((u==null?void 0:u.label)||"").trim()):[];if(!r.length)continue;const o=String(s.accordion_default||"closed")==="closed",p=`<ul class="mobile-sheet-bullet-list mobile-depth-list">${r.map(u=>Y(u)).join("")}</ul>`;o?t.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card mobile-sheet-accordion">
              <details>
                <summary class="mobile-sheet-accordion-summary">${d(n)}</summary>
                ${p}
              </details>
            </article>
          </div>
        `):t.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card">
              <h4 class="mobile-sheet-section-title">${d(n)}</h4>
              ${p}
            </article>
          </div>
        `)}return t.join("")}function K(e,i){const t=[],s=e.source_action;if(s&&String(s.state||"").trim()!=="not_applicable"){const o=v(s.url),c=String(s.label||"Ir a documento original").trim();o&&t.push(y({href:o,iconHtml:h.link,label:c,className:"mobile-sheet-action-btn"}).outerHTML)}const n=e.analysis_action;if(n&&String(n.state||"").trim()==="available"){const o=v(n.url),c=String(n.label||"Análisis profundo").trim();o&&t.push(y({href:o,iconHtml:h.search,label:c,className:"mobile-sheet-action-btn"}).outerHTML)}const r=e.companion_action;if(r&&String(r.state||"").trim()==="available"){const o=v(r.url),c=String(r.label||"Guía de formulario").trim();o&&t.push(`<button type="button" class="mobile-sheet-action-btn" data-mobile-form-guide-url="${C(o)}" data-mobile-form-guide-title="${C(c)}"><span class="mobile-sheet-action-icon" aria-hidden="true">${h.bookOpen}</span><span>${d(c)}</span></button>`)}return t.length===0&&i.externalUrl&&t.push(y({href:i.externalUrl,iconHtml:h.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML),t.length>0?`<div class="mobile-sheet-actions">${t.join("")}</div>`:""}async function Q(e){var i;if(e.action!=="modal"){a.open({title:e.title,subtitle:e.meta,html:k(e)});return}if(!e.rawCitation){a.open({title:e.title,subtitle:e.meta,html:k(e)});return}a.open({title:e.title,subtitle:e.meta,html:N()}),(i=m.onOpenCitation)==null||i.call(m,e.id),me(l);try{const t=await X(e.rawCitation);if(!a.isOpen())return;if(t.skipped){a.open({title:e.title,subtitle:e.meta,html:k(e)});return}const n=String(t.title||"").trim()||e.title,r=String(t.binding_force||"").trim(),o=r?L(r):String(e.meta||"").trim();if(a.open({title:n,subtitle:o,html:A(t,e)}),t.needs_llm)try{const c=await Z(e.rawCitation);if(!a.isOpen())return;const p={...t,lead:String(c.lead||"").trim()||t.lead,facts:Array.isArray(c.facts)&&c.facts.length>0?c.facts:t.facts,sections:Array.isArray(c.sections)&&c.sections.length>0?c.sections:t.sections,vigencia_detail:c.vigencia_detail??t.vigencia_detail};a.open({title:n,subtitle:o,html:A(p,e)})}catch{}}catch{if(!a.isOpen())return;a.open({title:e.title,subtitle:e.meta,html:D(e)})}}return{setCitations:w,clear:j}}function me(l){const a=l.querySelector("#modal-layer");a&&(a.hidden=!0);const m=l.querySelector("#modal-norma");m&&(m.classList.remove("is-open"),m.setAttribute("aria-hidden","true"))}export{Ae as mountMobileNormativaPanel};
