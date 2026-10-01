"""HTTP client for DemoPeter POST /api/rag/query (read-only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE = "http://127.0.0.1:5210"
ENDPOINT = "/api/rag/query"


def _base_url() -> str:
    return os.environ.get("GUIBU_DEMOPETER_BASE_URL", DEFAULT_BASE).rstrip("/")


def ask_rag(
    query: str,
    *,
    top_k: int | None = None,
    threshold: float | None = None,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """Call DemoPeter RAG and return the raw JSON body.

    Raises:
        ValueError: empty query
        RuntimeError: HTTP / network / non-JSON failure
    """
    q = (query or "").strip()
    if not q:
        raise ValueError("query must not be empty")

    body: dict[str, Any] = {"query": q}
    if top_k is None:
        env_k = os.environ.get("GUIBU_DEMOPETER_TOP_K")
        if env_k:
            top_k = int(env_k)
    if threshold is None:
        env_t = os.environ.get("GUIBU_DEMOPETER_THRESHOLD")
        if env_t:
            threshold = float(env_t)
    if top_k is not None:
        body["top_k"] = top_k
    if threshold is not None:
        body["threshold"] = threshold

    url = f"{_base_url()}{ENDPOINT}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DemoPeter HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"DemoPeter unreachable at {url}: {exc.reason}. "
            "Start DemoPeter Web or set GUIBU_DEMOPETER_BASE_URL."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"DemoPeter returned non-JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("DemoPeter response must be a JSON object")
    return payload
