import{g as u,A as g}from"./client-OE0sHIIg.js";import{a as E}from"./stateBlock-CleM9k1B.js";import{c as f}from"./factCard-Cu0UJHPY.js";import"./chip-Bjq03GaS.js";let h=0;const y=20;function H(e,n){e.innerHTML=w();const t=e.querySelector("#admin-api-key-section"),a=e.querySelector("#admin-api-stats"),s=e.querySelector("#admin-api-logs"),o=e.querySelector("#admin-api-logs-pagination"),i=e.querySelector("#admin-api-logs-refresh");t&&C(t),a&&x(a),s&&o&&m(s,o,0),i==null||i.addEventListener("click",()=>{s&&o&&m(s,o,h)})}function w(){return`
    <div class="admin-api-shell">
      <article class="ops-card ops-window">
        <div class="ops-window-head">
          <h2>Credenciales del servicio</h2>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-key-section">
            <p class="admin-api-empty">Cargando credenciales...</p>
          </div>
        </div>
      </article>

      <article class="ops-card ops-window" style="grid-column: 1 / -1">
        <div class="ops-window-head">
          <h2>Estadisticas de uso</h2>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-stats" class="admin-api-stats-grid">
            <p class="admin-api-empty">Cargando estadisticas...</p>
          </div>
        </div>
      </article>

      <article class="ops-card ops-window" style="grid-column: 1 / -1">
        <div class="ops-window-head" style="display:flex;justify-content:space-between;align-items:center">
          <h2>Logs recientes</h2>
          <button id="admin-api-logs-refresh" class="admin-api-copy-btn">Actualizar</button>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-logs">
            <p class="admin-api-empty">Cargando logs...</p>
          </div>
          <div id="admin-api-logs-pagination" class="admin-api-pagination"></div>
        </div>
      </article>
    </div>
  `}async function C(e){try{const t=(await u("/api/admin/eval/service-accounts")).service_accounts||[];if(t.length===0){e.innerHTML='<p class="admin-api-empty">No hay cuentas de servicio configuradas.</p>';return}e.innerHTML="";for(const a of t)e.appendChild(_(a))}catch(n){const t=n instanceof g?`${n.status}: ${n.message}`:"Error al cargar credenciales";e.innerHTML=`<p class="admin-api-empty" style="color:var(--status-error)">${t}</p>`}}function _(e){const n=document.createElement("div"),t=document.createElement("div");t.className="admin-api-key-row";const a=document.createElement("code");a.className="admin-api-key-hint",a.textContent=e.secret_hint||e.service_account_id||"—";const s=document.createElement("button");s.className="admin-api-copy-btn",s.textContent="Copiar",b(s,()=>a.textContent||"");const o=E({label:e.status||"unknown",tone:e.status==="active"?"success":"error"});t.append(a,s,o);const i=document.createElement("div");i.className="admin-api-key-meta";const p=e.created_at?new Date(e.created_at).toLocaleDateString():"—",r=e.last_used_at?new Date(e.last_used_at).toLocaleString():"nunca";return i.innerHTML=`<small>${e.display_name||""} &mdash; Creada: ${p} &mdash; Ultimo uso: ${r}</small>`,n.append(t,i),n}async function x(e){try{const t=(await u("/api/admin/eval/stats")).stats||{};e.innerHTML="";const a=[{label:"Total Requests",value:String(t.total_requests??0)},{label:"Errores",value:String(t.total_errors??0)},{label:"Error Rate",value:`${((t.error_rate??0)*100).toFixed(1)}%`},{label:"Latencia p50",value:`${t.latency_p50_ms??0}ms`},{label:"Latencia p95",value:`${t.latency_p95_ms??0}ms`},{label:"Input Tokens",value:v(t.total_input_tokens??0)},{label:"Output Tokens",value:v(t.total_output_tokens??0)}];for(const s of a)e.appendChild(f(s))}catch(n){const t=n instanceof g?`${n.status}: ${n.message}`:"Error al cargar estadisticas";e.innerHTML=`<p class="admin-api-empty" style="color:var(--status-error)">${t}</p>`}}async function m(e,n,t){h=t;try{const a=await u(`/api/admin/eval/logs?limit=${y}&offset=${t}`),s=a.logs||[],o=a.total??0;if(s.length===0){e.innerHTML='<p class="admin-api-empty">No hay logs de evaluacion.</p>',n.innerHTML="";return}e.innerHTML="";for(const i of s)e.appendChild(L(i));T(n,o,t,y)}catch(a){const s=a instanceof g?`${a.status}: ${a.message}`:"Error al cargar logs";e.innerHTML=`<p class="admin-api-empty" style="color:var(--status-error)">${s}</p>`,n.innerHTML=""}}function L(e){const n=document.createElement("div");n.className="ops-log-accordion admin-api-log-entry";const t=document.createElement("div");t.className="ops-log-accordion-summary admin-api-log-summary",t.setAttribute("role","button"),t.setAttribute("tabindex","0");const a=document.createElement("span");a.className="ops-log-accordion-marker",a.textContent="▶";const s=document.createElement("span");s.className="admin-api-log-method",s.textContent=e.method||"POST";const o=document.createElement("span");o.className="admin-api-log-endpoint",o.textContent=e.endpoint||"/api/eval/ask";const i=e.status_code??0,p=E({label:String(i),tone:i>=200&&i<400?"success":"error"}),r=document.createElement("span");r.className="admin-api-log-latency",r.textContent=e.latency_ms!=null?`${Math.round(e.latency_ms)}ms`:"—";const d=document.createElement("span");d.className="admin-api-log-time",d.textContent=e.created_at?new Date(e.created_at).toLocaleTimeString():"";const c=document.createElement("button");c.className="ops-log-copy-btn",c.textContent="Copiar",t.append(a,s,o,p,r,d,c);const l=document.createElement("pre");return l.className="ops-log-body",l.hidden=!0,l.textContent=JSON.stringify({request:e.request_body,response_summary:e.response_summary,error:e.error},null,2),$(t,l,a),b(c,()=>l.textContent||""),n.append(t,l),n}function T(e,n,t,a){e.innerHTML="";const s=e.previousElementSibling,o=document.createElement("span");o.className="admin-api-pagination-info";const i=t+1,p=Math.min(t+a,n);o.textContent=`${i}-${p} de ${n}`;const r=document.createElement("div");r.style.display="flex",r.style.gap="0.5rem";const d=document.createElement("button");d.className="admin-api-copy-btn",d.textContent="← Anterior",d.disabled=t<=0,d.addEventListener("click",()=>{s&&m(s,e,Math.max(0,t-a))});const c=document.createElement("button");c.className="admin-api-copy-btn",c.textContent="Siguiente →",c.disabled=t+a>=n,c.addEventListener("click",()=>{s&&m(s,e,t+a)}),r.append(d,c),e.append(o,r)}function $(e,n,t){const a=()=>{n.hidden=!n.hidden,t.textContent=n.hidden?"▶":"▼"};e.addEventListener("click",s=>{s.target.closest(".ops-log-copy-btn")||a()}),e.addEventListener("keydown",s=>{(s.key==="Enter"||s.key===" ")&&(s.preventDefault(),a())})}function b(e,n){e.addEventListener("click",async t=>{t.stopPropagation();try{await navigator.clipboard.writeText(n());const a=e.textContent;e.textContent="Copiado!",setTimeout(()=>{e.textContent=a},2e3)}catch{}})}function v(e){return e>=1e6?`${(e/1e6).toFixed(1)}M`:e>=1e3?`${(e/1e3).toFixed(1)}K`:String(e)}export{H as mountAdminApiTab};
