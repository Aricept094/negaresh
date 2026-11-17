"""Precision and recall of the mechanical checks on realistic sentences.

The safety property: on correct text the checker may raise flags, but it must
never offer an automatic patch. Cases come from the red-team run of 2026-11-17.
"""

import pytest

from negaresh import api

Z = "‌"

CORRECT = [
    f"در این پژوهش، داده{Z}ها با روش مطالعهٔ میدانی گردآوری شد.",
    f"نتایج نشان می{Z}دهد که میزان خطا کاهش یافته است.",
    "طایر قدسی در شعر حافظ نماد روح است.",
    f"مطالعه{Z}ای که در سال ۱۴۰۱ انجام شد، دو گروه را مقایسه کرد.",
    f"میانگین سنی شرکت{Z}کنندگان ۳۴٫۵ سال بود (انحراف معیار: ۲٫۱).",
    "وزیر امور خارجه روز دوشنبه به مسکو سفر کرد.",
    f"رئیس{Z}جمهور گفت: «ما به مذاکره ادامه می{Z}دهیم.»",
    f"بند (الف) تبصرهٔ ۲ این ماده اجرا می{Z}شود.",
    "۱) خواهان\n۲) خوانده\n۳) وکیل",
    "برای نصب، دستور `pip install negaresh` را اجرا کنید.",
    "فایل‌های با پسوند .py را در پوشهٔ src بگذارید.",
    "نشانی سایت https://example.com/fa?q=سلام&x=1 است.",
    "با ما از راه info@example.ir در تماس باشید.",
    "فناوری .NET را مایکروسافت ساخته است.",
    "مقدار p برابر .05 بود.",
    "در فایل config.yaml مقدار timeout: 30 را تنظیم کنید.",
    "دستور زیر را اجرا کنید:\n    python -m negaresh  --help\n",
    "کتاب «The Old Man and the Sea» اثر همینگوی است.",
    f"بشنو این نی چون شکایت می{Z}کند    از جدایی{Z}ها حکایت می{Z}کند",
    "ساقیا برخیز و درده جام را\nخاک بر سر کن غم ایام را",
    "بیا اینجا ها! نگفتم بهت؟",
    "ها ها ها، چه بامزه!",
    "قال رسول الله: «إنما الأعمال بالنيات».",
    "آیهٔ ﴿إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ﴾ را خواند.",
    "قیمت این کالا ۵۰۰۰ ﷼ است.",
    "پیامبر ﷺ فرمود.",
    "سطر اول  \nسطر دوم",
    "لباسم تر شد.",
    "ساعت ۱۰:۳۰ جلسه آغاز شد.",
    "منبع: [۱] و [۲].",
    f"دکتر میرزایی میزبان این نشست بود و میدانی برای گفت{Z}وگو فراهم کرد.",
    "Persian ZWNJ in Hindi: क्‌ष",
    "هوش مصنوعی :)",
]

# (text, check that must fire)
ERRORS = [
    ("او هر روز به مدرسه می رود.", "M08"),
    ("ما نمی دانیم.", "M08"),
    ("این کار را میکنم.", "M08"),
    ("نمی توان این را پذیرفت.", "M08"),
    ("این موضوع مهم می باشد.", "M08"),
    ("صدایش را می شنود.", "M08"),
    ("او برمی گردد.", "M08"),
    ("کتاب ها را خواندم.", "M08"),
    ("بزرگ ترین شهر.", "M08"),
    ("علي به كتابخانه رفت.", "M01"),
    ("موسى آمد.", "M01"),
    ("سلام ،خوبی؟", "M04"),
    ("سلام،خوبی؟", "M04"),
    ("فارسی ,انگلیسی", "M05"),
    ("پایان .", "M04"),
    ("گفت « سلام » و رفت.", "M13"),
    ("«سلام", "M13"),
    ('او گفت "سلام".', "M09"),
    ("قیمت ٥٠ تومان است.", "M03"),
    ("سال 1402 و ۱۴۰۳", "M03"),
    ("ســلام", "M10"),
    ("سلام‏ دنیا", "M11"),
    (f"کتاب{Z}{Z}ها", "M07"),
    ("این اطاق بزرگ است.", "M14"),
    ("ﻻ", "M02"),
]


def _check(text, profile="academic"):
    env, err = api.call("check_mechanics", {"text": text, "context": {"profile_id": profile}})
    assert not err
    return env["data"]


