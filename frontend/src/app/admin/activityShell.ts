export function renderActivityShell(): string {
  return `
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
  `;
}
