# Changelog

## Unreleased

- Sources: rules may now also cite journal articles and editing columns. Eight are added to `corpus/sources.json`; a human editor checked each cited finding against the article. The rule book marks any article source that is not yet checked (`human_checked: false`).
- Rules: GRM-038 gains corpus data on subject pronouns (18% of subjects in writing, 27% in speech) and keeps contrastive and topic-shift pronouns. STY-003 covers a verbal-noun subject that has its own actor and an evaluative predicate («... بدیهی است»); generic infinitives stay. GRM-014 adds corpus data on agentless passives and rejects «توسط» for an instrument. GRM-037 item (5): «نباید عجیب باشد» for a plain statement is suggested for a simpler form, after asking the author; «باید» of obligation, inference and scheduled expectation stays. STY-005 says the cleft «(این) او بود که» is attested and not a calque, and keeps established structures. USG-023 adds «به هر حال» for *however*, but keeps it for «در هر صورت». USG-014 lists more colloquial forms and guards «روبه‌رو». PUN-014: no ellipsis after «و غیره»; an ellipsis that marks a cut in a quotation stays. STY-018 routes these signs.

## 0.2.2

Fixes from two red-team reviews.

- Skill: «بازنویسی» now means one thing (rewrite, only on request); naturalizing rebuilds sentences and paragraph links but keeps the order of points. The literary-text exception now follows each rule's own exception. Protected content includes religious, legal and old texts. Rebuild step 4 keeps short evidentials and checks a sentence before deleting it. The evidence class says how to cite a rule, not whether to apply it.
- Rules: GRM-037 drops only stacked hedges that mean the same; its «باید … شده باشد» example now shows the action did not happen. GRM-016 no longer picks a reading for the author, and offers «کم‌کم + مضارع» and «تحت درمان». STY-020 keeps «می‌توان گفت» as a hedge. DSC-005 reports in copyedit and fixes in naturalize. USG-015 allows emphatic «هم هست». USG-024 keeps operational definitions. GRM-014 half-space fixed.
- Checker: linear time on hostile input (a 12,000-character text could take 20 seconds); tool calls run off the event loop. Auto patches next to a URL or code now validate; the auto patch set is capped at 256. Arabic letters in a cited word are flagged, not patched. A half-space before « ها» is no longer deleted. A double space that looks like a verse gap is flagged. M16 now catches «در حال بررسیِ …», «در حال تبدیل شدن به», «را به عنوان … در نظر گرفتند» and «در دنیای امروز».
- Server: over HTTP the server keeps no texts between calls (send `original_text`), so clients cannot read or evict each other's texts. Tool schemas have no `$ref`. ChatGPT `search`/`fetch` report bad input as errors and link to the rule's anchor. A text over the limit returns `limit_exceeded`. The `naturalizing` edit level is accepted.
- CLI: `check` and `search` exit 1 on an error; a non-UTF-8 file gives a clear message.
- Release: a manual run publishes only from main; all version fields are checked; the corpus version follows pyproject.
- README: links work on PyPI.

## 0.2.1

- The rules have been reviewed by a human editor. Rule status is now `reviewed`, and the draft notices are removed from the README, the skill, the server and the rule book (now `docs/RULEBOOK.md`).

## 0.2.0

- Added Samiee «نگارش و ویرایش» as a source. New families: DSC (paragraphs and discourse), TRM (numbers, dates, citations, notes, names). Punctuation and style rules are now sourced where the book supports them.
- Sentence-structure rules: tense in reports and narration (GRM-036), mood (GRM-037), redundant subjects and pronouns (GRM-038), natural word order (GRM-039), signs of machine and translated Persian (STY-018), building the sentence on its real subject (STY-019), saying the claim directly (STY-020), paragraph development (DSC-005), sentence-level calques (USG-023), native compound verbs (USG-024). GRM-016 no longer recommends «در حال … است».
- Skill: copyedit now includes a sentence pass with proposed rebuilds; a new naturalize level applies them. New procedures for rebuilding a sentence and for writing Persian.
- Checker: M15 (listed expressions to replace) and M16 (sentence shapes typical of machine Persian). Both flag only.
- Packaged as a Claude Code plugin (skill and MCP server) with a marketplace manifest.
- USG-022 is retired (merged into STY-012 and STY-013).

## 0.1.0

- First build: orthography, grammar, usage, punctuation, style and integrity rules; mechanical checks M01 to M14; MCP server.
