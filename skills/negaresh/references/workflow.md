# Editing workflow and report format

## Edit levels

| Level | Persian name | What changes | Rule families |
| --- | --- | --- | --- |
| proofreading | غلط‌گیری / نمونه‌خوانی | spelling, spacing, half-space, punctuation marks, characters | ORT, PUN |
| copyediting | ویرایش زبانی | the above, plus grammar and usage errors and consistency; a sentence pass that **proposes** rebuilt sentences for STY-018 signs; a paragraph pass that reports (DSC-005) | ORT, PUN, GRM, USG, TRM, STY-006; STY-018 and the rules it points to, as proposals |
| naturalizing | روان‌سازی | the above, with sentence rebuilds and paragraph links (connectors, repeated closers) **applied**, keeping the order of points; on request, or when the user says the text sounds translated or machine-written | all, with INT rules first |
| substantive | بازنویسی | naturalizing plus reordering and reorganizing paragraphs and sections; only when the user asks for بازنویسی (INT-005) | all, with INT rules first |

At every level the INT rules apply.

When the user supplies the source alongside a Persian translation for editing, use INT-007 to check meaning and scope the report to the passages compared.

## Order of work

For naturalizing and substantive editing, rebuild first and polish after, because a rebuilt sentence makes earlier character fixes useless:

1. Protected content.
2. Per paragraph: one line for its point and its mode of development (DSC-005), and the list of facts (actors, numbers, hedges, names).
3. Rebuild each sentence from the facts ("Rebuilding a sentence" in SKILL.md; STY-018 lists the signs).
4. Run `check_mechanics` on the new text and apply its fixes (steps 2 to 7 of the list below).
5. Compare the new text with the fact list (INT-001, INT-002), not with the old wording.

For proofreading and copyediting:

1. Protected content: mark quotations, verse, religious and legal text, code, URLs, names, numbers, dates and citations (INT-003, INT-004).
2. Characters: Arabic ي/ك, digits, invisible characters (PUN-010 to PUN-012).
3. Spacing and half-space (ORT-001 to ORT-019, ORT-028 to ORT-043).
4. Spelling: hamza, tanvin, variant spellings (ORT-020 to ORT-027, ORT-042).
5. Punctuation (PUN-001 to PUN-009, PUN-013 to PUN-018).
6. Grammar: agreement, «را», participial verbs, ellipsis, negation (GRM).
7. Usage: plurals, tanvin on Persian words, prepositions, register (USG).
8. Sentence pass (copyediting): for sentences with STY-018 signs, write a rebuilt version as a proposal. Paragraph pass: note missing points, summary closers and same-shape paragraphs (DSC-005, DSC-004).
9. Last read: compare with the original for meaning, actors, hedges and numbers (INT-001, INT-002).

## Severity and what to do

- `error`: correct it, and list it.
- `convention`: correct it in formal profiles; keep the author's consistent choice where a house style is in force.
- `advisory`: suggest it; do not apply it silently in proofreading.

## Report format

Give the edited text first. Then:

```
تغییرها
۱. «گزارشات» ← «گزارش‌ها» — USG-002 (پیشنهاد)
۲. «کتابی را که خریدم گم شد» ← «کتابی که خریدم گم شد» — GRM-009 (خطا)

اصلاح‌های مکانیکی: ۱۴ مورد (نیم‌فاصله، فاصلهٔ نشانه‌ها، ی/ک عربی)

پرسش از نویسنده
- «پسر هنرمند»: مقصود پسرِ هنرمند است یا پسری که هنرمند است؟ (GRM-026)
```

For a rebuilt sentence (proposed or applied), give the pair and the moves:

```
جملهٔ ۳
پیش: «تحلیل رگرسیون مورد استفاده قرار گرفت تا نقش متغیرها مورد بررسی قرار گیرد.»
پس: «برای سنجیدن سهم متغیرها از رگرسیون استفاده شد.»
کارها: فعل به‌جای «مورد … قرار گرفتن» (STY-004)؛ هدف پیش از فعل (GRM-039)؛ کنشگر افزوده نشد (INT-002)
```

Rules for the report:

- Count plain mechanical fixes; do not list each one unless the user asks.
- Give a rule ID for each listed change. If no rule covers it, write «نظر ویراستار».
- Mark rules of class `editorial_synthesis` as «پیشنهاد»; do not call them a rule of the Academy.
- Put open questions last. Do not resolve an ambiguity for the author.
- If the mechanical check did not run, say so.

## Calling the tools

- `check_mechanics`: `{"text": "...", "context": {"profile_id": "academic"}}`. Optional `protected_spans`: `[{"start": 10, "end": 42}]` or a locator.
- `validate_patches`: `{"text_revision": "sha256:...", "patches": [{"patch_id": "p1", "start": 7, "end": 8, "before": " ", "after": "‌", "rule_ids": ["ORT-003"]}]}`. Offsets are Unicode code points in the original text. You can pass the items of `auto_patch_set` as they are, plus your own patches with new `patch_id`s; two patches may not touch the same characters. If the server no longer holds the text (`needs_context`), run `check_mechanics` on the same chunk again and use the new `text_revision`.
- With the `negaresh` command, put the same patch objects in a JSON file and run `uvx --from "negaresh>=0.4.4" negaresh validate FILE PATCHES.json --out REVISED_FILE` on the exact file you checked; it never answers `needs_context`.
- `check_mechanics` check IDs: M01 Arabic letters, M02 presentation forms, M03 digits, M04 spacing around punctuation, M05 Latin punctuation, M06 spaces, M07 half-space misuse, M08 half-space with «می»، «ها»، «تر/ترین», M09 straight quotes, M10 kashida, M11 invisible characters, M12 mixed ezafe marks, M13 brackets and guillemets, M14 variant spellings, M15 listed expressions to replace (calques, padded or archaic expressions), M16 sentence shapes typical of translated or machine Persian (flags that point to a rebuild rule). No M15 or M16 finding does not mean the sentences are natural.
- `search_rules`: `{"query": "را پیش از که", "category": "grammar"}`. `get_rule`: `{"rule_id": "GRM-009"}`.
