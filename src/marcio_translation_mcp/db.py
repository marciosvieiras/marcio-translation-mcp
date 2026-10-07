from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any
from .normalise import normalise_text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "knowledge.sqlite3"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  source_text TEXT NOT NULL,
  target_text TEXT NOT NULL,
  source_norm TEXT NOT NULL,
  target_norm TEXT NOT NULL,
  source_locale TEXT NOT NULL,
  target_locale TEXT NOT NULL,
  domain TEXT NOT NULL,
  subdomain TEXT NOT NULL DEFAULT '',
  register TEXT NOT NULL DEFAULT '',
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'REFERENCE',
  priority INTEGER NOT NULL DEFAULT 50,
  notes TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_entries_source_norm ON entries(source_norm);
CREATE INDEX IF NOT EXISTS idx_entries_target_norm ON entries(target_norm);
CREATE INDEX IF NOT EXISTS idx_entries_domain ON entries(domain);
CREATE INDEX IF NOT EXISTS idx_entries_source_name ON entries(source_name);
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  entry_id UNINDEXED,
  source_text,
  target_text,
  domain,
  subdomain,
  tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS sources (
  source_name TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  domain TEXT NOT NULL,
  source_locale TEXT NOT NULL,
  target_locale TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);
"""


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else DEFAULT_DB
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def add_entry(con: sqlite3.Connection, *, source_text: str, target_text: str,
              source_locale: str, target_locale: str, domain: str,
              subdomain: str = "", register: str = "", source_name: str,
              source_type: str, status: str = "REFERENCE", priority: int = 50,
              notes: str = "", metadata: dict[str, Any] | None = None) -> int:
    cur = con.execute(
        """INSERT INTO entries
        (source_text,target_text,source_norm,target_norm,source_locale,target_locale,domain,subdomain,register,source_name,source_type,status,priority,notes,metadata_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_text,target_text,normalise_text(source_text),normalise_text(target_text),
         source_locale,target_locale,domain,subdomain,register,source_name,source_type,
         status,priority,notes,json.dumps(metadata or {},ensure_ascii=False))
    )
    entry_id = int(cur.lastrowid)
    con.execute("INSERT INTO entries_fts(entry_id,source_text,target_text,domain,subdomain) VALUES (?,?,?,?,?)",
                (entry_id,source_text,target_text,domain,subdomain))
    return entry_id


def _rowdict(row: sqlite3.Row) -> dict[str, Any]:
    d=dict(row)
    try: d["metadata"] = json.loads(d.pop("metadata_json"))
    except Exception: d["metadata"] = {}
    return d


def search_exact(con: sqlite3.Connection, term: str, *, direction: str = "en_pt", domain: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    norm=normalise_text(term)
    col = "source_norm" if direction == "en_pt" else "target_norm"
    sql=f"SELECT * FROM entries WHERE {col}=?"
    args=[norm]
    if domain and domain != "auto":
        sql += " AND domain=?"; args.append(domain)
    sql += " ORDER BY priority DESC, id LIMIT ?"; args.append(limit)
    return [_rowdict(r) for r in con.execute(sql,args).fetchall()]


def _fts_query(text: str) -> str:
    # Quoted tokens make punctuation-heavy user input safe for MATCH.
    parts=[p.replace('"','') for p in text.split() if p.strip()]
    return " OR ".join(f'"{p}"' for p in parts[:12]) or '""'


def search_fts(con: sqlite3.Connection, text: str, *, domain: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    q=_fts_query(text)
    sql="""SELECT e.*, bm25(entries_fts, 5.0, 2.0, 0.5, 0.5) AS fts_score
           FROM entries_fts JOIN entries e ON e.id=entries_fts.entry_id
           WHERE entries_fts MATCH ?"""
    args=[q]
    if domain and domain != "auto":
        sql += " AND e.domain=?"; args.append(domain)
    sql += " ORDER BY fts_score ASC, e.priority DESC LIMIT ?"; args.append(limit)
    return [_rowdict(r) for r in con.execute(sql,args).fetchall()]


def source_stats(con: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in con.execute("SELECT * FROM sources ORDER BY domain, source_name").fetchall()]
