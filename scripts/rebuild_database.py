from __future__ import annotations
import csv, json, sqlite3, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from marcio_translation_mcp.db import connect, init_db, add_entry

SRC=ROOT/"data"/"sources"
DB=ROOT/"data"/"knowledge.sqlite3"

if DB.exists(): DB.unlink()
con=connect(DB); init_db(con)

source_counts={}

def reg_source(name, source_type, domain, source_locale, target_locale, count, notes=""):
    con.execute("INSERT OR REPLACE INTO sources(source_name,source_type,domain,source_locale,target_locale,record_count,notes) VALUES (?,?,?,?,?,?,?)",
                (name,source_type,domain,source_locale,target_locale,count,notes))

# Bible corpus
count=0
with open(SRC/"bible.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        add_entry(con,source_text=r["ENG (KJV)"],target_text=r["PT-BR"],source_locale="en-KJV",target_locale="pt-BR",domain="religion",subdomain="biblical",register="biblical",source_name="Bible KJV-ARC normalized corpus",source_type="parallel_corpus",status="CORPUS_REFERENCE",priority=55,metadata={"book_en":r["Book EN"],"book_pt":r["Livro PT"],"chapter":r["Capítulo"],"verse_pt":r["Versículo PT"],"verse_kjv":r["Versículo KJV"],"source_status":r["Status"],"source_note":r["Observação"]})
        count+=1
reg_source("Bible KJV-ARC normalized corpus","parallel_corpus","religion","en-KJV","pt-BR",count,"Historical/Biblical English. High relevance only in religious/Biblical context.")

# Hymns
count=0
with open(SRC/"hymns.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        add_entry(con,source_text=r["source_text"],target_text=r["target_text"],source_locale="en-US",target_locale="pt-BR",domain="religion",subdomain="hymns",register="religious_poetic",source_name="Hymns EN-PT parallel corpus",source_type="parallel_corpus",status="CORPUS_REFERENCE",priority=45,metadata={"hymn_number":r["number"]})
        count+=1
reg_source("Hymns EN-PT parallel corpus","parallel_corpus","religion","en-US","pt-BR",count,"Poetic/adapted hymns; contextual evidence, not mandatory terminology.")

# Religious terms
count=0
with open(SRC/"religious_terms.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        add_entry(con,source_text=r["source_text"],target_text=r["target_text"],source_locale="en-US",target_locale="pt-BR",domain="religion",subdomain="religious_terms",register="religious",source_name="Religious Terms TMX revised",source_type="translation_memory",status=r["status"],priority=68)
        count+=1
reg_source("Religious Terms TMX revised","translation_memory","religion","en-US","pt-BR",count)

# Insurance
count=0
with open(SRC/"insurance.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        add_entry(con,source_text=r["source_text"],target_text=r["target_text"],source_locale="en-US",target_locale="pt-BR",domain="insurance",subdomain=r["subdomain"],register="technical",source_name=r["source_name"],source_type="glossary",status=r["status"],priority=72,notes=r["notes"],metadata={"page":r["page"]})
        count+=1
reg_source("Insurance Dictionary EN-PT","glossary","insurance","en-US","pt-BR",count)

# Microfinance
count=0
with open(SRC/"microfinance_cgap_2007.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        notes="; ".join(x for x in [r["source_note"],r["target_note"],("PT-PT variant: "+r["pt_pt_variant"] if r["pt_pt_variant"] else "")] if x)
        add_entry(con,source_text=r["source_text"],target_text=r["target_text"],source_locale="en",target_locale="pt-BR",domain="microfinance",subdomain="finance_accounting_credit",register="technical",source_name="CGAP Microfinance Glossary 2007",source_type="glossary",status=r["status"],priority=70,notes=notes,metadata={"source_equivalents":r["source_equivalents"],"target_source":r["target_source"],"page":r["page"]})
        count+=1
reg_source("CGAP Microfinance Glossary 2007","glossary","microfinance","en","pt-BR",count,"Contains explicitly marked Lusitanian variants; PT_BR field is preferred.")

# Idioms
count=0
with open(SRC/"idioms.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        target=r["Portuguese_BR"]
        notes="; ".join(x for x in [r.get("Portuguese_Variants",""),r.get("Notes","")] if x)
        add_entry(con,source_text=r["English"],target_text=target,source_locale=r["Source_Locale_Original"] or "en-US",target_locale=r["Target_Locale"] or "pt-BR",domain="idioms",subdomain=r["Subdomain"],register=r["Register"],source_name="Idioms SDLTB revised",source_type="glossary",status=r["Status_MCP"],priority=60,notes=notes,metadata={"en_gb_compatibility":r["EN_GB_Compatibility"],"occurrences":r["Occurrences"],"source_ids":r["Source_IDs"]})
        count+=1
reg_source("Idioms SDLTB revised","glossary","idioms","en-US","pt-BR",count,"Context-sensitive expressions; verify by context.")

# Legal
count=0
with open(SRC/"legal.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        notes="; ".join(x for x in [r.get("Portuguese_Variants",""),r.get("Jurisdiction_Note",""),r.get("Notes","")] if x)
        add_entry(con,source_text=r["English"],target_text=r["Portuguese_BR"],source_locale=r["Source_Locale_Original"] or "en-US",target_locale=r["Target_Locale"] or "pt-BR",domain="legal",subdomain=r["Subdomain"],register="legal",source_name="Legal Terms SDLTB revised",source_type="glossary",status=r["Status_MCP"],priority=58,notes=notes,metadata={"en_gb_compatibility":r["EN_GB_Compatibility"],"occurrences":r["Occurrences"],"source_ids":r["Source_IDs"]})
        count+=1
reg_source("Legal Terms SDLTB revised","glossary","legal","en-US","pt-BR",count,"US/Brazil source base. Jurisdiction-sensitive; reference only until checked for EN-GB legal context.")

con.commit()
print("Database:",DB)
print("Records:",con.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
for row in con.execute("SELECT domain,COUNT(*) FROM entries GROUP BY domain ORDER BY domain"):
    print(row[0],row[1])
con.close()
