"""Compare ablation result files produced by ``python -m evaluation.run --out ...``.

    python -m evaluation.compare A.json B.json [C.json ...]

Prints one row per file. For the first two files it also prints the relative
reduction (A - B) / A of the hallucination rate and the absolute change in
execution success, so a claim like "reduced X by N%" is computed, not asserted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _rate(metrics: dict[str, Any], key: str) -> float:
    total = metrics["answerable"]
    return metrics[key] / total if total else 0.0


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if len(paths) < 2:
        print(__doc__)
        return 2
    runs = [json.loads(p.read_text()) for p in paths]
    header = (
        f"{'file':<28}{'prompt':<14}{'corr':<5}{'n':<4}"
        f"{'halluc':>8}{'valid1':>8}{'exec':>8}{'acc':>8}"
    )
    print(header)
    for path, run in zip(paths, runs, strict=True):
        m, c = run["metrics"], run["config"]
        print(
            f"{path.name:<28}{c['prompt_mode']:<14}{c['max_corrections']:<5}{m['answerable']:<4}"
            f"{_rate(m, 'hallucinated_first_try'):>8.1%}{_rate(m, 'valid_sql_first_try'):>8.1%}"
            f"{_rate(m, 'execution_success'):>8.1%}{_rate(m, 'execution_accuracy'):>8.1%}"
        )
    a, b = runs[0]["metrics"], runs[1]["metrics"]
    ha, hb = _rate(a, "hallucinated_first_try"), _rate(b, "hallucinated_first_try")
    print()
    if ha > 0:
        print(f"hallucination rate {ha:.1%} -> {hb:.1%}: relative reduction {(ha - hb) / ha:.1%}")
    else:
        print("first file has no hallucinations; relative reduction undefined")
    ea, eb = _rate(a, "execution_success"), _rate(b, "execution_success")
    print(f"execution success  {ea:.1%} -> {eb:.1%}: change {100 * (eb - ea):+.1f} points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
