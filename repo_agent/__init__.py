"""repo-analyzer: diagnóstico de repos y contexto para LLM."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("repo-scanner-mvp")
except PackageNotFoundError:  # ejecución desde el árbol sin instalar
    __version__ = "0.0.0"

__all__ = ["cli", "__version__"]
