"""聚合 microlesson.v1 → skill-proof.v1。

输入：同一用户的多条 microlesson.v1 JSON（dict 列表）
输出：一条 skill-proof.v1 JSON（对齐 contracts/skill-proof.v1.json）

设计原则（对齐 Tractor 适配方案 §7.1 与 §十）：
- 壳层适配，不重写 DemoPeter / looma 内核
- Phase 1 只传 evidence[] 原文 + 轻量 skill_tags，技能语义由下游 LLM 判断
- user_id = sha256(email.lower().trim())（2026-08-12 已决策，对齐 §八），payload 只传 hash
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "skill-proof.v1"

# 轻量技术关键词白名单（Phase 1 兜底；语义提取由下游 LLM 判断，见 §十决策）
TECH_KEYWORDS = [
    "Python", "Java", "SQL", "JavaScript", "TypeScript", "React", "Vue",
    "Docker", "Kubernetes", "Linux", "Git", "REST API", "微服务", "数据分析",
    "机器学习", "深度学习", "列表推导式", "数据结构", "算法", "网络", "安全",
    "运维", "前端", "后端", "数据库", "Rust", "Go", "FastAPI", "Next.js",
]


def email_to_user_id(email: str) -> str:
    """sha256(email.lower().trim()) → 64 位 hex，跨平台统一关联键（§八决策）。"""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def extract_skill_tags(microlesson: dict[str, Any]) -> list[str]:
    """从 query 提取轻量技能标签；无命中时退回 query 前 30 字，保证 skill_tags 非空。"""
    query = (microlesson.get("query") or "").strip()
    ql = query.lower()
    seen: set[str] = set()
    tags: list[str] = []
    for kw in TECH_KEYWORDS:
        if kw.lower() in ql and kw not in seen:
            seen.add(kw)
            tags.append(kw)
    if tags:
        return tags
    return [query[:30]] if query else ["untitled"]


def build_evidence(microlessons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把每条 microlesson 的 sources 摊平成 skill-proof evidence。"""
    evidence: list[dict[str, Any]] = []
    for lesson in microlessons:
        tags = extract_skill_tags(lesson)
        skill = tags[0]
        learned_at = lesson.get("generated_at")
        for src in lesson.get("sources") or []:
            if not isinstance(src, dict):
                continue
            evidence.append(
                {
                    "skill": skill,
                    "source": str(src.get("source") or "unknown"),
                    "file_path": src.get("file_path"),
                    "start_sec": src.get("start_sec"),
                    "end_sec": src.get("end_sec"),
                    "excerpt": str(src.get("excerpt") or ""),
                    "similarity": src.get("similarity"),
                    "learned_at": learned_at,
                }
            )
    return evidence


def export_skill_proof(
    user_id: str,
    microlessons: list[dict[str, Any]],
    *,
    level: str | None = None,
    proofs: list[dict[str, Any]] | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """聚合多条 microlesson 为一条 skill-proof.v1。

    Raises:
        ValueError: 输入为空，或聚合后没有任何 evidence（contracts 要求 minItems:1）。
    """
    if not microlessons:
        raise ValueError("至少需要一条 microlesson 才能导出 skill-proof")

    evidence = build_evidence(microlessons)
    if not evidence:
        raise ValueError("所有 microlesson 均无 sources，无法生成非空 evidence")

    all_tags: list[str] = []
    seen: set[str] = set()
    for ml in microlessons:
        for t in extract_skill_tags(ml):
            if t not in seen:
                seen.add(t)
                all_tags.append(t)
    if not all_tags:
        all_tags = ["untitled"]

    return {
        "schema_version": SCHEMA_VERSION,
        "user_id": user_id,
        "skill_tags": all_tags,
        "level": level,
        "evidence": evidence,
        "total_micro_lessons": len(microlessons),
        "proofs": proofs or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    }


def _sign_body(secret: str, body: bytes) -> str:
    """HMAC-SHA256(secret, body) → hex 小写，对齐 Tatha ingest 的 X-Signature。"""
    return _hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def post_skill_proof(
    url: str,
    proof: dict[str, Any],
    *,
    secret: str | None = None,
    nonce: str | None = None,
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff_base: float = 0.5,
) -> dict[str, Any]:
    """POST 信封化 skill-proof 到摄入端（Tatha :8010）。

    信封：``{signal_type, user_id_hash, nonce, payload=proof}``；nonce 由客户端生成保证幂等。
    HMAC：``secret`` 非空时发 ``X-Signature = HMAC-SHA256(secret, raw_body)``（hex 小写）；
    ``secret`` 未传则读环境变量 ``SIGNAL_BRIDGE_SECRET``，仍无则不发送签名头（dev 免签）。
    重试：网络错误与 5xx 指数退避重试（最多 ``max_retries`` 次）；4xx（验签/契约失败）不重试。

    Args:
        url: 完整 ingest URL，如 ``http://127.0.0.1:8010/v1/skills/ingest``
        proof: skill-proof.v1 载荷
        secret: HMAC 密钥；缺省读 ``SIGNAL_BRIDGE_SECRET``
        nonce: 幂等 nonce；缺省自动生成 uuid4 hex
        timeout: 单次请求超时秒数
        max_retries: 最大尝试次数（含首次）
        backoff_base: 退避基数秒，第 k 次重试等待 ``backoff_base * 2**(k-1)``

    Returns:
        服务端 JSON 响应（dict）

    Raises:
        RuntimeError: HTTP 4xx/5xx（4xx 不重试；5xx 重试耗尽后抛出）
        urllib.error.URLError: 网络不可达且重试耗尽
        ValueError: 响应非 JSON 或非 object
    """
    if secret is None:
        secret = os.environ.get("SIGNAL_BRIDGE_SECRET") or None
    nonce = nonce or uuid.uuid4().hex

    envelope = {
        "signal_type": "skill_proof",
        "user_id_hash": proof.get("user_id") or "",
        "nonce": nonce,
        "payload": proof,
    }
    body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    if secret:
        headers["X-Signature"] = _sign_body(secret, body)

    raw = ""
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            err: Exception = RuntimeError(f"ingest HTTP {exc.code}: {detail or exc.reason}")
            if exc.code < 500:  # 4xx：验签/契约失败，重试无意义
                raise err from exc
        except Exception as exc:  # URLError / TimeoutError 等网络层错误，退避重试
            err = exc
        if attempt >= max_retries - 1:
            raise err
        time.sleep(backoff_base * (2 ** attempt))

    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"ingest 响应非 JSON object: {type(data).__name__}")
    return data
