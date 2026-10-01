"""Map DemoPeter RAG JSON → Guibu microlesson.v1 shape."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = "microlesson.v1"
PROVIDER_NAME = "demopeter"
PROVIDER_ENDPOINT = "POST /api/rag/query"

# RAG「无法从知识库回答」的拒答语义标记。
# 语料库膨胀后，离题问句的向量相似度与业务问句重叠（实测均 ~0.78），
# 无法用 similarity 阈值区分「覆盖/缺口」，应以 LLM 拒答语义为准。
_REFUSAL_MARKERS = (
    "无法回答", "无法提供", "无法给出", "无法确定",
    "没有关于", "没有找到", "未找到", "未提及",
    "没有相关", "无相关", "查无", "不足以回答",
    "资料中未", "知识库中暂无", "无法从", "暂无相关",
)


def _is_refusal(answer: str) -> bool:
    """判断 RAG answer 是否为「知识库无法回答」的拒答语义。

    - 空回答视为无覆盖（缺口）
    - 实质性长回答（>400 字符）视为有效回答，不做关键词检测
    - 短回答命中拒答关键词视为拒答
    """
    text = (answer or "").strip()
    if not text:
        return True
    if len(text) > 400:
        return False
    return any(marker in text for marker in _REFUSAL_MARKERS)


def _is_poetry_chunk(content: str) -> bool:
    """识别语料污染：全唐诗 JSON chunk（非业务文档）。

    DemoPeter 索引混入了诗词 JSON（含 "paragraphs"/"title" 键），
    离题问句命中此类 chunk 时相似度假高（~0.78），不构成有效覆盖。
    """
    c = (content or "").strip()
    if not c:
        return False
    return '"paragraphs"' in c and '"title"' in c


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
    similarity_threshold: float | None = None,
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
    thr = 0.35 if similarity_threshold is None else float(similarity_threshold)

    # 最高优先级：RAG 拒答 / 无覆盖 → 语义缺口。
    # 即使 sources 非空且 similarity 高于阈值，只要 LLM 明确表示无法回答，
    # 也视为覆盖缺口（向量相似度 ≠ 主题相关性，见 _REFUSAL_MARKERS 注释）。
    if not raw.get("answerable", True) or _is_refusal(answer):
        gaps.append({"topic": q or "unknown", "reason": "no_answer"})
    elif raw.get("error"):
        gaps.append({"topic": q or "unknown", "reason": "upstream_error"})
    elif not sources:
        gaps.append({"topic": q or "unknown", "reason": "no_hit"})
    elif raw.get("retrieval_only") or "+retrieval_only" in mode:
        gaps.append({"topic": q or "unknown", "reason": "retrieval_only"})
    elif sources and all(
        _is_poetry_chunk(s.get("content", "")) for s in sources_in if isinstance(s, dict)
    ):
        # 语料污染：命中的全是诗词 JSON，非业务文档，相似度是假高信号
        gaps.append({"topic": q or "unknown", "reason": "contaminated"})
    elif sources and all(
        s.get("similarity") is None or float(s["similarity"]) < thr for s in sources
    ):
        gaps.append({"topic": q or "unknown", "reason": "below_threshold"})
    elif sources and any(s.get("below_threshold") for s in sources_in if isinstance(s, dict)):
        # DemoPeter 可能标记部分 hit 低于阈值；若无一足够高置信则记缺口
        sims = [float(s["similarity"]) for s in sources if s.get("similarity") is not None]
        if not sims or max(sims) < thr:
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
