"""DemoPeter read-only adapter: RAG query → microlesson.v1."""

from .client import ask_rag
from .map import map_to_microlesson

__all__ = ["ask_rag", "map_to_microlesson"]
