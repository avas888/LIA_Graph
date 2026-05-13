"""fix_v13_may — dedicated `practica_erp` retrieval lane.

Parallels `interpretacion/` but smaller: chat-only consumer with no
side-panel surface, no expert-card rendering. Feeds the
`**Recomendaciones Prácticas**` lead section with real práctica
chunks through a reserved-slot budget, so they don't compete with
denser normative chunks for the unified pool's top-K.
"""
