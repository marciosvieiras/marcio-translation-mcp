from __future__ import annotations
import re
from typing import Any
from .db import connect, search_exact
from .validators import validate

NEG_EN={"not","no","never","neither","nor","without","n't"}
NEG_PT={"não","nunca","jamais","nem","sem"}
MODAL_EN={"may","might","can","could","must","shall","should","will","would"}
MODAL_PT={"pode","podem","poderia","poderiam","deve","devem","deverá","deverão","deveria","deveriam","irá","irão"}


def _contains_any(text: str, terms: set[str]) -> bool:
    low=text.casefold()
    return any((t in low if "'" in t else re.search(rf"(?<!\w){re.escape(t)}(?!\w)",low)) for t in terms)


def check_fidelity(source_text: str, target_text: str, *, domain: str="auto") -> dict[str,Any]:
    deterministic=validate(source_text,target_text)
    warnings=list(deterministic.get("warnings",[]))
    issues=list(deterministic.get("issues",[]))
    src_neg=_contains_any(source_text,NEG_EN)
    tgt_neg=_contains_any(target_text,NEG_PT)
    if src_neg != tgt_neg:
        warnings.append({"rule":"TR018","type":"negation","message":"Possible negation mismatch. Model must compare source and target meaning."})
    src_modal=_contains_any(source_text,MODAL_EN)
    tgt_modal=_contains_any(target_text,MODAL_PT)
    if src_modal and not tgt_modal:
        warnings.append({"rule":"TR018","type":"modality","message":"Source contains modality; verify that strength/possibility/obligation was preserved."})

    term_checks=[]
    # Exact terminology only. Fuzzy matches are intentionally excluded from fidelity QA
    # because they can create false positives for ordinary function words.
    words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", source_text)
    con=connect()
    try:
        seen=set()
        for n in range(min(5,len(words)),0,-1):
            for i in range(0,len(words)-n+1):
                phrase=" ".join(words[i:i+n])
                rows=search_exact(con,phrase,direction="en_pt",domain=None if domain=="auto" else domain,limit=3)
                if rows and phrase.casefold() not in seen:
                    seen.add(phrase.casefold())
                    term_checks.append({"phrase":phrase,"candidates":[{
                        "source":r["source_text"],"target":r["target_text"],"domain":r["domain"],
                        "source_locale":r["source_locale"],"target_locale":r["target_locale"],
                        "source_name":r["source_name"],"status":r["status"],"priority":r["priority"],
                        "notes":r.get("notes","")
                    } for r in rows]})
                    if len(term_checks)>=12: break
            if len(term_checks)>=12: break
    finally:
        con.close()

    return {
        "ok_deterministic": not issues,
        "issues": issues,
        "warnings": warnings,
        "terminology_evidence": term_checks,
        "mandatory_model_review":[
            "Compare every proposition in source and target.",
            "Check omissions and unsupported additions.",
            "Check agent, patient, negation, modality, tense/aspect, quantities and logical relations.",
            "Check terminology against context; glossary evidence is not permission to mistranslate.",
            "Preserve ambiguity and fragmentation when source does not resolve them.",
        ]
    }
