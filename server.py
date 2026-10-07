from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))

from dotenv import load_dotenv
load_dotenv(ROOT/".env")

from mcp.server.mcpserver import MCPServer
from marcio_translation_mcp.engine import prepare_context, lookup_local, database_summary
from marcio_translation_mcp.rules import core_rules, response_template, load_profile
from marcio_translation_mcp.validators import validate
from marcio_translation_mcp.external import online_lookup, list_dictionary_catalog, reference_urls
from marcio_translation_mcp.analysis import analyse_source
from marcio_translation_mcp.fidelity import check_fidelity
from marcio_translation_mcp.corpus import search_parallel_corpus as corpus_search
from marcio_translation_mcp.project import get_profile

MAX_SEGMENT_CHARS = int(os.getenv("MCP_MAX_SEGMENT_CHARS", "8000"))
MAX_TERM_CHARS = int(os.getenv("MCP_MAX_TERM_CHARS", "240"))

def _guard_segment(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("source_text deve conter texto.")
    if len(text) > MAX_SEGMENT_CHARS:
        raise ValueError(f"Segmento muito longo para este MCP: {len(text)} caracteres; limite {MAX_SEGMENT_CHARS}.")
    return text

def _guard_term(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("term deve conter texto.")
    if len(text) > MAX_TERM_CHARS:
        raise ValueError(f"Consulta lexical muito longa: limite {MAX_TERM_CHARS} caracteres.")
    return text

SERVER_INSTRUCTIONS = (
    "EN-GB→PT-BR translation assistant for Marcio. For every new source segment, first call "
    "prepare_translation_context. Apply all returned rules and project profile. Use local terminology/corpus "
    "before external dictionaries. Do not invent missing meaning. After drafting, call check_semantic_fidelity "
    "and validate_translation. Present the exact 17-item format unless the user explicitly requests another output mode."
)

mcp=MCPServer(
    "Marcio EN-GB to PT-BR Translation MCP",
    instructions=SERVER_INSTRUCTIONS,
    version="1.1.0",
)

@mcp.tool()
def prepare_translation_context(source_text: str, profile: str = "default", domain: str = "auto", auto_external: bool = True, max_results: int = 20) -> dict:
    """MANDATORY FIRST STEP for each EN-GB -> PT-BR source segment. Analyse the source, load Marcio's rules/profile, detect domain, retrieve relevant local terminology/corpora, and optionally consult an external dictionary only when local evidence is weak. Do not translate before using this context when this MCP is active."""
    _guard_segment(source_text)
    return prepare_context(source_text,profile_name=profile,domain=domain,auto_external=auto_external,max_results=max_results)

@mcp.tool()
def analyse_en_gb_source(source_text: str) -> dict:
    """Analyse a source segment before translation. Returns conservative EN-GB/US signals, question punctuation, fragmentation, protected tokens and mandatory linguistic checks. Heuristics are evidence only; the model must make the final linguistic judgement."""
    _guard_segment(source_text)
    return analyse_source(source_text)

@mcp.tool()
def lookup_terminology(term: str, domain: str = "auto", direction: str = "en_pt", limit: int = 10) -> dict:
    """Search the local bilingual knowledge base for terminology and idiomatic evidence. direction='en_pt' is the default. Use domain context when known. Results are evidence, not permission to ignore source meaning."""
    _guard_term(term)
    return lookup_local(term,domain=domain,direction=direction,limit=limit)

@mcp.tool()
def search_parallel_corpus(text: str, domain: str = "auto", limit: int = 10) -> dict:
    """Search only parallel corpora and translation-memory sources such as the Bible, hymns and approved/revised bilingual memories. Use for contextual examples, not as mandatory terminology."""
    _guard_segment(text)
    return corpus_search(text,domain=domain,limit=limit)

@mcp.tool()
def check_semantic_fidelity(source_text: str, target_text: str, domain: str = "auto") -> dict:
    """MANDATORY semantic QA after drafting. Detect deterministic omissions/protected-token problems, negation/modality risks and local terminology evidence, then return a checklist the model must use to compare source and target proposition by proposition."""
    _guard_segment(source_text)
    _guard_segment(target_text)
    return check_fidelity(source_text,target_text,domain=domain)

@mcp.tool()
def validate_translation(source_text: str, target_text: str, informal: bool = False) -> dict:
    """MANDATORY FINAL deterministic QA after drafting. Checks protected tokens, numbers, URLs, placeholders, asterisks, dashes, quotation marks, capitalisation and possible PT-PT terms. Semantic fidelity must also be checked with check_semantic_fidelity."""
    _guard_segment(source_text)
    _guard_segment(target_text)
    return validate(source_text,target_text,informal=informal)

@mcp.tool()
def get_translation_rules(profile: str = "default") -> dict:
    """Return the complete EN-GB -> PT-BR core rules, selected project profile and exact 17-item response template."""
    return {"core":core_rules(),"profile":load_profile(profile),"response_template":response_template()}

@mcp.tool()
def get_project_profile(profile: str = "default") -> dict:
    """Return one project profile. Known profiles include default, oneforma and literal_asr. Project rules override generic preferences only where explicitly configured."""
    return get_profile(profile)

@mcp.tool()
def lookup_online_dictionary(term: str, provider: str = "auto", include_examples: bool = True) -> dict:
    """Consult an external lexical reference only when local sources are insufficient or conflicting. provider: auto, microsoft, cambridge, collins or wiktionary. Licensed providers are called only when their API keys are configured. Do not send confidential full client sentences; use a short lexical term."""
    _guard_term(term)
    return online_lookup(term,provider=provider,include_examples=include_examples)

@mcp.tool()
def list_online_dictionary_catalog(provider: str) -> dict:
    """List dictionary products/codes available to a configured Cambridge or Collins API key. Intended for setup, not for every translation."""
    return list_dictionary_catalog(provider)

@mcp.tool()
def dictionary_reference_urls(term: str) -> dict:
    """Return official reference URLs for manual lexical verification. This tool does not scrape dictionary websites."""
    _guard_term(term)
    return reference_urls(term)

@mcp.tool()
def get_knowledge_base_summary() -> dict:
    """Return record counts and source metadata for every glossary/corpus loaded in the MCP database."""
    return database_summary()

@mcp.resource("translation-rules://core")
def rules_resource() -> str:
    import json
    return json.dumps(core_rules(),ensure_ascii=False,indent=2)

@mcp.resource("translation-template://full-analysis-17")
def template_resource() -> str:
    import json
    return json.dumps(response_template(),ensure_ascii=False,indent=2)

@mcp.prompt()
def translate_en_gb_to_pt_br(source_text: str, profile: str = "default") -> str:
    """Prompt for Marcio's required one-segment EN-GB -> PT-BR workflow."""
    return (
        "Translate one source segment using Marcio's EN-GB to PT-BR workflow. "
        "First call prepare_translation_context. Apply every relevant returned rule and terminology item. "
        "Draft without inventing omitted meaning. Then call check_semantic_fidelity and validate_translation, fix any supported issues, "
        "and present the exact 17-item template. Item 17 contains only the final PT-BR translation. "
        f"Profile: {profile}. Source text: {source_text}"
    )

if __name__ == "__main__":
    host=os.getenv("MCP_HOST","127.0.0.1")
    port=int(os.getenv("MCP_PORT","8000"))
    path=os.getenv("MCP_PATH","/mcp")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path=path,
        stateless_http=True,
        json_response=True,
    )
