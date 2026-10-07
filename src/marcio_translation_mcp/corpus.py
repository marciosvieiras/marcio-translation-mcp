from __future__ import annotations
from typing import Any
from .db import connect, _rowdict, _fts_query

CORPUS_TYPES=("parallel_corpus","translation_memory")

def search_parallel_corpus(text: str, *, domain: str="auto", limit: int=10) -> dict[str,Any]:
    con=connect()
    try:
        q=_fts_query(text)
        placeholders=",".join("?" for _ in CORPUS_TYPES)
        sql=f"""SELECT e.*, bm25(entries_fts, 5.0, 2.0, 0.5, 0.5) AS fts_score
                FROM entries_fts JOIN entries e ON e.id=entries_fts.entry_id
                WHERE entries_fts MATCH ? AND e.source_type IN ({placeholders})"""
        args=[q,*CORPUS_TYPES]
        if domain and domain!="auto":
            sql += " AND e.domain=?"; args.append(domain)
        sql += " ORDER BY fts_score ASC, e.priority DESC LIMIT ?"; args.append(limit)
        rows=[_rowdict(r) for r in con.execute(sql,args).fetchall()]
        return {"query":text,"domain":domain,"hits":[{
            "source":r["source_text"],"target":r["target_text"],"domain":r["domain"],
            "subdomain":r.get("subdomain",""),"source_name":r["source_name"],
            "source_locale":r["source_locale"],"target_locale":r["target_locale"],
            "status":r["status"],"priority":r["priority"],"notes":r.get("notes","")
        } for r in rows]}
    finally:
        con.close()
