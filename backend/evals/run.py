#!/usr/bin/env python3
"""
CLI runner for NiDaan RAG evaluation.

Usage:
    python -m backend.evals.run                          # run all
    python -m backend.evals.run --id tc_001              # single test case
    python -m backend.evals.run --mode nim               # specific LLM mode
    python -m backend.evals.run --format json            # JSON output
    python -m backend.evals.run --report html            # HTML report (opens browser)
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from evals.evaluator import Evaluator
from evals.report import print_report, save_json_report, save_html_report


def load_test_cases(path: str | None = None) -> list[dict]:
    if path is None:
        path = Path(__file__).resolve().parent / "test_cases.json"
    with open(path) as f:
        return json.load(f)


def set_mode(mode: str):
    """Override MODE in chain.py before importing it."""
    chain_path = Path(__file__).resolve().parent.parent / "chain.py"
    content = chain_path.read_text()
    content = content.replace(
        'MODE = "groq"',
        f'MODE = "{mode}"',
    )
    content = content.replace(
        'MODE = "nim"',
        f'MODE = "{mode}"',
    )
    content = content.replace(
        'MODE = "deepseek"',
        f'MODE = "{mode}"',
    )
    chain_path.write_text(content)
    print(f"  MODE set to: {mode}")


def main():
    parser = argparse.ArgumentParser(description="NiDaan RAG Evaluation Runner")
    parser.add_argument("--id", type=str, help="Run a single test case by ID")
    parser.add_argument("--mode", type=str, default=None,
                        choices=["groq", "nim", "deepseek"],
                        help="LLM mode to use")
    parser.add_argument("--format", type=str, default="cli",
                        choices=["cli", "json"],
                        help="Output format")
    parser.add_argument("--report", type=str, default=None,
                        choices=["html"],
                        help="Generate HTML report")
    parser.add_argument("--test-cases", type=str, default=None,
                        help="Path to test cases JSON file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path for JSON report")
    args = parser.parse_args()

    # Set mode if specified
    if args.mode:
        set_mode(args.mode)

    # Import chain after potential mode override
    from chain import get_chain

    # Load test cases
    all_cases = load_test_cases(args.test_cases)

    if args.id:
        all_cases = [c for c in all_cases if c["id"] == args.id]
        if not all_cases:
            print(f"❌ Test case '{args.id}' not found")
            sys.exit(1)

    print(f"\n{'=' * 55}")
    print(f"  NiDaan Eval — All Metrics")
    print(f"  Metrics: faithfulness, answer_relevancy, context_precision,")
    print(f"           clinical_accuracy, constraint_check, hindi_purity")
    print(f"  Test cases: {len(all_cases)}")
    print(f"{'=' * 55}\n")

    # Initialize chain and evaluator
    chain_fn = get_chain()
    evaluator = Evaluator(chain_fn=chain_fn)

    # Run evaluation
    result = evaluator.evaluate_all(all_cases)

    # Output
    if args.format == "json":
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            save_json_report(result, args.output)
            print(f"\n📄 Report saved to: {args.output}")
        else:
            print(output)
    else:
        print_report(result)

    if args.report == "html":
        html_path = save_html_report(result)
        print(f"\n📄 HTML report: {html_path}")

    # Exit with error code if any errors
    if result.get("errors"):
        sys.exit(1)


if __name__ == "__main__":
    main()
