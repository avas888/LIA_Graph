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
