from __future__ import annotations
from .rules import load_profile

KNOWN_PROFILES=("default","oneforma","literal_asr")

def get_profile(name: str="default") -> dict:
    p=load_profile(name)
    return {"requested":name,"resolved":p,"known_profiles":list(KNOWN_PROFILES)}
