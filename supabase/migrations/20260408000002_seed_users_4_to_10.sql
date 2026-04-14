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
