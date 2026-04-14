-- Seed platform users: admin + 3 tenant users for production.
-- Idempotent — uses ON CONFLICT DO NOTHING.

-- ── Tenants ──────────────────────────────────────────────────────────────────
INSERT INTO tenants (tenant_id, display_name) VALUES
    ('tenant-dev',   'LIA Dev'),
    ('tenant-alfa',  'Contadores Alfa SAS'),
    ('tenant-beta',  'Asesores Beta Ltda'),
    ('tenant-gamma', 'Firma Gamma & Asociados')
ON CONFLICT (tenant_id) DO NOTHING;

-- ── Users ────────────────────────────────────────────────────────────────────
INSERT INTO users (user_id, email, display_name, status) VALUES
    ('usr_admin_001', 'admin@lia.dev',    'Admin LIA',         'active'),
    ('usr_usuario1',  'usuario1@lia.dev', 'Ana García',        'active'),
    ('usr_usuario2',  'usuario2@lia.dev', 'Pedro López',       'active'),
    ('usr_usuario3',  'usuario3@lia.dev', 'María Rodríguez',   'active')
ON CONFLICT (user_id) DO NOTHING;

-- ── Tenant memberships (user→tenant + role) ─────────────────────────────────
INSERT INTO tenant_memberships (tenant_id, user_id, role) VALUES
    ('tenant-dev',   'usr_admin_001', 'platform_admin'),
    ('tenant-alfa',  'usr_usuario1',  'tenant_user'),
    ('tenant-beta',  'usr_usuario2',  'tenant_user'),
    ('tenant-gamma', 'usr_usuario3',  'tenant_user')
ON CONFLICT (tenant_id, user_id) DO NOTHING;
