from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def core_rules() -> dict:
    return load_json(ROOT / "config" / "rules" / "core_en_gb_pt_br.json")


def response_template() -> dict:
    return load_json(ROOT / "config" / "response_template_17.json")


def load_profile(name: str = "default") -> dict:
    safe="".join(c for c in name if c.isalnum() or c in "_-" ) or "default"
    path=ROOT / "config" / "profiles" / f"{safe}.json"
    if not path.exists(): path=ROOT / "config" / "profiles" / "default.json"
    profile=load_json(path)
    if profile.get("extends"):
        parent=load_profile(profile["extends"])
        parent.update(profile); profile=parent
    return profile


def compact_rule_text() -> list[str]:
    return [f'{r["id"]}: {r["rule"]}' for r in core_rules()["rules"]]
