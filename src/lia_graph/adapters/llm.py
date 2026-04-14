from __future__ import annotations

from typing import Protocol


class LLMAdapter(Protocol):
    """Contrato agnostico al proveedor para generacion de texto."""

    def generate(self, prompt: str) -> str:
        """Retorna texto de respuesta para el prompt dado."""
