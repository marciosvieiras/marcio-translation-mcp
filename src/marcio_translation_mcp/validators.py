from __future__ import annotations
import re
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN=json.loads((ROOT/"config"/"pt_pt_forbidden_terms.json").read_text(encoding="utf-8"))

DASH_CHARS="-–—"
QUOTE_CHARS='"“”‘’\''


def _count_chars(text: str, chars: str) -> dict[str,int]:
    return {c:text.count(c) for c in chars if text.count(c)}


def _tokens_to_preserve(text: str) -> dict[str,list[str]]:
    return {
        "numbers": re.findall(r"(?<!\w)[+-]?(?:\d+[.,]?\d*|[.,]\d+)%?", text),
        "urls": re.findall(r"https?://\S+|www\.\S+", text, flags=re.I),
        "placeholders": re.findall(r"\[[^\]]+\]|\{[^{}]+\}|<[^<>]+>", text),
        "codes": re.findall(r"\b[A-Z]{2,}(?:[-_/][A-Z0-9]+)*\b", text),
    }


def validate(source: str, target: str, *, informal: bool | None = None) -> dict:
    issues=[]; warnings=[]
    src_pres=_tokens_to_preserve(source); tgt_pres=_tokens_to_preserve(target)
    for kind,vals in src_pres.items():
        for v in vals:
            if v not in tgt_pres.get(kind,[]):
                issues.append({"rule":"TR014","type":kind,"message":f"Elemento protegido possivelmente ausente no alvo: {v}"})
    for ch in "*":
        if source.count(ch)!=target.count(ch):
            issues.append({"rule":"TR012","type":"asterisk","message":f"Contagem de asteriscos difere: fonte={source.count(ch)}, alvo={target.count(ch)}"})
    src_dash=sum(source.count(c) for c in DASH_CHARS); tgt_dash=sum(target.count(c) for c in DASH_CHARS)
    if tgt_dash>src_dash:
        warnings.append({"rule":"TR010","type":"dash","message":"O alvo introduziu hífen/travessão adicional. Verificar se há função gramatical ou lexical necessária."})
    # Straight/curly quotes are normalised as a family for QA.
    src_quotes=sum(source.count(c) for c in QUOTE_CHARS); tgt_quotes=sum(target.count(c) for c in QUOTE_CHARS)
    if src_quotes!=tgt_quotes:
        warnings.append({"rule":"TR011","type":"quotes","message":f"Quantidade de aspas/apóstrofos difere: fonte={src_quotes}, alvo={tgt_quotes}. Verificar contexto."})
    low=target.casefold()
    for term,replacement in FORBIDDEN.items():
        if re.search(rf"\b{re.escape(term.casefold())}\b",low):
            warnings.append({"rule":"TR006","type":"pt_pt","message":f"Possível termo PT-PT: '{term}'. Preferência PT-BR: {replacement}."})
    if informal is True and source and source[0].islower() and target and target[0].isupper():
        warnings.append({"rule":"TR013","type":"capitalisation","message":"Fonte informal inicia em minúscula e alvo inicia em maiúscula."})
    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "source_checks": src_pres,
        "target_checks": tgt_pres,
        "note": "Validações determinísticas não substituem revisão semântica pelo modelo."
    }
