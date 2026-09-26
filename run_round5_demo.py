"""Compile-check the Round 5 trader and regenerate the included report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
REFERENCE_JSON = ROOT / "data" / "round5_reference_result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the clean Round 5 demo checks.")
    parser.add_argument(
        "--reference-json",
        type=Path,
        default=REFERENCE_JSON,
        help="Saved Round 5 result JSON used to regenerate graphs.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS,
        help="Output directory for regenerated HTML and CSV reports.",
    )
    return parser.parse_args()


def run_checked(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)

    trader = ROOT / "trader_round5.py"
    compile_cmd = [
        sys.executable,
        "-B",
        "-c",
        (
            "from pathlib import Path; "
            f"p=Path(r'{trader}'); "
            "compile(p.read_text(encoding='utf-8'), str(p), 'exec'); "
            "print('compile ok')"
        ),
    ]
    run_checked(compile_cmd)

    report_cmd = [
        sys.executable,
        str(ROOT / "make_round5_report.py"),
        "--submission-json",
        str(args.reference_json),
        "--html",
        str(args.results_dir / "round5_reference_report.html"),
        "--summary-csv",
        str(args.results_dir / "round5_reference_summary.csv"),
        "--product-csv",
        str(args.results_dir / "round5_reference_product_pnl.csv"),
        "--cluster-csv",
        str(args.results_dir / "round5_reference_cluster_pnl.csv"),
    ]
    run_checked(report_cmd)

    print()
    print(f"Report: {args.results_dir / 'round5_reference_report.html'}")
    print(f"Summary: {args.results_dir / 'round5_reference_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
