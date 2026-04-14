from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestionRuntime:
    workspace_root: Path | None = None
    knowledge_base_root: Path | None = None
    manifest_path: Path | None = None
    index_output_file: Path | None = None
    status: str = "compat_stub"
