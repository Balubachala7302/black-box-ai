
"""Evaluate BLACK BOX AI's actual investigation decisions on synthetic cases."""

import json
from typing import Any

from app.evaluation.benchmark_cases import BENCHMARK_CASES
from app.schemas import IncidentRequest
from app.services.investigator import investigate


def evaluate_baseline() -> dict[str, Any]:
    results = []

    known_total = 0
    known_correct = 0
    healthy_total = 0
    healthy_correct = 0
    uncertain_total = 0
    uncertain_correct = 0

    for case in BENCHMARK_CASES:
        case_id = case["case_id"]
        expected = case["expected_cause"]

        # Build a validated incident request and run the real pipeline.
        incident = IncidentRequest(**case["incident"].model_dump()) \
            if hasattr(case["incident"], "model_dump") \
            else IncidentRequest(**case["incident"])

        investigation = investigate(incident)

        hypotheses = investigation.get("hypotheses", [])
        root_decision = investigation.get("root_cause_decision", {})

        predicted = root_decision.get("root_cause")
        decision_status = root_decision.get("status", "missing_decision")

        if expected is not None:
            category = "known_cause"
            known_total += 1
            correct = predicted == expected
            known_correct += int(correct)

        elif case_id == "healthy-001":
            category = "healthy"
            healthy_total += 1
            correct = predicted is None
            healthy_correct += int(correct)

        else:
            category = "uncertain"
            uncertain_total += 1
            correct = predicted is None
            uncertain_correct += int(correct)

        results.append({
            "case_id": case_id,
            "category": category,
            "expected_cause": expected,
            "predicted_cause": predicted,
            "decision_status": decision_status,
            "correct": correct,
            "hypothesis_count": len(hypotheses),
            "candidate_hypotheses": [
                {
                    "cause": hypothesis.get("cause"),
                    "verification_status": hypothesis.get(
                        "verification_status"
                    ),
                }
                for hypothesis in hypotheses
            ],
            "decision_reason": root_decision.get("reason"),
        })

    total = len(results)

    return {
        "benchmark": "BLACK BOX AI investigation pipeline",
        "cases_evaluated": total,
        "known_cause_accuracy": (
            round(known_correct / known_total, 4)
            if known_total else None
        ),
        "healthy_case_accuracy": (
            round(healthy_correct / healthy_total, 4)
            if healthy_total else None
        ),
        "uncertain_case_abstention_accuracy": (
            round(uncertain_correct / uncertain_total, 4)
            if uncertain_total else None
        ),
        "overall_case_accuracy": (
            round(sum(row["correct"] for row in results) / total, 4)
            if total else None
        ),
        "results": results,
        "limitations": [
            "The cases are synthetic and hand-designed.",
            "Expected causes are benchmark labels, not independent proof of causation.",
            "The investigation uses rule-based tools and verification rules.",
            "A supported candidate is not a confirmed real-world root cause.",
            "These metrics do not establish real-world diagnostic performance.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_baseline(), indent=2))
