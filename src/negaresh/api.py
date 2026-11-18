"""Typed tool inputs and the five tool functions. No MCP imports here, so the
CLI and tests call exactly what the server calls."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import SCHEMA_VERSION, __version__, mechanics, patches
from .corpus import load
from .search import search
from .textutil import revision_of

MAX_TEXT = 12000
ProfileId = Literal[
    "academic", "professional", "journalistic", "general_nonfiction", "literary",
    "conversational", "technical_instructional", "persuasive_marketing_social",
]
Category = Literal["orthography", "punctuation", "grammar", "usage", "style", "terminology", "discourse", "integrity"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Context(_Strict):
    profile_id: ProfileId | None = Field(default=None, description="Kind of text. Sets which mechanical fixes are offered as automatic patches and which checks are off.")
    formality: Literal["formal", "neutral", "informal", "unspecified"] | None = Field(default=None, description="Informational only; does not change the checks.")
    domain: str | None = Field(default=None, max_length=128, description="Informational only; does not change the checks.")
    edit_level: Literal["proofreading", "copyediting", "substantive"] | None = Field(default=None, description="Informational only; does not change the checks.")


class Locator(_Strict):
    """Find the patch's `before` text in the original by the text just before (prefix) and after (suffix) it."""
    prefix: str | None = Field(default=None, max_length=128, description="Exact text immediately before `before`.")
    suffix: str | None = Field(default=None, max_length=128, description="Exact text immediately after `before`.")


class SpanLocator(_Strict):
    text: str = Field(min_length=1, max_length=2000, description="Exact protected text as it appears in the original.")
    prefix: str | None = Field(default=None, max_length=128, description="Exact text immediately before it, if `text` occurs more than once.")
    suffix: str | None = Field(default=None, max_length=128, description="Exact text immediately after it.")


class Span(_Strict):
    """Give either start+end (code points) or locator. Not both."""
    start: int | None = Field(default=None, ge=0, description="Start offset in Unicode code points.")
    end: int | None = Field(default=None, ge=0, description="End offset in Unicode code points, exclusive.")
    locator: SpanLocator | None = None
    kind: str = Field(default="user", max_length=40)

    @model_validator(mode="after")
    def _one_form(self) -> "Span":
        offsets = self.start is not None and self.end is not None
        if offsets == (self.locator is not None) or (offsets and self.end < self.start):  # type: ignore[operator]
            raise ValueError("give exactly one of (start, end) or locator")
        return self


class Patch(_Strict):
    """Give either start+end (code points in the original) or locator. Not both."""
    patch_id: str = Field(min_length=1, max_length=40, description="Your own unique ID for this patch.")
    before: str = Field(max_length=4000, description="Exact original text to replace; empty for an insertion (then give offsets with start == end).")
    after: str = Field(max_length=4000, description="Replacement text; empty for a deletion.")
    start: int | None = Field(default=None, ge=0, description="Start offset of `before` in the original, in Unicode code points.")
    end: int | None = Field(default=None, ge=0, description="End offset, exclusive. start + len(before) in code points.")
    locator: Locator | None = None
    rule_ids: list[str] = Field(default_factory=list, max_length=16, description="Rule IDs that justify the change, e.g. ORT-003.")
    action_class: Literal["mechanical", "contextual", "style", "structure"] = "contextual"
    explanation: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def _one_form(self) -> "Patch":
        offsets = self.start is not None and self.end is not None
        if offsets == (self.locator is not None):
            raise ValueError("give exactly one of (start, end) or locator")
        if self.locator is not None and not (self.locator.prefix or self.locator.suffix):
            raise ValueError("a locator needs a prefix or a suffix")
        return self


class SearchRulesInput(_Strict):
    query: str = Field(min_length=1, max_length=512, description="Topic, word or phrase, in Persian or English.")
    context_text: str | None = Field(default=None, max_length=4096, description="The sentence in question; searched only if the query finds nothing.")
    context: Context | None = None
    category: Category | None = None
    limit: int = Field(default=5, ge=1, le=8)


class GetRuleInput(_Strict):
    rule_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")


class GetProfileInput(_Strict):
    profile_id: ProfileId | None = None


class CheckMechanicsInput(_Strict):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    context: Context | None = None
    protected_spans: list[Span] = Field(default_factory=list, max_length=256)


