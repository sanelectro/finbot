#!/usr/bin/env python3
"""
Quick metrics checker - Check evaluation results for a specific or latest JSON.

Usage:
    # Show latest result
    python src/evaluation/check_metrics.py

    # Show specific file
    python src/evaluation/check_metrics.py data/evaluation/internal_evaluation_hr_20260510_082901.json

    # Show specific role (picks latest file for that role)
    python src/evaluation/check_metrics.py --role hr
    python src/evaluation/check_metrics.py --role finance
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime

EVAL_DIR = "data/evaluation"

VALID_ROLES = ["hr", "finance", "engineering", "marketing", "employee", "all"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _latest_file(pattern: str) -> str | None:
    """Return the most recently created file matching a glob pattern, or None."""
    files = glob.glob(pattern)
    return max(files, key=os.path.getctime) if files else None


def resolve_target(args: argparse.Namespace) -> str | None:
    """
    Determine which JSON file to inspect:
      1. Explicit path passed as positional argument → use as-is
      2. --role flag → pick latest internal_evaluation_<role>_*.json
      3. Neither → pick the latest internal_evaluation_*.json
    """
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            return None
        return args.file

    if args.role:
        role_label = "all" if args.role == "all" else args.role
        pattern = f"{EVAL_DIR}/internal_evaluation_{role_label}_*.json"
        target = _latest_file(pattern)
        if not target:
            print(f"❌ No evaluation results found for role '{args.role}'.")
            print(f"   Run: python -m src.evaluation.ragas_orchestrator --role {args.role}")
            return None
        return target

    # Default: absolute latest
    target = _latest_file(f"{EVAL_DIR}/internal_evaluation_*.json")
    if not target:
        print("❌ No evaluation results found. Run evaluation first:")
        print("   python -m src.evaluation.ragas_orchestrator")
        return None
    return target


# ── Display functions ──────────────────────────────────────────────────────────

def show_metrics(filepath: str) -> None:
    """Pretty-print metrics from a result JSON file."""
    print(f"\n📊 Results: {filepath}")
    print("=" * 70)

    try:
        with open(filepath, "r") as f:
            results = json.load(f)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # Per-config results
    for config_name, config_result in results.items():
        if config_name in ("comparison", "metadata"):
            continue
        if not isinstance(config_result, dict):
            continue

        if "error" in config_result:
            print(f"\n❌ {config_name}: {config_result['error']}")
            continue

        print(f"\n🎯 {config_name}")
        print(f"   Overall Score : {config_result.get('overall_score', 0):.3f}")
        print(
            f"   Valid Results : "
            f"{config_result.get('valid_results', 0)}/{config_result.get('total_cases', 0)}"
        )

        if "metrics_summary" in config_result:
            print("   📈 Metrics:")
            for metric, stats in config_result["metrics_summary"].items():
                mean = stats.get("mean", 0)
                std = stats.get("std", 0)
                min_v = stats.get("min", 0)
                max_v = stats.get("max", 0)
                bar = _score_bar(mean)
                print(f"      {bar} {metric:<22} {mean:.3f} (±{std:.3f})  [min={min_v:.3f} max={max_v:.3f}]")

        if "collection_analysis" in config_result:
            print("   📊 Collection Performance:")
            for collection, stats in config_result["collection_analysis"].items():
                print(f"      • {collection}: {stats['mean_score']:.3f} ({stats['count']} cases)")

    # Comparison block
    if "comparison" in results:
        comparison = results["comparison"]
        print(f"\n{'─'*70}")
        print("🏆 Best Configuration per Metric:")
        if "best_configuration" in comparison:
            for metric, best in comparison["best_configuration"].items():
                print(f"   • {metric:<22} → {best['config']} ({best['score']:.3f})")

        if "performance_improvement" in comparison:
            print("\n📉 Full System vs Direct Search (delta):")
            for metric, imp in comparison["performance_improvement"].items():
                abs_i = imp["absolute_improvement"]
                pct_i = imp["percentage_improvement"]
                sign = "+" if abs_i >= 0 else ""
                print(f"   • {metric:<22} {sign}{abs_i:.3f}  ({sign}{pct_i:.1f}%)")


def _score_bar(score: float) -> str:
    """Return a coloured emoji indicator for a score 0-1."""
    if score >= 0.7:
        return "🟢"
    elif score >= 0.4:
        return "🟡"
    else:
        return "🔴"


def show_available_files() -> None:
    """List all evaluation JSON files grouped by role."""
    if not os.path.exists(EVAL_DIR):
        print(f"❌ Evaluation directory not found: {EVAL_DIR}")
        return

    json_files = sorted(
        glob.glob(f"{EVAL_DIR}/internal_evaluation_*.json"),
        key=os.path.getmtime,
        reverse=True,
    )

    if not json_files:
        print("   (No evaluation JSON files found)")
        return

    print(f"\n📁 Available evaluation results in '{EVAL_DIR}':\n")
    for fp in json_files:
        fname = os.path.basename(fp)
        size = os.path.getsize(fp)
        mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"   📄 {fname}  ({size:,} bytes, {mtime})")
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinBot Evaluation Metrics Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Latest result (any role)
  python src/evaluation/check_metrics.py

  # Latest result for a specific role
  python src/evaluation/check_metrics.py --role hr
  python src/evaluation/check_metrics.py --role finance

  # Specific JSON file
  python src/evaluation/check_metrics.py data/evaluation/internal_evaluation_hr_20260510_082901.json
        """,
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Path to a specific evaluation JSON file (optional).",
    )
    parser.add_argument(
        "--role",
        choices=VALID_ROLES,
        default=None,
        help="Show latest results for a specific role.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available evaluation result files and exit.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    print("🔍 FinBot Evaluation Metrics Checker")
    print("=" * 70)

    args = parse_args()

    if args.list:
        show_available_files()
        sys.exit(0)

    show_available_files()

    target = resolve_target(args)
    if target:
        show_metrics(target)