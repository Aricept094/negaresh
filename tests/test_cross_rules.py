"""Cross-rule consistency: the mechanical checker must not contradict the rule set on correct examples.

Every correct example in the rule set (each "right" alternative, split on " / ", and each "ok" text)
is run through check_mechanics, without a profile and under each of the eight profiles, the way the MCP
tool runs it. A finding on such a text is classified against the rule the example belongs to:

  SELF   the finding cites that same rule: the rule's own correct text is flagged by its own check
  CROSS  the finding cites another rule: one rule's correct text is flagged on another rule's authority
  PATCH  the finding's action is "patch": an automatic change to text the rules call correct

Checks:
  (a) no PATCH finding on any correct text
  (b) no SELF finding on any correct text
  (c) every CROSS finding is in ACCEPTED_CROSS, and every ACCEPTED_CROSS entry still fires
  (d) every advisory rule has an "ok" example (known gap, xfail)
  (e) no correct text is identical to another rule's wrong text

Cases that fail today are marked xfail with the reason; no assertion is weakened. The rules are read from
the packaged bundle (negaresh.corpus.load), the same data the checker serves. After editing corpus/rules,
run `python tools/build.py` first, or these checks see the previous build.

To judge a new finding: fix the rule or the checker if it is a real contradiction (add it to KNOWN_CROSS
or KNOWN_SELF with a reason until it is fixed); otherwise add the tuple to ACCEPTED_CROSS with the reason.
"""

from __future__ import annotations

import functools
from collections import defaultdict

import pytest

from negaresh import api
from negaresh.corpus import load

SEP = " / "
NO_RULE = "(no rule cites this check)"
CONTEXTS = [None, *sorted(load().profiles)]

# Cross findings judged acceptable: (rule of the example, cited rule, check id, example text).
ACCEPTED_CROSS = {
    # INT-006 is a change-report line whose before-form «می روم» is quoted on purpose. M08 flags only that
    # quoted form, as a flag: M08 is in no profile's patch set, so nothing is changed. The text flagged is
    # the wrong form the report is about, not text the rules call correct. The same finding cites ORT-002,
    # ORT-003 and ORT-004, since all three are M08 rules.
    ("INT-006", "ORT-002", "M08", "«می روم» ← «می‌روم» (ORT-002)"),
    ("INT-006", "ORT-003", "M08", "«می روم» ← «می‌روم» (ORT-002)"),
    ("INT-006", "ORT-004", "M08", "«می روم» ← «می‌روم» (ORT-002)"),
}

# Real contradictions between a correct text and a cited rule (xfail until fixed): key -> reason.
KNOWN_CROSS: dict[tuple[str, str, str, str], str] = {}

# Correct texts that their own rule's check flags (SELF), xfail until fixed: (rule, text) -> reason.
KNOWN_SELF: dict[tuple[str, str], str] = {
    ("ORT-042", "آزوقه، غورباغه، قوتی"): (
        "SELF: the ok example of ORT-042 is flagged by its own check M14 (flag only, never a patch). The rule's "
        "guidance says M14 shows these Samiee forms and does not correct them, so the flag is intended, but a "
        "text the rule accepts still triggers its own check. Needed: an M14 exemption for Samiee-listed forms, "
        "or a different example."
    ),
}

# Correct texts with a PATCH finding, xfail until fixed: (rule, text) -> reason. None currently.
KNOWN_PATCH: dict[tuple[str, str], str] = {}

# Advisory rules with no "ok" example at the time of writing (documented gap for check d).
ADVISORY_WITHOUT_OK = (
    "DSC-001", "DSC-002", "DSC-003", "GRM-024", "GRM-026", "GRM-035", "GRM-039", "ORT-043", "PUN-002",
    "PUN-004", "PUN-005", "PUN-006", "PUN-008", "PUN-013", "PUN-014", "PUN-015", "PUN-018", "STY-002",
    "STY-005", "STY-009", "STY-010", "STY-018", "STY-019", "TRM-006", "USG-002", "USG-012", "USG-016",
    "USG-019", "USG-021",
)


def _correct_texts() -> list[tuple[str, str, str]]:
    """(rule id, text, test id) for every right alternative and every ok text, in rule order."""
    out = []
    for rule in sorted(load().rules.values(), key=lambda r: r["id"]):
        for i, ex in enumerate(rule["examples"]):
            for kind in ("ok", "right"):
                if kind in ex:
                    for j, piece in enumerate(ex[kind].split(SEP)):
                        out.append((rule["id"], piece, f"{rule['id']}-{kind}{i}-{j}"))
    return out


