"""Exact patch validation and in-memory reconstruction.

Nothing is fuzzy-matched. Every patch is resolved against the unchanged
original. Texts are held in process memory only, keyed by revision.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .textutil import revision_of

MAX_HELD_TEXTS = 8
_store: "OrderedDict[str, str]" = OrderedDict()


def hold(text: str) -> str:
    rev = revision_of(text)
    _store[rev] = text
    _store.move_to_end(rev)
    while len(_store) > MAX_HELD_TEXTS:
        _store.popitem(last=False)
    return rev


def held(revision: str) -> str | None:
    return _store.get(revision)


def resolve_locator(original: str, text: str, prefix: str = "", suffix: str = "") -> tuple[int, int] | list[int]:
    """Return (start, end) for exactly one match, else the list of candidate starts."""
    hits: list[int] = []
    pos = original.find(text)
    while pos != -1:
        if original[max(0, pos - len(prefix)): pos] == prefix and original[pos + len(text): pos + len(text) + len(suffix)] == suffix:
            hits.append(pos)
        pos = original.find(text, pos + 1)
    if len(hits) == 1:
        return hits[0], hits[0] + len(text)
    return hits


def resolve_spans(original: str, spans: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved, issues = [], []
    for i, span in enumerate(spans):
        if span.get("locator"):
            loc = span["locator"]
            hit = resolve_locator(original, loc["text"], loc.get("prefix") or "", loc.get("suffix") or "")
            if isinstance(hit, list):
                issues.append({"code": "span_locator_ambiguous" if hit else "span_locator_not_found",
                               "span_index": i, "candidates": hit[:10]})
                continue
            start, end = hit
        else:
            start, end = span["start"], span["end"]
            if end > len(original):
                issues.append({"code": "span_out_of_bounds", "span_index": i})
                continue
        resolved.append({"start": start, "end": end, "kind": span.get("kind", "user")})
    return resolved, issues


def validate(
    original: str,
    patches: list[dict[str, Any]],
    protected: list[dict[str, Any]],
    known_rule_ids: set[str],
    max_total: int,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in patches:
        pid = p["patch_id"]
        if pid in seen:
            issues.append({"code": "duplicate_patch_id", "patch_id": pid})
            continue
        seen.add(pid)
        before = p["before"]
        if p.get("locator") is not None:
            if before == "":
                issues.append({"code": "insertion_needs_offsets", "patch_id": pid})
                continue
            loc = p["locator"]
            hit = resolve_locator(original, before, loc.get("prefix") or "", loc.get("suffix") or "")
            if isinstance(hit, list):
                issues.append({"code": "locator_ambiguous" if hit else "locator_not_found", "patch_id": pid,
                               "candidates": hit[:10]})
                continue
            start, end = hit
        else:
            start, end = p["start"], p["end"]
            if end > len(original) or start > end:
                issues.append({"code": "out_of_bounds", "patch_id": pid})
                continue
            if original[start:end] != before:
                issues.append({"code": "before_mismatch", "patch_id": pid,
                               "found": original[start:end][:80]})
                continue
        for sp in protected:
            if start <= sp["end"] and sp["start"] <= end and sp["end"] > sp["start"]:
                issues.append({"code": "protected_span", "patch_id": pid, "span": sp})
                break
        else:
            unknown = [r for r in p.get("rule_ids", []) if r not in known_rule_ids]
            if unknown:
                warnings.append({"code": "unknown_rule_id", "patch_id": pid, "rule_ids": unknown})
            if not p.get("rule_ids"):
                warnings.append({"code": "no_rule_evidence", "patch_id": pid})
            resolved.append({**{k: p[k] for k in ("patch_id", "before", "after", "action_class", "explanation") if k in p},
                             "rule_ids": p.get("rule_ids", []), "start": start, "end": end})
    ordered = sorted(resolved, key=lambda r: (r["start"], r["end"]))
    for a, b in zip(ordered, ordered[1:]):
        if b["start"] < a["end"] or (a["start"] == b["start"] and a["end"] == b["end"]) or (
            a["start"] == a["end"] == b["start"]
        ) or (b["start"] == b["end"] == a["end"] and a["start"] < a["end"]):
            issues.append({"code": "overlap", "patch_ids": [a["patch_id"], b["patch_id"]]})
    valid = not issues
    out: dict[str, Any] = {
        "valid": valid, "all_patches_checked": True, "issues": issues, "warnings": warnings,
        "resolved_patches": ordered if valid else [], "applied_patch_ids": [],
        "reconstructed_revision": None, "revised_text": None, "semantic_status": "not_assessed",
    }
    if not valid:
        return out
    text = original
    for r in sorted(ordered, key=lambda r: r["start"], reverse=True):
        text = text[: r["start"]] + r["after"] + text[r["end"]:]
    lost = [original[sp["start"]:sp["end"]] for sp in protected
            if sp["end"] > sp["start"] and original[sp["start"]:sp["end"]] not in text]
    if lost:
        out.update(valid=False, resolved_patches=[], issues=[{"code": "protected_text_changed", "spans": lost[:10]}])
        return out
    if len(text) > max_total:
        out.update(valid=False, resolved_patches=[], issues=[{"code": "revised_text_too_long", "limit": max_total}])
        return out
    out.update(applied_patch_ids=[r["patch_id"] for r in ordered], reconstructed_revision=revision_of(text), revised_text=text)
    return out
