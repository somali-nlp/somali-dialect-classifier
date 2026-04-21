"""
Script detection and code-switching ratio utilities for Somali text.

Somali is written primarily in Latin script (standard), with Arabic script
in Southern dialects and religious contexts, and Osmanya script (U+10480–U+104AF)
as the traditional Somali writing system.
"""

import unicodedata


def _classify_char_script(char: str) -> str | None:
    """
    Return the script family for a single character, or None for non-alphabetic.

    Returns one of: "latin", "arabic", "osmanya", "other_alpha".
    Returns None for digits, punctuation, whitespace.
    """
    cp = ord(char)
    # Osmanya block: U+10480–U+104AF
    if 0x10480 <= cp <= 0x104AF:
        return "osmanya"
    cat = unicodedata.category(char)
    if not cat.startswith("L"):
        return None
    try:
        name = unicodedata.name(char, "")
    except ValueError:
        return "other_alpha"
    if "LATIN" in name:
        return "latin"
    if "ARABIC" in name:
        return "arabic"
    return "other_alpha"


def detect_scripts(text: str) -> dict:
    """
    Detect which scripts are present in text and identify the dominant one.

    Args:
        text: Input text (any length).

    Returns:
        dict with keys:
          - "scripts": sorted list of script names present (e.g. ["arabic", "latin"])
          - "dominant_script": name of the most frequent script, or "latin" for empty text
    """
    counts: dict[str, int] = {}
    for ch in text:
        script = _classify_char_script(ch)
        if script is not None:
            counts[script] = counts.get(script, 0) + 1

    if not counts:
        return {"scripts": ["latin"], "dominant_script": "latin"}

    # Priority tiebreak: latin > arabic > osmanya > other_alpha
    priority = {"latin": 3, "arabic": 2, "osmanya": 1, "other_alpha": 0}
    dominant = max(counts, key=lambda s: (counts[s], priority.get(s, 0)))
    return {
        "scripts": sorted(counts.keys()),
        "dominant_script": dominant,
    }


def compute_cs_ratio(text: str) -> float:
    """
    Token-level code-switching ratio.

    Splits on whitespace; for each token computes its dominant script.
    Returns fraction of tokens whose script differs from the overall
    dominant script. Purely non-alphabetic tokens are skipped.

    Returns:
        Float in [0.0, 1.0]. 0.0 = monolingual; 1.0 = fully switched.
    """
    if not text or not text.strip():
        return 0.0

    overall = detect_scripts(text)["dominant_script"]
    tokens = text.split()

    alphabetic_count = 0
    switched_count = 0

    for token in tokens:
        token_counts: dict[str, int] = {}
        for ch in token:
            script = _classify_char_script(ch)
            if script is not None:
                token_counts[script] = token_counts.get(script, 0) + 1
        if not token_counts:
            continue
        priority = {"latin": 3, "arabic": 2, "osmanya": 1, "other_alpha": 0}
        token_dominant = max(token_counts, key=lambda s: (token_counts[s], priority.get(s, 0)))
        alphabetic_count += 1
        if token_dominant != overall:
            switched_count += 1

    if alphabetic_count == 0:
        return 0.0
    return switched_count / alphabetic_count
