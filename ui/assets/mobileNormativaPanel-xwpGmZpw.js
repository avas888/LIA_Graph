import{o as P,f as D,d as R,e as z}from"./brandMark-Danz1uVP.js";import{s as g,i as V}from"./format-CYFfBTRg.js";import{b}from"./button-1yFzSXrY.js";import{a as G}from"./stateBlock-CleM9k1B.js";import{i as p}from"./icons-D0mOOFcM.js";import"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./authGate-Bb2S6efH.js";import"./client-OE0sHIIg.js";import"./input-Byu2cnK9.js";import"./toasts-tYrWECOz.js";import"./chip-Bjq03GaS.js";function at(m,r,d={}){const v=m.querySelector("#mobile-normativa-list"),S=m.querySelector("#mobile-normativa-empty");let h=[];function C(t){if(h=[...t],h.length===0){v.replaceChildren(),S.hidden=!1;return}S.hidden=!0,z(v,h)}function L(){h=[],v.replaceChildren(),S.hidden=!1}v.addEventListener("click",t=>{const i=t.target.closest(".mobile-citation-card");if(!i||t.target.closest("a"))return;const e=parseInt(i.dataset.citationIndex??"-1",10),n=h[e];n&&U(n)}),document.addEventListener("click",t=>{const i=t.target.closest(".mobile-depth-item-link");if(!i)return;t.preventDefault();const e=i.dataset.docId||"",n=i.dataset.docLabel||"",s=i.dataset.knowledgeClass||"practica_erp";e&&P(e,n,s)});function T(){return`
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
    `}function $(t){const i=t.externalUrl?`<div class="mobile-sheet-actions">
           ${b({href:t.externalUrl,iconHtml:p.link,label:"Abrir en Normograma DIAN",className:"mobile-sheet-action-btn"}).outerHTML}
         </div>`:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          <strong>${c(t.title)}</strong> fue mencionada en la respuesta de LIA como soporte normativo.
          ${t.externalUrl?"":"<br><br>Esta normativa no está incluida aún en el corpus de LIA. Puedes buscarla directamente en fuentes oficiales."}
        </div>
      </div>
      ${i}
    `}function w(t){const i=t.externalUrl?b({href:t.externalUrl,iconHtml:p.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML:"";return`
      <div class="mobile-sheet-section">
        <div class="mobile-sheet-excerpt">
          No fue posible cargar el detalle de esta referencia normativa.
        </div>
      </div>
      ${i?`<div class="mobile-sheet-actions">${i}</div>`:""}
    `}function y(t,i){const e=[],n=I(t.caution_banner);n&&e.push(n);const s=String(t.binding_force||"").trim(),a=typeof t.binding_force_rank=="number"?t.binding_force_rank:0;s&&e.push(`
        <div class="mobile-sheet-section">
          <span class="mobile-sheet-badge" data-tone="${K(s,a)}">${c(x(s))}</span>
        </div>
      `);const l=String(t.lead||"").trim();l&&e.push(`
        <div class="mobile-sheet-section">
          <div class="mobile-sheet-excerpt">${c(l)}</div>
        </div>
      `);const o=M(t.original_text,l);o&&e.push(o);const f=N(t),u=B(f);u&&e.push(u);const _=j(t.sections,t);_&&e.push(_);const H=F(t.additional_depth_sections);H&&e.push(H);const k=O(t,i);return k&&e.push(k),e.join("")}function I(t){const i=String((t==null?void 0:t.title)||"").trim(),e=String((t==null?void 0:t.body)||"").trim();return!i&&!e?"":`
      <div class="mobile-sheet-caution" data-tone="${String((t==null?void 0:t.tone)||"").trim()}">
        ${i?`<strong>${c(i)}</strong>`:""}
        ${e?`<p>${c(e)}</p>`:""}
      </div>
    `}function M(t,i){if(!t)return"";const e=String(t.evidence_status||"").trim();if(e&&e!=="verified"&&e!=="missing")return"";const n=String(t.title||"").trim(),s=String(t.quote||"").trim();if(!n)return"";const a=i?`<p class="mobile-sheet-intro">${c(i)}</p>`:"",l=g(t.source_url),o=l?`<a class="mobile-sheet-source-link" href="${l}" target="_blank" rel="noopener noreferrer">Ver fuente del artículo</a>`:"";if(!s)return`
        <div class="mobile-sheet-section mobile-sheet-original-text">
          ${a}
          <h4 class="mobile-sheet-section-title">${c(n)}</h4>
          ${o}
        </div>
      `;const f=s.replace(/\r\n/g,`
`).split(/\n{2,}/).map(u=>u.trim()).filter(Boolean).map(u=>`<p>${c(u)}</p>`).join("");return`
      <div class="mobile-sheet-section mobile-sheet-original-text">
        ${a}
        <h4 class="mobile-sheet-section-title">${c(n)}</h4>
        <blockquote class="mobile-sheet-quote">${f}</blockquote>
        ${o}
      </div>
    `}function N(t){const i=Array.isArray(t.facts)?[...t.facts]:[],e=t.vigencia_detail;if(e&&V(e.evidence_status)&&String(e.label||"").trim()){const s=String(e.summary||"").trim()||[String(e.label||"").trim(),String(e.basis||"").trim(),String(e.notes||"").trim(),String(e.last_verified_date||"").trim()?`Última verificación del corpus: ${String(e.last_verified_date||"").trim()}`:""].filter(Boolean).join(`
`),a=i.findIndex(o=>/vigencia/i.test(String((o==null?void 0:o.label)||""))),l={label:"Vigencia específica",value:s};a>=0?i.splice(a,1,l):i.push(l)}return i}function B(t){const i=t.filter(n=>n&&String(n.label||"").trim()&&String(n.value||"").trim());return i.length===0?"":`
      <div class="mobile-sheet-section">
        <h4 class="mobile-sheet-section-title">Datos clave</h4>
        <div class="mobile-sheet-facts">${i.map(n=>`
        <div class="mobile-sheet-fact">
          <span class="mobile-sheet-fact-label">${c(String(n.label||"").trim())}</span>
          <div class="mobile-sheet-fact-value">${A(String(n.value||"").trim())}</div>
        </div>`).join("")}</div>
      </div>
    `}function j(t,i){if(!Array.isArray(t))return"";const e=t.filter(s=>{if(!s||!String(s.title||"").trim()||!String(s.body||"").trim())return!1;const a=String(s.id||"").trim();return!(a==="texto_original_relevante"&&i.original_text||a==="comentario_experto_relevante"&&i.expert_comment||/instrumento de diligenciamiento/i.test(String(s.title||"").trim()))});return e.length===0?"":`<div class="mobile-sheet-section">${e.map(s=>`
        <article class="mobile-sheet-section-card">
          <h4 class="mobile-sheet-section-title">${c(String(s.title||"").trim())}</h4>
          <div class="mobile-sheet-section-body">${A(String(s.body||"").trim())}</div>
        </article>`).join("")}</div>`}function q(t){switch(t){case"normative_base":return{label:"Normativa",tone:"info"};case"interpretative_guidance":return{label:"Expertos",tone:"warning"};case"practica_erp":return{label:"Práctico",tone:"success"};default:return{label:"",tone:"neutral"}}}function E(t){const i=c(String(t.label||"").trim()),e=String(t.kind||"").trim(),n=String(t.doc_id||"").trim(),s=q(e),a=s.label?G({label:s.label,tone:s.tone}).outerHTML+" ":"";if(n)return`<li><a href="#" class="mobile-depth-item-link" data-doc-id="${c(n)}" data-doc-label="${i}" data-knowledge-class="${c(e)}">${a}${i}</a></li>`;const l=g(t.url);return l?`<li><a href="${l}" target="_blank" rel="noopener noreferrer">${a}${i}</a></li>`:`<li>${a}${i}</li>`}function F(t){if(!Array.isArray(t))return"";const i=[...t].filter(Boolean).sort((n,s)=>{const a=String(n.accordion_default||"closed")==="open"?0:1,l=String(s.accordion_default||"closed")==="open"?0:1;return a-l}),e=[];for(const n of i){if(!n)continue;const s=String(n.title||"").trim()||"Contenido relacionado de posible utilidad",a=Array.isArray(n.items)?n.items.filter(u=>String((u==null?void 0:u.label)||"").trim()):[];if(!a.length)continue;const l=String(n.accordion_default||"closed")==="closed",f=`<ul class="mobile-sheet-bullet-list mobile-depth-list">${a.map(u=>E(u)).join("")}</ul>`;l?e.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card mobile-sheet-accordion">
              <details>
                <summary class="mobile-sheet-accordion-summary">${c(s)}</summary>
                ${f}
              </details>
            </article>
          </div>
        `):e.push(`
          <div class="mobile-sheet-section">
            <article class="mobile-sheet-section-card">
              <h4 class="mobile-sheet-section-title">${c(s)}</h4>
              ${f}
            </article>
          </div>
        `)}return e.join("")}function O(t,i){const e=[],n=t.source_action;if(n&&String(n.state||"").trim()!=="not_applicable"){const l=g(n.url),o=String(n.label||"Ir a documento original").trim();l&&e.push(b({href:l,iconHtml:p.link,label:o,className:"mobile-sheet-action-btn"}).outerHTML)}const s=t.analysis_action;if(s&&String(s.state||"").trim()==="available"){const l=g(s.url),o=String(s.label||"Análisis profundo").trim();l&&e.push(b({href:l,iconHtml:p.search,label:o,className:"mobile-sheet-action-btn"}).outerHTML)}const a=t.companion_action;if(a&&String(a.state||"").trim()==="available"){const l=g(a.url),o=String(a.label||"Guía de formulario").trim();l&&e.push(b({href:l,iconHtml:p.bookOpen,label:o,className:"mobile-sheet-action-btn"}).outerHTML)}return e.length===0&&i.externalUrl&&e.push(b({href:i.externalUrl,iconHtml:p.link,label:"Abrir fuente",className:"mobile-sheet-action-btn"}).outerHTML),e.length>0?`<div class="mobile-sheet-actions">${e.join("")}</div>`:""}async function U(t){var i;if(t.action!=="modal"){r.open({title:t.title,subtitle:t.meta,html:$(t)});return}if(!t.rawCitation){r.open({title:t.title,subtitle:t.meta,html:$(t)});return}r.open({title:t.title,subtitle:t.meta,html:T()}),(i=d.onOpenCitation)==null||i.call(d,t.id),J(m);try{const e=await D(t.rawCitation);if(!r.isOpen())return;if(e.skipped){r.open({title:t.title,subtitle:t.meta,html:$(t)});return}const s=String(e.title||"").trim()||t.title,a=String(e.binding_force||"").trim(),l=a?x(a):String(t.meta||"").trim();if(r.open({title:s,subtitle:l,html:y(e,t)}),e.needs_llm)try{const o=await R(t.rawCitation);if(!r.isOpen())return;const f={...e,lead:String(o.lead||"").trim()||e.lead,facts:Array.isArray(o.facts)&&o.facts.length>0?o.facts:e.facts,sections:Array.isArray(o.sections)&&o.sections.length>0?o.sections:e.sections,vigencia_detail:o.vigencia_detail??e.vigencia_detail};r.open({title:s,subtitle:l,html:y(f,t)})}catch{}}catch{if(!r.isOpen())return;r.open({title:t.title,subtitle:t.meta,html:w(t)})}}return{setCitations:C,clear:L}}function J(m){const r=m.querySelector("#modal-layer");r&&(r.hidden=!0);const d=m.querySelector("#modal-norma");d&&(d.classList.remove("is-open"),d.setAttribute("aria-hidden","true"))}function K(m,r=0){if(r>=700)return"success";if(r>=300)return"warning";if(r>0)return"neutral";const d=m.toLowerCase();return d.includes("alta")?"success":d.includes("media")?"warning":/(rango constitucional|ley o estatuto|compilaci[oó]n tributaria|decreto reglamentario|precedente judicial|resoluci[oó]n dian)/.test(d)?"success":/(instrumento operativo|doctrina administrativa|circular administrativa)/.test(d)?"warning":"neutral"}function x(m){const r=String(m||"").trim();return r?/^fuerza\s+vinculante\b/i.test(r)?r:`Fuerza vinculante: ${r}`:""}function c(m){const r=document.createElement("div");return r.textContent=m,r.innerHTML}function A(m){return m.replace(/\r\n/g,`
`).split(/\n{2,}/).map(r=>r.trim()).filter(Boolean).map(r=>`<p>${c(r)}</p>`).join("")}export{at as mountMobileNormativaPanel};
