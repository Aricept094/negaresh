"""Shared character classes and search normalization.

Search keys are for retrieval only. They are never used to build a patch and
never replace the user's text.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

ZWNJ = "‌"
PERSIAN_LETTERS = "آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیئأؤإءۀة"
# Letters that never join to the following letter.
NON_JOINING = "اآأإؤدذرزژوۀةء"
LETTER_CLASS = "ء-غف-يٮ-ۓە"
DIACRITICS = "ً-ٰٟ"
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

_DIACRITIC_RE = re.compile(f"[{DIACRITICS}ـ]")
_TOKEN_RE = re.compile(r"[0-9A-Za-zء-ۿ]+")

_FOLD = str.maketrans(
    {
        "ي": "ی", "ى": "ی", "ئ": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه",
        "أ": "ا", "إ": "ا", "آ": "ا", "ؤ": "و",
        **{a: str(i) for i, a in enumerate(ARABIC_DIGITS)},
        **{p: str(i) for i, p in enumerate(PERSIAN_DIGITS)},
    }
)

_SUFFIXES = ("هایی", "های", "ها", "ترین", "تر", "ان", "ی")
_PREFIXES = ("نمی", "می", "بی")


def revision_of(text: str) -> str:
    """SHA-256 of the exact UTF-8 text, with no normalization."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def fold(text: str) -> str:
    """Lossy search form of a string."""
    text = unicodedata.normalize("NFC", text)
    text = _DIACRITIC_RE.sub("", text)
    return text.translate(_FOLD).lower()


def search_tokens(text: str) -> list[str]:
    """Tokens for matching. A half-space splits a word into its parts and the
    joined form is kept too, so «می‌رود», «می رود» and «میرود» can meet."""
    out: list[str] = []
    for chunk in re.split(r"\s+", fold(text)):
        if not chunk:
            continue
        parts = [p for p in re.split(ZWNJ, chunk) if p]
        joined = "".join(parts)
        for piece in [joined, *parts] if len(parts) > 1 else [joined]:
            out.extend(_TOKEN_RE.findall(piece))
    return out


def stem_variants(token: str) -> set[str]:
    """A token plus forms with common closed-class affixes removed."""
    forms = {token}
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 2:
            forms.add(token[: -len(suf)])
    for pre in _PREFIXES:
        if token.startswith(pre) and len(token) - len(pre) >= 2:
            forms.add(token[len(pre):])
    return forms


def is_persian_letter(ch: str) -> bool:
    return bool(ch) and (
        "ء" <= ch <= "غ" or "ف" <= ch <= "ي" or "ٮ" <= ch <= "ۓ" or ch == "ە"
    )
