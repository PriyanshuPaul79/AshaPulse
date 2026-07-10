import re
from typing import Optional


DEVANAGARI_UNICODE_RANGE = r"[\u0900-\u097F]"
DEVANAGARI_PUNCTUATION = set("।॥,;.!?-:\"'()[]{}")
DEVANAGARI_NUMERALS = set("०१२३४५६७८९")


def _is_devanagari_only(text: str) -> bool:
    """Check if text contains only Devanagari characters, punctuation, and whitespace."""
    for char in text:
        if char.isspace():
            continue
        if char in DEVANAGARI_PUNCTUATION:
            continue
        if char in DEVANAGARI_NUMERALS:
            continue
        if not re.match(DEVANAGARI_UNICODE_RANGE, char):
            return False
    return True


def _find_english_chunks(text: str) -> list[dict]:
    """Find portions of text that are not Devanagari."""
    violations = []
    current_word = ""
    current_start = -1

    for i, char in enumerate(text):
        if char.isspace() or char in DEVANAGARI_PUNCTUATION:
            if current_word and not all(
                c.isspace() or c in DEVANAGARI_PUNCTUATION or c in DEVANAGARI_NUMERALS or re.match(DEVANAGARI_UNICODE_RANGE, c)
                for c in current_word
            ):
                has_non_devanagari = False
                for c in current_word:
                    if not (c.isspace() or c in DEVANAGARI_PUNCTUATION or c in DEVANAGARI_NUMERALS or re.match(DEVANAGARI_UNICODE_RANGE, c)):
                        has_non_devanagari = True
                        break
                if has_non_devanagari:
                    violations.append({
                        "text": current_word,
                        "position": current_start,
                        "length": len(current_word),
                    })
            current_word = ""
            current_start = -1
        else:
            if current_start == -1:
                current_start = i
            current_word += char

    if current_word:
        has_non_devanagari = False
        for c in current_word:
            if not (c.isspace() or c in DEVANAGARI_PUNCTUATION or c in DEVANAGARI_NUMERALS or re.match(DEVANAGARI_UNICODE_RANGE, c)):
                has_non_devanagari = True
                break
        if has_non_devanagari:
            violations.append({
                "text": current_word,
                "position": current_start,
                "length": len(current_word),
            })

    return violations


def _find_english_chunks_simple(text: str) -> list[str]:
    """Find non-Devanagari words using regex."""
    english_words = re.findall(r"[a-zA-Z0-9]+", text)
    result = []
    for word in english_words:
        if any(c.isalpha() and ord(c) < 128 for c in word):
            if not all(c in "0123456789" for c in word):
                result.append(word)
    return result


def hindi_purity(
    context: str,
    symptoms: str,
    output: dict,
) -> dict:
    """
    Check that 'advice_in_hindi' field contains only Devanagari script.
    Returns purity score (1.0 = pure Hindi, 0.0 = contains English/Roman text).
    """
    try:
        advice = output.get("advice_in_hindi", "")
        if not advice:
            return {
                "score": 0.0,
                "purity": 0.0,
                "num_violations": 1,
                "violations": ["advice_in_hindi is empty"],
                "total_chars": 0,
                "non_hindi_chars": 0,
                "error": "Empty advice_in_hindi field",
            }

        total_chars = len(advice.strip())
        non_hindi_chars = 0
        non_hindi_words = []

        english_words = _find_english_chunks_simple(advice)

        for char in advice:
            if char.isspace():
                continue
            if char in DEVANAGARI_PUNCTUATION:
                continue
            if char in DEVANAGARI_NUMERALS:
                continue
            if not re.match(DEVANAGARI_UNICODE_RANGE, char):
                non_hindi_chars += 1

        total_non_space = sum(1 for c in advice if not c.isspace())
        purity = (
            1.0 - (non_hindi_chars / max(total_non_space, 1))
            if total_non_space > 0
            else 1.0
        )

        is_pure = _is_devanagari_only(advice)

        return {
            "score": round(purity, 4),
            "purity": round(purity, 4),
            "is_pure": is_pure,
            "num_violations": len(english_words),
            "violations": english_words[:20],
            "total_chars": total_chars,
            "non_hindi_chars": non_hindi_chars,
            "error": None,
        }

    except Exception as e:
        return {"score": 0.0, "error": str(e), "violations": []}