@pytest.mark.parametrize("text", CORRECT)
def test_no_automatic_patch_on_correct_text(text):
    for profile in ("academic", "general_nonfiction", "literary", "conversational"):
        patches = [f for f in _check(text, profile)["findings"] if f["action"] == "patch"]
        assert not patches, (profile, [(f["check"], f["text"], f["candidate_patch"]) for f in patches])


@pytest.mark.parametrize("text,check", ERRORS)
def test_common_error_is_found(text, check):
    assert check in {f["check"] for f in _check(text)["findings"]}


def test_arabic_quotation_is_flag_only():
    data = _check("قال رسول الله: «إنما الأعمال بالنيات».", "literary")
    assert data["findings"] and all(f["action"] == "flag" for f in data["findings"])


def test_auto_patch_set_validates_cleanly():
    text = "سلام  .  این متن ، با كتاب و علي نوشته شد ;آری"
    data = _check(text)
    assert data["auto_patch_set"]
    env, err = api.call("validate_patches", {"text_revision": data["text_revision"], "patches": data["auto_patch_set"]})
    assert not err and env["data"]["valid"], env["data"]["issues"]
    assert not env["data"]["warnings"]


def test_patch_touching_protected_span_is_rejected():
    text = "نشانی http://x.ir/a b"
    data = _check(text)
    url_end = text.index(" b")
    for patch in ({"start": url_end, "end": url_end, "before": "", "after": "Q"},
                  {"start": url_end, "end": url_end + 1, "before": " ", "after": ""}):
        env, _ = api.call("validate_patches", {"text_revision": data["text_revision"],
                                               "patches": [{"patch_id": "x", **patch}]})
        assert not env["data"]["valid"]


def test_insertion_at_end_of_replacement_is_rejected():
    text = "کتاب ها"
    data = _check(text)
    env, _ = api.call("validate_patches", {"text_revision": data["text_revision"], "patches": [
        {"patch_id": "a", "start": 4, "end": 5, "before": " ", "after": Z},
        {"patch_id": "b", "start": 5, "end": 5, "before": "", "after": "X"},
    ]})
    assert not env["data"]["valid"]


def test_long_finding_text_is_shortened():
    data = _check("الف" + Z * 500 + "ب")
    assert all(len(f["text"]) <= 160 for f in data["findings"])


SAMIEE_CONVENTIONS = [
    "این را گفت . . . و رفت.",
    "چه گفت... ؟",
    "نشانه‌های «، ؟!» را ببینید.",
    "(Lyons 1977, p. 45) را ببینید؛ نیز ۱۲ مورد دیگر.",
    'در کتاب "Persian Grammar" آمده است.',
]


@pytest.mark.parametrize("text", SAMIEE_CONVENTIONS)
def test_samiee_conventions_are_not_patched_or_flagged_as_digits(text):
    data = _check(text)
    assert not [f for f in data["findings"] if f["action"] == "patch"]
    assert not [f for f in data["findings"] if f["check"] in ("M03", "M09")]


# M15 (usage phrases): flags only, and not on ordinary senses of the same words
M15_SILENT = [
    "جهت ثابتی نداشت.",
    "نظرات داوران را خواندیم.",
    "این نمودار نشانگر روند افزایش است.",
    "درمان طولانی‌مدت لازم بود.",
    "این دارو غیر قابل استفاده است.",
    "آن نمونه را به آزمایشگاه فرستادیم.",
    "راننده مسافران را پیاده کرد.",
    "او می‌رود که نان بخرد.",
    "او به نظر بیمار می‌نماید.",
    "این خانه از نعمت آب برخوردار است.",
    "او را به عنوان رئیس برگزیدند.",
    "خبرها را از رادیو دنبال کردم.",
    "او سال‌ها برای فرزندانش رنج می‌برد.",
]
M15_FIRES = [
    ("این مقاله توسط او نوشته شد.", "GRM-014"),
    ("این موضوع مورد بررسی قرار گرفت.", "USG-021"),
    ("در رابطه با این موضوع سخن گفت.", "USG-009"),
    ("این ادعا غیر قابل انکار است.", None),
    ("این ادعا غیرقابل انکار است.", None),
    ("این شهر از آلودگی برخوردار است.", "USG-018"),
    ("جهت اطلاع شما نوشتم.", "USG-009"),
    ("طرح را پیاده کردند.", "USG-016"),
    ("گروه به چکاد رسید.", "STY-012"),
]


