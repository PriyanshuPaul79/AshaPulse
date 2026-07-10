import re
from typing import Optional


def _normalize(text: str) -> str:
    """Lowercase and strip for comparison."""
    return text.lower().strip()


def _check_keywords_presence(text: str, keywords: list[str]) -> dict:
    """Check which keywords are present in the text."""
    text_lower = _normalize(text)
    found = []
    missing = []
    for kw in keywords:
        if _normalize(kw) in text_lower:
            found.append(kw)
        else:
            missing.append(kw)
    return {"found": found, "missing": missing, "count": len(found), "total": len(keywords)}


def clinical_accuracy(
    context: str,
    symptoms: str,
    output: dict,
    expected: Optional[dict] = None,
) -> dict:
    """
    Compute clinical accuracy by comparing output against expected ground truth.
    Metrics:
    - criticality_match: exact match of severity level
    - refer_to_phc_match: boolean match
    - diagnosis_keyword_recall: proportion of expected diagnosis keywords found
    - must_not_have_violations: if any prohibited keywords appear
    - follow_up_days_match: exact follow-up days match
    - medicines_count_check: whether medicines count is in expected range
    - home_care_count_check: whether home care count is in expected range
    - red_flags_count_check: whether red flags count is in expected range
    """
    try:
        if expected is None:
            return {
                "score": 0.0,
                "error": "No expected ground truth provided",
                "details": {},
            }

        details = {}

        # 1. Criticality match
        output_crit = output.get("criticality", "").lower().strip()
        expected_crit = expected.get("criticality", "").lower().strip()
        criticality_match = output_crit == expected_crit
        details["criticality_match"] = {
            "expected": expected_crit,
            "actual": output_crit,
            "match": criticality_match,
        }

        # 2. Refer to PHC match
        output_refer = bool(output.get("refer_to_phc", False))
        expected_refer = bool(expected.get("refer_to_phc", False))
        refer_match = output_refer == expected_refer
        details["refer_to_phc_match"] = {
            "expected": expected_refer,
            "actual": output_refer,
            "match": refer_match,
        }

        # 3. Diagnosis keyword recall
        output_text = " ".join([
            output.get("diagnosis", ""),
            " ".join(output.get("differential_diagnosis", [])),
            output.get("reason", ""),
        ])
        diagnosis_kw = expected.get("diagnosis_keywords", [])
        kw_result = _check_keywords_presence(output_text, diagnosis_kw)
        details["diagnosis_keywords"] = kw_result

        # 4. Must-not-have violations
        must_not = expected.get("must_not_have", [])
        violations = _check_keywords_presence(output_text, must_not)
        violations["found"] = violations["found"]
        details["must_not_have_violations"] = {
            "violations": violations["found"],
            "num_violations": len(violations["found"]),
        }

        # 5. Follow-up days match
        expected_follow_up = expected.get("follow_up_days", "")
        output_follow_up = str(output.get("follow_up_days", ""))
        follow_up_match = _normalize(expected_follow_up) == _normalize(output_follow_up)
        details["follow_up_days_match"] = {
            "expected": expected_follow_up,
            "actual": output_follow_up,
            "match": follow_up_match,
        }

        # 6. Medicines count check
        output_meds_count = len(output.get("medicines", []))
        med_min = expected.get("medicines_count_min", 0)
        med_max = expected.get("medicines_count_max", 100)
        med_in_range = med_min <= output_meds_count <= med_max
        details["medicines_count"] = {
            "expected_min": med_min,
            "expected_max": med_max,
            "actual": output_meds_count,
            "in_range": med_in_range,
        }

        # 7. Home care count check
        output_hc_count = len(output.get("home_care", []))
        hc_min = expected.get("home_care_count_min", 0)
        hc_max = expected.get("home_care_count_max", 100)
        hc_in_range = hc_min <= output_hc_count <= hc_max
        details["home_care_count"] = {
            "expected_min": hc_min,
            "expected_max": hc_max,
            "actual": output_hc_count,
            "in_range": hc_in_range,
        }

        # 8. Red flags count check
        output_rf_count = len(output.get("red_flags", []))
        rf_min = expected.get("red_flags_count_min", 0)
        rf_max = expected.get("red_flags_count_max", 100)
        rf_in_range = rf_min <= output_rf_count <= rf_max
        details["red_flags_count"] = {
            "expected_min": rf_min,
            "expected_max": rf_max,
            "actual": output_rf_count,
            "in_range": rf_in_range,
        }

        # Composite score: weighted average of all checks
        binary_checks = [
            criticality_match,
            refer_match,
            follow_up_match,
            med_in_range,
            hc_in_range,
            rf_in_range,
        ]

        kw_score = kw_result["count"] / max(kw_result["total"], 1)
        must_not_score = 0.0 if violations["found"] else 1.0

        weights = {
            "criticality": 0.30,
            "refer_to_phc": 0.10,
            "follow_up": 0.10,
            "medicines_count": 0.05,
            "home_care_count": 0.05,
            "red_flags_count": 0.05,
            "diagnosis_keywords": 0.20,
            "must_not_have": 0.15,
        }

        weighted_score = (
            (1.0 if criticality_match else 0.0) * weights["criticality"]
            + (1.0 if refer_match else 0.0) * weights["refer_to_phc"]
            + (1.0 if follow_up_match else 0.0) * weights["follow_up"]
            + (1.0 if med_in_range else 0.0) * weights["medicines_count"]
            + (1.0 if hc_in_range else 0.0) * weights["home_care_count"]
            + (1.0 if rf_in_range else 0.0) * weights["red_flags_count"]
            + kw_score * weights["diagnosis_keywords"]
            + must_not_score * weights["must_not_have"]
        )

        return {
            "score": round(weighted_score, 4),
            "details": details,
            "error": None,
        }

    except Exception as e:
        return {"score": 0.0, "error": str(e), "details": {}}
