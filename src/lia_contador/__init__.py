"""Compatibility package that aliases `lia_contador.*` to `lia_graph.*`.

LIA_Graph inherited code from Lia_contadores while renaming the local package
to `lia_graph`. Some copied modules still use absolute imports rooted at
`lia_contador`. This shim keeps those imports working while we finish the
selective refactor.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from types import ModuleType


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target_name: str) -> None:
        self._target_name = target_name

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType | None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        target = importlib.import_module(self._target_name)
        module.__dict__.clear()
        module.__dict__.update(target.__dict__)
        module.__loader__ = self
        module.__package__ = module.__name__.rpartition(".")[0]
        module.__spec__ = importlib.util.spec_from_loader(
            module.__name__,
            self,
            is_package=hasattr(target, "__path__"),
        )
        if hasattr(target, "__path__"):
            module.__path__ = list(target.__path__)  # type: ignore[attr-defined]

    def get_code(self, fullname: str) -> object | None:
        target_spec = importlib.util.find_spec(self._target_name)
        if target_spec is None or target_spec.loader is None:
            return None
        get_code = getattr(target_spec.loader, "get_code", None)
        if callable(get_code):
            return get_code(self._target_name)
        return None

    def get_source(self, fullname: str) -> str | None:
        target_spec = importlib.util.find_spec(self._target_name)
        if target_spec is None or target_spec.loader is None:
            return None
        get_source = getattr(target_spec.loader, "get_source", None)
        if callable(get_source):
            return get_source(self._target_name)
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    PREFIX = "lia_contador."
    TARGET_PREFIX = "lia_graph."

    def find_spec(
        self,
        fullname: str,
        path: object | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith(self.PREFIX):
            return None
        mapped = self.TARGET_PREFIX + fullname[len(self.PREFIX):]
        target_spec = importlib.util.find_spec(mapped)
        if target_spec is None:
            return None
        spec = importlib.util.spec_from_loader(
            fullname,
            _AliasLoader(mapped),
            is_package=target_spec.submodule_search_locations is not None,
        )
        if spec is not None:
            spec.origin = target_spec.origin
            spec.has_location = bool(target_spec.origin)
            if target_spec.submodule_search_locations is not None:
                spec.submodule_search_locations = list(target_spec.submodule_search_locations)
        return spec


if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

__all__: list[str] = []
