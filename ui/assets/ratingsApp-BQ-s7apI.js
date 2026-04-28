import{g as F}from"./client-OE0sHIIg.js";import{r as U}from"./format-CYFfBTRg.js";import{a as T,c as D}from"./button-1yFzSXrY.js";import{a as w}from"./chip-Bjq03GaS.js";import{i as f}from"./icons-BZwBwwSI.js";import{c as j,b as z,T as y}from"./recordCollections-B45-VFE4.js";import{t as G,w as W,x as J,y as V}from"./brandMark-Cqvkq-MC.js";import"./bootstrap-BApbUZ11.js";import"./index-DF3uq1vv.js";import"./authGate-Bb2S6efH.js";import"./badge-UV61UhzD.js";import"./input-Byu2cnK9.js";import"./toasts-Dx3CUztl.js";import"./stateBlock-Dqw5sa9X.js";function o(n){const l=document.createElement("span");return l.textContent=n,l.innerHTML}function q(n){const l=Math.max(0,Math.min(5,n));return"★".repeat(l)+"☆".repeat(5-l)}function H(n){const l=new Date(n);if(isNaN(l.getTime()))return"";const e=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"],c=G(l),d=c.hour>=12?"p.m.":"a.m.",p=c.hour%12||12;return`${c.day} ${e[c.month]} ${c.year}, ${p}:${String(c.minute).padStart(2,"0")} ${d}`}function X(n){return n?n==="today"?W().toISOString():n==="week"?J().toISOString():n==="month"?V().toISOString():null:null}const C=50;function dt(n,{i18n:l}){const e={entries:[],loading:!1,errorMessage:"",userFilter:"",ratingFilter:new Set,timeFilter:"",offset:0,hasMore:!0};let c=[];n.innerHTML=`
    <div class="ratings-shell">
      <header class="ratings-header">
        <h1 class="ratings-title">Calificaciones de usuarios</h1>
        <div class="ratings-filters">
          <div class="ratings-user-dropdown"></div>
          <div class="ratings-time-chips" aria-label="Filtrar por periodo"></div>
          <div class="ratings-rating-chips" aria-label="Filtrar por calificacion"></div>
        </div>
      </header>
      <div class="ratings-list"></div>
      <div class="ratings-footer"></div>
      <dialog class="ratings-detail-dialog"></dialog>
    </div>
  `;const d=n.querySelector(".ratings-list"),p=n.querySelector(".ratings-footer"),v=j("Cargando calificaciones..."),g=n.querySelector(".ratings-detail-dialog"),S=n.querySelector(".ratings-user-dropdown"),x=n.querySelector(".ratings-time-chips"),N=n.querySelector(".ratings-rating-chips");async function h(t=!1){e.loading=!0,b();const a=new URLSearchParams({limit:String(C),offset:String(e.offset)});if(e.userFilter&&e.userFilter.startsWith(y)?a.set("tenant_id",e.userFilter.slice(y.length)):e.userFilter&&a.set("user_id",e.userFilter),e.ratingFilter.size>0){const i=[...e.ratingFilter];a.set("rating_min",String(Math.min(...i))),a.set("rating_max",String(Math.max(...i)))}const s=X(e.timeFilter);s&&a.set("since",s);try{const i=await F(`/api/admin/ratings?${a}`);let r=(i==null?void 0:i.ratings)||[];e.ratingFilter.size>0&&(r=r.filter(u=>e.ratingFilter.has(u.rating))),e.entries=t?[...e.entries,...r]:r,e.hasMore=r.length>=C,e.errorMessage=""}catch(i){console.error("Error loading ratings:",i),e.hasMore=!1,t||(e.entries=[]);const r=i;r.status===401||r.status===403?e.errorMessage="No tiene permisos para ver calificaciones. Verifique su sesion.":e.errorMessage=r.message||"Error al cargar calificaciones."}e.loading=!1,b()}function b(){if(e.loading&&e.entries.length===0){d.innerHTML="",d.appendChild(v.el),v.show(),p.innerHTML="";return}if(v.hide(),!e.loading&&e.entries.length===0){e.errorMessage?d.innerHTML=`<p class="ratings-error">${o(e.errorMessage)}</p>`:d.innerHTML='<p class="ratings-empty">No se encontraron calificaciones.</p>',p.innerHTML="";return}d.innerHTML=e.entries.map(k).join(""),e.hasMore?p.replaceChildren(D({label:"Cargar mas",tone:"ghost",className:"ratings-load-more"})):p.replaceChildren()}function k(t){const a=H(t.timestamp),s=q(t.rating),i=o((t.question_text||"").slice(0,120)),r=(t.question_text||"").length>120,u=t.comment?`<p class="rating-card-comment">${o(t.comment)}</p>`:"",m=t.tenant_id?`<span class="rating-card-tenant">${o(t.tenant_id)}</span>`:"";return`
      <div class="rating-card" data-trace-id="${o(t.trace_id)}">
        <div class="rating-card-header">
          <span class="rating-card-stars" aria-label="${t.rating} de 5">${s}</span>
          <span class="rating-card-user">${o(t.user_id||"Anonimo")}</span>
          ${m}
          <span class="rating-card-date">${a}</span>
        </div>
        <p class="rating-card-question">${i}${r?"...":""}</p>
        ${u}
      </div>
    `}function I(t){const a=q(t.rating),s=o(t.question_text||"(sin pregunta)"),i=t.comment?`<div class="rating-detail-section">
           <h3>Comentario</h3>
           <p>${o(t.comment)}</p>
         </div>`:"";g.innerHTML=`
      <div class="ratings-detail">
        <header class="rating-detail-header">
          <span class="rating-detail-stars" aria-label="${t.rating} de 5">${a}</span>
          <span class="rating-detail-actions" id="rating-detail-actions"></span>
        </header>
        <div class="rating-detail-section">
          <h3>Consulta</h3>
          <p>${s}</p>
        </div>
        <div class="rating-detail-section">
          <h3>Respuesta</h3>
          <div class="rating-detail-answer bubble-content"></div>
        </div>
        ${i}
        <div class="rating-detail-meta">
          <span>Usuario: ${o(t.user_id||"Anonimo")}</span>
          <span>Sesion: ${o(t.session_id||"—")}</span>
          <span>${H(t.timestamp)}</span>
        </div>
      </div>
    `;const r=g.querySelector(".rating-detail-answer");U(r,t.answer_text||"(sin respuesta)",{});const u=g.querySelector("#rating-detail-actions"),m=T({iconHtml:f.copy,tone:"ghost",className:"rating-detail-copy",attrs:{"aria-label":"Copiar contenido",title:"Copiar"},onClick:async()=>{var _;const R=`CONSULTA:
${t.question_text||""}

RESPUESTA:
${t.answer_text||""}`;await navigator.clipboard.writeText(R);const $=((_=m.querySelector("svg"))==null?void 0:_.parentElement)??m;$.innerHTML=f.checkCircle,m.setAttribute("title","Copiado!"),setTimeout(()=>{$.innerHTML=f.copy,m.setAttribute("title","Copiar")},1500)}});u.appendChild(m);const P=T({iconHtml:f.close,tone:"ghost",className:"rating-detail-close",attrs:{"aria-label":"Cerrar"},onClick:()=>g.close()});u.appendChild(P),g.showModal()}d.addEventListener("click",t=>{const a=t.target.closest(".rating-card");if(!a)return;const s=a.dataset.traceId,i=e.entries.find(r=>r.trace_id===s);i&&I(i)}),S.addEventListener("change",t=>{const a=t.target.closest("select");a&&(e.userFilter=a.value,e.offset=0,h())});const E=[{key:"",label:"Todos"},{key:"today",label:"Hoy"},{key:"week",label:"Esta semana"},{key:"month",label:"Este mes"}],L=[];E.forEach(({key:t,label:a})=>{const s=w({label:a,tone:t===""?"brand":"neutral",emphasis:t===""?"solid":"soft",className:"ratings-chip-toggle",onClick:()=>{e.timeFilter=t,e.offset=0,A(),h()}});L.push(s),x.appendChild(s)});function A(){L.forEach((t,a)=>{const s=e.timeFilter===E[a].key;t.classList.toggle("lia-chip--solid",s),t.classList.toggle("lia-chip--soft",!s),t.classList.toggle("lia-chip--brand",s),t.classList.toggle("lia-chip--neutral",!s)})}const O=["1 — Malo","2","3","4","5 — Bueno"],M=[];for(let t=1;t<=5;t++){const a=w({label:O[t-1],tone:"neutral",emphasis:"soft",className:"ratings-chip-toggle",onClick:()=>{e.ratingFilter.has(t)?e.ratingFilter.delete(t):e.ratingFilter.add(t),B(),e.offset=0,h()}});M.push(a),N.appendChild(a)}function B(){M.forEach((t,a)=>{const s=e.ratingFilter.has(a+1);t.classList.toggle("lia-chip--solid",s),t.classList.toggle("lia-chip--soft",!s),t.classList.toggle("lia-chip--brand",s),t.classList.toggle("lia-chip--neutral",!s)})}p.addEventListener("click",t=>{t.target.closest(".ratings-load-more")&&(e.offset+=C,h(!0))}),g.addEventListener("click",t=>{t.target===g&&g.close()}),F("/api/admin/tenants").then(t=>{c=((t==null?void 0:t.tenants)||[]).sort((i,r)=>i.display_name.localeCompare(r.display_name));const a=c.map(i=>({tenantLabel:i.display_name,users:(i.members||[]).map(r=>({userId:r.user_id,login:(r.email||"").split("@")[0]||r.user_id,displayName:r.display_name||r.user_id}))})).filter(i=>i.users.length>0),s=z(a,null,{includePublic:!0});s.className="ratings-tenant-filter",S.replaceChildren(s)}).catch(()=>{S.style.display="none"}).finally(()=>void h())}export{dt as mountRatingsApp};
