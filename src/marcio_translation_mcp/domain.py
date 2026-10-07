from __future__ import annotations
from collections import Counter
from .db import connect, search_fts

KEYWORDS = {
    "insurance": {"policy","insurer","insured","premium","claim","coverage","deductible","liability","reinsurance","underwriting"},
    "legal": {"court","lawsuit","claimant","defendant","plaintiff","appeal","injunction","statute","legal","lawyer","attorney","contract"},
    "microfinance": {"microfinance","borrower","loan","credit","portfolio","arrears","delinquency","savings","mfi","microloan"},
    "religion": {"lord","god","jesus","christ","gospel","apostle","disciple","salvation","covenant","hymn","holy","spirit"},
    "idioms": set(),
}


def detect_domains(text: str, limit: int = 3) -> list[dict]:
    low=text.casefold()
    scores=Counter()
    for domain, words in KEYWORDS.items():
        for word in words:
            if word in low:
                scores[domain]+=3
    try:
        con=connect()
        for row in search_fts(con,text,limit=20):
            scores[row["domain"]]+=1
        con.close()
    except Exception:
        pass
    if not scores:
        return [{"domain":"general","score":0}]
    return [{"domain":d,"score":s} for d,s in scores.most_common(limit)]
