"""Backend package bootstrap and legacy import shims."""

from importlib import import_module
import sys


def _ensure_alias(alias: str, target: str) -> None:
    """Map legacy module name to package module to avoid duplication."""
    if alias not in sys.modules:
        sys.modules[alias] = import_module(target)


_ensure_alias("api", "backend.api")
_ensure_alias("services", "backend.services")
_ensure_alias("models", "backend.models")
_ensure_alias("config", "backend.config")
_ensure_alias("database", "backend.database")
