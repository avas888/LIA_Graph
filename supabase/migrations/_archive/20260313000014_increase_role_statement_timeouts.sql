-- Increase statement_timeout for PostgREST roles.
-- Default anon=3s is too low for hybrid_search RPC on 34K+ chunks corpus.
-- hybrid_search (FTS + vector via RRF) needs ~5-8s cold, ~1-3s warm.
ALTER ROLE anon SET statement_timeout = '15s';
ALTER ROLE authenticator SET statement_timeout = '15s';
ALTER ROLE authenticated SET statement_timeout = '15s';
