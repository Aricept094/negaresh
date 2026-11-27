"""Integrity checks across the same boundaries used by editing clients."""
import gc
import json
import subprocess
import sys
import weakref

import pytest
from starlette.testclient import TestClient

from negaresh import api, mechanics, patches
from negaresh.corpus import load
from negaresh.server import http_app


TEXT = "نام  ثبت شد."
SPAN = {"locator": {"text": "نام"}}
EDIT = {"patch_id": "p1", "before": "نام", "after": "نشان", "start": 0, "end": 3}


def test_stdio_context_keeps_distinct_protections_for_identical_text():
    checked = api.call("check_mechanics", {"text": TEXT, "protected_spans": [SPAN]})[0]["data"]
    plain = api.call("check_mechanics", {"text": TEXT})[0]["data"]
    assert plain["text_revision"] != checked["text_revision"]
    for extra in [{}, {"original_text": TEXT}]:
        data = api.call("validate_patches", {"text_revision": checked["text_revision"], "patches": [EDIT], **extra})[0]["data"]
        assert not data["valid"] and data["issues"][0]["code"] == "protected_span"
    assert api.call("validate_patches", {**plain["validation_context"], "patches": [EDIT]})[0]["data"]["valid"]


def test_http_check_and_validate_with_protections():
    with TestClient(http_app(), base_url="http://127.0.0.1:8000") as client:
        def call(name, args):
            response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                                   json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                         "params": {"name": name, "arguments": args}})
            response.raise_for_status()
            return response.json()["result"]["structuredContent"]

        assert call("get_profile", {})["data"]["limits"]["held_texts"] == 0
        text = TEXT + " شناسهٔ دوم."
        data = call("check_mechanics", {"text": text, "protected_spans": [SPAN, {"locator": {"text": "دوم"}}]})["data"]
        context = data["validation_context"]
        assert patches.held(data["text_revision"]) is None
        args = {"text_revision": data["text_revision"], "patches": [EDIT]}
        assert call("validate_patches", args)["error"]["code"] == "original_text_required"
        args["original_text"] = text
        assert call("validate_patches", args)["error"]["code"] == "protected_spans_required"
        args["protected_spans"] = [SPAN]
        assert call("validate_patches", args)["error"]["code"] == "protected_spans_mismatch"
        args["protected_spans"] = list(reversed(context["protected_spans"]))
        blocked = call("validate_patches", args)["data"]
        assert not blocked["valid"] and blocked["issues"][0]["code"] == "protected_span"
        result = call("validate_patches", {**args, "patches": data["auto_patch_set"]})["data"]
        assert result["valid"] and result["revised_text"] == text.replace("  ", " ")


@pytest.mark.parametrize("profile", list(load().profiles))
@pytest.mark.parametrize("quoted", ['«' + 'واژه ' * 20 + 'يك  نقل\nبا  فاصله»', '“يك  متن”', '"يك  متن"', '«او “يك  متن” خواند»',
                                    '‘it’s  يك  متن’', '«يك  متن بدون پایان'])
def test_quotes_require_review_in_every_profile(profile, quoted):
    text = "متن  بیرونی " + quoted
    data = mechanics.check(text, profile_id=profile)
    start = text.index(quoted)
    inside = [f for f in data["findings"] if f["start"] >= start]
    assert inside and all(f["action"] == "flag" for f in inside)
    assert all(p["end"] <= start for p in data["auto_patch_set"])


@pytest.mark.parametrize("prefix", ['`"literal`', '"https://example.org/abc"', '«متن  داخلی»'])
def test_prose_after_quotes_and_code_remains_editable(prefix):
    text = prefix + "\nاین پایان  متن است."
    data = mechanics.check(text, profile_id="professional")
    assert any(p["start"] == text.rindex("  ") for p in data["auto_patch_set"])


def test_saved_cli_revision_rejects_change_outside_patch(tmp_path):
    draft, spec, out = [tmp_path / name for name in ("draft.txt", "patches.json", "out.txt")]
    draft.write_bytes((TEXT + "\r\n").encode())
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "negaresh.cli", *args], capture_output=True, check=False)

    data = json.loads(cli("check", draft).stdout)["data"]
    spec.write_text(json.dumps({**data["validation_context"], "patches": data["auto_patch_set"]}), encoding="utf-8")
    assert cli("validate", draft, spec, "--out", out).returncode == 0
    expected = (TEXT.replace("  ", " ") + "\r\n").encode()
    assert out.read_bytes() == expected
    draft.write_bytes(draft.read_bytes() + "جملهٔ تازه".encode())
    failed = cli("validate", draft, spec, "--out", out)
    assert failed.returncode != 0 and json.loads(failed.stdout)["error"]["code"] == "revision_mismatch"
    assert out.read_bytes() == expected


def test_mechanics_releases_text_after_request():
    class Document(str):
        pass

    text = Document("در متن عدد 12 و نشانه, هست.")
    document_ref = weakref.ref(text)
    mechanics.check(text)
    del text
    gc.collect()
    assert document_ref() is None
