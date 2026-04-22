import"./main-DE-rE2No.js";import{c as m,p as w,A as y,s as u}from"./client-OE0sHIIg.js";const o=document.querySelector("#app");if(!o)throw new Error("Missing #app root.");o.innerHTML=`
  <main class="ops-shell">
    <section class="ops-card ops-window" style="max-width: 780px; margin: 8vh auto;">
      <div class="ops-window-head">
        <div>
          <p class="eyebrow">Embed Gateway</p>
          <h1 style="margin: 0.25rem 0 0;">LIA embebido</h1>
        </div>
      </div>
      <div class="ops-window-body">
        <p id="embed-status" class="ops-copy">Esperando grant firmado de la app host.</p>
        <pre id="embed-detail" class="diagnostics" style="white-space: pre-wrap;">Handshake pendiente.</pre>
      </div>
    </section>
  </main>
`;const c=o.querySelector("#embed-status"),p=o.querySelector("#embed-detail");function i(n,t){c&&(c.textContent=n),p&&(p.textContent=t)}async function f(n){var t,s,r,d;i("Intercambiando sesion con LIA...","Validando grant, origin y alcance de tenant.");try{const{response:a,data:e}=await w("/api/embed/exchange",{grant:n});if(!a.ok||!(e!=null&&e.access_token)){const g=e&&typeof e=="object"&&"error"in e?JSON.stringify(e.error):a.statusText;throw new y(g||"exchange_failed",a.status,e)}u(e.access_token),i("Sesion embebida lista.",`tenant=${((t=e.me)==null?void 0:t.tenant_id)||"-"} user=${((s=e.me)==null?void 0:s.user_id)||"-"} company=${((r=e.me)==null?void 0:r.active_company_id)||"-"} integration=${((d=e.me)==null?void 0:d.integration_id)||"-"}`),window.setTimeout(()=>{window.location.replace("/")},250)}catch(a){m();const e=a instanceof Error?a.message:"exchange_failed";i("No fue posible inicializar el embed.",e)}}window.addEventListener("message",n=>{const t=n.data;if(!t||t.type!=="lia:init")return;const s=String(t.grant||t.host_grant||"").trim();if(!s){i("Grant faltante.","La app host envio `lia:init` sin grant firmado.");return}f(s)});m();var l;(l=window.parent)==null||l.postMessage({type:"lia:ready"},"*");
