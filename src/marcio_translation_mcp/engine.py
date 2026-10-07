from __future__ import annotations
from collections import defaultdict
from .db import connect, search_exact, search_fts, source_stats
from .domain import detect_domains
from .normalise import ngrams, normalise_text
from .rules import core_rules, load_profile, response_template
from .external import online_lookup
from .analysis import analyse_source
from .corpus import search_parallel_corpus


def _compact_hit(row: dict) -> dict:
    return {
        "source": row["source_text"], "target": row["target_text"],
        "domain": row["domain"], "subdomain": row.get("subdomain", ""),
        "source_locale": row["source_locale"], "target_locale": row["target_locale"],
        "source_name": row["source_name"], "status": row["status"],
        "priority": row["priority"], "notes": row.get("notes", ""),
        "metadata": row.get("metadata", {})
    }


def lookup_local(term: str, *, domain: str = "auto", direction: str = "en_pt", limit: int = 10) -> dict:
    con=connect()
    try:
        exact=search_exact(con,term,direction=direction,domain=None if domain=="auto" else domain,limit=limit)
        fuzzy=[] if len(exact)>=limit else search_fts(con,term,domain=None if domain=="auto" else domain,limit=limit-len(exact))
        seen=set(); hits=[]
        for row in exact+fuzzy:
            if row["id"] in seen: continue
            seen.add(row["id"]); hits.append(_compact_hit(row))
        return {"term":term,"direction":direction,"domain":domain,"hits":hits}
    finally:
        con.close()


def prepare_context(source_text: str, *, profile_name: str = "default", domain: str = "auto", auto_external: bool = True, max_results: int = 20) -> dict:
    profile=load_profile(profile_name)
    source_analysis=analyse_source(source_text)
    domains=detect_domains(source_text) if domain=="auto" else [{"domain":domain,"score":999}]
    preferred_domain=domains[0]["domain"] if domains else "general"
    con=connect(); matches=[]; seen=set()
    try:
        for phrase in ngrams(source_text,max_n=6):
            rows=search_exact(con,phrase,direction="en_pt",domain=None if preferred_domain in {"general","idioms"} else preferred_domain,limit=4)
            if not rows and len(phrase.split())>=2:
                rows=search_exact(con,phrase,direction="en_pt",domain=None,limit=3)
            for row in rows:
                if row["id"] in seen: continue
                seen.add(row["id"]); matches.append(_compact_hit(row))
                if len(matches)>=max_results: break
            if len(matches)>=max_results: break
        corpus=[]
    finally:
        con.close()
    if len(matches)<6:
        corpus_result=search_parallel_corpus(source_text,domain="auto" if preferred_domain=="general" else preferred_domain,limit=min(8,max_results-len(matches)))
        corpus=corpus_result.get("hits",[])
    external=None
    local_strength=len(matches)+len(corpus)
    if auto_external and local_strength<2:
        # Avoid sending long confidential text externally. Lookup only a short lexical candidate.
        candidates=[x for x in ngrams(source_text,max_n=3) if 1<=len(x.split())<=3 and len(x)<=100]
        if candidates:
            external=online_lookup(candidates[0],provider="auto",include_examples=True)
    return {
        "source_text":source_text,
        "profile":profile,
        "source_analysis":source_analysis,
        "detected_domains":domains,
        "preferred_domain":preferred_domain,
        "terminology_matches":matches,
        "corpus_matches":corpus,
        "external_lookup":external,
        "core_rules":core_rules(),
        "response_template":response_template(),
        "model_instruction":"Translate only after applying the core rules and the profile. Treat local terminology as evidence according to status and domain, not as permission to ignore context. Preserve malformed/fragmented source without inventing missing meaning. After drafting, call check_semantic_fidelity and validate_translation before delivering the final answer in the required 17-item format."
    }


def database_summary() -> dict:
    con=connect()
    try:
        stats=source_stats(con)
        total=sum(x["record_count"] for x in stats)
        return {"total_records":total,"sources":stats}
    finally:
        con.close()