class ValidatePatchesInput(_Strict):
    text_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_text: str | None = Field(default=None, max_length=MAX_TEXT)
    patches: list[Patch] = Field(min_length=1, max_length=256)
    protected_spans: list[Span] = Field(default_factory=list, max_length=256)
    include_revised_text: bool = True


def envelope(status: str, data: Any = None, *, warnings: list[dict[str, Any]] | None = None,
             truncated: bool = False, error: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "package_version": __version__, "corpus_version": load().version,
        "request_id": uuid.uuid4().hex[:12], "status": status, "warnings": warnings or [],
        "truncated": truncated, "data": data, "error": error,
    }


def _error(status: str, code: str, message: str, action: str) -> dict[str, Any]:
    return envelope(status, error={"code": code, "message": message, "retryable": False, "suggested_action": action})


def _summary(rule: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "title_fa", "title_en", "category", "severity", "action", "profiles", "guidance",
            "exceptions", "evidence_class", "status")
    out = {k: rule[k] for k in keys if k in rule}
    out["citations"] = [f'{e["source"]}: {e["loc"]}' for e in rule.get("evidence", [])]
    out["conflicts"] = rule.get("conflicts", [])
    return out


def search_rules(args: SearchRulesInput) -> dict[str, Any]:
    profile = args.context.profile_id if args.context else None
    hits = search(args.query, category=args.category, profile_id=profile, limit=args.limit)
    if not hits and args.context_text:
        hits = search(args.context_text, category=args.category, profile_id=profile, limit=args.limit)
    data = {
        "backend": "in_memory_scan",
        "results": [{**_summary(h["rule"]), "match_rationale": h["match_rationale"],
                     "applies_to_profile": h["applies_to_profile"]} for h in hits],
        "returned_count": len(hits),
        "coverage_note": "قاعده‌ای که بازیابی شده لزوماً بر متن شما صدق نمی‌کند؛ شرایط و استثناها را بخوانید. "
                         "نیافتن قاعده به معنای درست بودن عبارت نیست.",
    }
    return envelope("ok" if hits else "no_match", data)


def get_rule(args: GetRuleInput) -> dict[str, Any]:
    corpus = load()
    rule = corpus.rule(args.rule_id)
    if rule is None:
        tomb = corpus.tombstones.get(args.rule_id)
        return envelope("ok", {"tombstone": tomb}) if tomb else envelope("no_match", {"rule": None})
    sources = {e["source"]: corpus.sources.get(e["source"]) for e in rule.get("evidence", [])}
    return envelope("ok", {"rule": rule, "sources": sources})


def get_profile(args: GetProfileInput) -> dict[str, Any]:
    corpus = load()
    if args.profile_id is None:
        data = {
            "variety": "Iranian standard Persian (fa-IR)",
            "profiles": [{"id": p["id"], "title_fa": p["title_fa"]} for p in corpus.profiles.values()],
            "formality_values": ["formal", "neutral", "informal", "unspecified"],
            "edit_levels": ["proofreading", "copyediting", "substantive"],
            "rule_count": len(corpus.rules),
            "categories": sorted({r["category"] for r in corpus.rules.values()}),
            "limits": {"max_text_code_points": MAX_TEXT, "search_limit": 8, "held_texts": patches.MAX_HELD_TEXTS},
            "review_status": "Reviewed by a human editor.",
            "sources": list(corpus.sources.values()),
        }
        return envelope("ok", data)
    return envelope("ok", {"profile": corpus.profiles[args.profile_id]})


def check_mechanics(args: CheckMechanicsInput) -> dict[str, Any]:
    spans, issues = patches.resolve_spans(args.text, [s.model_dump() for s in args.protected_spans])
    if issues:
        return envelope("invalid_input", {"span_issues": issues},
                        error={"code": "protected_span_unresolved", "message": "A protected span could not be resolved.",
                               "retryable": True, "suggested_action": "Fix the span locator or give exact offsets."})
    patches.hold(args.text)
    profile = args.context.profile_id if args.context else None
    data = mechanics.check(args.text, profile_id=profile, protected_spans=spans)
    return envelope("ok", data, truncated=data["findings_omitted"] > 0)


