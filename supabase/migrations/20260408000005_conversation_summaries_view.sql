-- Materialized view that pre-joins conversations with turn aggregates.
-- Eliminates the N+1 query pattern in the Historial list endpoint
-- (previously 2 extra round-trips per conversation row).

CREATE OR REPLACE VIEW conversation_summaries AS
SELECT
    c.id,
    c.session_id,
    c.tenant_id,
    c.accountant_id,
    c.topic,
    c.pais,
    c.user_id,
    c.company_id,
    c.integration_id,
    c.host_session_id,
    c.channel,
    c.status,
    c.memory_summary,
    c.created_at,
    c.updated_at,
    COALESCE(agg.turn_count, 0)    AS turn_count,
    COALESCE(agg.first_question, '') AS first_question
FROM conversations c
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)::int AS turn_count,
        (
            SELECT SUBSTRING(ct2.content FOR 120)
            FROM conversation_turns ct2
            WHERE ct2.conversation_id = c.id
              AND ct2.role = 'user'
              AND ct2.content <> ''
            ORDER BY ct2.created_at
            LIMIT 1
        ) AS first_question
    FROM conversation_turns ct
    WHERE ct.conversation_id = c.id
) agg ON true;