_CORRECT = _correct_texts()


def _params(known: dict) -> list:
    """Parametrize cases for correct texts; known failures are marked xfail with their reason."""
    params = []
    for rid, text, pid in _CORRECT:
        marks = [pytest.mark.xfail(strict=False, reason=known[(rid, text)])] if (rid, text) in known else []
        params.append(pytest.param(rid, text, id=pid, marks=marks))
    return params


@functools.lru_cache(maxsize=None)
def _findings(text: str) -> tuple:
    """Every finding on one text under every context, as (profile, finding) pairs."""
    out = []
    for ctx in CONTEXTS:
        args: dict = {"text": text}
        if ctx is not None:
            args["context"] = {"profile_id": ctx}
        env, is_error = api.call("check_mechanics", args)
        assert not is_error, env["error"]
        out.extend((ctx or "none", f) for f in env["data"]["findings"])
    return tuple(out)


def _classified(rid: str, text: str):
    """Yield (class, cited rule, check id, action, profile, finding) for each finding on the text."""
    for profile, f in _findings(text):
        for cited in f["rule_ids"] or [NO_RULE]:
            yield ("SELF" if cited == rid else "CROSS"), cited, f["check"], f["action"], profile, f


def _describe(profile: str, f: dict) -> tuple:
    return profile, f["check"], f["action"], f["text"], f["start"], f["end"], f["rule_ids"]


def _cross_found() -> set[tuple[str, str, str, str]]:
    found = set()
    for rid, text, _ in _CORRECT:
        for cls, cited, check, _action, _profile, _f in _classified(rid, text):
            if cls == "CROSS":
                found.add((rid, cited, check, text))
    return found


@pytest.mark.parametrize("rid,text", _params(KNOWN_PATCH))
def test_a_no_automatic_patch_on_correct_text(rid, text):
    hits = [_describe(p, f) for p, f in _findings(text) if f["action"] == "patch"]
    assert not hits, hits


@pytest.mark.parametrize("rid,text", _params(KNOWN_SELF))
def test_b_no_self_flag_on_correct_text(rid, text):
    hits = [_describe(p, f) for cls, _cited, _check, _action, p, f in _classified(rid, text) if cls == "SELF"]
    assert not hits, hits


def test_c_every_cross_finding_is_judged():
    new = _cross_found() - ACCEPTED_CROSS - set(KNOWN_CROSS)
    assert not new, f"new CROSS findings (judge each: fix, or add to ACCEPTED_CROSS with a reason): {sorted(new)}"


def test_c_accepted_cross_entries_still_fire():
    stale = ACCEPTED_CROSS - _cross_found()
    assert not stale, f"ACCEPTED_CROSS entries that no longer fire, remove them: {sorted(stale)}"


_KNOWN_CROSS_PARAMS = [pytest.param(k, marks=pytest.mark.xfail(strict=False, reason=r))
                       for k, r in KNOWN_CROSS.items()]


@pytest.mark.skipif(not KNOWN_CROSS, reason="no known CROSS contradictions")
@pytest.mark.parametrize("key", _KNOWN_CROSS_PARAMS)
def test_c_known_cross_contradiction_is_fixed(key):
    assert key not in _cross_found(), KNOWN_CROSS[key]


@pytest.mark.xfail(
    strict=False,
    reason=f"{len(ADVISORY_WITHOUT_OK)} advisory rules have no ok example (documented gap, not a contradiction): "
           + ", ".join(ADVISORY_WITHOUT_OK),
)
def test_d_every_advisory_rule_has_an_ok_example():
    missing = sorted(r["id"] for r in load().rules.values()
                     if r["severity"] == "advisory" and not any("ok" in ex for ex in r["examples"]))
    assert not missing, missing


def test_e_no_correct_text_is_another_rules_wrong_text():
    rules = list(load().rules.values())
    wrong: dict[str, list[str]] = defaultdict(list)
    for r in rules:
        for ex in r["examples"]:
            if "wrong" in ex:
                wrong[ex["wrong"]].append(r["id"])
    clashes = []
    for rid, text, _ in _CORRECT:
        clashes += [(rid, other, text) for other in wrong.get(text, []) if other != rid]
    for r in rules:
        for ex in r["examples"]:
            if "right" in ex and SEP in ex["right"]:
                clashes += [(r["id"], other, ex["right"]) for other in wrong.get(ex["right"], []) if other != r["id"]]
    assert not clashes, clashes
