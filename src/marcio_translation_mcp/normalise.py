from __future__ import annotations
import re
import unicodedata


def normalise_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", text or "")


def ngrams(text: str, max_n: int = 6) -> list[str]:
    ts = tokens(text)
    out: list[str] = []
    for n in range(min(max_n, len(ts)), 0, -1):
        for i in range(0, len(ts) - n + 1):
            out.append(" ".join(ts[i:i+n]))
    # Stable de-duplication
    seen=set(); dedup=[]
    for x in out:
        k=normalise_text(x)
        if k and k not in seen:
            seen.add(k); dedup.append(x)
    return dedup
