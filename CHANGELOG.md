# Changelog

## 0.4.3

- Expand the corpus to 180 rules. Thirteen page-checked additions are marked as drafts. Updated examples protect quotation fidelity, causal direction, modifier scope and the distinction between promises and completed events.

- The skill runs the command as `uvx --from "negaresh>=0.4.2" negaresh …`. Plain `uvx negaresh` reuses any copy uv has cached, so a machine that had run 0.4.1 or older got a version without `validate`, `rule` and `profile`. The version floor makes uv fetch the new version once; after that it runs offline from the cache.

## 0.4.2

- The Claude Code plugin no longer starts an MCP server. Before, each open session and the desktop app kept a negaresh server (uvx, uv and two Python processes) running in the background. Now the skill runs the `negaresh` command only when it needs a check, and the command exits when it is done.
- New commands: `negaresh validate FILE PATCHES.json [--out REVISED]` (the same check as the `validate_patches` tool, on the exact file you checked), `negaresh rule RULE_ID` and `negaresh profile [PROFILE_ID]`. `negaresh check` and `validate` read UTF-8 files and stop with a clear message if a file is not UTF-8.
- SKILL.md and workflow.md explain the command path next to the MCP path. The command keeps nothing between calls, so it never answers `needs_context`.
- To keep the MCP tools in every session, add the server yourself: `claude mcp add negaresh -- uvx negaresh serve`. Other clients (Gemini CLI, Cursor, VS Code) are unchanged.

## 0.4.1

- Spelling rules checked page by page against the Academy's «دستور خطّ فارسی» (new edition). ORT-012 and ORT-041 write «به‌طوری که» with a half-space, as the book prints it. ORT-043 now covers only plural «ها» and «گر/گری» after a pronounced «ه»; the indefinite «ی» stays joined (گرهی). ORT-042 calls the non-preferred spellings non-preferred, not wrong. Page references fixed in ORT-001, ORT-021 and ORT-026; smaller fixes in ORT-008, ORT-009, ORT-015 (four more prefixes), ORT-033, ORT-035, ORT-038, ORT-039 and ORT-040. The claim that ORT-040 and ORT-041 are new in 1401 is now marked as the editor's view.
- ORT-019 and ORT-025 give the page numbers in the Anvari and Ahmadi-Givi grammar.
- Ten sentence rules checked on the book page images, not only the scanned text: DSC-006, GRM-029, GRM-036, GRM-037, GRM-038, GRM-039, STY-001, STY-005, USG-024 and USG-028. Where a rule said more than the book, the extra part is now marked as editorial advice (for example GRM-029 on «برای + مصدر», GRM-037 on «باید»ِ استنباط, USG-024 on intransitive pairs other than کردن / شدن). USG-024 cites the right page for impersonal verbs.
- Near-duplicate rules: STY-004 and STY-005 keep the principle and point to the lists in USG-016, USG-020 and USG-021; repeated examples are removed.
- Tests: a cross-rule test checks that no rule's correct example is flagged or patched under another rule.

## 0.4.0

From a review of the W3C Arabic & Persian Layout Requirements (alreq), the Unicode CLDR 49 data for Persian and a browser render test.

- Ezafe after a silent «ه»: rules, examples, profiles and the README now write «هٔ» (U+0647 U+0654), not «ۀ» (U+06C0). They look the same, but «ۀ» decomposes to Kurdish «ە» and hamza under Unicode normalization (NFD), which breaks search. ORT-019 explains this; «ۀ» is not counted as a spelling error.
- Checker (mechanics version 2):
  - M01 flags Arabic-script letters of other languages (ھ ہ ە ے ڤ and others), with the Persian letter where one exists. M02 offers the NFC form of a decomposed letter.
  - M03 and M04 check numbers written with Persian digits: «٫» for decimals and «٬» for thousands (CLDR), «٪» for «%», no space before «٪», and an advisory for a hyphen used as a minus sign. A date or version with dots is left alone.
  - M06 flags a digit glued to a unit word («۵کیلو», TRM-001). M08 puts a half-space between a Latin acronym and «ها».
  - M09 flags curly quotes (“ ”), and ‘ ’ outside «…».
  - M11 is split into tiers: direction overrides, embeddings and unbalanced isolates are flagged; LRM, RLM and balanced isolates next to Latin text or numbers, and ZWJ in abbreviations such as «ه‍.ش», are no longer flagged. A BOM inside text names U+2060. A Persian paragraph that starts with a Latin word gets an advisory.
  - M12 suggests «هٔ» for each «ۀ» and treats the two as one style when it checks mixed ezafe marks.
