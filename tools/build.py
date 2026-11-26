"""Validate the public corpus and generate every derived file from it:
the packaged bundle, the skill's rule references and the full rule book.

Run:  python tools/build.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
OUT_DATA = ROOT / "src" / "negaresh" / "data" / "corpus.json"
OUT_REFS = ROOT / "skills" / "negaresh" / "references"
OUT_BOOK = ROOT / "docs" / "RULEBOOK.md"

CATEGORIES = {
    "orthography": "املا و فاصله‌گذاری",
    "punctuation": "نشانه‌گذاری و نویسه‌ها",
    "grammar": "دستور",
    "usage": "کاربرد واژه و ساخت",
    "style": "سبک و روانی",
    "discourse": "ساختار متن",
    "terminology": "اصطلاح‌ها",
    "integrity": "حفظ معنا و امانت",
}
SEVERITY = {"error": "خطا", "convention": "قرارداد", "advisory": "توصیه"}
ACTION = {"patch", "suggest", "flag"}
REQUIRED = ("id", "title_fa", "title_en", "category", "severity", "action", "profiles", "guidance",
            "examples", "evidence_class", "status")
PROFILES = {"all", "academic", "professional", "journalistic", "general_nonfiction", "literary",
            "conversational", "technical_instructional", "persuasive_marketing_social"}
PRIVATE_MARKERS = ("C:\\", "/mnt/", "/home/", "/Users/", "_notes\\", "_notes/")


def fail(msg: str) -> None:
    print("CORPUS ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)


def load_rules() -> list[dict]:
    rules: list[dict] = []
    for path in sorted((CORPUS / "rules").glob("*.json")):
        try:
            rules.extend(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            fail(f"{path.name}: {exc}")
    return rules


def validate(rules: list[dict], sources: dict, profiles: list[dict]) -> None:
    seen: set[str] = set()
    for r in rules:
        rid = r.get("id", "?")
        for key in REQUIRED:
            if key not in r:
                fail(f"{rid}: missing {key}")
        if not re.fullmatch(r"[A-Z]{3}-\d{3}", rid):
            fail(f"{rid}: bad id")
        if rid in seen:
            fail(f"{rid}: duplicate id")
        seen.add(rid)
        if r["category"] not in CATEGORIES:
            fail(f"{rid}: bad category {r['category']}")
        if r["severity"] not in SEVERITY or r["action"] not in ACTION:
            fail(f"{rid}: bad severity/action")
        if not set(r["profiles"]) <= PROFILES:
            fail(f"{rid}: bad profile")
        if r["evidence_class"] not in ("sourced", "editorial_synthesis"):
            fail(f"{rid}: bad evidence_class")
        if r["evidence_class"] == "sourced" and not r.get("evidence"):
            fail(f"{rid}: sourced rule without evidence")
        if r["evidence_class"] == "editorial_synthesis" and r["severity"] == "error":
            fail(f"{rid}: a synthesis rule cannot have severity error")
        for ev in r.get("evidence", []):
            if ev["source"] not in sources:
                fail(f"{rid}: unknown source {ev['source']}")
        if not r["examples"]:
            fail(f"{rid}: no example")
        blob = json.dumps(r, ensure_ascii=False)
        if any(m in blob for m in PRIVATE_MARKERS):
            fail(f"{rid}: private path or file name in rule")
        if len(blob) > 6000:
            fail(f"{rid}: rule too large")
    for r in rules:
        for other in r.get("related", []) + r.get("conflicts", []):
            if other not in seen:
                fail(f"{r['id']}: unknown related rule {other}")
    if {p["id"] for p in profiles} != PROFILES - {"all"}:
        fail("profiles.json does not define exactly the eight profiles")


def render_rule(r: dict, sources: dict) -> str:
    lines = [f'<a id="{r["id"].lower()}"></a>', "", f"### {r['id']} — {r['title_fa']}", ""]
    meta = f"{SEVERITY[r['severity']]} · {'منبع‌دار' if r['evidence_class'] == 'sourced' else 'جمع‌بندی ویراستاری (بدون منبع کتابی)'}"
    if r["status"] == "draft":
        meta += " · پیش‌نویس"
    if r["profiles"] != ["all"]:
        meta += " · فقط: " + "، ".join(r["profiles"])
    lines += [f"*{meta}* — {r['title_en']}", "", r["guidance"], ""]
    for ex in r["examples"]:
        if "ok" in ex:
            line = f"- درست و بی‌نیاز از تغییر: {ex['ok']}"
        elif "wrong" in ex:
            line = f"- ✗ {ex['wrong']} ← ✓ {ex['right']}"
        else:
            line = f"- ✓ {ex['right']}"
        if ex.get("note"):
            line += f" ({ex['note']})"
        lines.append(line)
    if r.get("exceptions"):
        lines += ["", "استثناها و شرایط:"] + [f"- {e}" for e in r["exceptions"]]
    if r.get("evidence"):
        cites = "؛ ".join(f"{sources[e['source']]['short']}، {e['loc']}" for e in r["evidence"])
        lines += ["", f"منبع: {cites}"]
        unchecked = [sources[e["source"]]["short"] for e in r["evidence"]
                     if sources[e["source"]].get("human_checked") is False]
        if unchecked:
            lines += ["", "هنوز با متن اصلی مقابله نشده است: " + "؛ ".join(dict.fromkeys(unchecked))]
    if r.get("checks"):
        lines += ["", "بررسی خودکار: " + "، ".join(r["checks"])]
    if r.get("verified"):
        lines += ["", "مقابله با تصویر صفحهٔ کتاب: انجام شد."]
    return "\n".join(lines) + "\n"


def main() -> None:
    rules = sorted(load_rules(), key=lambda r: r["id"])
    sources_list = json.loads((CORPUS / "sources.json").read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in sources_list}
    profiles = json.loads((CORPUS / "profiles.json").read_text(encoding="utf-8"))
    lexicon = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((CORPUS / "lexicon").glob("*.json"))}
    validate(rules, sources, profiles)
    if "--check" in sys.argv:
        print(f"corpus OK: {len(rules)} rules"); return

    digest = hashlib.sha256(json.dumps([rules, profiles, sources_list, lexicon], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]
    pkg_version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
    version = f"{pkg_version}+{digest}"
    bundle = {"corpus_version": version, "rules": rules, "profiles": profiles, "sources": sources_list,
              "lexicon": lexicon, "tombstones": []}
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    OUT_DATA.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    header = (f"<!-- generated by tools/build.py from corpus/ ; corpus {version} ; do not edit by hand -->\n\n"
)
    OUT_REFS.mkdir(parents=True, exist_ok=True)
    for old in OUT_REFS.glob("rules-*.md"):
        old.unlink()
    book = ["# راهنمای نگارش فارسی — مجموعهٔ قاعده‌ها", "", header.strip(), ""]
    for cat, title in CATEGORIES.items():
        cat_rules = [r for r in rules if r["category"] == cat]
        if not cat_rules:
            continue
        body = "\n".join(render_rule(r, sources) for r in cat_rules)
        (OUT_REFS / f"rules-{cat}.md").write_text(f"# {title} ({len(cat_rules)} قاعده)\n\n{header}{body}", encoding="utf-8")
        book += [f"## {title}", "", body]
    book += ["## منابع", ""] + [f"- **{s['short']}**: {s['citation']}"
                                 + (" (هنوز با متن اصلی مقابله نشده است.)" if s.get("human_checked") is False else "")
                                 for s in sources_list]
    OUT_BOOK.parent.mkdir(parents=True, exist_ok=True)
    OUT_BOOK.write_text("\n".join(book) + "\n", encoding="utf-8")

    index = ["# فهرست قاعده‌ها", "", header.strip(), ""]
    for cat, title in CATEGORIES.items():
        cat_rules = [r for r in rules if r["category"] == cat]
        if cat_rules:
            index += [f"## {title} — `rules-{cat}.md`", ""] + [f"- {r['id']}: {r['title_fa']} ({r['title_en']})" for r in cat_rules] + [""]
    (OUT_REFS / "rules-index.md").write_text("\n".join(index), encoding="utf-8")

    counts = {c: sum(r["category"] == c for r in rules) for c in CATEGORIES}
    print(f"corpus {version}: {len(rules)} rules", {k: v for k, v in counts.items() if v})


if __name__ == "__main__":
    main()
