from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# Conservative list: these are signals of US usage, not automatic errors.
US_TO_GB = {
    "color": "colour",
    "colors": "colours",
    "favorite": "favourite",
    "favorites": "favourites",
    "honor": "honour",
    "honors": "honours",
    "labor": "labour",
    "neighbor": "neighbour",
    "neighbors": "neighbours",
    "center": "centre",
    "centers": "centres",
    "theater": "theatre",
    "theaters": "theatres",
    "defense": "defence",
    "offense": "offence",
    "license plate": "number plate",
    "zip code": "postcode",
    "sidewalk": "pavement",
    "gasoline": "petrol",
    "elevator": "lift",
    "apartment": "flat",
    "vacation": "holiday",
    "cell phone": "mobile phone",
}

QUESTION_OPENERS = {
    "what", "when", "where", "why", "who", "whom", "whose", "which", "how",
    "do", "does", "did", "is", "are", "am", "was", "were", "can", "could",
    "will", "would", "shall", "should", "have", "has", "had", "may", "might", "must",
}

COMMON_EN = {
    "the","a","an","i","you","he","she","it","we","they","is","are","am","was","were",
    "be","been","have","has","had","do","does","did","to","of","in","on","at","for","from",
    "with","and","or","but","not","this","that","these","those","my","your","his","her","our",
    "their","what","when","where","why","who","how","can","could","will","would","shall","should",
}

@dataclass
class SourceAnalysis:
    source_text: str
    probable_language: str
    english_signal: float
    possible_us_usage: list[dict[str, str]]
    direct_question_without_question_mark: bool
    fragmented_or_incomplete: bool
    mixed_language_signal: bool
    protected_tokens: dict[str, list[str]]
    recommended_classification: str
    model_checks_required: list[str]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)


def _english_signal(text: str) -> float:
    ws=[w.casefold() for w in _words(text)]
    if not ws:
        return 0.0
    common=sum(1 for w in ws if w in COMMON_EN)
    ascii_letters=sum(ch.isascii() and ch.isalpha() for ch in text)
    letters=sum(ch.isalpha() for ch in text) or 1
    ascii_ratio=ascii_letters/letters
    return round(min(1.0, 0.55*ascii_ratio + 0.45*min(1.0, common/max(1,len(ws))*4)), 3)


def _protected(text: str) -> dict[str,list[str]]:
    return {
        "urls": re.findall(r"https?://\S+|www\.\S+", text, flags=re.I),
        "placeholders": re.findall(r"\[[^\]]+\]|\{[^{}]+\}|<[^<>]+>", text),
        "numbers": re.findall(r"(?<!\w)[+-]?(?:\d+[.,]?\d*|[.,]\d+)%?", text),
        "codes": re.findall(r"\b[A-Z]{2,}(?:[-_/][A-Z0-9]+)*\b", text),
    }


def analyse_source(text: str) -> dict[str, Any]:
    stripped=text.strip()
    words=_words(stripped)
    signal=_english_signal(stripped)
    probable="English" if signal >= 0.48 else ("Unknown/needs model verification" if words else "No lexical text")
    low=stripped.casefold()
    us=[]
    for us_term,gb_term in US_TO_GB.items():
        if re.search(rf"(?<!\w){re.escape(us_term)}(?!\w)", low):
            us.append({"source_form":us_term,"possible_en_gb_form":gb_term,"status":"possible_US_usage_review_context"})
    first=words[0].casefold() if words else ""
    direct_q=bool(first in QUESTION_OPENERS and stripped and not stripped.endswith("?"))
    # Heuristic only. It intentionally does not 'repair' the source.
    fragmented=bool(stripped and (
        stripped.endswith(("and","or","but","because","if","when","what about"))
        or len(words) <= 2
        or re.search(r"\b(my your|the the|to to|we we|my my)\b", low)
    ))
    non_ascii_letters=sum(ch.isalpha() and not ch.isascii() for ch in stripped)
    mixed=bool(non_ascii_letters and words and signal >= 0.4)
    classification="None apply"
    if mixed:
        classification="More than 1 language"
    elif probable != "English" and words:
        classification="Wrong language"
    elif fragmented and len(words) <= 1:
        classification="Garbled"
    elif direct_q:
        classification="Typos or Spelling errors"
    return asdict(SourceAnalysis(
        source_text=text,
        probable_language=probable,
        english_signal=signal,
        possible_us_usage=us,
        direct_question_without_question_mark=direct_q,
        fragmented_or_incomplete=fragmented,
        mixed_language_signal=mixed,
        protected_tokens=_protected(text),
        recommended_classification=classification,
        model_checks_required=[
            "orthography and typing errors",
            "grammar and syntax",
            "verb tense and aspect",
            "prepositions and phrasal verbs",
            "punctuation and capitalisation",
            "semantic coherence and ambiguity",
            "EN-GB localisation",
            "register, tone and style",
        ],
    ))
