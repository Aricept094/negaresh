import asyncio
import json
import os
import sys

import pytest

from negaresh import api, mechanics
from negaresh.corpus import load
from negaresh.textutil import ZWNJ

CORPUS = load()


def findings(text, **kw):
    return mechanics.check(text, **kw)["findings"]


def checks(text, **kw):
    return {f["check"] for f in findings(text, **kw)}


def test_corpus_shape():
    assert len(CORPUS.rules) >= 100
    assert len(CORPUS.profiles) == 8
    ids = list(CORPUS.rules)
    assert len(ids) == len(set(ids))


def test_arabic_letters_and_spacing():
    c = checks("كتاب علي رسيد ،ولی  دیر.")
    assert {"M01", "M04", "M06"} <= c


def test_mi_and_ha_get_zwnj_patch():
    fs = [f for f in findings("من کتاب ها را می خوانم.", profile_id="academic") if f["check"] == "M08"]
    assert len(fs) == 2
    assert all(f["candidate_patch"]["after"] == ZWNJ for f in fs)


def test_correct_text_is_clean():
    text = "من کتاب‌ها را می‌خوانم و او گزارش را نوشته است."
    assert findings(text, profile_id="academic") == []


def test_variant_spelling_is_flag_only():
    fs = [f for f in findings("اطاق بزرگ است.") if f["check"] == "M14"]
    assert fs and fs[0]["action"] == "flag"


def test_common_words_not_flagged_as_variants():
    assert "M14" not in checks("این خطا در آخر متن است و او در کار غرق شد.")


def test_protected_spans_are_skipped():
    text = "نشانی https://example.com/a,b?x=1 را ببینید."
    assert "M05" not in checks(text)


def test_rule_examples_are_self_consistent():
    """A form the rule book calls right must not get a patch from the checker."""
    bad = []
    for r in CORPUS.rules.values():
        for ex in r["examples"]:
            good = ex.get("right") or ex.get("ok")
            if not good or "←" in good:
                continue
            for f in findings(good, profile_id="general_nonfiction"):
                if f["action"] == "patch":
                    bad.append((r["id"], good, f["check"], f["message"]))
    assert not bad, json.dumps(bad[:15], ensure_ascii=False, indent=1)


def test_api_rejects_unknown_fields_and_tools():
    env, is_error = api.call("search_rules", {"query": "نیم‌فاصله", "bogus": 1})
    assert is_error and env["status"] == "invalid_input"
    env, is_error = api.call("no_such_tool", {})
    assert is_error


def test_search_get_rule_get_profile():
    env, err = api.call("search_rules", {"query": "گزارشات"})
    assert not err and env["data"]["results"][0]["id"] == "USG-002"
    env, err = api.call("get_rule", {"rule_id": "GRM-009"})
    assert not err and "guidance" in json.dumps(env, ensure_ascii=False)
    env, err = api.call("get_profile", {"profile_id": "literary"})
    assert not err


def test_validate_patches_roundtrip():
    text = "من کتاب ها را می خوانم."
    env, err = api.call("check_mechanics", {"text": text, "context": {"profile_id": "academic"}})
    assert not err
    patches = [dict(f["candidate_patch"], patch_id=f"p{i}", rule_ids=f["rule_ids"][:1])
               for i, f in enumerate(env["data"]["findings"]) if f["candidate_patch"]]
    env2, err2 = api.call("validate_patches", {"text_revision": env["data"]["text_revision"], "patches": patches})
    assert not err2, env2
    assert env2["data"]["revised_text"] == "من کتاب‌ها را می‌خوانم."


def test_input_limit():
    env, err = api.call("check_mechanics", {"text": "ا" * 12001})
    assert err


def test_mcp_stdio_roundtrip():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "negaresh.cli", "serve"], env=dict(os.environ))
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                names = {t.name for t in tools.tools}
                res = await s.call_tool("check_mechanics", {"text": "می روم به خانه ي او"})
                return names, res

    names, res = asyncio.run(run())
    assert names == {"search_rules", "get_rule", "get_profile", "check_mechanics", "validate_patches"}
    payload = json.loads(res.content[0].text)
    assert {f["check"] for f in payload["data"]["findings"]} >= {"M01", "M08"}


def test_persian_digits_alone_are_not_mixed_digits():
    assert "M03" not in checks("در سال ۱۳۹۵ سهم زنان ۹۶٫۷٪ بود.")
    assert "M03" in checks("در سال 1395 سهم زنان ۹۶٫۷٪ بود.")


def test_http_mode_offers_chatgpt_search_and_fetch():
    import asyncio
    import json

    from negaresh import server

    names = [t.name for t in server.tool_definitions(chatgpt=True)]
    assert {"search", "fetch", "check_mechanics"} <= set(names)
    assert "search" not in [t.name for t in server.tool_definitions()]
    found = json.loads(server._chatgpt_call("search", {"query": "متن ماشینی"}).content[0].text)
    assert found["results"] and found["results"][0]["url"].startswith(server.REPO_URL)
    doc = json.loads(server._chatgpt_call("fetch", {"id": found["results"][0]["id"]}).content[0].text)
    assert doc["id"] and doc["text"] and doc["url"]
    assert server._chatgpt_call("fetch", {"id": "XXX-999"}).is_error
    assert server.http_app() is not None
    asyncio.run(asyncio.sleep(0))
