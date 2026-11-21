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


def test_check_is_linear_on_hostile_input():
    import time

    for text in ('"' * 11999 + "ب", "ي" * 12000, "1 " * 5999 + "۱"):
        t0 = time.perf_counter()
        api.call("check_mechanics", {"text": text})
        assert time.perf_counter() - t0 < 3


def test_auto_patch_next_to_url_validates():
    text = "سلام https://a.com  و خوب"
    env, err = api.call("check_mechanics", {"text": text})
    data = env["data"]
    assert data["auto_patch_set"]
    out, err = api.call("validate_patches", {"text_revision": data["text_revision"], "patches": data["auto_patch_set"]})
    assert not err and out["data"]["valid"], out["data"]["issues"]


def test_auto_patch_set_is_capped():
    data = api.call("check_mechanics", {"text": "ب  " * 4000})[0]["data"]
    assert len(data["auto_patch_set"]) <= 256 and data["auto_patch_set_omitted"] > 0


def test_arabic_letters_in_cited_words_are_flagged_not_patched():
    for text in ("در عربی حرف «في» به معنای «در» است.", "او گفت: «كتاب» در عربی یعنی نامه."):
        hits = [f for f in findings(text, profile_id="academic") if f["check"] == "M01"]
        assert hits and all(f["action"] == "flag" for f in hits)


def test_zwnj_before_space_and_plural_is_not_auto_deleted():
    hits = [f for f in findings("کتاب" + ZWNJ + " ها را خواندم.") if f["check"] == "M07"]
    assert hits and all(f["action"] == "flag" for f in hits)
    assert hits[0]["candidate_patch"]["after"] == ZWNJ


def test_text_too_long_is_limit_exceeded():
    env, err = api.call("check_mechanics", {"text": "ب" * 12001})
    assert err and env["status"] == "limit_exceeded"


def test_remote_server_keeps_no_texts():
    from negaresh import patches

    patches.HOLD_ENABLED = False
    try:
        text = "متنی  تازه برای آزمون."
        data = api.call("check_mechanics", {"text": text})[0]["data"]
        patch = [{"patch_id": "p", "before": "", "after": "x", "start": 0, "end": 0}]
        env, _ = api.call("validate_patches", {"text_revision": data["text_revision"], "patches": patch})
        assert env["status"] == "needs_context" and env["error"]["code"] == "original_text_required"
        env, _ = api.call("validate_patches", {"text_revision": data["text_revision"], "original_text": text,
                                               "patches": data["auto_patch_set"]})
        assert env["data"]["valid"]
    finally:
        patches.HOLD_ENABLED = True


def test_tool_schemas_have_no_refs():
    from negaresh import server

    for tool in server.tool_definitions(chatgpt=True):
        blob = json.dumps(tool.input_schema)
        assert "$ref" not in blob and "$defs" not in blob, tool.name


def test_chatgpt_tools_report_bad_input_as_errors():
    from negaresh import server

    assert server._chatgpt_call("search", {}).is_error
    assert server._chatgpt_call("search", {"query": "x" * 600}).is_error
    assert server._chatgpt_call("fetch", {"id": 5}).is_error
    found = json.loads(server._chatgpt_call("search", {"query": "نیم‌فاصله"}).content[0].text)
    assert "#" in found["results"][0]["url"]


def test_cli_runs_once_and_validates_patches(tmp_path, capsys):
    from negaresh import cli

    text = "كتاب ها"
    draft = tmp_path / "draft.txt"
    draft.write_text(text, encoding="utf-8")
    assert cli.main(["check", str(draft)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"

    good = [{"patch_id": "p1", "start": 0, "end": 1, "before": "ك", "after": "ک", "rule_ids": ["ORT-005"]}]
    patches = tmp_path / "patches.json"
    patches.write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "revised.txt"
    assert cli.main(["validate", str(draft), str(patches), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "کتاب ها"
    capsys.readouterr()

    bad = [{"patch_id": "p1", "start": 0, "end": 1, "before": "x", "after": "ک"}]
    patches.write_text(json.dumps(bad), encoding="utf-8")
    out.unlink()
    assert cli.main(["validate", str(draft), str(patches), "--out", str(out)]) == 1
    assert not out.exists()
    capsys.readouterr()

    patches.write_text("{not json", encoding="utf-8")
    assert cli.main(["validate", str(draft), str(patches)]) == 2


def test_cli_rule_and_profile(capsys):
    from negaresh import cli

    assert cli.main(["rule", "ORT-002"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["rule"]["id"] == "ORT-002"
    assert cli.main(["profile", "academic"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
