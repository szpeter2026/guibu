"""CLI: python -m exporters.skill_proof

两种输入：
  1. --query（可多次）：实时调 DemoPeter，问句 → microlesson → 聚合
  2. --lesson-file（可多次）：读本地 microlesson.v1 JSON → 聚合

输出 skill-proof.v1 JSON 到 stdout，可选 --out 写文件、--validate 校验 schema、
--ingest 推送到 mock/Tatha 摄入端。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow `python -m exporters.skill_proof` from repo root
_ROOT = Path(__file__).resolve().parents[2]
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

from exporters.skill_proof.exporter import (  # noqa: E402
    email_to_user_id,
    export_skill_proof,
    post_skill_proof,
)

DEFAULT_INGEST_URL = "http://127.0.0.1:3999/v1/skills/ingest"


def _lessons_from_queries(
    queries: list[str],
    level: str | None,
    top_k: int | None,
    threshold: float | None,
) -> list[dict]:
    from adapters.demopeter.client import ask_rag
    from adapters.demopeter.map import map_to_microlesson

    lessons: list[dict] = []
    for q in queries:
        raw = ask_rag(q, top_k=top_k, threshold=threshold)
        lessons.append(
            map_to_microlesson(
                raw, query=q, level=level, similarity_threshold=threshold
            )
        )
    return lessons


def _lessons_from_files(paths: list[str]) -> list[dict]:
    lessons: list[dict] = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if isinstance(data, list):
            lessons.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            lessons.append(data)
        else:
            raise ValueError(f"无法解析 microlesson 文件: {p}")
    return lessons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m exporters.skill_proof",
        description="Guibu skill-proof 导出方：microlesson.v1 → skill-proof.v1",
    )
    ident = parser.add_mutually_exclusive_group(required=True)
    ident.add_argument("--email", help="明文 email，自动 sha256 生成 user_id")
    ident.add_argument("--user-id", help="直接给定 user_id（应为 email hash）")
    parser.add_argument("--query", action="append", default=[], help="实时问句（可多次）")
    parser.add_argument(
        "--lesson-file", action="append", default=[], help="本地 microlesson JSON 路径（可多次）"
    )
    parser.add_argument("--level", choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--out", type=Path, help="写 skill-proof JSON 到文件")
    parser.add_argument("--validate", action="store_true", help="按 contracts/skill-proof.v1.json 校验")
    parser.add_argument(
        "--ingest",
        nargs="?",
        const=DEFAULT_INGEST_URL,
        default=None,
        metavar="URL",
        help=(
            "schema 通过后 POST 到摄入端；"
            f"可省略 URL（默认 {DEFAULT_INGEST_URL}）"
        ),
    )
    args = parser.parse_args(argv)

    if not args.query and not args.lesson_file:
        parser.error("必须提供 --query 或 --lesson-file 至少一种输入")

    user_id = email_to_user_id(args.email) if args.email else args.user_id

    try:
        lessons: list[dict] = []
        lessons += _lessons_from_queries(args.query, args.level, args.top_k, args.threshold)
        lessons += _lessons_from_files(args.lesson_file)
        proof = export_skill_proof(user_id, lessons, level=args.level)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.validate:
        try:
            import jsonschema
        except ImportError:
            print("jsonschema not installed; skip --validate", file=sys.stderr)
        else:
            schema = json.loads(
                (_ROOT / "contracts" / "skill-proof.v1.json").read_text(encoding="utf-8")
            )
            try:
                jsonschema.validate(proof, schema)
            except jsonschema.ValidationError as exc:
                print(json.dumps({"error": f"schema: {exc.message}"}, ensure_ascii=False, indent=2))
                return 1

    if args.ingest:
        ingest_url = args.ingest
        if ingest_url.rstrip("/").endswith("/v1/skills/ingest"):
            url = ingest_url
        else:
            url = ingest_url.rstrip("/") + "/v1/skills/ingest"
        try:
            resp = post_skill_proof(url, proof)
        except (RuntimeError, OSError, ValueError) as exc:
            print(json.dumps({"error": f"ingest: {exc}"}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"ingest": resp}, ensure_ascii=False, indent=2), file=sys.stderr)

    out = json.dumps(proof, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(out + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