def validate_patches(args: ValidatePatchesInput) -> dict[str, Any]:
    original = args.original_text
    if original is None:
        original = patches.held(args.text_revision)
        if original is None:
            return _error("needs_context", "text_not_held", "The server no longer holds this text.",
                          "Call check_mechanics again with the exact text, then retry with the new text_revision.")
    elif revision_of(original) != args.text_revision:
        return _error("invalid_input", "revision_mismatch",
                      "original_text does not match text_revision; the text was altered when it was re-sent.",
                      "Send only text_revision (omit original_text) after check_mechanics, or re-run check_mechanics.")
    spans, span_issues = patches.resolve_spans(original, [s.model_dump() for s in args.protected_spans])
    if span_issues:
        return envelope("invalid_input", {"span_issues": span_issues},
                        error={"code": "protected_span_unresolved", "message": "A protected span could not be resolved.",
                               "retryable": True, "suggested_action": "Fix the span locator or give exact offsets."})
    spans = [*spans, *mechanics.detect_protected(original)]
    result = patches.validate(original, [p.model_dump() for p in args.patches], spans, set(load().rules), MAX_TEXT * 2)
    if not args.include_revised_text:
        result["revised_text"] = None
    return envelope("ok", result)


TOOLS: dict[str, tuple[type[BaseModel], Any, str]] = {
    "search_rules": (SearchRulesInput, search_rules,
                     "Search the Persian writing rule set (Iranian standard Persian) by topic, word or phrase, in Persian or English. "
                     "Use before changing spelling, spacing, grammar or usage you are not sure about. Returns rules with conditions, "
                     "exceptions and sources. A returned rule may not apply; no match does not mean the text is correct."),
    "get_rule": (GetRuleInput, get_rule,
                 "Get one full rule by ID (for example ORT-002), with all examples, exceptions and source details. "
                 "Use after search_rules or when a finding cites a rule ID."),
    "get_profile": (GetProfileInput, get_profile,
                    "Without arguments: list writing profiles, corpus scope, limits and review status. With profile_id: "
                    "conventions and preservation policy for that kind of text. Call once at the start of an editing task."),
    "check_mechanics": (CheckMechanicsInput, check_mechanics,
                        "Run deterministic checks (M01-M16) on Persian text: Arabic letters, presentation forms, digits, punctuation "
                        "spacing and Latin marks, spaces, half-space (ZWNJ) misuse, half-space after «می/نمی» before common verb stems "
                        "and before «ها/تر/ترین», quotes, kashida, invisible characters, mixed ezafe marks, brackets, preferred spellings "
                        "(Academy and Samiee lists), listed expressions to replace (M15) and sentence-shape patterns typical of translated or machine Persian (M16, flags pointing to a rebuild rule). Returns findings with exact code-point offsets, "
                        "candidate patches with rule IDs, auto_patch_set (low-risk, non-overlapping fixes, ready for validate_patches) "
                        "and text_revision. Flags need judgement. Check complete_scan. It does not judge grammar, meaning or style, "
                        "and never changes the text."),
    "validate_patches": (ValidatePatchesInput, validate_patches,
                         "Validate proposed edits against the exact original and return the rebuilt text. Pass text_revision from "
                         "check_mechanics (do not re-send the original). Each patch gives 'before', 'after' and either offsets or a "
                         "locator with adjacent prefix/suffix. Rejects stale, ambiguous, overlapping edits and edits that touch or "
                         "change protected spans (URLs, e-mail, code, given spans). Present the "
                         "returned revised_text as it is; do not retype it. Meaning is not assessed."),
}


def call(name: str, arguments: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Returns (envelope, is_error)."""
    if name not in TOOLS:
        return _error("invalid_input", "unknown_tool", f"Unknown tool: {name}", "Use one of: " + ", ".join(TOOLS)), True
    model, fn, _ = TOOLS[name]
    try:
        args = model.model_validate(arguments or {})
    except ValidationError as exc:
        details = [{"field": ".".join(str(p) for p in e["loc"]), "problem": e["type"]} for e in exc.errors()[:12]]
        env = _error("invalid_input", "argument_validation", "Arguments rejected. Unknown or mistyped fields are not ignored.",
                     "Correct the listed fields and call again.")
        env["data"] = {"fields": details}
        return env, True
    try:
        env = fn(args)
    except Exception:  # content-free failure; no text or traceback reaches the model
        return _error("resource_unavailable", "internal_error", "Internal error.", "Retry once; if it repeats, report the request_id."), True
    return env, env["error"] is not None and env["status"] not in ("needs_context",)
