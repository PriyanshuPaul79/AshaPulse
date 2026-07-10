import re
from typing import Optional


REQUIRED_FIELDS = [
    "criticality",
    "refer_to_phc",
    "reason",
    "red_flags",
    "diagnosis",
    "differential_diagnosis",
    "home_care",
    "medicines",
    "advice_in_hindi",
    "follow_up_days",
    "reassess_if_worsens",
]

VALID_CRITICALITIES = {"low", "medium", "high"}


def _check_medicines_structure(medicines: list) -> list[str]:
    """Check each medicine has required sub-fields."""
    errors = []
    required_med_fields = {"name", "dosage", "duration"}
    for i, med in enumerate(medicines):
        if not isinstance(med, dict):
            errors.append(f"medicines[{i}]: expected dict, got {type(med).__name__}")
            continue
        missing = required_med_fields - set(med.keys())
        if missing:
            errors.append(f"medicines[{i}]: missing fields {missing}")
        for key in required_med_fields:
            if key in med and not isinstance(med[key], str):
                errors.append(f"medicines[{i}].{key}: expected string, got {type(med[key]).__name__}")
    return errors


def _check_field_types(output: dict) -> list[str]:
    """Check field types match expected schema."""
    errors = []

    if not isinstance(output.get("criticality", ""), str):
        errors.append("criticality: expected string")
    if output.get("criticality", "").lower() not in VALID_CRITICALITIES:
        errors.append(f"criticality: '{output.get('criticality')}' not in {VALID_CRITICALITIES}")

    if not isinstance(output.get("refer_to_phc"), bool):
        errors.append(f"refer_to_phc: expected bool, got {type(output.get('refer_to_phc')).__name__}")

    for field in ["reason", "diagnosis", "advice_in_hindi", "follow_up_days"]:
        val = output.get(field, "")
        if not isinstance(val, str):
            errors.append(f"{field}: expected string")

    for field in ["red_flags", "home_care", "differential_diagnosis", "reassess_if_worsens"]:
        val = output.get(field, [])
        if not isinstance(val, list):
            errors.append(f"{field}: expected list")
        else:
            for i, item in enumerate(val):
                if not isinstance(item, str):
                    errors.append(f"{field}[{i}]: expected string")

    medicines = output.get("medicines", [])
    if not isinstance(medicines, list):
        errors.append("medicines: expected list")
    else:
        errors.extend(_check_medicines_structure(medicines))

    return errors


def _check_clinical_rules(output: dict) -> list[str]:
    """Check clinical constraints based on criticality level."""
    errors = []
    criticality = output.get("criticality", "").lower()
    medicines = output.get("medicines", [])
    home_care = output.get("home_care", [])
    red_flags = output.get("red_flags", [])
    refer_to_phc = output.get("refer_to_phc", False)

    if criticality == "high":
        if len(medicines) > 0:
            errors.append(f"HIGH criticality but {len(medicines)} medicines prescribed (expected [])")
        if len(home_care) > 0:
            errors.append(f"HIGH criticality but {len(home_care)} home care items (expected [])")
        if not refer_to_phc:
            errors.append("HIGH criticality but refer_to_phc is False")
        if len(red_flags) < 2:
            errors.append(f"HIGH criticality but only {len(red_flags)} red flags (expected ≥2)")

    elif criticality == "medium":
        if len(medicines) < 1:
            errors.append("MEDIUM criticality but no medicines prescribed (expected ≥1)")
        if refer_to_phc:
            errors.append("MEDIUM criticality but refer_to_phc is True")
        if len(home_care) < 3 or len(home_care) > 5:
            errors.append(f"MEDIUM criticality but {len(home_care)} home care items (expected 3-5)")

    elif criticality == "low":
        if referral := output.get("follow_up_days", ""):
            if referral == "immediate_referral":
                errors.append("LOW criticality but follow_up_days is 'immediate_referral'")
        if len(medicines) > 2:
            errors.append(f"LOW criticality but {len(medicines)} medicines (expected 0-2)")
        if refer_to_phc:
            errors.append("LOW criticality but refer_to_phc is True")
        if len(home_care) < 3 or len(home_care) > 4:
            errors.append(f"LOW criticality but {len(home_care)} home care items (expected 3-4)")

    follow_up = output.get("follow_up_days", "")
    if criticality == "high" and follow_up != "immediate_referral":
        errors.append(f"HIGH criticality but follow_up_days is '{follow_up}' (expected 'immediate_referral')")

    if output.get("reassess_if_worsens") == "already_high":
        pass
    elif isinstance(output.get("reassess_if_worsens"), list):
        if len(output.get("reassess_if_worsens", [])) < 2:
            errors.append(f"reassess_if_worsens has only {len(output.get('reassess_if_worsens', []))} items (expected ≥2)")

    return errors


def constraint_check(
    context: str,
    symptoms: str,
    output: dict,
) -> dict:
    """
    Check structural and clinical constraints on the output.
    Returns a score (1.0 = all constraints passed) and a list of violations.
    """
    try:
        all_errors = []
        all_errors.extend(_check_field_types(output))
        all_errors.extend(_check_clinical_rules(output))

        missing_fields = [f for f in REQUIRED_FIELDS if f not in output]
        if missing_fields:
            all_errors.append(f"Missing required fields: {missing_fields}")

        num_checks = 10 + len(REQUIRED_FIELDS)
        num_violations = len(all_errors)
        score = max(0.0, 1.0 - (num_violations / max(num_checks, 1)))

        return {
            "score": round(score, 4),
            "num_violations": num_violations,
            "violations": all_errors,
            "missing_fields": missing_fields,
            "error": None,
        }

    except Exception as e:
        return {"score": 0.0, "error": str(e), "violations": []}