@pytest.mark.parametrize("text", M15_SILENT)
def test_m15_silent_on_ordinary_words(text):
    assert not [f for f in _check(text)["findings"] if f["check"] == "M15"]


@pytest.mark.parametrize("text,rule", M15_FIRES)
def test_m15_flags_phrase(text, rule):
    hits = [f for f in _check(text)["findings"] if f["check"] == "M15"]
    assert hits and all(f["action"] == "flag" for f in hits)
    if rule:
        assert any(rule in f["rule_ids"] for f in hits)


def test_m15_off_in_literary_profile():
    assert not [f for f in _check("این مقاله توسط او نوشته شد.", "literary")["findings"] if f["check"] == "M15"]


# M16 (sentence shapes of translated or machine Persian): flags only, silent on natural prose
M16_FIRES = [
    ("نتایج حاصل از تحلیل داده‌ها نشان داد که اضطراب کاهش یافت. یافته‌ها حاکی از آن بود که سن مؤثر است.", "STY-020"),
    ("لازم به ذکر است که جلسه لغو شد.", "STY-020"),
    ("این روش مورد بررسی دقیق قرار گرفت.", "STY-004"),
    ("جلسه روز دوشنبه برگزار گردید.", "STY-004"),
    ("قیمت‌ها در حال افزایش است.", "GRM-016"),
    ("او را به عنوان مدیر کل برگزیدند.", "USG-024"),
    ("فروش به طور قابل توجهی افزایش یافت.", "USG-024"),
    ("سن نقش مهمی در این زمینه ایفا می‌کند.", "USG-023"),
    ("این ابزار کمک می‌کند تا وقت کمتری صرف شود.", "USG-023"),
    ("همچنین داده‌ها گردآوری شد. علاوه بر این، پرسش‌نامه پر شد.", "GRM-029"),
    ("نکتهٔ مهم این است که بودجه کم است.", "STY-020"),
    ("قیمت‌ها در حالِ افزایش است.", "GRM-016"),
    ("بررسی‌های لازم صورت گرفت.", "STY-004"),
    ("شرکت قصد دارد تا خدمات تازه‌ای ارائه کند.", "USG-023"),
    ("در این راستا، کارگاهی برگزار شد.", "GRM-029"),
    ("او را به عنوان بهترین بازیکن سال معرفی کردند.", "USG-024"),
]
M16_SILENT = [
    "پس از مداخله، میانگین نمرهٔ اضطراب کاهش یافت؛ این کاهش در زنان شدیدتر بود.",
    "در حال حاضر مدیر بخش است.",
    "در حالی که باران می‌بارید، به خانه رسیدیم.",
    "او به خانه برگردد بهتر است.",
    "داده‌ها گردآوری شد. پرسش‌نامه را هم شرکت‌کنندگان پر کردند. همچنین مصاحبه‌ای انجام شد.",
    "فردا جلسه برگزار می‌شود و نتیجه را خواهیم دید.",
    "مشکل این است که بودجه کم است.",
    "پرسش این بود که چه کسی مسئول است.",
    "پرونده هنوز در حال بررسی است.",
    "این کشور در حال توسعه است.",
    "امیدوارم او به وطن باز گردد.",
    "او را به عنوان سفیر به پاریس فرستادند.",
    "نقش اول را بازیگری جوان بازی کرد.",
    "پدرم به من کمک کرد تا صبح درس خواندم.",
]


@pytest.mark.parametrize("text,rule", M16_FIRES)
def test_m16_flags_machine_shape(text, rule):
    hits = [f for f in _check(text)["findings"] if f["check"] == "M16"]
    assert hits and all(f["action"] == "flag" for f in hits)
    assert any(rule in f["rule_ids"] for f in hits), [(f["text"], f["rule_ids"]) for f in hits]


@pytest.mark.parametrize("text", M16_SILENT + CORRECT)
def test_m16_silent_on_natural_prose(text):
    assert not [f["text"] for f in _check(text)["findings"] if f["check"] == "M16"]


def test_m16_off_in_literary_profile():
    assert not [f for f in _check("جلسه برگزار گردید.", "literary")["findings"] if f["check"] == "M16"]
