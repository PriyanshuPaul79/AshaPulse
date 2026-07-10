import json
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Callable, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from chain import load_retriever
from evals.metrics.faithfulness import faithfulness as faithfulness_metric
from evals.metrics.answer_relevancy import answer_relevancy as answer_relevancy_metric
from evals.metrics.context_precision import context_precision as context_precision_metric
from evals.metrics.clinical_accuracy import clinical_accuracy as clinical_accuracy_metric
from evals.metrics.constraint_check import constraint_check as constraint_check_metric
from evals.metrics.hindi_purity import hindi_purity as hindi_purity_metric


class Evaluator:
    """
    Core evaluation engine.
    Runs the actual RAG chain on test cases, then computes all metrics.
    """

    METRIC_NAMES = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "clinical_accuracy",
        "constraint_check",
        "hindi_purity",
    ]

    def __init__(self, chain_fn: Callable, embedding_model=None):
        self.chain_fn = chain_fn
        self.retriever = load_retriever()
        self.embedding_model = embedding_model

    def evaluate_single(self, tc: dict) -> dict:
        symptoms = tc["symptoms"]
        expected = tc.get("expected")

        # 1. Run the actual RAG chain
        output = self.chain_fn(symptoms)

        # 2. Retrieve context for faithfulness
        context_docs = self.retriever.invoke(symptoms)
        context = "\n\n".join([d.page_content for d in context_docs])

        # 3. Compute all metrics
        faithfulness_result = faithfulness_metric(
            context=context, symptoms=symptoms, output=output,
        )

        answer_relevancy_result = answer_relevancy_metric(
            context=context, symptoms=symptoms, output=output,
        )

        context_precision_result = context_precision_metric(
            context=context, symptoms=symptoms, output=output,
        )

        clinical_accuracy_result = clinical_accuracy_metric(
            context=context, symptoms=symptoms, output=output,
            expected=expected,
        )

        constraint_check_result = constraint_check_metric(
            context=context, symptoms=symptoms, output=output,
        )

        hindi_purity_result = hindi_purity_metric(
            context=context, symptoms=symptoms, output=output,
        )

        return {
            "id": tc["id"],
            "symptoms": symptoms,
            "expected": expected,
            "output": output,
            "faithfulness": faithfulness_result,
            "answer_relevancy": answer_relevancy_result,
            "context_precision": context_precision_result,
            "clinical_accuracy": clinical_accuracy_result,
            "constraint_check": constraint_check_result,
            "hindi_purity": hindi_purity_result,
        }

    def evaluate_all(self, test_cases: list[dict]) -> dict:
        results = []
        errors = []

        for tc in test_cases:
            try:
                result = self.evaluate_single(tc)
                results.append(result)
                self._print_progress(result)
            except Exception as e:
                errors.append({"id": tc["id"], "error": str(e)})
                print(f"  [{tc['id']}] ❌ Error: {e}")

        return {
            "results": results,
            "errors": errors,
            "summary": self._aggregate(results),
        }

    def _print_progress(self, result: dict):
        parts = []
        for name in self.METRIC_NAMES:
            metric = result.get(name, {})
            score = metric.get("score", 0.0)
            label = f"{name}={score:.4f}"
            err = metric.get("error")
            if err and score == 0.0:
                label += f"[!{err}]"
            parts.append(label)
        print(f"  [{result['id']}]  " + "  ".join(parts))

    def _aggregate(self, results: list[dict]) -> dict:
        if not results:
            return {}

        summary = {"num_cases": len(results)}

        for name in self.METRIC_NAMES:
            scores = []
            for r in results:
                metric = r.get(name, {})
                score = metric.get("score")
                if score is not None:
                    scores.append(score)
            if scores:
                summary[f"avg_{name}"] = round(mean(scores), 4)
                summary[f"min_{name}"] = round(min(scores), 4)
                summary[f"max_{name}"] = round(max(scores), 4)

        summary["total_claims_evaluated"] = sum(
            r["faithfulness"].get("total_claims", 0) for r in results
        )
        summary["total_supported_claims"] = sum(
            r["faithfulness"].get("supported_claims", 0) for r in results
        )
        summary["overall_support_rate"] = round(
            summary["total_supported_claims"]
            / max(summary["total_claims_evaluated"], 1),
            4,
        ) if summary.get("total_claims_evaluated", 0) > 0 else 0.0

        return summary
