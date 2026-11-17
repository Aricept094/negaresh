"""Bounded mechanical checks (M01-M16).

Offsets are Unicode code points in logical order, end exclusive. The input
text is never modified. Every patch is a candidate for review.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .corpus import Corpus, load
from .textutil import ARABIC_DIGITS, DIACRITICS, LETTER_CLASS, NON_JOINING, PERSIAN_DIGITS, ZWNJ, is_persian_letter, revision_of

MECHANICS_VERSION = "1"
MAX_FINDINGS = 200
DEFAULT_PATCH_CHECKS = {"M01", "M02", "M06", "M07"}

L = LETTER_CLASS
_PROTECT_RE = re.compile(
    r"```.*?```|~~~.*?~~~|`[^`\n]+`|^(?: {4}|\t)[^\n]*|https?://[^\s<>«»]+|www\.[^\s<>«»]+"
    r"|(?<![\w.+-])[\w.+-]+@[\w-]+\.[\w.-]+",
    re.S | re.M,
)

# Closed-class verb stems authored for this project (not taken from any word list).
_PRESENT = (
    "کن شو رو آی گوی دار خواه توان دان بین ده گیر آور بر خور زن نویس خوان ساز مان رس گذار گذر کش یاب پرس "
    "شناس فهم افت ایست نشین خیز پذیر فرست آموز کوش جوی خر فروش ریز سوز دو پر شکن بند گشای نمای افزای کاه "
    "خند گری ترس جنگ چرخ گرد پوش شوی پز بخش سنج انجام نام رسان گذران کشان بای شای ارز پرداز انداز اندیش "
    "باش شنو میر آفرین آزمای آمیز انگیز باز پیوند تاب تراش جه چین خواب دوز ران روی زای سپار ستای شمار فشار کار گزین گنج لرز نگر ورز"
).split()
_PAST = (
    "کرد شد رفت آمد گفت داشت خواست توانست دانست دید داد گرفت آورد برد خورد زد نوشت خواند ساخت ماند رسید "
    "گذاشت گذشت کشید یافت پرسید شناخت فهمید افتاد ایستاد نشست خاست پذیرفت فرستاد آموخت کوشید جست خرید "
    "فروخت ریخت سوخت دوید پرید شکست بست گشود نمود افزود کاست خندید گریست ترسید جنگید چرخید گشت پوشید شست "
    "پخت بخشید سنجید انجامید نامید رساند گذراند کشاند بود بایست شایست ارزید پرداخت انداخت اندیشید آفرید آزمود "
    "شنید مرد آمیخت انگیخت باخت پیوست تابید تراشید جهید چید خوابید دوخت راند رویید زاد سپرد ستود شمرد فشرد کاشت گزید گنجید لرزید نگریست ورزید"
).split()
_VERB_REST = (
    "(?:(?:" + "|".join(sorted(_PRESENT, key=len, reverse=True)) + ")(?:یم|ید|ند|م|ی|د)"
    "|(?:" + "|".join(sorted(_PAST, key=len, reverse=True)) + ")(?:یم|ید|ند|م|ی)?"
    "|توان)"
)
_MI_SPACE_RE = re.compile(rf"(?<![{L}{ZWNJ}])((?:بر|در|باز|فرا|فرو)?ن?می) (?={_VERB_REST}(?![{L}{ZWNJ}]))")
_MI_JOINED_RE = re.compile(rf"(?<![{L}{ZWNJ}])((?:بر|در|باز|فرا|فرو)?ن?می)(?={_VERB_REST}(?![{L}{ZWNJ}]))")
_HA_RE = re.compile(rf"([{L}]) (ها(?:ی(?:ی|م|ت|ش|مان|تان|شان)?)?)(?![{L}{ZWNJ}])")
_TARIN_RE = re.compile(rf"([{L}]) (ترین|تر)(?![{L}{ZWNJ}])")

_CONTROL_NAMES = {
    "‎": "LEFT-TO-RIGHT MARK", "‏": "RIGHT-TO-LEFT MARK", "‪": "LRE", "‫": "RLE",
    "‬": "PDF", "‭": "LRO", "‮": "RLO", "⁦": "LRI", "⁧": "RLI", "⁨": "FSI",
    "⁩": "PDI", "﻿": "BYTE ORDER MARK", "­": "SOFT HYPHEN", " ": "NO-BREAK SPACE",
    "‍": "ZERO WIDTH JOINER", "​": "ZERO WIDTH SPACE",
}
# Words that start like «می» + verb stem but are nouns; never flag them as a joined «می».
_MI_NOUNS = tuple("میدان میان میز میوه میراث میل میهن میخ مینو میش میکروب میلیون میلی میزان میگو میهمان مینا میرا میراب".split())
_AR_ONLY = re.compile("[ةىأإ\u064B-\u0652]|(?<![\u0622-\u06CC])ال(?=[\u0622-\u06CC])")
_AR_PERSIAN_ONLY = re.compile("[پچژگ]")
_PAIRS = {"(": ")", "«": "»", "[": "]", "{": "}"}


def detect_protected(text: str) -> list[dict[str, Any]]:
    return [{"start": m.start(), "end": m.end(), "kind": "auto"} for m in _PROTECT_RE.finditer(text)]


class _Collector:
    def __init__(self, text: str, protected: list[dict[str, Any]], patch_checks: set[str], off: set[str]):
        self.text = text
        self.protected = protected
        self.patch_checks = patch_checks
        self.off = off
        self.items: list[dict[str, Any]] = []

    def _is_protected(self, start: int, end: int) -> bool:
        return any(start < p["end"] and p["start"] < max(end, start + 1) for p in self.protected)

    def add(self, check: str, start: int, end: int, message: str, *, after: str | None = None,
            severity: str = "convention", action_class: str = "mechanical", force_flag: bool = False) -> None:
        if check in self.off or self._is_protected(start, end):
            return
        before = self.text[start:end]
        patch = None
        if end - start > 200:
            after, force_flag = None, True
            before = before[:100] + "…" + before[-50:]
        if after is not None and after != before:
            patch = {"start": start, "end": end, "before": before, "after": after}
        action = "patch" if patch and check in self.patch_checks and not force_flag else "flag"
        self.items.append({
            "check": check, "start": start, "end": end, "text": before, "severity": severity,
            "action": action, "action_class": action_class, "message": message, "candidate_patch": patch,
        })


def _segment(text: str, i: int) -> str:
    """The quotation «…» around position i, else the sentence or line around it."""
    qo, qc = text.rfind("«", 0, i), text.rfind("»", 0, i)
    if qo > qc:
        close = text.find("»", i)
        return text[qo: close if close != -1 else len(text)]
    begin = max(text.rfind(ch, 0, i) for ch in ".!؟\n:") + 1
    ends = [e for e in (text.find(ch, i) for ch in ".!؟\n") if e != -1]
    return text[begin: min(ends) if ends else len(text)]


def _letter_near(text: str, i: int, step: int) -> str:
    """The nearest letter before (step=-1) or after (step=1) position i, skipping digits, spaces and marks."""
    j = i
    while 0 <= j < len(text):
        if text[j].isalpha():
            return text[j]
        j += step
    return ""


def _is_latin(ch: str) -> bool:
    return bool(ch) and ch.isascii() and ch.isalpha()


def _looks_arabic(segment: str) -> bool:
    return bool(_AR_ONLY.search(segment)) and not _AR_PERSIAN_ONLY.search(segment)


def _check_letters(c: _Collector) -> None:
    text = c.text
    for m in re.finditer("[يكى]", text):
        ch = m.group()
        target = {"ي": "ی", "ك": "ک", "ى": "ی"}[ch]
        if _looks_arabic(_segment(text, m.start())):
            c.add("M01", m.start(), m.end(),
                  f"حرف عربی «{ch}» در عبارتی که عربی به نظر می‌رسد؛ اگر نقل عربی است تغییر ندهید",
                  after=target, severity="advisory", force_flag=True)
        else:
            c.add("M01", m.start(), m.end(), f"حرف عربی «{ch}» در متن فارسی", after=target, force_flag=(ch == "ى"))
    for m in re.finditer("[\uFB50-\uFDFF\uFE70-\uFEFC]+", text):
        run = m.group()
        if all(ch in "\uFD3E\uFD3F" for ch in run):
            continue
        single = all("\uFB50" <= ch <= "\uFBFF" or "\uFE80" <= ch <= "\uFEFC" for ch in run)
        if single:
            c.add("M02", m.start(), m.end(), "نویسهٔ شکل نمایشی (Presentation Form) به‌جای حرف اصلی",
                  after=unicodedata.normalize("NFKC", run))
        else:
            c.add("M02", m.start(), m.end(),
                  "نویسهٔ ترکیبی یا نمادین (مانند ﷺ، ﷼ یا حرکت جدا)؛ اگر عمدی است تغییر ندهید",
                  after=unicodedata.normalize("NFKC", run), severity="advisory", force_flag=True)


def _check_digits(c: _Collector) -> None:
    text = c.text
    for m in re.finditer(f"[{ARABIC_DIGITS}]+", text):
        c.add("M03", m.start(), m.end(), "رقم عربی (U+0660–U+0669) به‌جای رقم فارسی",
              after=m.group().translate(str.maketrans(ARABIC_DIGITS, PERSIAN_DIGITS)), force_flag=True)
    has_fa = re.search(f"[{PERSIAN_DIGITS}]", text)
    latin = [m for m in re.finditer(r"(?<![A-Za-z0-9_./:-])[0-9]+(?![A-Za-z0-9_/-])", text)
             if not _is_latin(_letter_near(text, m.start() - 1, -1))]
    if has_fa and latin:
        m = latin[0]
        c.add("M03", m.start(), m.end(), "آمیختگی رقم فارسی و لاتین در یک متن؛ یک‌دست کنید", severity="advisory")


def _check_punct(c: _Collector) -> None:
    text = c.text
    for m in re.finditer(r"(?<=\S)([ \t]+)([،؛:.؟!])", text):
        nxt = text[m.end(): m.end() + 1]
        if m.group(2) == "." and (nxt == "." or text[m.start() - 1] == "."):
            continue
        if m.group(2) == ":" and not is_persian_letter(text[m.start() - 1]):
            continue
        if nxt and (nxt.isalnum() or nxt in "()"):
            continue
        if m.group(2) == "." and text[m.end():].lstrip(" ").startswith("."):
            continue  # spaced dots «. . .»
        if text[m.start() - 1] in ".…،؛:؟!«(":
            continue  # spaced dots, «... ؟», or a mark cited after another mark
        c.add("M04", m.start(1), m.end(1), f"فاصله پیش از «{m.group(2)}»", after="")
    for m in re.finditer(rf"([،؛؟])(?=[{L}])", text):
        c.add("M04", m.start(), m.end(), f"پس از «{m.group()}» فاصله لازم است", after=m.group() + " ")
    for m in re.finditer(rf"(?<=[{L}{ZWNJ}{DIACRITICS}])([ \t]?)([,;?])", text):
        ch = m.group(2)
        nxt = text[m.end(): m.end() + 1]
        if ch == "," and nxt.isdigit():
            continue
        mark = {",": "،", ";": "؛", "?": "؟"}[ch]
        after = mark + (" " if nxt and is_persian_letter(nxt) else "")
        c.add("M05", m.start(), m.end(), f"نشانهٔ لاتین «{ch}» در متن فارسی", after=after)


def _check_spaces(c: _Collector) -> None:
    text = c.text
    for m in re.finditer(r"(?<=[^\s|]) {2,}(?=[^\s|])", text):
        if m.end() - m.start() == 2:
            c.add("M06", m.start(), m.end(), "چند فاصلهٔ پیاپی", after=" ")
        else:
            c.add("M06", m.start(), m.end(), "چند فاصلهٔ پیاپی (شاید فاصلهٔ دو مصراع یا ستون‌بندی باشد)",
                  after=" ", severity="advisory", force_flag=True)
    for m in re.finditer(r"(?<=\S)[ \t]+(?=\r?\n|$)", text):
        if m.group() == "  " and text[m.end(): m.end() + 1] in ("\n", "\r"):
            continue  # Markdown line break
        c.add("M06", m.start(), m.end(), "فاصلهٔ اضافی در پایان سطر", after="")


def _check_zwnj(c: _Collector) -> None:
    text = c.text
    for m in re.finditer(f"{ZWNJ}{{2,}}", text):
        c.add("M07", m.start(), m.end(), "نیم‌فاصلهٔ تکراری", after=ZWNJ)
    for m in re.finditer(ZWNJ, text):
        i = m.start()
        prev, nxt = text[i - 1: i] if i else "", text[i + 1: i + 2]
        if prev == ZWNJ or nxt == ZWNJ:
            continue
        if any(ch and ord(ch) > 0x7F and "ARABIC" not in unicodedata.name(ch, "") for ch in (prev, nxt)):
            continue  # another script (e.g. Devanagari) uses ZWNJ for its own shaping
        if not prev or not nxt or prev.isspace() or nxt.isspace() or not (
            is_persian_letter(nxt) or nxt.isalnum()
        ) or not (is_persian_letter(prev) or prev.isalnum() or re.match(f"[{DIACRITICS}]", prev)):
            c.add("M07", i, i + 1, "نیم‌فاصله در جایی که اثری ندارد (کنار فاصله، نشانه یا لبهٔ واژه)", after="")
        elif prev in NON_JOINING:
            c.add("M07", i, i + 1,
                  f"نیم‌فاصله پس از حرف منفصل «{prev}» لازم نیست (بی‌فاصله)", after="",
                  severity="advisory", force_flag=True)


def _check_affixes(c: _Collector) -> None:
    text = c.text
    for m in _MI_SPACE_RE.finditer(text):
        s = m.end(1)
        c.add("M08", s, s + 1, f"«{m.group(1)}» با نیم‌فاصله به فعل می‌پیوندد", after=ZWNJ, action_class="contextual")
    for m in _MI_JOINED_RE.finditer(text):
        s = m.end(1)
        word = re.match(rf"[{L}]*", text[m.start():]).group()
        if word.startswith(_MI_NOUNS):
            continue
        c.add("M08", s, s, f"میان «{m.group(1)}» و فعل نیم‌فاصله لازم است", after=ZWNJ,
              action_class="contextual", force_flag=True)
    for m in _HA_RE.finditer(text):
        s = m.end(1)
        after = "" if m.group(1) in NON_JOINING else ZWNJ
        c.add("M08", s, s + 1, "نشانهٔ جمع «ها» با فاصلهٔ کامل از واژه جدا نمی‌شود", after=after, action_class="contextual")
    for m in _TARIN_RE.finditer(text):
        s = m.end(1)
        after = "" if m.group(1) in NON_JOINING else ZWNJ
        flag = m.group(2) == "تر"
        c.add("M08", s, s + 1, f"پسوند «{m.group(2)}» با نیم‌فاصله/بی‌فاصله نوشته می‌شود"
              + ("؛ اگر «تر» واژهٔ مستقل است تغییر ندهید" if flag else ""), after=after,
              action_class="contextual", force_flag=flag, severity="advisory" if flag else "convention")


def _check_marks(c: _Collector) -> None:
    text = c.text
    if re.search(f"[{L}]", text):
        for m in re.finditer('"', text):
            if _is_latin(_letter_near(text, m.start() - 1, -1)) or _is_latin(_letter_near(text, m.end(), 1)):
                continue
            c.add("M09", m.start(), m.end(), "گیومهٔ راست (\") در متن فارسی؛ معمولاً «» به کار می‌رود", severity="advisory")
    for m in re.finditer(rf"(?<=[{L}])ـ+(?=[{L}])", text):
        c.add("M10", m.start(), m.end(),
              "کشیده (ـ) میان حروف؛ اگر به‌جای خط تیره میان دو واژه آمده است، آن را با فاصله یا «–» بنویسید",
              severity="advisory", force_flag=True)
    for m in re.finditer("[" + "".join(_CONTROL_NAMES) + "]", text):
        c.add("M11", m.start(), m.end(), f"نویسهٔ نادیدنی {_CONTROL_NAMES[m.group()]} (U+{ord(m.group()):04X})",
              severity="advisory")


def _check_hamza_he(c: _Collector) -> None:
    text = c.text
    styles = {
        "ۀ": [m.span() for m in re.finditer("ۀ", text)],
        "هٔ": [m.span() for m in re.finditer("هٔ", text)],
        "ه‌ی": [m.span() for m in re.finditer(rf"ه{ZWNJ}ی(?![{L}{ZWNJ}])", text)],
    }
    used = {k: v for k, v in styles.items() if v}
    if len(used) < 2:
        return
    major = max(used, key=lambda k: len(used[k]))
    for style, spans in used.items():
        if style == major:
            continue
        for start, end in spans:
            c.add("M12", start, end, f"ناهمسانی در نشانهٔ اضافه پس از های غیرملفوظ: «{style}» در کنار «{major}»",
                  severity="advisory")


def _check_brackets(c: _Collector) -> None:
    text = c.text
    stack: list[tuple[str, int]] = []
    closers = {v: k for k, v in _PAIRS.items()}
    for i, ch in enumerate(text):
        if ch in _PAIRS:
            stack.append((ch, i))
        elif ch in closers:
            if stack and stack[-1][0] == closers[ch]:
                stack.pop()
            elif ch == ")" and re.search(r"(?:^|\n)[ \t]*[0-9۰-۹A-Za-z\u0622-\u06CC]{1,3}$", text[max(0, i - 8): i]):
                continue  # list item such as «۱)» or «الف)»
            else:
                c.add("M13", i, i + 1, f"«{ch}» بدون نشانهٔ آغاز", severity="advisory")
    for ch, i in stack:
        c.add("M13", i, i + 1, f"«{ch}» بسته نشده است", severity="advisory")
    for m in re.finditer(r"([(«\[]) +|(?<! ) +([)»\]])", text):
        c.add("M13", m.start(), m.end(), "فاصله در درون پرانتز یا گیومه", after=(m.group(1) or m.group(2)),
              severity="advisory", force_flag=True)


def _check_variants(c: _Collector, corpus: Corpus) -> None:
    academy: dict[str, list[str]] = corpus.lexicon.get("variant_spellings", {})
    samiee: dict[str, list[str]] = corpus.lexicon.get("variant_spellings_samiee", {})
    notes: dict[str, str] = corpus.lexicon.get("variant_notes", {})
    if not academy and not samiee:
        return
    strip = re.compile(f"[{DIACRITICS}]")
    for m in re.finditer(rf"[{L}{ZWNJ}{DIACRITICS}]+", c.text):
        key = strip.sub("", m.group())
        if key in academy:
            preferred, who = academy[key], "فرهنگستان"
        elif key in samiee:
            preferred, who = samiee[key], "سمیعی (نگارش و ویرایش)"
        else:
            continue
        msg = f"واژهٔ چنداملایی؛ املای مرجّح {who}: " + "/ ".join(preferred)
        if notes.get(key):
            msg += " — " + notes[key]
        c.add("M14", m.start(), m.end(), msg,
              after=preferred[0] if len(preferred) == 1 else None,
              severity="convention" if who == "فرهنگستان" else "advisory", force_flag=True)


_FOLD = str.maketrans({"ۀ": "ه", "ي": "ی", "ك": "ک", "ى": "ی"})
_LETTER_ALTS = {"ه": "[هۀ]", "ی": "[یيى]", "ک": "[کك]"}


def _phrase_key(s: str) -> str:
    return re.sub(f"[ {ZWNJ}]+", " ", re.sub(f"[{DIACRITICS}]", "", s.translate(_FOLD))).strip()


_PHRASE_CACHE: dict[str, tuple[re.Pattern[str] | None, dict[str, dict[str, Any]]]] = {}


def _phrase_index(corpus: Corpus) -> tuple[re.Pattern[str] | None, dict[str, dict[str, Any]]]:
    cached = _PHRASE_CACHE.get(corpus.version)
    if cached:
        return cached
    entries = corpus.lexicon.get("usage_replacements", {}).get("entries", [])
    strip = re.compile(f"[{DIACRITICS}]")
    by_key: dict[str, dict[str, Any]] = {}
    parts = []
    for e in entries:
        key = _phrase_key(e["avoid"])
        if key.startswith("غیر "):
            key = "غیر" + key[4:]
        if len(key) < 2 or key in by_key:
            continue
        by_key[key] = e
        letters = []
        if key.startswith("غیر") and not key.startswith("غیر "):
            key_body, letters = key[3:], [f"غیر[ {ZWNJ}]?"]
        else:
            key_body = key
        for ch in key_body:
            if ch == " ":
                letters.append(f"[ {ZWNJ}]+")
            else:
                letters.append(_LETTER_ALTS.get(ch, re.escape(ch)) + f"[{DIACRITICS}]*")
        parts.append((len(key), "".join(letters)))
    if not parts:
        result = (None, by_key)
    else:
        alt = "|".join(p for _, p in sorted(parts, key=lambda x: -x[0]))
        result = (re.compile(rf"(?<![{L}{ZWNJ}])(?:{alt})(?![{L}{ZWNJ}])"), by_key)
    _PHRASE_CACHE[corpus.version] = result
    return result


def _check_phrases(c: _Collector, corpus: Corpus) -> None:
    pattern, by_key = _phrase_index(corpus)
    if pattern is None:
        return
    strip = re.compile(f"[{DIACRITICS}]")
    for m in pattern.finditer(c.text):
        found = _phrase_key(m.group())
        e = by_key.get("غیر" + found[4:] if found.startswith("غیر ") else found)
        if not e:
            continue
        msg = "تعبیری که بهتر است جایگزین شود؛ پیشنهاد: " + "/ ".join(e.get("prefer", []))
        if e.get("note"):
            msg += f" ({e['note']})"
        before = len(c.items)
        c.add("M15", m.start(), m.end(), msg, severity=e.get("level", "advisory"),
              action_class="style", force_flag=True)
        if len(c.items) > before and e.get("rule"):
            c.items[-1]["rule_ids_override"] = [e["rule"]]


_STRUCT_CACHE: dict[str, list[tuple[dict[str, Any], re.Pattern[str]]]] = {}


def _struct_patterns(corpus: Corpus) -> list[tuple[dict[str, Any], re.Pattern[str]]]:
    cached = _STRUCT_CACHE.get(corpus.version)
    if cached is not None:
        return cached
    out = []
    for e in corpus.lexicon.get("structure_patterns", {}).get("entries", []):
        rx = e["pattern"].replace("_", f"[ {ZWNJ}]+")
        out.append((e, re.compile(rf"(?<![{L}{ZWNJ}])(?:{rx})(?![{L}{ZWNJ}])")))
    _STRUCT_CACHE[corpus.version] = out
    return out


def _check_structures(c: _Collector, corpus: Corpus) -> None:
    """M16: sentence-shape patterns typical of translated or machine Persian. Flags only.

    In a pattern, "_" stands for one or more spaces or half-spaces. An entry with
    "per_paragraph": n fires only from the n-th match inside one paragraph on.
    """
    paras = [m.start() for m in re.finditer(r"\n\s*\n", c.text)]
    for e, rx in _struct_patterns(corpus):
        need = e.get("per_paragraph", 1)
        seen: dict[int, int] = {}
        for m in rx.finditer(c.text):
            para = sum(1 for b in paras if b < m.start())
            seen[para] = seen.get(para, 0) + 1
            if seen[para] < need:
                continue
            if any(f["check"] == "M15" and f["start"] < m.end() and m.start() < f["end"] for f in c.items):
                continue  # already flagged as a listed expression
            before = len(c.items)
            c.add("M16", m.start(), m.end(), e["message"], severity=e.get("level", "advisory"),
                  action_class="style", force_flag=True)
            if len(c.items) > before and e.get("rule"):
                c.items[-1]["rule_ids_override"] = [e["rule"]]


def check(
    text: str,
    *,
    profile_id: str | None = None,
    protected_spans: list[dict[str, Any]] | None = None,
    corpus: Corpus | None = None,
) -> dict[str, Any]:
    corpus = corpus or load()
    detected = detect_protected(text)
    protected = [*(protected_spans or []), *detected]
    profile = corpus.profiles.get(profile_id or "", {})
    mech = profile.get("mechanics", {})
    patch_checks = set(mech.get("patch", DEFAULT_PATCH_CHECKS)) if profile_id else set(DEFAULT_PATCH_CHECKS)
    off = set(mech.get("off", []))
    c = _Collector(text, protected, patch_checks, off)
    for fn in (_check_letters, _check_digits, _check_punct, _check_spaces, _check_zwnj, _check_affixes,
               _check_marks, _check_hamza_he, _check_brackets):
        fn(c)
    _check_variants(c, corpus)
    _check_phrases(c, corpus)
    _check_structures(c, corpus)
    rule_map: dict[str, list[str]] = {}
    for rid, rule in corpus.rules.items():
        for chk in rule.get("checks", []):
            rule_map.setdefault(chk, []).append(rid)
    items = sorted(c.items, key=lambda f: (f["start"], f["end"], f["check"]))
    for f in items:
        f["rule_ids"] = f.pop("rule_ids_override", None) or sorted(rule_map.get(f["check"], []))
    accepted: list[tuple[int, int]] = []
    auto_set: list[dict[str, Any]] = []
    for f in items:
        cp = f["candidate_patch"]
        if cp:
            cp["rule_ids"] = f["rule_ids"]
        if f["action"] != "patch":
            continue
        a, b = cp["start"], cp["end"]
        clash = any((a < e and s0 < b) or (a == b == s0) or (a == s0 and b == e) or (a == b == e) or (s0 == e == a)
                    for s0, e in accepted)
        if clash:
            f["action"] = "flag"
            f["message"] += " (هم‌پوشان با اصلاح دیگری؛ پس از اعمال آن دوباره بررسی کنید)"
            continue
        accepted.append((a, b))
        auto_set.append({"patch_id": f"m{len(auto_set) + 1}", **cp, "action_class": f["action_class"]})
    omitted = max(0, len(items) - MAX_FINDINGS)
    return {
        "text_revision": revision_of(text),
        "offset_unit": "unicode_code_points",
        "mechanics_version": MECHANICS_VERSION,
        "complete_scan": omitted == 0,
        "findings": items[:MAX_FINDINGS],
        "findings_omitted": omitted,
        "checked_categories": [f"M{n:02d}" for n in range(1, 17) if f"M{n:02d}" not in off],
        "resolved_protected_spans": protected_spans or [],
        "detected_protected_spans": detected[:256],
        "detected_protected_spans_omitted": max(0, len(detected) - 256),
        "auto_patch_set": auto_set,
        "note": "یافته‌نشدن خطا به معنای درستی کامل متن نیست؛ فقط بررسی‌های مکانیکی فهرست‌شده انجام شده است.",
    }
