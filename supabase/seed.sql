-- Seed data: minimal fixtures for local development

-- 1 conversation with 2 turns
INSERT INTO conversations (session_id, tenant_id, accountant_id, topic, pais)
VALUES ('seed-session-001', 'tenant-dev', 'accountant-dev', 'renta', 'colombia');

INSERT INTO conversation_turns (conversation_id, role, content, trace_id)
VALUES
    ((SELECT id FROM conversations WHERE session_id = 'seed-session-001'),
     'user', '¿Cuál es el plazo para declarar renta en 2026?', 'trace-seed-001'),
    ((SELECT id FROM conversations WHERE session_id = 'seed-session-001'),
     'assistant', 'El plazo depende de los dos últimos dígitos de su NIT...', 'trace-seed-001');

-- 1 feedback record
INSERT INTO feedback (trace_id, session_id, rating, tags, comment)
VALUES ('trace-seed-001', 'seed-session-001', 4, '{precisa,practica}', 'Respuesta útil y clara');

-- 1 contribution
INSERT INTO contributions (contribution_id, topic, content_markdown, authority_claim, submitter_id, tenant_id, status)
VALUES ('contrib-seed-001', 'renta', '## Nota sobre plazos\nLos plazos se publican en el decreto reglamentario anual.', 'Contador Público', 'user-dev-001', 'tenant-dev', 'pending');

-- 1 clarification session
INSERT INTO clarification_sessions (session_id, state, expires_at)
VALUES ('clarif-seed-001', '{"step": 1, "pending_field": "nit"}', now() + interval '2 hours');
