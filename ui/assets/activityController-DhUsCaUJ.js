import{g as y}from"./client-OE0sHIIg.js";import{T as p}from"./brandMark-BZ3quspr.js";import{c as h}from"./badge-UV61UhzD.js";import{c as d}from"./factCard-Cu0UJHPY.js";import{c as v}from"./stateBlock-Dqw5sa9X.js";import"./bootstrap-DAARwiGO.js";import"./index-BAf9D_ld.js";import"./authGate-Bb2S6efH.js";import"./format-CYFfBTRg.js";import"./icons-BZwBwwSI.js";import"./button-1yFzSXrY.js";import"./input-Byu2cnK9.js";import"./toasts-Dx3CUztl.js";import"./chip-Bjq03GaS.js";function f(){return`
    <div class="activity-panel-shell">
      <header class="activity-panel-header">
        <h1>Actividad de Usuarios</h1>
        <p style="color:var(--text-secondary);font-size:0.875rem;margin:0.25rem 0 0">Logins, interacciones y uso por usuario</p>
      </header>

      <div id="activity-summary"></div>

      <section class="activity-section">
        <h2>Logins recientes</h2>
        <div class="activity-table-wrap">
          <table class="activity-table" id="activity-logins-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Estado</th>
                <th>IP</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody id="activity-logins-tbody"></tbody>
          </table>
        </div>
      </section>

      <section class="activity-section">
        <h2>Uso por usuario</h2>
        <div class="activity-table-wrap">
          <table class="activity-table" id="activity-stats-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Logins</th>
                <th>Interacciones</th>
                <th>Ultima actividad</th>
              </tr>
            </thead>
            <tbody id="activity-stats-tbody"></tbody>
          </table>
        </div>
      </section>
    </div>
  `}function g(t){const e=document.createElement("div");return e.className="activity-summary-cards",e.setAttribute("data-lia-component","activity-summary"),e.append(d({label:"Logins hoy",value:String(t.loginsToday)}),d({label:"Usuarios activos (7d)",value:String(t.activeUsers7d)}),d({label:"Interacciones (7d)",value:String(t.totalInteractions7d)})),e}function b(t){const e=document.createElement("tr");e.setAttribute("data-lia-component","login-event-row");const a=document.createElement("td");a.textContent=t.displayName||t.email,t.displayName&&(a.title=t.email);const n=document.createElement("td");n.appendChild(h({label:t.statusLabel,tone:t.statusTone==="success"?"success":"error"}));const i=document.createElement("td");i.textContent=t.ipAddress||"-",i.className="activity-ip-cell";const s=document.createElement("td");return s.textContent=t.createdAt,e.append(a,n,i,s),e}function C(t){const e=document.createElement("tr");e.setAttribute("data-lia-component","user-stats-row");const a=document.createElement("td");a.textContent=t.displayName||t.email,t.displayName&&(a.title=t.email);const n=document.createElement("td");n.textContent=String(t.loginCount),n.className="activity-numeric-cell";const i=document.createElement("td");i.textContent=String(t.interactionCount),i.className="activity-numeric-cell";const s=document.createElement("td");return s.textContent=t.lastActiveAt||"-",e.append(a,n,i,s),e}function o(t,e,a=4){const n=document.createElement("tr");n.setAttribute("data-lia-component","activity-feedback-row");const i=document.createElement("td");return i.colSpan=a,i.appendChild(v({className:"activity-feedback",compact:!0,message:t,tone:e})),n.appendChild(i),n}function u(t,e){const a=(e||"").split("@")[0]||"";return t?a?`${t} (${a})`:t:a||e}function m(t){if(!t)return"-";try{const e=new Date(t),n=Date.now()-e.getTime(),i=Math.floor(n/6e4);if(i<1)return"ahora";if(i<60)return`hace ${i}m`;const s=Math.floor(i/60);if(s<24)return`hace ${s}h`;const c=Math.floor(s/24);return c<7?`hace ${c}d`:e.toLocaleDateString("es-CO",{day:"numeric",month:"short",timeZone:p})}catch{return t}}function R(t){t.innerHTML=f(),A(t)}async function A(t){const e=t.querySelector("#activity-logins-tbody"),a=t.querySelector("#activity-stats-tbody"),n=t.querySelector("#activity-summary");e&&e.replaceChildren(o("Cargando...","loading")),a&&a.replaceChildren(o("Cargando...","loading"));try{const s=(await y("/api/admin/activity?limit=100")).activity;if(n){const c={loginsToday:s.summary.logins_today,activeUsers7d:s.summary.active_users_7d,totalInteractions7d:s.summary.total_interactions_7d};n.replaceChildren(g(c))}if(e){const c=s.recent_logins||[];if(c.length===0)e.replaceChildren(o("Sin logins registrados","empty"));else{const l=c.map(r=>({email:r.email,displayName:u(r.display_name,r.email),status:r.status==="success"?"success":"failure",statusTone:r.status==="success"?"success":"error",statusLabel:r.status==="success"?"OK":"Fallido",ipAddress:r.ip_address,createdAt:m(r.created_at)}));e.replaceChildren(...l.map(b))}}if(a){const c=s.user_stats||[];if(c.length===0)a.replaceChildren(o("Sin datos de usuarios","empty"));else{const l=c.map(r=>({userId:r.user_id,email:r.email,displayName:u(r.display_name,r.email),loginCount:r.login_count,interactionCount:r.interaction_count,lastActiveAt:m(r.last_login_at||r.last_interaction_at)}));a.replaceChildren(...l.map(C))}}}catch(i){console.error("[LIA] Failed to load activity:",i),e&&e.replaceChildren(o("Error al cargar actividad","error")),a&&a.replaceChildren(o("Error al cargar estadisticas","error"))}}export{R as mountActivityPanel};
