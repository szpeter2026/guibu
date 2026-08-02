"""CLI: python -m adapters.demopeter \"你的问题\""""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python -m adapters.demopeter` from repo root
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapters.demopeter.client import ask_rag
from adapters.demopeter.map import map_to_microlesson


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m adapters.demopeter",
        description="Guibu ← DemoPeter：问一句，输出 microlesson.v1 JSON",
    )
    parser.add_argument("query", help="卡点问题 / 检索问句")
    parser.add_argument(
        "--level",
        choices=["beginner", "intermediate", "advanced"],
        default=None,
    )
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="若已安装 jsonschema，按 contracts/microlesson.v1.json 校验",
    )
    args = parser.parse_args(argv)

    try:
        raw = ask_rag(args.query, top_k=args.top_k, threshold=args.threshold)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    lesson = map_to_microlesson(raw, query=args.query, level=args.level)

    if args.validate:
        try:
            import jsonschema
        except ImportError:
            print("jsonschema not installed; skip --validate", file=sys.stderr)
        else:
            schema_path = _ROOT / "contracts" / "microlesson.v1.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(lesson, schema)

    print(json.dumps(lesson, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
