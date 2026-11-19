# negaresh (نگارش)

[![ci](https://github.com/Aricept094/negaresh/actions/workflows/ci.yml/badge.svg)](https://github.com/Aricept094/negaresh/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/negaresh.svg)](https://pypi.org/project/negaresh/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Persian (Farsi) writing guide for AI assistants and editors. It has three parts that work together or alone:

- **A rule set**: 163 rules for Iranian standard Persian. They cover sentence structure and natural word order, verb tense and mood, paragraph flow, removing translated or machine-like Persian, grammar, usage, punctuation, numbers and citations, Academy orthography (نیم‌فاصله), and meaning preservation. Each rule has a test and examples; 157 of them cite the book and page they come from (some also cite a journal article), and the other 6 are marked as editorial practice.
- **A skill** (standard Agent Skills `SKILL.md` folder) for Claude, Codex and other agents: how to write, copyedit, proofread or naturalize (روان‌سازی) a Persian text with the rules.
- **An MCP server** (stdio and Streamable HTTP) for Claude, ChatGPT, Codex, Gemini CLI, Cursor, VS Code and any MCP client: deterministic checks (Arabic letters and letters of other languages, digits and number separators, spacing, half-spaces, quotes, invisible direction marks, variant spellings, listed calques, and sentence shapes typical of machine Persian), rule search, and validation of edits before they are applied.

راهنمای نگارش فارسی برای دستیارهای هوش مصنوعی و ویراستاران. این راهنما ۱۶۳ قاعده دارد دربارهٔ ساخت جمله، ترتیب طبیعی اجزا، زمان و وجه فعل، پیوند بندها، زدودن نثر ترجمه‌ای و ماشینی، دستور، کاربرد، نشانه‌گذاری و دستور خط فرهنگستان. یک مهارت (skill) برای Claude و یک سرور MCP محلی برای بررسی‌های مکانیکی هم دارد.

## Sources

The rules were built from five books: the Academy's «دستور خطّ فارسی» (1401), Anvari and Ahmadi-Givi's «دستور زبان فارسی» 1 and 2, Arzhang's «دستور زبان فارسی امروز», and Samiee's «نگارش و ویرایش». The author bought the books, scanned them with OCR, extracted the rules, and rewrote and tuned them to the author's needs. The books are not included, and the skill and server cannot read or search them; the skill applies the rules, not the books.

Some rules also cite journal articles and editing columns: corpus studies of written and spoken Persian and of translated Persian, and published before-and-after edits. Their findings are summarized in the author's own words. A human editor checked each cited finding against the article. Full titles of the books and articles are in [NOTICE.md](https://github.com/Aricept094/negaresh/blob/main/NOTICE.md).

## What it does

| Task | Ask for | What happens |
| --- | --- | --- |
| Write | «این را به فارسی بنویس» / "write this in Persian" | The model writes with a real subject and a finite verb for each action, no stock frames, natural order and tense. |
| Copyedit | «ویرایش کن» | Grammar, usage and spelling are fixed. Sentences with machine or translated shapes get a proposed rebuild. |
| Naturalize | «روانش کن»، «طبیعی‌ترش کن»، «ترجمه‌ای است» | Sentences and paragraphs are rebuilt from their meaning. Facts, hedges, actors, numbers and names are kept. |
| Proofread | «غلط‌گیری کن» | Characters, spacing, half-spaces, spelling and punctuation only. |
| Ask | «این درست است؟» | The rule is found and cited. |

## Example: before and after

A paragraph from an academic introduction, naturalized with the skill (profile: academic). The mechanical check found nothing in either version; the changes are sentence rebuilds that the rules ask for. Citations, hedges and technical terms are unchanged.

**Before**

> اختلال مصرف تنباکو و نیکوتین همچنان یکی از مهم‌ترین اختلالات مزمن و عودکننده در طب اعتیاد به شمار می‌رود. در بسیاری از بیماران، حتی با وجود انگیزه جدی برای ترک، تداوم مصرف تنها ناشی از وابستگی فیزیولوژیک نیست، بلکه پیامد تعامل پیچیده میان ولع مصرف (craving)، یادگیری شرطی، نشانه‌های محیطی و نقص در کنترل اجرایی است (1, 2).
>
> در این میان، ولع القاشده با نشانه (cue-induced craving) از اهمیت ویژه‌ای برخوردار است، زیرا بسیاری از موارد عود بالینی در پاسخ به محرک‌های دیداری، بویایی، اجتماعی و موقعیتی مرتبط با سیگار رخ می‌دهند، حتی زمانی که علائم حاد ترک چندان برجسته نیستند (3, 4). از این رو، درک و تعدیل واکنش‌پذیری به نشانه (cue reactivity) نه‌تنها از منظر نظری، بلکه از دیدگاه درمانی نیز اهمیت بسزایی دارد.
>
> مطالعات مرتبط با واکنش‌پذیری به نشانه در سال‌های اخیر نشان داده‌اند که مواجهه با محرک‌های مرتبط با سیگار می‌تواند به‌طور هم‌زمان، هم در سطح ذهنی موجب افزایش میل آنی به مصرف شود و هم در سطح عصبی، شبکه‌های مرتبط با برجستگی محرک، ارزش‌گذاری پاداش، ادراک درونی و کنترل شناختی را درگیر کند (5, 6).

**After**

> اختلال مصرف تنباکو و نیکوتین همچنان یکی از مهم‌ترین اختلالات مزمن و عودکننده در طب اعتیاد به شمار می‌رود. بسیاری از بیماران حتی با انگیزهٔ جدی برای ترک به مصرف ادامه می‌دهند، و علت آن تنها وابستگی فیزیولوژیک نیست، بلکه تعامل پیچیدهٔ ولع مصرف (craving)، یادگیری شرطی، نشانه‌های محیطی و نقص در کنترل اجرایی است (1, 2).
>
> ولع القاشده با نشانه (cue-induced craving) اهمیت ویژه‌ای دارد، زیرا بسیاری از عودهای بالینی در پاسخ به محرک‌های دیداری، بویایی، اجتماعی و موقعیتی مرتبط با سیگار رخ می‌دهند، حتی وقتی علائم حاد ترک چندان برجسته نیستند (3, 4). از این رو درک و تعدیل واکنش‌پذیری به نشانه (cue reactivity) هم از نظر نظری و هم برای درمان اهمیت بسزایی دارد.
>
> مطالعات سال‌های اخیر دربارهٔ واکنش‌پذیری به نشانه نشان داده‌اند که مواجهه با محرک‌های مرتبط با سیگار می‌تواند هم‌زمان در سطح ذهنی میل آنی به مصرف را افزایش دهد و در سطح عصبی شبکه‌های دخیل در برجستگی محرک، ارزش‌گذاری پاداش، ادراک درونی و کنترل شناختی را درگیر کند (5, 6).

**What changed, and why**

| Before | After | Rule |
| --- | --- | --- |
| «در بسیاری از بیماران ... تداوم مصرف ... ناشی از ... نیست، بلکه پیامد ... است» | «بسیاری از بیماران ... به مصرف ادامه می‌دهند، و علت آن ... نیست، بلکه ... است» | STY-019, STY-003: the patients become the subject and get a verb; the abstract noun «تداوم مصرف» goes. The contrast «تنها ... نیست، بلکه» stays. |
| «از اهمیت ویژه‌ای برخوردار است» | «اهمیت ویژه‌ای دارد» | STY-019: a padded verb replaced by the plain one. |
| «در این میان،» at the start of a paragraph | (removed) | GRM-029: an opening connector with no real turn. «زیرا» and «از این رو» mark real cause and result and stay. |
| «موجب افزایش ... شود» | «... را افزایش دهد» | STY-004: a long verb phrase replaced by the verb. |
| «به‌طور هم‌زمان» | «هم‌زمان» | STY-004: «به طورِ + adjective» shortened. |
| «مطالعات مرتبط با ...»، «شبکه‌های مرتبط با ...» | «مطالعات ... دربارهٔ ...»، «شبکه‌های دخیل در ...» | STY-009: «مرتبط با» appeared four times. The technical term «محرک‌های مرتبط با سیگار» keeps its wording. |
| «مطالعات ... در سال‌های اخیر نشان داده‌اند» | «مطالعات سال‌های اخیر ... نشان داده‌اند» | GRM-039: the time phrase sits next to the noun it limits, not between subject and verb. |
| «نه‌تنها از منظر نظری، بلکه از دیدگاه درمانی نیز» | «هم از نظر نظری و هم برای درمان» | USG-023: a simpler pair. The original is also correct if the "not only… but also" stress is wanted. |
| «بسیاری از موارد عود»، «حتی زمانی که» | «بسیاری از عودها»، «حتی وقتی» | STY-001: words that add nothing. |
| «انگیزه جدی»، «پیچیده میان»، «از این رو،» | «انگیزهٔ جدی»، «پیچیدهٔ»، «از این رو» | ORT-019: the ezafe mark after a silent «ه»; no comma after a short connector. |

## Requirements

- For the MCP server: Python 3.11 or later and [uv](https://docs.astral.sh/uv/) (`uvx` must be on the PATH). The server needs no network access while it runs.
- The skill and the rule set need nothing.

## Install

The server is on [PyPI](https://pypi.org/project/negaresh/) and in the [official MCP Registry](https://registry.modelcontextprotocol.io/) as `io.github.Aricept094/negaresh`. The command is the same everywhere:

```
uvx negaresh serve
```

### Claude Code (plugin: skill and MCP server together)

In Claude Code:

```
/plugin marketplace add Aricept094/negaresh
/plugin install negaresh@negaresh
```

Or from a terminal:

```bash
claude plugin marketplace add Aricept094/negaresh
```

```bash
claude plugin install negaresh@negaresh
```

### Claude Desktop

Add the server to `claude_desktop_config.json` (Settings → Developer → Edit Config) and restart the app:

```json
{
  "mcpServers": {
    "negaresh": {
      "command": "uvx",
      "args": ["negaresh", "serve"]
    }
  }
}
```

For the skill, upload `negaresh-skill.zip` from the [latest release](https://github.com/Aricept094/negaresh/releases/latest) under Settings → Capabilities → Skills.

### Claude.ai

Upload `negaresh-skill.zip` from the [latest release](https://github.com/Aricept094/negaresh/releases/latest) under Settings → Capabilities → Skills. The skill works without the server.

### ChatGPT

Two ways, both in [clients/chatgpt](https://github.com/Aricept094/negaresh/blob/main/clients/chatgpt/README.md): an MCP connector in developer mode (run the server with `--http` behind an HTTPS tunnel), or a custom GPT with the rule files as knowledge.

### Codex CLI

```bash
codex mcp add negaresh -- uvx negaresh serve
```

For the skill, copy `skills/negaresh` to `~/.codex/skills/negaresh`.

### Gemini CLI

```bash
gemini extensions install https://github.com/Aricept094/negaresh
```

### Cursor

[Install in Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=negaresh&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJuZWdhcmVzaCIsInNlcnZlIl19), or add the JSON block above to `~/.cursor/mcp.json`.

### VS Code

[Install in VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=negaresh&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22negaresh%22%2C%22serve%22%5D%7D), or:

```bash
code --add-mcp "{\"name\":\"negaresh\",\"command\":\"uvx\",\"args\":[\"negaresh\",\"serve\"]}"
```

### Any other MCP client

- stdio: `uvx negaresh serve`
- Streamable HTTP: `uvx negaresh serve --http --port 8000`, then connect to `http://127.0.0.1:8000/mcp`. Use `--allowed-host <name>` for a proxy or tunnel host.
- With pip: `pip install negaresh`, then `negaresh serve`.
- Development version from GitHub: `uvx --from git+https://github.com/Aricept094/negaresh negaresh serve`.

### Skill only (any client that reads Agent Skills)

The skill is a standard `SKILL.md` folder: [`skills/negaresh`](https://github.com/Aricept094/negaresh/tree/main/skills/negaresh). Copy it into the client's skills folder (`~/.claude/skills/`, `~/.codex/skills/`, or the client's own location).

### Rule set only

- `corpus/rules/*.json`: the rules as JSON (one array per category).
- `docs/RULEBOOK.md`: the full rule book in Persian.
- `corpus/lexicon/`: variant spellings, listed expressions and sentence-shape patterns.

## MCP tools

| Tool | Use |
| --- | --- |
| `search_rules` | Find rules by Persian or English words. |
| `get_rule` | One rule in full. |
| `get_profile` | Conventions for a kind of text (academic, journalistic, literary, ...). |
| `check_mechanics` | Checks M01 to M16. It returns findings with exact offsets, candidate patches, and a low-risk `auto_patch_set`. |
| `validate_patches` | Checks that a set of edits applies cleanly and leaves URLs, code and other protected text unchanged. |
| `search`, `fetch` | Over HTTP only: the search-and-read pair that ChatGPT connectors use. |

All tools are read-only. The server stores no text on disk. Each call takes up to 12,000 Unicode code points.

## Command line

```bash
negaresh doctor
```

```bash
negaresh check draft.txt --profile academic
```

```bash
negaresh search "نیم‌فاصله می"
```

## Rule families

| Prefix | Family | Rules | Main sources |
| --- | --- | --- | --- |
| ORT | Orthography and spacing | 44 | Academy «دستور خطّ فارسی» (1401) |
| GRM | Grammar, word order, tense and mood | 39 | Anvari and Ahmadi-Givi 1 and 2; Arzhang; Samiee; corpus studies |
| USG | Usage and calques | 23 | the three grammars; Samiee |
| STY | Style and sentence building | 19 | Samiee; editorial synthesis; translation studies |
| PUN | Punctuation and characters | 18 | Samiee |
| TRM | Numbers, dates, citations, notes, names | 9 | Samiee |
| INT | Meaning preservation | 6 | Samiee; editorial synthesis |
| DSC | Paragraphs and discourse | 5 | Samiee |

Each rule has a severity (`error`, `convention`, `advisory`) and an evidence class. `sourced` rules name the book and page they come from, and some also name a journal article; `editorial_synthesis` rules are editorial practice with no book behind them. The evidence class tells you how to cite a rule; the severity tells you how firmly to apply it.

## Edit the rules

1. Edit the JSON in `corpus/rules/`.
2. Run `python tools/build.py`. It validates the corpus and regenerates the bundle, the skill references and the rule book.
3. Run `pytest`.

Do not edit generated files: `src/negaresh/data/corpus.json`, `skills/negaresh/references/rules-*.md`, `docs/RULEBOOK.md`.

To make the release files (wheel, skill zip, clean folder): `python tools/package.py`.

<!-- mcp-name: io.github.Aricept094/negaresh -->

## Limits

- The mechanical checker sees characters, listed expressions and a few sentence shapes. No finding does not mean that the prose is natural. Sentence and paragraph rebuilding is done by the model with the rules.
- The «می» half-space check uses a closed list of verb stems.

## Licence

MIT. See [LICENSE](https://github.com/Aricept094/negaresh/blob/main/LICENSE).
