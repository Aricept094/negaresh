"""Read-only access to the packaged corpus bundle."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any


@dataclass(frozen=True)
class Corpus:
    version: str
    rules: dict[str, dict[str, Any]]
    profiles: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    lexicon: dict[str, Any]
    tombstones: dict[str, dict[str, Any]]

    def rule(self, rule_id: str) -> dict[str, Any] | None:
        return self.rules.get(rule_id)


@lru_cache(maxsize=1)
def load() -> Corpus:
    raw = resources.files("negaresh").joinpath("data/corpus.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    return Corpus(
        version=data["corpus_version"],
        rules={r["id"]: r for r in data["rules"]},
        profiles={p["id"]: p for p in data["profiles"]},
        sources={s["id"]: s for s in data["sources"]},
        lexicon=data["lexicon"],
        tombstones={t["id"]: t for t in data.get("tombstones", [])},
    )