- Rules: PUN-003 (number separators, percent, negative numbers), PUN-007 (curly quotes), PUN-011 (letters of other languages, NFC, word ligatures are reported, not converted), PUN-012 (control characters in three tiers), TRM-001 (space between number and unit), ORT-003 («PDF‌ها»).
- Sources: W3C alreq, Unicode CLDR 49 and the Unicode Character Database. A human editor checked the cited points against the originals.
- STY-001: a list of three adjectives or nouns gets Samiee's padding test as an editorial suggestion (remove one item; if no meaning is lost, it was decoration). STY-018 points to it.
- Sentence structure, from a page-by-page review of the four grammars and Samiee (167 rules):
  - New: USG-026 («در حالی که» for a simultaneous action of the same subject: an adverb, «X که + past continuous», or «… می‌کرد که»), USG-027 (generic singular instead of a translated plural, narrow scope), DSC-006 (comparison sentences: parallel sides, correlative «همان‌قدر … که» and «بیشتر … تا», «هرچه … بیشتر»), USG-028 (reported speech: «گفت» or the verb that names the act; indirect speech is never turned into a quotation; the writer's judgement adverbs).
  - Also extended: STY-001 («مختلف» after a plural; a rising series is not padding), USG-024 («نسبت به … شناخت دارید» becomes «با … آشنایید»), USG-023 («تکمیلِ X»، «در کوتاه‌ترین مدت»), DSC-005 (findings listed with no sentence from the writer), GRM-028 (merging clauses that differ in one part; «…، نه X»; verbless runs in narrative stay), GRM-038 (a repeated time or place phrase), USG-016 («رمانی از X»), STY-003 (Pakar: a verbal noun with its own subject), GRM-034 («نگارنده» with first-person verbs).
  - Extended: GRM-014 (impersonal «باید … کرد» for a passive with no subject), STY-005 («یک + noun + adjective» becomes «…ـی», «یکی از»), GRM-036 (pluperfect for the earlier event), DSC-005 (circular "because": report only), GRM-027 (no resumptive «آن را» in a relative clause), GRM-024 (predicate adjective after its complement).
  - Corrected: GRM-014 and GRM-017 now state Arzhang exactly (only «کردن» compounds lack a passive; «می‌توان + short infinitive» is current usage), GRM-039 (6) no longer recommends inverted forms, STY-003 keeps nominal sides in a correlative comparison, USG-014 and STY-007 (personal letters are not written in colloquial forms; chat is).
  - STY-018 lists the new signs, so the copyedit sentence pass proposes them.

## 0.3.0

- Sources: rules may now also cite journal articles and editing columns. Eight are added to `corpus/sources.json`; a human editor checked each cited finding against the article. The rule book marks any article source that is not yet checked (`human_checked: false`).
- Rules: GRM-038 gains corpus data on subject pronouns (18% of subjects in writing, 27% in speech) and keeps contrastive and topic-shift pronouns. STY-003 covers a verbal-noun subject that has its own actor and an evaluative predicate («... بدیهی است»); generic infinitives stay. GRM-014 adds corpus data on agentless passives and rejects «توسط» for an instrument. GRM-037 item (5): «نباید عجیب باشد» for a plain statement is suggested for a simpler form, after asking the author; «باید» of obligation, inference and scheduled expectation stays. STY-005 says the cleft «(این) او بود که» is attested and not a calque, and keeps established structures. USG-023 adds «به هر حال» for *however*, but keeps it for «در هر صورت». USG-014 lists more colloquial forms and guards «روبه‌رو». PUN-014: no ellipsis after «و غیره»; an ellipsis that marks a cut in a quotation stays. STY-018 routes these signs.
- Round 4 (Iranian research papers): seven more articles, checked against the articles by a human editor. STY-004 adds administrative long-verb pairs and keeps «نمودن» as a suggestion in research prose. STY-020 adds «این در حالی است که» from a press corpus. GRM-024 says the «ی» object mostly comes before the complement and that a long «را» object does not move. STY-018: sentence length and connector count alone are not signs of translation. USG-015 keeps colloquial «هست» outside formal prose. GRM-017 does not apply to «اگر».
- Skill: do not mark a word wrong only because a popular usage list such as «غلط ننویسیم» does.

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
