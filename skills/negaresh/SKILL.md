---
name: negaresh
license: MIT
description: Write, edit, proofread, naturalize, rewrite or review Persian (Farsi) text with a sourced rule set - sentence structure and natural Persian word order, verb and tense choice, removing translated or machine-like (AI) Persian, paragraph flow, grammar, usage, Academy orthography (نیم‌فاصله / ZWNJ), punctuation and meaning preservation. Use when the user asks to ویرایش، روان‌سازی، طبیعی‌تر کردن، بازنویسی، غلط‌گیری، نمونه‌خوانی or نگارش a Persian text, says a Persian text sounds translated or machine-written, asks whether a Persian spelling or construction is correct (درست‌نویسی، املای درست، دستور خط), or wants Persian text written to a formal standard. Not for translation quality review, poetry scansion or Arabic text.
---

# negaresh: Persian writing guide

## What you have

- `references/rules-index.md`: one line for each rule (ID, Persian title, English title). Read it first.
- `references/rules-<category>.md`: the full rules. Categories: orthography (ORT), punctuation (PUN), grammar (GRM), usage (USG), style (STY), discourse (DSC), terminology (TRM), integrity (INT).
- Start every sentence-level job with STY-018: a short list of the signs of translated and machine Persian, each pointing to the rule that fixes it.
- `references/workflow.md`: the editing procedure, edit levels and the report format.
- MCP server `negaresh` (optional), five tools: `search_rules`, `get_rule`, `get_profile`, `check_mechanics`, `validate_patches`. Tool names can have a client prefix; match on the last part of the name.

Each rule has a severity (`error`, `convention`, `advisory`) and an evidence class:

- `sourced`: comes from one of five books (the Academy's «دستور خطّ فارسی» 1401, three grammars, and Samiee's «نگارش و ویرایش»). You can cite the source line of the rule. Parts marked «پیشنهاد ویراستاری» inside a sourced rule are editorial advice. Some sourced rules also cite a journal article or editing column (a corpus study, or a published edit); cite such a finding as that study's result, not as an Academy or book rule.
- `editorial_synthesis`: editorial practice with no book in this set behind it (for example STY-018). Never present these as Academy or book rules.

The evidence class only tells you how to cite a rule. How firmly to apply it comes from its severity: an `editorial_synthesis` rule with severity `convention` (for example INT-004, PUN-011) is applied like any other convention.

## Procedure

1. **Find the task.** One of:
   - **write** (نگارش): you produce Persian from scratch or from notes. Follow "Writing Persian" below from the first sentence.
   - **proofread** (غلط‌گیری): characters, spacing, spelling, punctuation only.
   - **copyedit** (ویرایش زبانی): the above, plus grammar and usage, plus a **sentence pass**: for each sentence that shows a sign from STY-018, propose a rebuilt sentence in the report (do not apply it silently). Samiee's own copyedits rebuild whole sentences; a copyedit that only swaps words leaves the translated skeleton.
   - **naturalize** (روان‌سازی): the user asks to make the text روان، طبیعی or «کمتر ترجمه‌ای/ماشینی». Rebuild sentences, and the links between sentences in a paragraph, from their meaning (see "Rebuilding a sentence"), keeping content, the order of points, claim strength, hedges, actors, numbers and names (INT-001 to INT-005).
   - **rewrite** (بازنویسی): only when the user asks for it in so many words. Naturalize, and also reorder or reorganize paragraphs and sections. If a copyedit or naturalize job seems to need this, say so in the report and ask; do not do it unasked (INT-005).
   - answer a question about a rule.
   If the user did not say, copyedit. If most paragraphs show three or more STY-018 signs, say so in the report and offer naturalizing.
