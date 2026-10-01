#!/usr/bin/env python3
"""第二条业务闭环冒烟：Guibu microlesson.v1 → skill-proof.v1 → mock ingest

验收：
  1. DemoPeter Web 可达（默认 :5210）
  2. 多条问句 → microlesson → export_skill_proof 聚合为一条 skill-proof.v1
  3. 输出通过 contracts/skill-proof.v1.json schema（含 evidence minItems、user_id=email hash）
  4. user_id 由 email 经 sha256 生成（对齐 §八决策）
  5. （可选）POST 到 Tatha :8010 /v1/skills/ingest，端到端打通 Guibu → Tatha

用法（DemoPeter 与 Tatha 需已启动）：
  cd /Users/jason/SurfaceZervi/guibu
  source .venv/bin/activate
  python scripts/smoke_skill_proof.py
  python scripts/smoke_skill_proof.py --email learner@example.com --out out/skill-proof.json
  python scripts/smoke_skill_proof.py --ingest-url http://127.0.0.1:8010
  python scripts/smoke_skill_proof.py --no-ingest   # 仅本地聚合 + schema
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_dotenv() -> None:
    path = _ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from adapters.demopeter.client import ask_rag  # noqa: E402
from adapters.demopeter.map import map_to_microlesson  # noqa: E402
from exporters.skill_proof.exporter import (  # noqa: E402
    email_to_user_id,
    export_skill_proof,
    post_skill_proof,
)

# Jason Mac / SurfaceZervi lineage 上已有的命中问句（与首仓冒烟复用）
QUERIES = [
    "Ctrl4U 是什么，和 Ring 有什么关系？",
    "RingGuard Coastal 赛道在讲什么？",
    "列表推导式怎么用",
]

DEFAULT_INGEST_BASE = "http://127.0.0.1:8010"


def check_demopeter(base_url: str) -> tuple[bool, str]:
    health = f"{base_url.rstrip('/')}/api/health/config"
    try:
        req = urllib.request.Request(health, method="GET")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return False, f"DemoPeter 不可达 ({health}): {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return False, f"健康检查失败: {exc}"
    return bool(data.get("ok", True)), f"health ok={data.get('ok', True)}"


def validate_schema(proof: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema 未安装（pip install -r requirements.txt）"]
    schema_path = _ROOT / "contracts" / "skill-proof.v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(proof, schema)
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]
    return []


def _ingest_url(base_or_full: str) -> str:
    base = base_or_full.rstrip("/")
    if base.endswith("/v1/skills/ingest"):
        return base
    return f"{base}/v1/skills/ingest"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guibu skill-proof 聚合导出冒烟")
    parser.add_argument("--base-url", default=os.environ.get("GUIBU_DEMOPETER_BASE_URL", "http://127.0.0.1:5210"))
    parser.add_argument("--email", default="learner@example.com", help="明文 email，自动生成 user_id hash")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--out", type=Path, default=None, help="写 skill-proof JSON 到文件")
    parser.add_argument(
        "--ingest-url",
        default=os.environ.get("TATHA_SIGNAL_INGEST_URL", DEFAULT_INGEST_BASE),
        help=f"Tatha 摄入基址或完整 URL（默认 {DEFAULT_INGEST_BASE}）",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="跳过 POST ingest，仅本地聚合 + schema 校验",
    )
    args = parser.parse_args(argv)

    os.environ["GUIBU_DEMOPETER_BASE_URL"] = args.base_url.rstrip("/")
    user_id = email_to_user_id(args.email)

    print("=== Guibu skill-proof 聚合导出冒烟 ===")
    print(f"base_url: {args.base_url}")
    print(f"email:    {args.email}")
    print(f"user_id:  {user_id}")

    ok, health_detail = check_demopeter(args.base_url)
    print(f"[health] {'PASS' if ok else 'FAIL'} — {health_detail}")
    if not ok:
        print("请先启动 DemoPeter：cd DemoPeter && ./scripts/manage.sh dev")
        return 2

    lessons: list[dict[str, Any]] = []
    for q in QUERIES:
        print(f"\n--- query: {q}")
        try:
            raw = ask_rag(q, top_k=args.top_k, threshold=args.threshold)
            lesson = map_to_microlesson(
                raw, query=q, level="beginner", similarity_threshold=args.threshold
            )
        except (ValueError, RuntimeError) as exc:
            print(f"    [FAIL] {exc}")
            return 1
        lessons.append(lesson)
        print(f"    sources={len(lesson.get('sources') or [])} gaps={len(lesson.get('gaps') or [])}")

    try:
        proof = export_skill_proof(user_id, lessons, level="beginner")
    except ValueError as exc:
        print(f"[FAIL] 聚合失败: {exc}")
        return 1

    errors = validate_schema(proof)
    tags = proof.get("skill_tags") or []
    evidence = proof.get("evidence") or []
    print("\n--- skill-proof 摘要 ---")
    print(f"    schema_version: {proof.get('schema_version')}")
    print(f"    skill_tags:     {tags}")
    print(f"    evidence:       {len(evidence)} 条")
    print(f"    total_micro:    {proof.get('total_micro_lessons')}")
    print(f"    user_id==hash:  {proof.get('user_id') == user_id}")

    if errors:
        print("\n[schema] FAIL")
        for e in errors:
            print(f"    - {e}")
        return 1
    print("\n[schema] PASS — skill-proof.v1 校验通过")

    out = json.dumps(proof, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(out + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print("\n" + out[:800] + ("\n..." if len(out) > 800 else ""))

    if args.no_ingest:
        print("\n=== skill-proof 闭环可用：microlesson → 聚合 → 契约校验通过（跳过 ingest）===")
        return 0

    url = _ingest_url(args.ingest_url)
    print(f"\n--- ingest → {url}")
    try:
        resp = post_skill_proof(url, proof)
    except (RuntimeError, OSError, ValueError) as exc:
        # best-effort：聚合/schema 已通过，ingest 失败不抹掉上游成功，但冒烟整体 FAIL
        print(f"[ingest] FAIL — {exc}")
        print("提示：先启动 Tatha（uv run uvicorn tatha.api.app:app --port 8010），再跑本冒烟")
        return 3
    print(f"[ingest] PASS — {json.dumps(resp, ensure_ascii=False)}")
    print("\n=== skill-proof 闭环可用：microlesson → 聚合 → 契约校验 → Tatha ingest ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
