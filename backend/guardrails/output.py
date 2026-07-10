import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OutputCheckResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    is_valid_json: bool = True
    has_all_fields: bool = True
    missing_fields: list[str] = field(default_factory=list)
    clinical_violations: list[str] = field(default_factory=list)
    hindi_violations: list[str] = field(default_factory=list)
    medicine_violations: list[str] = field(default_factory=list)


REQUIRED_FIELDS = [
    "criticality", "refer_to_phc", "reason", "red_flags",
    "diagnosis", "differential_diagnosis", "home_care",
    "medicines", "advice_in_hindi", "follow_up_days",
    "reassess_if_worsens",
]


def _check_field_types(output: dict) -> list[str]:
    """Type-check the output fields."""
    errors = []
    if not isinstance(output.get("criticality", ""), str):
        errors.append("criticality must be a string")
    if output.get("criticality", "") not in {"low", "medium", "high"}:
        errors.append(f"criticality must be one of low/medium/high, got '{output.get('criticality')}'")
    if not isinstance(output.get("refer_to_phc"), bool):
        errors.append("refer_to_phc must be a boolean")
    if not isinstance(output.get("reason", ""), str):
        errors.append("reason must be a string")
    for field in ["red_flags", "home_care", "differential_diagnosis", "reassess_if_worsens"]:
        val = output.get(field, [])
        if not isinstance(val, list):
            errors.append(f"{field} must be a list")
    medicines = output.get("medicines", [])
    if not isinstance(medicines, list):
        errors.append("medicines must be a list")
    else:
        for i, med in enumerate(medicines):
            if not isinstance(med, dict):
                errors.append(f"medicines[{i}] must be a dict")
                continue
            for key in ["name", "dosage", "duration"]:
                if key not in med:
                    errors.append(f"medicines[{i}] missing '{key}'")
    return errors


def _check_clinical_rules(output: dict) -> list[str]:
    """Clinical rule violations."""
    errors = []
    criticality = output.get("criticality", "")
    medicines = output.get("medicines", [])
    home_care = output.get("home_care", [])
    red_flags = output.get("red_flags", [])
    refer = output.get("refer_to_phc", False)

    if criticality == "high":
        if medicines:
            errors.append(f"HIGH severity: expected 0 medicines, got {len(medicines)}")
        if home_care:
            errors.append(f"HIGH severity: expected 0 home care items, got {len(home_care)}")
        if not refer:
            errors.append("HIGH severity: refer_to_phc must be true")
        if len(red_flags) < 2:
            errors.append(f"HIGH severity: expected ≥2 red flags, got {len(red_flags)}")

    elif criticality == "medium":
        if not medicines:
            errors.append("MEDIUM severity: must prescribe at least 1 medicine")
        if refer:
            errors.append("MEDIUM severity: refer_to_phc must be false")
        if len(home_care) < 3 or len(home_care) > 5:
            errors.append(f"MEDIUM severity: expected 3-5 home care items, got {len(home_care)}")

    elif criticality == "low":
        if len(medicines) > 2:
            errors.append(f"LOW severity: expected ≤2 medicines, got {len(medicines)}")
        if refer:
            errors.append("LOW severity: refer_to_phc must be false")
    else:
        errors.append(f"Unknown criticality: '{criticality}'")

    follow_up = output.get("follow_up_days", "")
    if criticality == "high" and follow_up != "immediate_referral":
        errors.append(f"HIGH severity: follow_up_days should be 'immediate_referral', got '{follow_up}'")

    return errors


def _check_hindi_purity(output: dict) -> list[str]:
    """Check that advice_in_hindi is pure Devanagari."""
    errors = []
    advice = output.get("advice_in_hindi", "")
    if not advice:
        errors.append("advice_in_hindi is empty")
        return errors

    english_words = re.findall(r"[a-zA-Z]+", advice)
    if english_words:
        errors.append(f"advice_in_hindi contains {len(english_words)} non-Devanagari words: {english_words[:5]}")

    return errors


def _check_medicine_safety(output: dict) -> list[str]:
    """Basic medicine safety checks."""
    errors = []
    for med in output.get("medicines", []):
        name = med.get("name", "").lower()
        dosage = med.get("dosage", "").lower()
        duration = med.get("duration", "").lower()

        if "paracetamol" in name and "mg" not in dosage and "ml" not in dosage:
            errors.append(f"Paracetamol dosage missing strength: '{dosage}'")

        if "ors" in name and "water" not in dosage and "liter" not in dosage and "पानी" not in dosage and "लीटर" not in dosage:
            errors.append(f"ORS should specify dilution water: '{dosage}'")

        if "antibiotic" in name or "antibacterial" in name:
            errors.append(f"Antibiotic prescribed: '{name}' — only if F-IMNCI recommends")

    return errors


def check_output(output: dict) -> OutputCheckResult:
    """Validate the model output against structural, clinical, and safety rules."""
    violations = []

    type_violations = _check_field_types(output)
    violations.extend(type_violations)

    clinical_violations = _check_clinical_rules(output)
    violations.extend(clinical_violations)

    hindi_violations = _check_hindi_purity(output)
    violations.extend(hindi_violations)

    med_violations = _check_medicine_safety(output)
    violations.extend(med_violations)

    missing = [f for f in REQUIRED_FIELDS if f not in output]

    passed = len(violations) == 0

    return OutputCheckResult(
        passed=passed,
        violations=violations,
        is_valid_json=isinstance(output, dict),
        has_all_fields=len(missing) == 0,
        missing_fields=missing,
        clinical_violations=clinical_violations,
        hindi_violations=hindi_violations,
        medicine_violations=med_violations,
    )