2. **Find the profile.** One of: academic, professional, journalistic, general_nonfiction, literary, conversational, technical_instructional, persuasive_marketing_social. If unclear, use general_nonfiction. In literary and conversational text, fix only clear typing errors; if the user asks to naturalize such text, keep its images, voice and rhythm, follow each rule's own exception for literary and colloquial text, and propose rather than apply where a rule says "suggest only" for this profile (INT-005). Never make colloquial text formal (USG-014, STY-007).
3. **Mark protected content** before you edit (INT-003, INT-004): direct quotations, verse, religious text (آیه، حدیث، دعا), old texts quoted as they stand, legal and contract wording, code, URLs, names, numbers, dates and citations. Do not change their wording or values. In running text you may still convert Latin digits to Persian digits where INT-004 allows it; never change a number's value.
4. **Paragraph pass** (copyedit and naturalize). For each paragraph, note in one line its point and how it develops it (DSC-005). A missing point, a summary closer that repeats the opening, or the same shape in every paragraph goes to the report (copyedit) or is fixed (naturalize).
5. **Short text (light path).** For a short text or one question: read the index, open the one or two rule files you need, edit, and report. No tool call is necessary.
6. **Long or important text (audited path).** If the MCP server is available:
   - Call `get_profile` for the profile.
   - Call `check_mechanics` with the text (limit 12,000 code points for each call; split longer text at paragraph borders, and finish check and validation of one chunk before you send the next, because the server keeps only the last 8 texts). It returns findings with offsets in Unicode code points, a `text_revision`, and `auto_patch_set`.
   - `auto_patch_set` holds the low-risk character fixes (Arabic ي/ك, presentation forms, spacing around punctuation, double spaces, wrong half-spaces), already free of overlaps and with rule IDs. They are candidates, not proof: before you apply them, look at each one that falls inside a quotation, verse, a number, a name or code, and drop it if it changes that content.
   - Findings with `action: "flag"` need your judgement; read the cited rule first. Half-space fixes after «می» and before «ها/تر/ترین» (M08) are flags with a ready candidate patch: apply them after a glance at the word. Variant spellings (M14) and listed expressions (M15) are suggestions only; never apply them silently. M16 flags sentence shapes typical of translated or machine Persian («مورد … قرار گرفت», «گردید», «در حالِ … است», stacked opening connectors, report frames, «را به عنوان»); each points to the rule that says how to rebuild the sentence. Some shapes are flagged only when they repeat: report frames and opening connectors from the second in a paragraph, «خواهد» from the third. A single one is not a fault, and the checker stays silent on it. Treat M15 and M16 as pointers to a rebuild, not as word swaps.
   - If `complete_scan` is false or `findings_omitted` is above 0, the list is cut. Send a shorter chunk; do not tell the user that all mechanical fixes were made.
   - The checker sees characters, listed expressions and a few sentence shapes only. No finding means the text is clean of those; it does not mean the sentences are natural Persian. It cannot judge grammar, usage or style. Do those yourself with the rule files or `search_rules` / `get_rule`.
   - Before you give the user the edited text, send all your changes to `validate_patches` with the `text_revision`. Fix each issue it reports. It proves that patches apply cleanly and leave protected spans (URLs, e-mail addresses, code, your own protected spans) unchanged. It does not prove that meaning is kept; that is your job (INT-001, INT-002). If it answers `needs_context`, call `check_mechanics` again on the exact same chunk and retry; do not try to retype the original text.
7. **Without the MCP server**, do the same checks by hand from `rules-orthography.md` and `rules-punctuation.md`, and tell the user that the mechanical check did not run.
8. **Report.** Give the edited text, then the list of changes that are not plain mechanical fixes, each with a rule ID. Separate corrections (`error`) from conventions and from suggestions (`advisory`). Use the format in `references/workflow.md`.

## Rebuilding a sentence

Use this for the sentence pass, for naturalizing, and when you write.

1. Write the facts of the sentence: who does what, to what, when, with what strength (hedges, «برخی», «احتمالاً»), and the numbers and names.
2. Pick the real subject: the person or thing that acts, named in the text as the doer of this same action (STY-019). Promoting that actor is allowed. Inventing one is not, and neither is carrying an actor over from another action: if the text says «مدیریت اقدام کرد» and then «رضایت سنجیده شد», it does not say who measured satisfaction, so that clause keeps no actor (INT-002). Where no actor is given, a passive or an impersonal form is the right choice.
3. Give each action a finite verb; turn verbal nouns and «مورد … قرار گرفتن / انجام / صورت گرفتن» into verbs (STY-003, STY-004); use the native compound verb (USG-024).
4. Cut frames and announcements; say the claim directly (STY-020). Keep a short evidential when the text reports a source or an inference («بنابر یافته‌ها»، «به نظر می‌رسد»، «می‌توان گفت»). Before you delete a whole sentence, check that it carries no claim, number or hedge that appears nowhere else (INT-001).
5. Put the parts in Persian order: subject early, at most one setting phrase before it, verb near the end, a heavy part after the verb where that reads better (GRM-024, GRM-039). Do not repeat what the verb ending already says (GRM-038). Join sentences by content; use a connector only at a real turn (GRM-029). Remove sentence-level calques (USG-023).
6. Choose tense and mood by meaning (GRM-016, GRM-036, GRM-037).
7. Check the new sentence against the facts from step 1, not against the old wording.
8. In the audited path, run `check_mechanics` on the new text, not on the old one. For a rebuilt sentence, send one patch that replaces the whole sentence; do not combine it with `auto_patch_set` items from the old text inside the same span.

## Writing Persian

When you write, apply the same moves from the start: a real subject and a finite verb for each action; no opening frames («لازم به ذکر است», «در دنیای امروز»); no connector at the head of every sentence; present tense for actions in progress and for the near future (GRM-016, GRM-036); no subject pronouns that the verb ending already carries (GRM-038); varied sentence length (DSC-004); one point per paragraph, developed with an example, a reason or a comparison (DSC-005); established Persian idiom rather than a translated image (STY-014). Read STY-018 before you start, and read your draft once against it before you hand it over.

## Hard limits

- Do not change meaning, strength of a claim, hedges, actors, numbers or names (INT-001 to INT-004). Rebuilding a sentence that keeps all of these is not a change of meaning.
- Where a rule says two forms are both correct (for example GRM-002, GRM-013), do not change one to the other. Report inconsistency only.
- If a sentence has two readings, ask. Do not choose for the author.
- Do not cite a rule that is not in this set. If no rule covers the point, say that it is your own judgement.
- Write the half-space as U+200C. Do not put it after ا د ذ ر ز ژ و (ORT-001).
- Answer in the language the user wrote in. Rule text is Persian; explain it in English if the user writes English.
