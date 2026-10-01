#!/usr/bin/env python3
"""第一条业务闭环冒烟：DemoPeter 产品仓 → Guibu microlesson.v1

验收：
  1. DemoPeter Web 可达
  2. 业务问句能命中且 sources 带来源摘录
  3. 适配器输出通过 microlesson.v1 schema
  4. 无覆盖问句能产生 gaps（可审计缺口）

用法（DemoPeter 需已启动，默认 :5210）：
  cd /Users/jason/SurfaceZervi/guibu
  source .venv/bin/activate   # 或 python3 -m venv .venv && pip install -r requirements.txt
  python scripts/smoke_first_warehouse.py
  python scripts/smoke_first_warehouse.py --base-url http://127.0.0.1:5210
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
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


@dataclass
class Case:
    name: str
    query: str
    expect: str  # hit | gap
    threshold: float = 0.25
    top_k: int = 5
    notes: str = ""


@dataclass
class CaseResult:
    name: str
    ok: bool
    detail: str
    lesson: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)


# Jason Mac / SurfaceZervi lineage 上已有的内部问句
CASES: list[Case] = [
    Case(
        name="hit_ctrl4u",
        query="Ctrl4U 是什么，和 Ring 有什么关系？",
        expect="hit",
        notes="InnoX / Ctrl4U 叙事应能命中 lineage",
    ),
    Case(
        name="hit_ringguard",
        query="RingGuard Coastal 赛道在讲什么？",
        expect="hit",
        notes="RingGuard 文档线索",
    ),
    Case(
        name="hit_surfacezervi",
        query="SurfaceZervi 博物馆工作区做什么用？",
        expect="hit",
        notes="lineage / README 类文档",
    ),
    Case(
        name="gap_unrelated",
        query="火星种植西瓜的补贴学时如何申报？",
        expect="gap",
        notes="离题问句：命中诗词污染(contaminated)或 LLM 拒答(no_answer) → 应产生 gap（相似度与业务问句重叠，不能用阈值区分）",
        threshold=0.55,
    ),
]


def _http_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_demopeter(base_url: str) -> tuple[bool, str]:
    health = f"{base_url.rstrip('/')}/api/health/config"
    try:
        data = _http_json(health)
    except urllib.error.URLError as exc:
        return False, f"DemoPeter 不可达 ({health}): {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return False, f"健康检查失败: {exc}"
    warns = data.get("warnings") or []
    ok = bool(data.get("ok", True))
    extra = f" warnings={len(warns)}" if warns else ""
    return ok, f"health ok={ok}{extra}"


def validate_schema(lesson: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema 未安装（pip install -r requirements.txt）"]
    schema_path = _ROOT / "contracts" / "microlesson.v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(lesson, schema)
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]
    return []


def eval_hit(lesson: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not (lesson.get("summary") or "").strip():
        errs.append("summary 为空")
    sources = lesson.get("sources") or []
    if not sources:
        errs.append("sources 为空（期望命中）")
        return errs
    first = sources[0]
    if not (first.get("excerpt") or "").strip():
        errs.append("sources[0].excerpt 为空")
    if not (first.get("source") or "").strip():
        errs.append("sources[0].source 为空")
    if lesson.get("provider", {}).get("name") != "demopeter":
        errs.append("provider.name 不是 demopeter")
    # 文档阶段允许 file_path / 时间戳为 null
    return errs


def eval_gap(lesson: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    gaps = lesson.get("gaps") or []
    sources = lesson.get("sources") or []
    if gaps:
        return errs
    # 无 gaps 时，至少应表现为无可用高置信来源
    if sources:
        errs.append("期望 gaps 非空（无覆盖问句），但 gaps=[] 且仍有 sources")
    else:
        errs.append("期望 gaps 非空（no_hit），但 gaps=[]")
    return errs


def run_case(case: Case) -> CaseResult:
    try:
        raw = ask_rag(case.query, top_k=case.top_k, threshold=case.threshold)
    except (ValueError, RuntimeError) as exc:
        return CaseResult(case.name, False, case.query, errors=[str(exc)])

    lesson = map_to_microlesson(
        raw,
        query=case.query,
        level="beginner",
        similarity_threshold=case.threshold,
    )
    errors = validate_schema(lesson)
    if case.expect == "hit":
        errors.extend(eval_hit(lesson))
    else:
        errors.extend(eval_gap(lesson))

    src_n = len(lesson.get("sources") or [])
    gap_n = len(lesson.get("gaps") or [])
    mode = lesson.get("retrieval_mode")
    detail = (
        f"expect={case.expect} sources={src_n} gaps={gap_n} "
        f"mode={mode} ms={lesson.get('provider', {}).get('response_time_ms')}"
    )
    return CaseResult(
        name=case.name,
        ok=not errors,
        detail=detail,
        lesson=lesson,
        errors=errors,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guibu × DemoPeter 首仓业务闭环冒烟")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("GUIBU_DEMOPETER_BASE_URL", "http://127.0.0.1:5210"),
        help="DemoPeter Web 根地址",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="把每条 microlesson JSON 写到目录（可选）",
    )
    parser.add_argument(
        "--only",
        default="",
        help="只跑指定 case 名，逗号分隔，如 hit_ctrl4u,gap_unrelated",
    )
    args = parser.parse_args(argv)

    os.environ["GUIBU_DEMOPETER_BASE_URL"] = args.base_url.rstrip("/")

    print("=== Guibu × DemoPeter 首仓冒烟 ===")
    print(f"base_url: {args.base_url}")

    ok, health_detail = check_demopeter(args.base_url)
    print(f"[health] {'PASS' if ok else 'FAIL'} — {health_detail}")
    if not ok:
        print("请先启动 DemoPeter：cd DemoPeter && ./scripts/manage.sh dev")
        return 2

    selected = CASES
    if args.only.strip():
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        selected = [c for c in CASES if c.name in want]
        if not selected:
            print(f"无匹配 case: {want}")
            return 2

    if args.json_out:
        args.json_out.mkdir(parents=True, exist_ok=True)

    results: list[CaseResult] = []
    for case in selected:
        print(f"\n--- {case.name}: {case.query}")
        if case.notes:
            print(f"    note: {case.notes}")
        result = run_case(case)
        results.append(result)
        status = "PASS" if result.ok else "FAIL"
        print(f"    [{status}] {result.detail}")
        for err in result.errors:
            print(f"      - {err}")
        if args.json_out and result.lesson is not None:
            out = args.json_out / f"{case.name}.json"
            out.write_text(
                json.dumps(result.lesson, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"    wrote {out}")

    passed = sum(1 for r in results if r.ok)
    total = len(results)
    print(f"\n=== 结果: {passed}/{total} passed ===")
    if passed != total:
        print("闭环未完全跑通：检查语料是否已 import-jason，或调整问句/阈值。")
        return 1
    print("第一条业务闭环可用：检索溯源 + Guibu 微课契约均通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
