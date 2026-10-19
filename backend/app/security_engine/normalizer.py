"""Normalize text before security pattern matching and model forwarding."""

import unicodedata


# Common Cyrillic and Greek lookalikes used to disguise ASCII attack words.
_CONFUSABLES = str.maketrans({
    "а": "a", "А": "A", "с": "c", "С": "C", "е": "e", "Е": "E",
    "і": "i", "І": "I", "ј": "j", "Ј": "J", "о": "o", "О": "O",
    "р": "p", "Р": "P", "ѕ": "s", "Ѕ": "S", "х": "x", "Х": "X",
    "у": "y", "У": "Y", "ԁ": "d", "ԛ": "q", "ν": "v", "Ν": "N",
    "ο": "o", "Ο": "O", "ι": "i", "Ι": "I", "κ": "k", "Κ": "K",
    "τ": "t", "Τ": "T", "μ": "m", "Μ": "M",
})


def normalize_text(value: str) -> str:
    """Apply compatibility normalization and remove invisible separators."""
    normalized = unicodedata.normalize("NFKC", value).translate(_CONFUSABLES)
    return "".join(
        char for char in normalized
        if unicodedata.category(char) not in {"Cf", "Cc"} or char in "\n\r\t"
    )

