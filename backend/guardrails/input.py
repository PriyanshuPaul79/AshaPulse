import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InputCheckResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    is_empty: bool = False
    is_too_long: bool = False
    has_prompt_injection: bool = False
    is_irrelevant: bool = False
    sanitized: str = ""


SUSPECTED_INJECTION_PATTERNS = [
    r"(?i)(ignore|disregard|forget|override|bypass)\s+(all\s+)?(previous|above|system|instructions)",
    r"(?i)(you\s+are\s+not|you\s+don'?t\s+have\s+to|act\s+as\s+if|pretend)",
    r"(?i)(system\s+prompt|system\s+message|your\s+prompt|your\s+instructions)",
    r"(?i)\b(sudo|root|admin|shell|terminal|exec|eval|exec)\b",
    r"(?i)\b(repeat|say|output|print)\s+(after|everything|all|the\s+above)\b",
    r"(?i)(forget|disregard|ignore)\s+(the\s+)?(above|previous|instructions|prompt)",
]

IRRELEVANT_KEYWORDS = [
    r"(?i)\b(what\s+is|who\s+is|weather|news|sports|cricket|movie|song|recipe|stock|price|cricket|bollywood|politics)\b",
    r"(?i)\b(computer|programming|python|javascript|code|github|website|app)\s+(help|question|problem|write|how)\b",
    r"(?i)\b(hello|hi|hey|thanks|thank\s+you)\s+(how\s+are\s+you|what\s+can\s+you\s+do|what do you do)\b",
    r"(?i)\b(write|create|build|make|tell)\s+(me\s+)?(a|an|the|some)\s+(poem|story|song|joke|recipe|code|function)\b",
    r"(?i)\b(how\s+(to|do\s+I|can\s+I|would\s+I))\b",
    r"(?i)\b(what\s+is\s+the\s+(capital|population|area|meaning|definition))\b",
]

MIN_SYMPTOM_LENGTH = 10
MAX_SYMPTOM_LENGTH = 2000


def is_relevant_symptom(text: str) -> bool:
    """Check if text looks like a symptom description rather than casual conversation."""
    medical_patterns = [
        r"(?i)\b(bukhaar|fever|dard|pain|khansi|cough|dast|diarrhea|ulti|vomit|sans|breath)\b",
        r"(?i)\b(baccha|child|bachhe|shishu|infant|mahila|woman|aadmi|man|patient|log|aadmi|aurat)\b",
        r"(?i)\b(din|day|week|month|hour|ghanta|saal|year|mahina|pichle|kal|aaj)\b",
        r"(?i)\b(dawai|medicine|dawa|injection|goli|tablet|syrup|ilaaj)\b",
        r"(?i)\b(phc|hospital|clinic|doctor|nurse|asha|anm|asptaal)\b",
        r"(?i)\b(khoon|blood|infection|sepsis|pneumonia|malaria|typhoid|dengue|infection|jaundice)\b",
        r"(?i)\b(degree|°[cf]|temperature|temp|bp|blood\s*pressure|pulse|weight|vajan)\b",
        r"(?i)\b(kamzori|thakan|kamjor|weakness|fatigue|chakkar|garda|garda)\b",
        r"(?i)\b(pet|stomach|paani|water|doodh|milk|khaana|food|bhookh|appetite)\b",
        r"(?i)\b(sar|head|gala|throat|naak|nose|aankh|eye|khaan|cough|senna|chest)\b",
        r"(?i)\b(daura|convulsion|seizure|behosh|unconscious|jhatka|fit|mirgi)\b",
        r"(?i)\b(prasav|pregnancy|garbh|delivery|baccheda|postpartum|period|maasik)\b",
    ]
    matches = sum(1 for p in medical_patterns if re.search(p, text))
    return matches >= 1


def check_input(symptoms: str) -> InputCheckResult:
    """Check if the input symptoms are valid, safe, and relevant."""
    violations = []

    sanitized = symptoms.strip()

    if not sanitized:
        return InputCheckResult(
            passed=False,
            violations=["Empty input"],
            is_empty=True,
        )

    if len(sanitized) < MIN_SYMPTOM_LENGTH:
        violations.append(
            f"Symptom description too short ({len(sanitized)} chars, "
            f"minimum {MIN_SYMPTOM_LENGTH})"
        )

    if len(sanitized) > MAX_SYMPTOM_LENGTH:
        violations.append(
            f"Symptom description too long ({len(sanitized)} chars, "
            f"maximum {MAX_SYMPTOM_LENGTH})"
        )

    has_injection = False
    for pattern in SUSPECTED_INJECTION_PATTERNS:
        if re.search(pattern, sanitized):
            violations.append(f"Possible prompt injection detected: {pattern}")
            has_injection = True

    is_irrelevant = False
    if not is_relevant_symptom(sanitized):
        is_irrelevant = True
        reason = "Input appears non-medical/irrelevant"
        for pattern in IRRELEVANT_KEYWORDS:
            if re.search(pattern, sanitized):
                reason = f"Input appears non-medical/irrelevant (matched: {pattern})"
                break
        violations.append(reason)

    passed = len(violations) == 0

    return InputCheckResult(
        passed=passed,
        violations=violations,
        is_empty=False,
        is_too_long=len(sanitized) > MAX_SYMPTOM_LENGTH,
        has_prompt_injection=has_injection,
        is_irrelevant=is_irrelevant,
        sanitized=sanitized,
    )
