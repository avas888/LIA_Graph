import{o as Q,f as W,d as X,e as Z}from"./brandMark-B4R1O0p6.js";import{s as y,i as ee}from"./format-CYFfBTRg.js";import{b as $}from"./button-1yFzSXrY.js";import{a as te}from"./stateBlock-CleM9k1B.js";import{i as g}from"./icons-BZwBwwSI.js";import"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./authGate-Bb2S6efH.js";import"./client-OE0sHIIg.js";import"./input-Byu2cnK9.js";import"./toasts-Dx3CUztl.js";import"./chip-Bjq03GaS.js";const M="mobile-form-guide-modal",ie="embed=1";function ne(r){return!r||/(^|[?&])embed=1(&|$)/.test(r)?r:r+(r.includes("?")?"&":"?")+ie}function w(){return document.getElementById(M)}function S(){const r=w();if(!r)return;r.classList.remove("is-open");const l=()=>{r.removeEventListener("transitionend",l),r.remove(),document.querySelector(".mobile-sheet-overlay.is-open")||(document.body.style.overflow="")};r.addEventListener("transitionend",l,{once:!0}),setTimeout(()=>{r.classList.contains("is-open")||(r.remove(),document.querySelector(".mobile-sheet-overlay.is-open")||(document.body.style.overflow=""))},400)}function se(r,l){var f,p;if(!r)return;S();const d=document.createElement("div");d.id=M,d.className="mobile-form-guide-modal-overlay",d.innerHTML=`
    <div class="mfgm-scrim"></div>
    <div class="mfgm-dialog" role="dialog" aria-modal="true" aria-label="${A(l)}">
      <header class="mfgm-chrome">
        <span class="mfgm-title">${q(l)}</span>
        <button type="button" class="mfgm-close" aria-label="Cerrar guía">&times;</button>
      </header>
      <iframe class="mfgm-iframe" src="${A(ne(r))}" title="${A(l)}"></iframe>
    </div>
  `,document.body.appendChild(d),document.body.style.overflow="hidden",d.offsetHeight,d.classList.add("is-open"),(f=d.querySelector(".mfgm-close"))==null||f.addEventListener("click",S),(p=d.querySelector(".mfgm-scrim"))==null||p.addEventListener("click",S)}let L=!1;function re(){L||(L=!0,document.addEventListener("click",r=>{const l=r.target,d=l==null?void 0:l.closest("[data-mobile-form-guide-url]");if(!d)return;r.preventDefault();const f=d.getAttribute("data-mobile-form-guide-url")||"",p=d.getAttribute("data-mobile-form-guide-title")||"Guía";se(f,p)}),document.addEventListener("keydown",r=>{r.key==="Escape"&&w()&&S()}))}function q(r){const l=document.createElement("div");return l.textContent=r,l.innerHTML}function A(r){return q(r).replace(/"/g,"&quot;")}function $e(r,l,d={}){const f=r.querySelector("#mobile-normativa-list"),p=r.querySelector("#mobile-normativa-empty");let v=[];re();function B(e){if(v=[...e],v.length===0){f.replaceChildren(),p.hidden=!1;return}p.hidden=!0,Z(f,v)}function T(){v=[],f.replaceChildren(),p.hidden=!1}f.addEventListener("click",e=>{const n=e.target.closest(".mobile-citation-card");if(!n||e.target.closest("a"))return;const t=parseInt(n.dataset.citationIndex??"-1",10),s=v[t];s&&K(s)}),document.addEventListener("click",e=>{const n=e.target.closest(".mobile-depth-item-link");if(!n)return;e.preventDefault();const t=n.dataset.docId||"",s=n.dataset.docLabel||"",i=n.dataset.knowledgeClass||"practica_erp";t&&Q(t,s,i)}),document.addEventListener("click",e=>{const n=e.target.closest(".mobile-sheet-annot-tab");if(!n||!n.dataset.tabIndex)return;const t=n.closest(".mobile-sheet-annot");if(!t)return;e.preventDefault();const s=n.dataset.tabIndex;t.querySelectorAll(".mobile-sheet-annot-tab").forEach(i=>{const o=i.dataset.tabIndex===s;i.setAttribute("aria-selected",o?"true":"false"),i.tabIndex=o?0:-1}),t.querySelectorAll(".mobile-sheet-annot-panel").forEach(i=>{const o=i.dataset.tabIndex===s;i.hidden=!o})});function j(){return`
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
    `}function _(e){const n=e.externalUrl?`<div class="mobile-sheet-actions">
           ${$({href:e.externalUrl,iconHtml:g.link,label:"Abrir en Normograma DIAN",className:"mobile-sheet-action-btn"}).outerHTML}
         </div>`:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          <strong>${m(e.title)}</strong> fue mencionada en la respuesta de LIA como soporte normativo.
          ${e.externalUrl?"":"<br><br>Esta normativa no está incluida aún en el corpus de LIA. Puedes buscarla directamente en fuentes oficiales."}
        </div>
      </div>
      ${n}
    `}function N(e){const n=e.externalUrl?$({href:e.externalUrl,iconHtml:g.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          No fue posible cargar el detalle de esta referencia normativa.
        </div>
      </div>
      ${n?`<div class="mobile-sheet-actions">${n}</div>`:""}
    `}function k(e,n){const t=[],s=D(e.caution_banner);s&&t.push(s);const i=String(e.binding_force||"").trim(),o=typeof e.binding_force_rank=="number"?e.binding_force_rank:0;i&&t.push(`
        <div class="mobile-sheet-section">
          <span class="mobile-sheet-badge" data-tone="${oe(i,o)}">${m(E(i))}</span>
        </div>
      `);const c=String(e.lead||"").trim();c&&t.push(`
        <div class="mobile-sheet-section">
          <div class="mobile-sheet-excerpt">${m(c)}</div>
        </div>
      `);const a=F(e.original_text,c);a&&t.push(a);const u=U(e),b=R(u);b&&t.push(b);const h=z(e.sections,e);h&&t.push(h);const H=Y(e.additional_depth_sections);H&&t.push(H);const x=J(e,n);return x&&t.push(x),t.join("")}function D(e){const n=String((e==null?void 0:e.title)||"").trim(),t=String((e==null?void 0:e.body)||"").trim();return!n&&!t?"":`
      <div class="mobile-sheet-caution" data-tone="${String((e==null?void 0:e.tone)||"").trim()}">
        ${n?`<strong>${m(n)}</strong>`:""}
        ${t?`<p>${m(t)}</p>`:""}
      </div>
    `}function F(e,n){if(!e)return"";const t=String(e.evidence_status||"").trim();if(t&&t!=="verified"&&t!=="missing")return"";const s=String(e.title||"").trim(),i=String(e.quote||"").trim();if(!s)return"";const o=n?`<p class="mobile-sheet-intro">${m(n)}</p>`:"",c=y(e.source_url),a=c?`<a class="mobile-sheet-source-link" href="${c}" target="_blank" rel="noopener noreferrer">Ver fuente del artículo</a>`:"";if(!i)return`
        <div class="mobile-sheet-section mobile-sheet-original-text">
          ${o}
          <h4 class="mobile-sheet-section-title">${m(s)}</h4>
          ${a}
        </div>
      `;const u=i.replace(/\r\n/g,`
`).split(/\n{2,}/).map(h=>h.trim()).filter(Boolean).map(h=>`<p>${m(h)}</p>`).join(""),b=P(e.annotations);return`
      <div class="mobile-sheet-section mobile-sheet-original-text">
        ${o}
        <h4 class="mobile-sheet-section-title">${m(s)}</h4>
        <blockquote class="mobile-sheet-quote">${u}</blockquote>
        ${b}
        ${a}
      </div>
    `}function O(e){const n=String(e||"").replace(/\r\n/g,`
`).trim();return n?n.split(/\n{2,}/).map(s=>s.trim()).filter(Boolean).map(s=>{const i=s.split(`
`).map(a=>a.trim()).filter(Boolean),o=/^[-•·]\s+/;return i.length>0&&i.every(a=>o.test(a))?`<ul class="mobile-sheet-annot-list">${i.map(u=>`<li>${m(u.replace(o,""))}</li>`).join("")}</ul>`:`<p>${m(i.join(" "))}</p>`}).join(""):""}function P(e){const n=Array.isArray(e)?e.map(i=>({label:String((i==null?void 0:i.label)||"").trim(),body:String((i==null?void 0:i.body)||"").trim()})).filter(i=>i.label&&i.body):[];if(n.length===0)return"";const t=n.map((i,o)=>`
        <button
          type="button"
          class="mobile-sheet-annot-tab"
          role="tab"
          data-tab-index="${o}"
          aria-selected="${o===0?"true":"false"}"
          tabindex="${o===0?0:-1}"
        >${m(i.label)}</button>`).join(""),s=n.map((i,o)=>`
        <div
          class="mobile-sheet-annot-panel"
          role="tabpanel"
          data-tab-index="${o}"
          ${o===0?"":"hidden"}
        >${O(i.body)}</div>`).join("");return`
      <div class="mobile-sheet-annot" data-count="${n.length}">
        <div class="mobile-sheet-annot-tabs" role="tablist">${t}</div>
        <div class="mobile-sheet-annot-panels">${s}</div>
      </div>
    `}function U(e){const n=Array.isArray(e.facts)?[...e.facts]:[],t=e.vigencia_detail;if(t&&ee(t.evidence_status)&&String(t.label||"").trim()){const i=String(t.summary||"").trim()||[String(t.label||"").trim(),String(t.basis||"").trim(),String(t.notes||"").trim(),String(t.last_verified_date||"").trim()?`Última verificación del corpus: ${String(t.last_verified_date||"").trim()}`:""].filter(Boolean).join(`
`),o=n.findIndex(a=>/vigencia/i.test(String((a==null?void 0:a.label)||""))),c={label:"Vigencia específica",value:i};o>=0?n.splice(o,1,c):n.push(c)}return n}function R(e){const n=e.filter(s=>s&&String(s.label||"").trim()&&String(s.value||"").trim());return n.length===0?"":`
      <div class="mobile-sheet-section">
        <h4 class="mobile-sheet-section-title">Datos clave</h4>
        <div class="mobile-sheet-facts">${n.map(s=>`
        <div class="mobile-sheet-fact">
          <span class="mobile-sheet-fact-label">${m(String(s.label||"").trim())}</span>
          <div class="mobile-sheet-fact-value">${I(String(s.value||"").trim())}</div>
        </div>`).join("")}</div>
      </div>
    `}function z(e,n){if(!Array.isArray(e))return"";const t=e.filter(i=>{if(!i||!String(i.title||"").trim()||!String(i.body||"").trim())return!1;const o=String(i.id||"").trim();return!(o==="texto_original_relevante"&&n.original_text||o==="comentario_experto_relevante"&&n.expert_comment||/instrumento de diligenciamiento/i.test(String(i.title||"").trim()))});return t.length===0?"":`<div class="mobile-sheet-section">${t.map(i=>`
        <article class="mobile-sheet-section-card">
          <h4 class="mobile-sheet-section-title">${m(String(i.title||"").trim())}</h4>
          <div class="mobile-sheet-section-body">${I(String(i.body||"").trim())}</div>
        </article>`).join("")}</div>`}function G(e){switch(e){case"normative_base":return{label:"Normativa",tone:"info"};case"interpretative_guidance":return{label:"Expertos",tone:"warning"};case"practica_erp":return{label:"Práctico",tone:"success"};default:return{label:"",tone:"neutral"}}}function V(e){const n=m(String(e.label||"").trim()),t=String(e.kind||"").trim(),s=String(e.doc_id||"").trim(),i=G(t),o=i.label?te({label:i.label,tone:i.tone}).outerHTML+" ":"";if(s)return`<li><a href="#" class="mobile-depth-item-link" data-doc-id="${m(s)}" data-doc-label="${n}" data-knowledge-class="${m(t)}">${o}${n}</a></li>`;const c=y(e.url);return c?`<li><a href="${c}" target="_blank" rel="noopener noreferrer">${o}${n}</a></li>`:`<li>${o}${n}</li>`}function Y(e){if(!Array.isArray(e))return"";const n=[...e].filter(Boolean).sort((s,i)=>{const o=String(s.accordion_default||"closed")==="open"?0:1,c=String(i.accordion_default||"closed")==="open"?0:1;return o-c}),t=[];for(const s of n){if(!s)continue;const i=String(s.title||"").trim()||"Contenido relacionado de posible utilidad",o=Array.isArray(s.items)?s.items.filter(b=>String((b==null?void 0:b.label)||"").trim()):[];if(!o.length)continue;const c=String(s.accordion_default||"closed")==="closed",u=`<ul class="mobile-sheet-bullet-list mobile-depth-list">${o.map(b=>V(b)).join("")}</ul>`;c?t.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card mobile-sheet-accordion">
              <details>
                <summary class="mobile-sheet-accordion-summary">${m(i)}</summary>
                ${u}
              </details>
            </article>
          </div>
        `):t.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card">
              <h4 class="mobile-sheet-section-title">${m(i)}</h4>
              ${u}
            </article>
          </div>
        `)}return t.join("")}function J(e,n){const t=[],s=e.source_action;if(s&&String(s.state||"").trim()!=="not_applicable"){const c=y(s.url),a=String(s.label||"Ir a documento original").trim();c&&t.push($({href:c,iconHtml:g.link,label:a,className:"mobile-sheet-action-btn"}).outerHTML)}const i=e.analysis_action;if(i&&String(i.state||"").trim()==="available"){const c=y(i.url),a=String(i.label||"Análisis profundo").trim();c&&t.push($({href:c,iconHtml:g.search,label:a,className:"mobile-sheet-action-btn"}).outerHTML)}const o=e.companion_action;if(o&&String(o.state||"").trim()==="available"){const c=y(o.url),a=String(o.label||"Guía de formulario").trim();c&&t.push(`<button type="button" class="mobile-sheet-action-btn" data-mobile-form-guide-url="${C(c)}" data-mobile-form-guide-title="${C(a)}"><span class="mobile-sheet-action-icon" aria-hidden="true">${g.bookOpen}</span><span>${m(a)}</span></button>`)}return t.length===0&&n.externalUrl&&t.push($({href:n.externalUrl,iconHtml:g.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML),t.length>0?`<div class="mobile-sheet-actions">${t.join("")}</div>`:""}async function K(e){var n;if(e.action!=="modal"){l.open({title:e.title,subtitle:e.meta,html:_(e)});return}if(!e.rawCitation){l.open({title:e.title,subtitle:e.meta,html:_(e)});return}l.open({title:e.title,subtitle:e.meta,html:j()}),(n=d.onOpenCitation)==null||n.call(d,e.id),le(r);try{const t=await W(e.rawCitation);if(!l.isOpen())return;if(t.skipped){l.open({title:e.title,subtitle:e.meta,html:_(e)});return}const i=String(t.title||"").trim()||e.title,o=String(t.binding_force||"").trim(),c=o?E(o):String(e.meta||"").trim();if(l.open({title:i,subtitle:c,html:k(t,e)}),t.needs_llm)try{const a=await X(e.rawCitation);if(!l.isOpen())return;const u={...t,lead:String(a.lead||"").trim()||t.lead,facts:Array.isArray(a.facts)&&a.facts.length>0?a.facts:t.facts,sections:Array.isArray(a.sections)&&a.sections.length>0?a.sections:t.sections,vigencia_detail:a.vigencia_detail??t.vigencia_detail};l.open({title:i,subtitle:c,html:k(u,e)})}catch{}}catch{if(!l.isOpen())return;l.open({title:e.title,subtitle:e.meta,html:N(e)})}}return{setCitations:B,clear:T}}function le(r){const l=r.querySelector("#modal-layer");l&&(l.hidden=!0);const d=r.querySelector("#modal-norma");d&&(d.classList.remove("is-open"),d.setAttribute("aria-hidden","true"))}function oe(r,l=0){if(l>=700)return"success";if(l>=300)return"warning";if(l>0)return"neutral";const d=r.toLowerCase();return d.includes("alta")?"success":d.includes("media")?"warning":/(rango constitucional|ley o estatuto|compilaci[oó]n tributaria|decreto reglamentario|precedente judicial|resoluci[oó]n dian)/.test(d)?"success":/(instrumento operativo|doctrina administrativa|circular administrativa)/.test(d)?"warning":"neutral"}function E(r){const l=String(r||"").trim();return l?/^fuerza\s+vinculante\b/i.test(l)?l:`Fuerza vinculante: ${l}`:""}function m(r){const l=document.createElement("div");return l.textContent=r,l.innerHTML}function C(r){return m(r).replace(/"/g,"&quot;")}function I(r){return r.replace(/\r\n/g,`
`).split(/\n{2,}/).map(l=>l.trim()).filter(Boolean).map(l=>`<p>${m(l)}</p>`).join("")}export{$e as mountMobileNormativaPanel};
