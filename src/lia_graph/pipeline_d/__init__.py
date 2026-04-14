"""Pipeline D — graph-native tax reasoning for Colombian accounting.

Builds answers from typed knowledge-graph traversal over the Estatuto
Tributario while preserving the shared product shell contracts.
"""

from .orchestrator import run_pipeline_d

__all__ = ["run_pipeline_d"]
