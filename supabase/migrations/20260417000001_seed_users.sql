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
-- Temporary testing exception: seed shared-password access for @lia.dev test users.

WITH seeded_users AS (
    SELECT *
    FROM (
        VALUES
            ('usr_admin_001', 'admin@lia.dev', 'Admin LIA', 'active', 'tenant-dev',   'platform_admin'),
            ('usr_usuario1',  'usuario1@lia.dev', 'Ana García', 'active', 'tenant-alfa',  'tenant_user'),
            ('usr_usuario2',  'usuario2@lia.dev', 'Pedro López', 'active', 'tenant-beta',  'tenant_user'),
            ('usr_usuario3',  'usuario3@lia.dev', 'María Rodríguez', 'active', 'tenant-gamma', 'tenant_user'),
            ('usr_usuario4',  'usuario4@lia.dev', 'Laura Martínez', 'active', 'tenant-alfa',  'tenant_user'),
            ('usr_usuario5',  'usuario5@lia.dev', 'Carlos Pérez', 'active', 'tenant-beta',  'tenant_user'),
            ('usr_usuario6',  'usuario6@lia.dev', 'Sofía Ramírez', 'active', 'tenant-gamma', 'tenant_user')
    ) AS rows(user_id, email, display_name, status, tenant_id, role)
)
INSERT INTO users (
    user_id,
    email,
    display_name,
    status,
    password_hash,
    password_reset_required,
    password_updated_at
)
SELECT
    user_id,
    lower(email),
    display_name,
    status,
    'pbkdf2_sha256$600000$QEtYDu4kbGlEkbe3rjevYw$6ariTmHIIufFOzB76gyjxSuzagtfjN-MT9pWW6BWOFo',
    FALSE,
    CURRENT_TIMESTAMP
FROM seeded_users
ON CONFLICT (user_id) DO UPDATE
SET
    email = EXCLUDED.email,
    display_name = EXCLUDED.display_name,
    status = 'active',
    password_hash = EXCLUDED.password_hash,
    password_reset_required = FALSE,
    password_updated_at = CURRENT_TIMESTAMP;

WITH seeded_users AS (
    SELECT *
    FROM (
        VALUES
            ('usr_admin_001', 'admin@lia.dev', 'Admin LIA', 'active', 'tenant-dev',   'platform_admin'),
            ('usr_usuario1',  'usuario1@lia.dev', 'Ana García', 'active', 'tenant-alfa',  'tenant_user'),
            ('usr_usuario2',  'usuario2@lia.dev', 'Pedro López', 'active', 'tenant-beta',  'tenant_user'),
            ('usr_usuario3',  'usuario3@lia.dev', 'María Rodríguez', 'active', 'tenant-gamma', 'tenant_user'),
            ('usr_usuario4',  'usuario4@lia.dev', 'Laura Martínez', 'active', 'tenant-alfa',  'tenant_user'),
            ('usr_usuario5',  'usuario5@lia.dev', 'Carlos Pérez', 'active', 'tenant-beta',  'tenant_user'),
            ('usr_usuario6',  'usuario6@lia.dev', 'Sofía Ramírez', 'active', 'tenant-gamma', 'tenant_user')
    ) AS rows(user_id, email, display_name, status, tenant_id, role)
)
INSERT INTO tenant_memberships (tenant_id, user_id, role)
SELECT tenant_id, user_id, role::platform_role
FROM seeded_users
ON CONFLICT (tenant_id, user_id) DO UPDATE
SET role = EXCLUDED.role;

UPDATE users
SET
    status = 'active',
    password_hash = 'pbkdf2_sha256$600000$QEtYDu4kbGlEkbe3rjevYw$6ariTmHIIufFOzB76gyjxSuzagtfjN-MT9pWW6BWOFo',
    password_reset_required = FALSE,
    password_updated_at = CURRENT_TIMESTAMP
WHERE lower(email) LIKE '%@lia.dev';
-- Seed users 4–10: all assigned to tenant-dev with shared password.
-- Idempotent — uses ON CONFLICT DO NOTHING / DO UPDATE.

-- ── Users ────────────────────────────────────────────────────────────────────
INSERT INTO users (user_id, email, display_name, status, password_hash, password_reset_required) VALUES
    ('usr_usuario4',  'usuario4@lia.dev',  'Carlos Martínez',    'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario5',  'usuario5@lia.dev',  'Laura Hernández',    'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario6',  'usuario6@lia.dev',  'Andrés Torres',      'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario7',  'usuario7@lia.dev',  'Camila Díaz',        'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario8',  'usuario8@lia.dev',  'Santiago Morales',   'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario9',  'usuario9@lia.dev',  'Valentina Ramírez',  'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false),
    ('usr_usuario10', 'usuario10@lia.dev', 'Diego Castillo',     'active', 'pbkdf2_sha256$600000$LpP0oZHkuFd3sxeW7HsDTg$O-yrEKQ1T0prNx2R-j5PUjAwkC2PmE-kh9gNmKLrQcs', false)
ON CONFLICT (user_id) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    password_reset_required = EXCLUDED.password_reset_required,
    status = EXCLUDED.status;

-- ── Tenant memberships ───────────────────────────────────────────────────────
INSERT INTO tenant_memberships (tenant_id, user_id, role) VALUES
    ('tenant-dev', 'usr_usuario4',  'tenant_user'),
    ('tenant-dev', 'usr_usuario5',  'tenant_user'),
    ('tenant-dev', 'usr_usuario6',  'tenant_user'),
    ('tenant-dev', 'usr_usuario7',  'tenant_user'),
    ('tenant-dev', 'usr_usuario8',  'tenant_user'),
    ('tenant-dev', 'usr_usuario9',  'tenant_user'),
    ('tenant-dev', 'usr_usuario10', 'tenant_user')
ON CONFLICT (tenant_id, user_id) DO NOTHING;
