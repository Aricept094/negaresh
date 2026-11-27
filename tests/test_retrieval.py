"""Rank the intended rule for editor questions before authoring new aliases."""
import pytest

from negaresh import api


REVIEW_QUESTIONS = [
    ("ORT-045", "برای سقف گنبد تاق بنویسم یا طاق؟"),
    ("INT-009", "دو سند برای سال تأسیس عدد متفاوتی نوشته‌اند"),
    ("GRM-050", "آیا هرگز باید با فعل منفی بیاید؟"),
    ("GRM-049", "بچه‌ها خوششان آمد یا آمدند؟"),
    ("DSC-010", "چراغ سمت راست کدام قطعه است؟"),
    ("GRM-051", "آیا تأیید مدیر برای پذیرش کافی است یا فقط شرط لازم است؟"),
    ("INT-010", "تیتر خبر وعده را قطعی جلوه می‌دهد"),
    ("DSC-011", "چطور برای نمره‌ای که به کتاب می‌دهم دلیل بیاورم؟"),
    ("TRM-011", "آیا ده پانزده نفر یعنی حداکثر پانزده نفر؟"),
    ("GRM-046", "مدیر مدرسه و درمانگاه یک نفر است یا دو نفر؟"),
]

ADDITIONAL_QUESTIONS = [
    ("INT-009", "سال انتشار در شناسنامه و در فهرست کتابخانه یکی نیست. کدام تاریخ را ثبت کنم؟"),
    ("GRM-050", "«هرگز» در جملهٔ پرسشی هم فعل را منفی می‌کند؟"),
    ("INT-010", "در متن خبر فقط از احتمال ادغام می‌گویند ولی از تیتر برمی‌آید که ادغام انجام شده است."),
    ("DSC-011", "نقد فیلم را با چه معیاری بنویسم تا خواننده بفهمد چرا این امتیاز را داده‌ام؟"),
    ("GRM-051", "داشتن مدرک برای ثبت‌نام لازم است. آیا از این جمله برمی‌آید که هر دارندهٔ مدرک پذیرفته می‌شود؟"),
    ("ORT-045", "املای طاق در شرح معماری بنا چیست؟"),
]


@pytest.mark.parametrize("questions,first,five", [(REVIEW_QUESTIONS, 8, 9), (ADDITIONAL_QUESTIONS, 4, 5)])
def test_question_retrieval(questions, first, five):
    ranks = {}
    for target, query in questions:
        env, error = api.call("search_rules", {"query": query, "context": {"profile_id": "professional"}, "limit": 5})
        assert not error
        ids = [rule["id"] for rule in env["data"]["results"]]
        ranks[query] = ids.index(target) + 1 if target in ids else None
    assert sum(rank == 1 for rank in ranks.values()) >= first, ranks
    assert sum(rank is not None for rank in ranks.values()) >= five, ranks
