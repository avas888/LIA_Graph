import"./main-DlGGXO8P.js";import{r as x}from"./authGate-Bb2S6efH.js";import{p as h,g as y,A as S}from"./client-OE0sHIIg.js";import{s as b}from"./colors-ps0hVFT8.js";import{c as k}from"./button-1yFzSXrY.js";import{c as I,a as L}from"./stateBlock-CleM9k1B.js";import"./chip-Bjq03GaS.js";function f(e,a){const i=document.createElement("tr");i.setAttribute("data-lia-component","admin-users-feedback-row");const s=document.createElement("td");return s.colSpan=5,s.appendChild(I({className:"admin-users-feedback",compact:!0,message:e,tone:a})),i.appendChild(s),i}function N(e,a){const i=document.createElement("tr");i.dataset.uid=e.userId,i.setAttribute("data-lia-component","admin-user-row");const s=document.createElement("td");s.textContent=e.displayName;const n=document.createElement("td");n.textContent=e.email;const t=document.createElement("td");t.textContent=e.roleLabel;const l=document.createElement("td");l.appendChild(L({className:`admin-user-status-pill admin-user-status-pill--${e.statusTone}`,label:e.statusLabel,tone:e.statusTone==="neutral"?"neutral":e.statusTone}));const d=document.createElement("td");return d.className="admin-users-actions",e.actions.forEach(o=>{const c=o.kind==="delete"?"destructive":o.kind==="reactivate"?"secondary":"ghost",r=k({className:`btn-action btn-${o.kind}`,dataComponent:"admin-user-action",label:o.label,tone:c,type:"button"});r.dataset.uid=o.userId,r.dataset.name=o.userName,r.addEventListener("click",()=>a[o.kind](o)),d.appendChild(r)}),i.append(s,n,t,l,d),i}let g=null,w="";function A(e){return{active:"Activo",suspended:"Suspendido",invited:"Invitado"}[e]||e}function q(e){return e==="tenant_admin"?"Admin":"Usuario"}async function p(){if(!g||!w)return;const e=g.querySelector("#users-tbody");if(e){e.replaceChildren(f("Cargando...","loading"));try{const i=(await y(`/api/admin/users?tenant_id=${w}`)).users||[];if(i.length===0){e.replaceChildren(f("Sin usuarios","empty"));return}const s=document.createDocumentFragment();i.map(n=>{const t=[],l=n.display_name||n.email;return n.status==="active"?t.push({kind:"suspend",label:"Suspender",userId:n.user_id,userName:l}):n.status==="suspended"&&t.push({kind:"reactivate",label:"Reactivar",userId:n.user_id,userName:l}),t.push({kind:"delete",label:"Eliminar",userId:n.user_id,userName:l}),{actions:t,displayName:n.display_name||n.email.split("@")[0],email:n.email,roleLabel:q(n.role),statusLabel:A(n.status),statusTone:n.status==="active"?"success":n.status==="suspended"?"warning":"neutral",userId:n.user_id}}).forEach(n=>{s.appendChild(N(n,{delete:t=>void T(t.userId,t.userName),reactivate:t=>void B(t.userId,t.userName),suspend:t=>void $(t.userId,t.userName)}))}),e.replaceChildren(s)}catch(a){e.replaceChildren(f(a instanceof Error?a.message:"Error al cargar usuarios","error"))}}}async function $(e,a){if(confirm(`¿Suspender al usuario ${a}?`))try{await h(`/api/admin/users/${e}/suspend`,{}),await p()}catch{alert("Error al suspender usuario.")}}async function B(e,a){if(confirm(`¿Reactivar al usuario ${a}?`))try{await h(`/api/admin/users/${e}/reactivate`,{}),await p()}catch{alert("Error al reactivar usuario.")}}async function T(e,a){if(confirm(`¿Eliminar al usuario ${a}? Esta acción no se puede deshacer.`))try{await h(`/api/admin/users/${e}/delete`,{confirm:!0}),await p()}catch{alert("Error al eliminar usuario.")}}function _(e,a){e.replaceChildren();const i=document.createElement("p");i.textContent=a,i.style.color=b.status.error,e.appendChild(i),e.style.display="block"}function R(e,a){e.replaceChildren();const i=document.createElement("p");i.textContent="Invitación creada.",i.style.color=b.status.success,i.style.marginBottom="0.5rem";const s=document.createElement("div");s.style.display="flex",s.style.gap="0.5rem",s.style.alignItems="center";const n=document.createElement("input");n.type="text",n.readOnly=!0,n.value=a,n.style.flex="1",n.style.padding="0.375rem 0.5rem",n.style.border=`1px solid ${b.border.default}`,n.style.borderRadius="6px",n.style.fontSize="0.8125rem";const t=document.createElement("button");return t.type="button",t.className="btn-copy lia-btn lia-btn--secondary",t.style.whiteSpace="nowrap",t.textContent="Copiar",s.append(n,t),e.append(i,s),e.style.display="block",t}async function U(e){const a=document.createElement("dialog");a.className="invite-dialog",a.innerHTML=`
    <form method="dialog" class="invite-form">
      <h3>Invitar usuario</h3>
      <label for="invite-email">Correo electrónico</label>
      <input type="email" id="invite-email" name="email" required placeholder="usuario@ejemplo.com" autofocus>
      <label for="invite-role">Rol</label>
      <select id="invite-role" name="role">
        <option value="tenant_user">Usuario</option>
        <option value="tenant_admin">Administrador</option>
      </select>
      <div class="invite-actions">
        <button type="button" class="btn-cancel lia-btn lia-btn--ghost">Cancelar</button>
        <button type="submit" class="btn-submit lia-btn lia-btn--primary">Enviar invitación</button>
      </div>
      <div class="invite-result" style="display:none"></div>
    </form>
  `,document.body.appendChild(a),a.showModal();const i=a.querySelector("form"),s=a.querySelector(".invite-result"),n=a.querySelector(".btn-cancel"),t=a.querySelector(".btn-submit");n.addEventListener("click",()=>{a.close(),a.remove()}),i.addEventListener("submit",async l=>{var c;l.preventDefault();const d=i.querySelector("#invite-email").value.trim(),o=i.querySelector("#invite-role").value;t.disabled=!0,t.textContent="Enviando...",s.style.display="none";try{const{data:r}=await h("/api/admin/users/invite",{email:d,role:o,tenant_id:e});if(r!=null&&r.ok&&((c=r.invite)!=null&&c.invite_url)){const m=R(s,r.invite.invite_url);m.addEventListener("click",async()=>{await navigator.clipboard.writeText(r.invite.invite_url),m.textContent="Copiado",setTimeout(()=>{m.textContent="Copiar"},2e3)}),t.textContent="Listo",setTimeout(()=>p(),500)}else _(s,(r==null?void 0:r.error)||"Error al crear invitación."),t.disabled=!1,t.textContent="Enviar invitación"}catch{_(s,"Error de conexión."),t.disabled=!1,t.textContent="Enviar invitación"}}),a.addEventListener("close",()=>a.remove())}function P(e,a){g=e,w=a,e.innerHTML=`
    <table class="admin-users-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Correo</th>
          <th>Rol</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody id="users-tbody">
        <tr><td colspan="5" style="text-align:center;color:${b.text.tertiary}">Cargando...</td></tr>
      </tbody>
    </table>
  `,p()}x()&&J();function J(){const e=document.querySelector("#app");if(!e)throw new Error("Missing #app root.");e.innerHTML=`
    <main class="ops-shell">
      <header class="app-header app-hero">
        <div class="hero-copy">
          <p class="eyebrow">Admin Plane</p>
          <h1>LIA Administracion</h1>
          <p class="hero-lede">Consumo, reviews y alcance actual del tenant sin acoplar el runtime a un proveedor LLM especifico.</p>
        </div>
      </header>
      <section class="ops-backstage">
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Contexto</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-me" class="diagnostics">Cargando identidad...</pre>
          </div>
        </article>
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Uso</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-usage" class="diagnostics">Cargando consumo...</pre>
          </div>
        </article>
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Reviews</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-reviews" class="diagnostics">Cargando feedback...</pre>
          </div>
        </article>
        <article class="ops-card ops-window" style="grid-column: 1 / -1">
          <div class="ops-window-head" style="display:flex;justify-content:space-between;align-items:center">
            <h2>Usuarios</h2>
            <button id="btn-invite-user" class="lia-btn lia-btn--primary" data-lia-component="invite-user-btn">+ Invitar</button>
          </div>
          <div class="ops-window-body">
            <div id="admin-users">Cargando usuarios...</div>
          </div>
        </article>
      </section>
    </main>
  `;const a=e.querySelector("#admin-me"),i=e.querySelector("#admin-usage"),s=e.querySelector("#admin-reviews"),n=e.querySelector("#admin-users");function t(d,o){d&&(d.textContent=JSON.stringify(o,null,2))}async function l(){var d,o;try{const[c,r,m]=await Promise.all([y("/api/me"),y("/api/admin/usage?group_by=user_id&limit=500"),y("/api/admin/reviews?limit=50")]),C=c.me||{};t(a,C);const v=C.tenant_id||"";n&&v&&P(n,v);const E=e.querySelector("#btn-invite-user");E&&v&&E.addEventListener("click",()=>U(v)),t(i,{totals:((d=r.summary)==null?void 0:d.totals)||{},groups:((o=r.summary)==null?void 0:o.groups)||[]}),t(s,(m.reviews||[]).map(u=>({trace_id:u.trace_id,vote:u.vote,user_id:u.user_id,company_id:u.company_id,timestamp:u.timestamp,comment:u.comment})))}catch(c){const r=c instanceof S?`${c.status} ${c.message}`:c instanceof Error?c.message:"unknown_error";t(a,{error:r}),t(i,{error:r}),t(s,{error:r})}}l()}
