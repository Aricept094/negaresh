"""In-memory rule search. No index file, no stemmer: authored aliases plus
closed-class affix variants."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from math import log1p
from typing import Any

from .corpus import Corpus, load
from .textutil import fold, search_tokens, stem_variants

_FIELD_WEIGHTS = (("aliases", 5.0), ("title_fa", 4.0), ("title_en", 3.0), ("guidance", 1.5), ("examples_text", 1.0))
_STOP = {"و", "در", "به", "از", "که", "را", "با", "این", "ان", "است", "برای", "یا", "تا", "the", "a", "of", "in", "to", "and", "or", "is"}


def _examples_text(rule: dict[str, Any]) -> str:
    parts: list[str] = []
    for ex in rule.get("examples", []):
        parts.extend(str(v) for k, v in ex.items() if k in ("right", "wrong", "ok", "note"))
    parts.extend(rule.get("exceptions", []))
    return " ".join(parts)


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    return _build_index(load())


def _build_index(corpus: Corpus) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    frequencies: Counter[str] = Counter()
    index: dict[str, dict[str, Any]] = {}
    for rid, rule in corpus.rules.items():
        fields: dict[str, set[str]] = {}
        for name, _ in _FIELD_WEIGHTS:
            if name == "examples_text":
                raw = _examples_text(rule)
            elif name == "aliases":
                raw = " ".join(rule.get("aliases", []))
            else:
                raw = str(rule.get(name, ""))
            toks: set[str] = set()
            for tok in search_tokens(raw):
                toks |= stem_variants(tok)
            fields[name] = toks
        frequencies.update(set().union(*fields.values()))
        index[rid] = {
            "fields": fields,
            "alias_phrases": [fold(a) for a in rule.get("aliases", [])],
            "title": fold(rule.get("title_fa", "")),
        }
    weights = {t: log1p((len(index) - n + 0.5) / (n + 0.5)) for t, n in frequencies.items()}
    return index, weights


def _applies(rule: dict[str, Any], profile_id: str | None) -> bool:
    profiles = rule.get("profiles", ["all"])
    return profile_id is None or "all" in profiles or profile_id in profiles


def _alias_in_query(alias: str, q_fold: str) -> bool:
    """A long alias may sit anywhere in the query; a short one must be a whole word or phrase."""
    if len(alias) >= 5:
        return alias in q_fold
    return f" {alias} " in f" {q_fold} "


def search(
    query: str,
    *,
    category: str | None = None,
    profile_id: str | None = None,
    limit: int = 5,
    corpus: Corpus | None = None,
) -> list[dict[str, Any]]:
    corpus = corpus or load()
    index, weights = _index() if corpus is load() else _build_index(corpus)
    q_fold = fold(query).strip()
    q_tokens = [stem_variants(t) for t in dict.fromkeys(search_tokens(query)) if t not in _STOP]
    if not q_tokens and not q_fold:
        return []
    scored: list[tuple[float, str, str]] = []
    for rid, entry in index.items():
        rule = corpus.rules[rid]
        if category and rule["category"] != category:
            continue
        score = 0.0
        rationale = "lexical"
        if q_fold and any(q_fold == a for a in entry["alias_phrases"]):
            score += 20.0
            rationale = "alias"
        elif q_fold and len(q_fold) >= 3 and (
            any(q_fold in a or _alias_in_query(a, q_fold) for a in entry["alias_phrases"] if len(a) >= 3)
            or q_fold in entry["title"]
        ):
            score += 8.0
            rationale = "normalized"
        for variants in q_tokens:
            best = 0.0
            for name, weight in _FIELD_WEIGHTS:
                for term in variants & entry["fields"][name]:
                    best = max(best, weight * weights[term])
            score += best
        if score <= 0:
            continue
        if not _applies(rule, profile_id):
            score *= 0.5
        scored.append((score, rid, rationale))
    scored.sort(key=lambda s: (s[2] != "alias", -s[0], s[1]))
    floor = max(2.0, scored[0][0] * 0.25) if scored else 0
    return [
        {"rule": corpus.rules[rid], "match_rationale": rationale, "applies_to_profile": _applies(corpus.rules[rid], profile_id)}
        for score, rid, rationale in scored[:limit]
        if score >= floor
    ]
