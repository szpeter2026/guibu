"""Map DemoPeter RAG JSON → Guibu microlesson.v1 shape."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = "microlesson.v1"
PROVIDER_NAME = "demopeter"
PROVIDER_ENDPOINT = "POST /api/rag/query"


def _split_steps(answer: str, max_steps: int = 6) -> list[str]:
    """Heuristic: split answer into short steps for auditable micro-steps."""
    text = (answer or "").strip()
    if not text:
        return []

    lines = [ln.strip(" -*\t") for ln in text.splitlines() if ln.strip()]
    numbered: list[str] = []
    for ln in lines:
        # "1. xxx" / "1、xxx" / "- xxx"
        cleaned = ln
        for prefix in ("- ", "* ", "• "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        if len(cleaned) > 2 and cleaned[0].isdigit() and cleaned[1] in ".、)）":
            cleaned = cleaned[2:].strip()
        elif len(cleaned) > 3 and cleaned[:2].isdigit() and cleaned[2] in ".、)）":
            cleaned = cleaned[3:].strip()
        if cleaned:
            numbered.append(cleaned)

    if len(numbered) >= 2:
        return numbered[:max_steps]

    # Fallback: sentence split
    parts = []
    buf = ""
    for ch in text.replace("\n", " "):
        buf += ch
        if ch in "。！？；.!?;" and len(buf.strip()) > 8:
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return (parts or [text[:240]])[:max_steps]


def _map_source(item: dict[str, Any]) -> dict[str, Any]:
    excerpt = item.get("content") or item.get("excerpt") or ""
    source = item.get("source") or item.get("source_file") or item.get("title") or "unknown"
    file_path = item.get("file_path") or item.get("source_path")
    start_sec = item.get("start_sec")
    end_sec = item.get("end_sec")
    # DemoPeter today: document-level sources only
    return {
        "source": str(source),
        "file_path": file_path if file_path else None,
        "start_sec": float(start_sec) if start_sec is not None else None,
        "end_sec": float(end_sec) if end_sec is not None else None,
        "excerpt": str(excerpt)[:1200],
        "similarity": item.get("similarity"),
        "corpus_id": item.get("corpus_id") or item.get("corpus_label"),
    }


def map_to_microlesson(
    raw: dict[str, Any],
    *,
    query: str | None = None,
    level: str | None = None,
) -> dict[str, Any]:
    """Convert DemoPeter /api/rag/query body into microlesson.v1."""
    q = (query or raw.get("query") or "").strip()
    answer = (raw.get("answer") or "").strip()
    sources_in = raw.get("sources") or []
    if not isinstance(sources_in, list):
        sources_in = []

    sources = [_map_source(s) for s in sources_in if isinstance(s, dict)]
    mode = str(raw.get("retrieval_mode") or "unknown")
    gaps: list[dict[str, str]] = []

    if raw.get("error"):
        gaps.append({"topic": q or "unknown", "reason": "upstream_error"})
    elif not sources:
        gaps.append({"topic": q or "unknown", "reason": "no_hit"})
    elif raw.get("retrieval_only") or "+retrieval_only" in mode:
        gaps.append({"topic": q or "unknown", "reason": "retrieval_only"})
    elif all(s.get("similarity") is not None and float(s["similarity"]) < 0.35 for s in sources):
        gaps.append({"topic": q or "unknown", "reason": "below_threshold"})

    return {
        "schema_version": SCHEMA_VERSION,
        "query": q,
        "level": level,
        "summary": answer,
        "steps": _split_steps(answer),
        "code_blocks": [],
        "sources": sources,
        "gaps": gaps,
        "retrieval_mode": mode,
        "provider": {
            "name": PROVIDER_NAME,
            "endpoint": PROVIDER_ENDPOINT,
            "response_time_ms": raw.get("response_time_ms"),
            "raw_chunk_count": raw.get("chunk_count"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
