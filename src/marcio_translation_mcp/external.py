from __future__ import annotations
import os
from typing import Any
from urllib.parse import quote
import httpx

UA="MarcioTranslationMCP/0.1 (translation-reference-tool)"
TIMEOUT=12.0


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent":UA})


def microsoft_dictionary(term: str, *, include_examples: bool = True, source: str = "en", target: str = "pt") -> dict[str,Any]:
    key=os.getenv("MICROSOFT_TRANSLATOR_KEY","").strip()
    if not key:
        return {"provider":"microsoft_translator_dictionary","configured":False,"message":"MICROSOFT_TRANSLATOR_KEY não configurada."}
    region=os.getenv("MICROSOFT_TRANSLATOR_REGION","").strip()
    endpoint=os.getenv("MICROSOFT_TRANSLATOR_ENDPOINT","https://api.cognitive.microsofttranslator.com").rstrip("/")
    headers={"Ocp-Apim-Subscription-Key":key,"Content-Type":"application/json"}
    if region: headers["Ocp-Apim-Subscription-Region"]=region
    with _client() as c:
        r=c.post(f"{endpoint}/dictionary/lookup",params={"api-version":"3.0","from":source,"to":target},headers=headers,json=[{"text":term}])
        r.raise_for_status(); data=r.json()
        out={"provider":"microsoft_translator_dictionary","configured":True,"lookup":data}
        if include_examples and data and data[0].get("translations"):
            best=data[0]["translations"][0]
            back=best.get("backTranslations") or []
            source_norm=(back[0].get("normalizedText") if back else data[0].get("normalizedSource")) or term
            target_norm=best.get("normalizedTarget") or best.get("displayTarget")
            if target_norm:
                ex=c.post(f"{endpoint}/dictionary/examples",params={"api-version":"3.0","from":source,"to":target},headers=headers,json=[{"text":source_norm,"translation":target_norm}])
                if ex.is_success: out["examples"]=ex.json()
        return out


def wiktionary_definition(term: str) -> dict[str,Any]:
    url=f"https://en.wiktionary.org/api/rest_v1/page/definition/{quote(term, safe='')}"
    try:
        with _client() as c:
            r=c.get(url,headers={"Accept":"application/json"})
            r.raise_for_status()
            return {"provider":"wiktionary","configured":True,"data":r.json(),"url":url}
    except Exception as e:
        return {"provider":"wiktionary","configured":True,"error":str(e),"url":url}


def _skpublish_catalog(provider: str) -> dict[str,Any]:
    if provider=="cambridge":
        key=os.getenv("CAMBRIDGE_API_KEY","").strip(); base=os.getenv("CAMBRIDGE_API_BASE","https://dictionary.cambridge.org/api/v1").rstrip("/")
    else:
        key=os.getenv("COLLINS_API_KEY","").strip(); base=os.getenv("COLLINS_API_BASE","https://api.collinsdictionary.com/api/v1").rstrip("/")
    if not key: return {"provider":provider,"configured":False,"message":f"Chave de API de {provider} não configurada."}
    with _client() as c:
        r=c.get(f"{base}/dictionaries",headers={"accessKey":key,"Accept":"application/json"})
        r.raise_for_status(); return {"provider":provider,"configured":True,"data":r.json()}


def list_dictionary_catalog(provider: str) -> dict[str,Any]:
    p=provider.casefold()
    if p in {"cambridge","collins"}: return _skpublish_catalog(p)
    return {"provider":provider,"error":"Catálogo disponível apenas para Cambridge ou Collins."}


def skpublish_lookup(term: str, provider: str) -> dict[str,Any]:
    p=provider.casefold()
    if p=="cambridge":
        key=os.getenv("CAMBRIDGE_API_KEY","").strip(); base=os.getenv("CAMBRIDGE_API_BASE","https://dictionary.cambridge.org/api/v1").rstrip("/"); code=os.getenv("CAMBRIDGE_DICTIONARY_CODE","").strip()
    elif p=="collins":
        key=os.getenv("COLLINS_API_KEY","").strip(); base=os.getenv("COLLINS_API_BASE","https://api.collinsdictionary.com/api/v1").rstrip("/"); code=os.getenv("COLLINS_DICTIONARY_CODE","").strip()
    else:
        return {"provider":provider,"error":"Provider inválido."}
    if not key: return {"provider":p,"configured":False,"message":f"Chave de API de {p} não configurada."}
    if not code:
        return {"provider":p,"configured":True,"needs_dictionary_code":True,"message":"Defina o código do dicionário no .env. Use list_online_dictionary_catalog para descobrir os códigos disponíveis."}
    with _client() as c:
        r=c.get(f"{base}/dictionaries/{quote(code,safe='')}/search/first",params={"q":term,"format":"html"},headers={"accessKey":key,"Accept":"application/json"})
        r.raise_for_status(); return {"provider":p,"configured":True,"dictionary_code":code,"data":r.json()}


def online_lookup(term: str, provider: str = "auto", include_examples: bool = True) -> dict[str,Any]:
    p=provider.casefold()
    if p=="microsoft": return microsoft_dictionary(term,include_examples=include_examples)
    if p in {"cambridge","collins"}: return skpublish_lookup(term,p)
    if p=="wiktionary": return wiktionary_definition(term)
    # Auto: use configured bilingual services first, then free lexical fallback.
    results=[]
    for name,fn in [
        ("microsoft",lambda: microsoft_dictionary(term,include_examples=include_examples)),
        ("cambridge",lambda: skpublish_lookup(term,"cambridge")),
        ("collins",lambda: skpublish_lookup(term,"collins")),
    ]:
        try:
            res=fn(); results.append(res)
            if res.get("configured") and not res.get("error") and not res.get("needs_dictionary_code"):
                return {"selected":name,"result":res,"attempts":results}
        except Exception as e:
            results.append({"provider":name,"error":str(e)})
    wik=wiktionary_definition(term); results.append(wik)
    return {"selected":"wiktionary","result":wik,"attempts":results}


def reference_urls(term: str) -> dict[str,str]:
    q=quote(term.strip())
    return {
        "Cambridge English-Portuguese": f"https://dictionary.cambridge.org/dictionary/english-portuguese/{q}",
        "Cambridge English": f"https://dictionary.cambridge.org/dictionary/english/{q}",
        "Collins English-Portuguese": f"https://www.collinsdictionary.com/dictionary/english-portuguese/{q}",
        "Wiktionary": f"https://en.wiktionary.org/wiki/{q}",
        "Oxford Learner/Dictionary API info": "https://developer.oxforddictionaries.com/"
    }
