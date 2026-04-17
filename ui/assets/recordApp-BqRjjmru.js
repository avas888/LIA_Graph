import{g as _}from"./client-OE0sHIIg.js";import{g as E,b as M}from"./authGate-Bb2S6efH.js";import{T as S,b as U,d as H,e as L,f as P,t as D,a as B,c as R}from"./recordCollections-iJepLptp.js";import{k,l as F,T as $,n as I}from"./brandMark-Danz1uVP.js";import{r as O}from"./format-CYFfBTRg.js";import{a as T}from"./button-1yFzSXrY.js";import{i as C}from"./icons-D0mOOFcM.js";import"./chip-Bjq03GaS.js";import"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./stateBlock-CleM9k1B.js";import"./input-Byu2cnK9.js";import"./toasts-tYrWECOz.js";const A=50;function G(){return{sessions:[],activeTopicFilter:null,activeUserFilter:null,loading:!1,offset:0,hasMore:!0,error:null}}function J(t){var n;const r=new URLSearchParams,e=E();if((n=t.activeUserFilter)!=null&&n.startsWith(S))r.set("tenant_id",t.activeUserFilter.slice(S.length));else{const s=e.role==="platform_admin"?"__all__":e.tenantId||"public";r.set("tenant_id",s),t.activeUserFilter&&r.set("user_id",t.activeUserFilter)}return r.set("limit",String(A)),r.set("offset",String(t.offset)),r.set("status","active"),`/api/conversations?${r.toString()}`}async function W(t,r){const e=J(t);try{const s=(await _(e)).sessions??[];return{...t,sessions:r?[...t.sessions,...s]:s,hasMore:s.length>=A,loading:!1,error:null}}catch(n){return{...t,loading:!1,error:n instanceof Error?n.message:"Error cargando conversaciones"}}}function q(t){return(t||"").split("@")[0]||""}async function Z(){try{return((await _("/api/admin/tenants")).tenants??[]).sort((r,e)=>r.display_name.localeCompare(e.display_name))}catch{return[]}}async function j(){const t=E(),r=new URLSearchParams;r.set("tenant_id",t.role==="platform_admin"?"__all__":t.tenantId||"public"),r.set("status","active");try{return((await _(`/api/conversations/topics?${r.toString()}`)).topics??[]).sort()}catch{return[]}}const z=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];function K(t,r){const e=new Date(t);if(isNaN(e.getTime()))return{key:"unknown",label:""};const n=k(r),s=k(e),c=F(n.year,n.month,n.day),u=F(s.year,s.month,s.day),m=c.getTime()-u.getTime(),o=Math.floor(m/(1e3*60*60*24));if(o===0)return{key:"today",label:"Hoy"};if(o===1)return{key:"yesterday",label:"Ayer"};if(o<7)return{key:"thisWeek",label:"Esta semana"};if(s.month===n.month&&s.year===n.year)return{key:"thisMonth",label:"Este mes"};const l=`month:${s.year}-${String(s.month).padStart(2,"0")}`,f=`${z[s.month]} ${s.year}`;return{key:l,label:f}}function Q(t,r,e=new Date){const n=["today","yesterday","thisWeek","thisMonth"],s=new Map,c=new Map;for(const o of n)s.set(o,{key:o,label:"",items:[]});for(const o of t){const{key:l,label:f}=K(r(o),e);if(n.includes(l)){const v=s.get(l);v.label=f,v.items.push(o)}else c.has(l)||c.set(l,{key:l,label:f,items:[]}),c.get(l).items.push(o)}const u=n.map(o=>s.get(o)).filter(o=>o.items.length>0),m=Array.from(c.values()).sort((o,l)=>l.key.localeCompare(o.key));return[...u,...m]}function V(t){try{return new Date(t).toLocaleTimeString("es-CO",{hour:"numeric",minute:"2-digit",hour12:!0,timeZone:$})}catch{return""}}function X(t){const r=new Date(t);return(Date.now()-r.getTime())/(1e3*60*60*24*30)>=22}function Y(t,r){const e=Math.floor((t.turn_count||0)/2),n=`${e} ${e===1?r.t("record.answer"):r.t("record.answers")}`;return{expiresSoon:X(t.updated_at),question:t.first_question||"...",resumeLabel:r.t("record.resume"),sessionId:t.session_id,tenantId:t.tenant_id,timeLabel:V(t.updated_at),topicClassName:t.topic?B(t.topic):"topic-default",topicLabel:t.topic?D(t.topic):"",turnsLabel:n,userLabel:M()&&t.user_id?t.user_display_name||t.user_id:""}}function tt(t,r){if(!M()||t.length===0)return null;const e=t.map(n=>({tenantLabel:n.display_name,users:(n.members||[]).map(s=>({userId:s.user_id,login:q(s.email),displayName:s.display_name||q(s.email)}))})).filter(n=>n.users.length>0);return U(e,r,{includePublic:!0})}function et(t,r,e){return H(t,r,e)}function rt(t,r){if(t.length===0)return L([],r.t("record.empty"));const e=new Map(t.map(s=>[s.session_id,s.updated_at])),n=Q(t.map(s=>Y(s,r)),s=>e.get(s.sessionId)||"");return L(n,r.t("record.empty"))}function nt(t,r,e){return P(t,r,e.t("record.loadMore"))}function st(t){const r=[];let e="";for(const n of t)n.role==="user"?e=n.content||"":n.role==="assistant"&&e&&(r.push({question:e,answer:n.content||""}),e="");return r}function ot(t,r){return t.map(e=>I(e.question,e.answer,r)).join(`

---

`)}function x(t){var e;const r=((e=t.querySelector("svg"))==null?void 0:e.parentElement)??t;r.innerHTML=C.checkCircle,t.setAttribute("title","Copiado!"),setTimeout(()=>{r.innerHTML=C.copy,t.setAttribute("title","Copiar")},1500)}async function at(t,r,e,n){t.innerHTML=`
    <div class="record-transcript">
      <header class="record-transcript-header">
        <span class="record-transcript-title">Conversacion</span>
        <span class="record-transcript-actions" id="transcript-actions-loading"></span>
      </header>
      <div class="record-transcript-body record-transcript-loading">Cargando...</div>
    </div>
  `,t.showModal();const s=E(),c=n||s.tenantId||"public";let u;try{u=await _(`/api/conversation/${encodeURIComponent(r)}?tenant_id=${encodeURIComponent(c)}`)}catch{t.innerHTML=`
      <div class="record-transcript">
        <header class="record-transcript-header">
          <span class="record-transcript-title">Error</span>
          <span class="record-transcript-actions" id="transcript-actions-err"></span>
        </header>
        <div class="record-transcript-body">No se pudo cargar la conversacion.</div>
      </div>
    `,w(t,"#transcript-actions-err");return}const m=u==null?void 0:u.session;if(!m||!Array.isArray(m.turns)||m.turns.length===0){t.innerHTML=`
      <div class="record-transcript">
        <header class="record-transcript-header">
          <span class="record-transcript-title">Conversacion</span>
          <span class="record-transcript-actions" id="transcript-actions-empty"></span>
        </header>
        <div class="record-transcript-body">Sin turnos registrados.</div>
      </div>
    `,w(t,"#transcript-actions-empty");return}const o=st(m.turns);t.innerHTML=`
    <div class="record-transcript">
      <header class="record-transcript-header">
        <span class="record-transcript-title">Conversacion</span>
        <span class="record-transcript-actions" id="transcript-actions"></span>
      </header>
      <div class="record-transcript-body" id="transcript-pairs"></div>
    </div>
  `;const l=t.querySelector("#transcript-actions"),f=t.querySelector("#transcript-pairs"),v=T({iconHtml:C.copy,tone:"ghost",className:"record-transcript-copy",attrs:{"aria-label":"Copiar toda la conversacion",title:"Copiar todo"},onClick:async()=>{const d=ot(o,e);await navigator.clipboard.writeText(d),x(v)}});l.appendChild(v),w(t,"#transcript-actions");for(let d=0;d<o.length;d++){const h=o[d],y=document.createElement("div");y.className="record-transcript-pair";const b=T({iconHtml:C.copy,tone:"ghost",className:"record-transcript-pair-copy",attrs:{"aria-label":"Copiar este intercambio",title:"Copiar"},onClick:async()=>{const i=I(h.question,h.answer,e);await navigator.clipboard.writeText(i),x(b)}});y.innerHTML=`
      <div class="record-transcript-question">
        <h3>Consulta</h3>
        <p></p>
      </div>
      <div class="record-transcript-answer">
        <h3>Respuesta</h3>
        <div class="record-transcript-answer-content bubble-content"></div>
      </div>
    `,y.querySelector(".record-transcript-question p").textContent=h.question;const a=y.querySelector(".record-transcript-answer-content");if(O(a,h.answer||"(sin respuesta)",{}),y.querySelector(".record-transcript-question").prepend(b),f.appendChild(y),d<o.length-1){const i=document.createElement("hr");i.className="record-transcript-separator",f.appendChild(i)}}}function w(t,r){const e=t.querySelector(r);if(!e)return;const n=T({iconHtml:C.close,tone:"ghost",className:"record-transcript-close",attrs:{"aria-label":"Cerrar"},onClick:()=>t.close()});e.appendChild(n)}function Ct(t,{i18n:r}){let e=G(),n=[],s=[],c=[];t.innerHTML=`
    <div class="record-shell">
      <div class="record-admin-filters"></div>
      <div class="record-filters"></div>
      <div class="record-list"></div>
      <div class="record-footer"></div>
      <dialog class="record-transcript-dialog"></dialog>
    </div>
  `;const u=t.querySelector(".record-admin-filters"),m=t.querySelector(".record-filters"),o=t.querySelector(".record-list"),l=t.querySelector(".record-footer"),f=R(r.t("record.loading"));function v(){return e.activeTopicFilter?c.filter(a=>a.topic===e.activeTopicFilter):c}function d(){const a=tt(s,e.activeUserFilter);u.replaceChildren(...a?[a]:[]),m.replaceChildren(et(n,e.activeTopicFilter,r)),e.loading&&c.length===0?(o.replaceChildren(),o.appendChild(f.el),f.show()):(f.hide(),o.replaceChildren(rt(v(),r))),l.replaceChildren(nt(e.hasMore,e.loading,r))}async function h(a=!1){e={...e,loading:!0},d(),e=await W(e,a),a?c=[...c,...e.sessions.slice(c.length)]:c=e.sessions,d()}u.addEventListener("change",a=>{const i=a.target.closest(".record-tenant-filter");i&&(e={...e,activeUserFilter:i.value||null,offset:0,activeTopicFilter:null},c=[],h())}),m.addEventListener("click",a=>{const i=a.target.closest("[data-topic-filter]");if(!i)return;const p=i.dataset.topicFilter||null;e={...e,activeTopicFilter:p},d()});const y=t.querySelector(".record-transcript-dialog");o.addEventListener("click",a=>{const i=a.target;if(i.closest("[data-resume-session]"))return;const p=i.closest(".record-card");if(!p)return;const g=p.dataset.sessionId;g&&at(y,g,r,p.dataset.tenantId)}),o.addEventListener("click",a=>{const i=a.target.closest("[data-resume-session]");if(!i)return;const p=i.dataset.resumeSession;p&&document.dispatchEvent(new CustomEvent("resume-conversation",{detail:{sessionId:p}}))}),l.addEventListener("click",a=>{!a.target.closest(".record-load-more")||e.loading||(e={...e,offset:e.offset+50},h(!0))});const b=[j().then(a=>{n=a}),h()];M()&&b.push(Z().then(a=>{s=a})),Promise.all(b).then(()=>d()),document.addEventListener("lia:historial-upsert",(a=>{const i=a.detail;if(!(i!=null&&i.session_id))return;const p=c.findIndex(N=>N.session_id===i.session_id);p>=0?c[p]={...c[p],...i}:c.unshift(i);const g=(i.detected_topic||"").trim();g&&!n.includes(g)&&n.push(g),e={...e,sessions:c},d()}))}export{Ct as mountRecordApp};
