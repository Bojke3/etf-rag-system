import re

_CYRILLIC_TO_LATIN = {
    'А': 'A', 'а': 'a',
    'Б': 'B', 'б': 'b',
    'В': 'V', 'в': 'v',
    'Г': 'G', 'г': 'g',
    'Д': 'D', 'д': 'd',
    'Ђ': 'Dj', 'ђ': 'd ',
    'Е': 'E', 'е': 'e',
    'Ж': 'Z', 'ж': 'z',
    'З': 'Z', 'з': 'z',
    'И': 'I', 'и': 'i',
    'Ј': 'J', 'ј': 'j',
    'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l',
    'Љ': 'Lj', 'љ': 'lj',
    'М': 'M', 'м': 'm',
    'Н': 'N', 'н': 'n',
    'Њ': 'Nj', 'њ': 'nj',
    'О': 'O', 'о': 'o',
    'П': 'P', 'п': 'p',
    'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's',
    'Т': 'T', 'т': 't',
    'Ћ': 'C', 'ћ': 'c',
    'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f',
    'Х': 'H', 'х': 'h',
    'Ц': 'C', 'ц': 'c',
    'Ч': 'C', 'ч': 'c',
    'Џ': 'Dz', 'џ': 'dz',
    'Ш': 'S', 'ш': 's',
}


# Page separator inserted by the loaders; preserved through cleanup so that
# chunkers can still derive page numbers.
PAGE_SEPARATOR = "\f"

# Lines that are page furniture rather than content: a bare number, "- 12 -",
# "Strana 12", "12/48", "Str. 12".
_PAGE_ARTIFACT_RE = re.compile(
    r"^[ \t]*(?:[-–—]?[ \t]*\d{1,4}[ \t]*[-–—]?|\d{1,4}\s*/\s*\d{1,4}"
    r"|(?:Strana|Str\.?|Stranica)[ \t]*\d{1,4})[ \t]*$",
    re.IGNORECASE,
)

# A word broken across a line break by the PDF/OCR layout: "akadem-\nskim".
_HYPHEN_BREAK_RE = re.compile(r"(\w)[-\u2010\u2011\u00ad][ \t]*\n[ \t]*(\w)")

# A line that ends a sentence (or is a heading) should not be glued to the next.
_SENTENCE_END_RE = re.compile(r"[.!?:;)\]]['\"]?$")
_HEADING_LINE_RE = re.compile(
    r"^[ \t]*(?:(?:Clan|Član|Члан)[ \t]+\d+|[IVXLC]+\.|\d+\.)", re.IGNORECASE
)

_MAX_BOILERPLATE_LINE = 80
_MIN_BOILERPLATE_PAGES = 3
_BOILERPLATE_PAGE_RATIO = 0.6


class TextPreprocessor:
    """Text normalisation applied once per document, upstream of any chunker.

    ``ocr_cleanup`` gates the OCR-repair passes (hyphenation, wrapped lines,
    page furniture, repeated headers/footers).  With it disabled the output is
    exactly what this class produced before those passes existed, which is what
    keeps the flat baseline reproducible.
    """

    def __init__(self, ocr_cleanup: bool = False):
        self.ocr_cleanup = ocr_cleanup

    def clean(self, text: str) -> str:
        text = self.cyrillic_to_latin(text)

        if self.ocr_cleanup:
            text = self.fix_hyphenation(text)
            text = self.strip_page_artifacts(text)
            text = self.strip_repeated_boilerplate(text)
            text = self.rejoin_wrapped_lines(text)

        text = self.remove_extra_whitespace(text)
        text = self.normalize_newlines(text)
        return text.strip()

    # -- OCR repair passes ------------------------------------------------

    def fix_hyphenation(self, text: str) -> str:
        """Rejoin words split by a hyphen at a line break."""
        previous = None
        # Repeat: consecutive hyphenated breaks can overlap on the shared \n.
        while previous != text:
            previous = text
            text = _HYPHEN_BREAK_RE.sub(r"\1\2", text)
        return text

    def strip_page_artifacts(self, text: str) -> str:
        """Drop standalone page numbers and "Strana N" lines."""
        kept = [
            line
            for line in text.split("\n")
            if not _PAGE_ARTIFACT_RE.match(line)
        ]
        return "\n".join(kept)

    def strip_repeated_boilerplate(self, text: str) -> str:
        """Remove short lines that repeat across most pages (headers/footers).

        Only runs when the document has real page separators -- without them
        there is no way to tell a repeated header from repeated body text.
        """
        pages = text.split(PAGE_SEPARATOR)
        if len(pages) < _MIN_BOILERPLATE_PAGES:
            return text

        counts = {}
        for page in pages:
            for line in {l.strip() for l in page.split("\n") if l.strip()}:
                if len(line) <= _MAX_BOILERPLATE_LINE:
                    counts[line] = counts.get(line, 0) + 1

        threshold = max(_MIN_BOILERPLATE_PAGES, int(len(pages) * _BOILERPLATE_PAGE_RATIO))
        boilerplate = {line for line, n in counts.items() if n >= threshold}
        if not boilerplate:
            return text

        cleaned_pages = []
        for page in pages:
            cleaned_pages.append(
                "\n".join(l for l in page.split("\n") if l.strip() not in boilerplate)
            )
        return PAGE_SEPARATOR.join(cleaned_pages)

    def rejoin_wrapped_lines(self, text: str) -> str:
        """Join lines the PDF/OCR layout broke mid-sentence.

        A line is joined to the next when it does not end a sentence, is not a
        heading, and the next line continues in lower case.  Blank lines and
        page separators always break the join.
        """
        lines = text.split("\n")
        out = []

        for line in lines:
            stripped = line.rstrip()

            if not out:
                out.append(stripped)
                continue

            previous = out[-1]
            candidate = stripped.lstrip()

            joinable = (
                previous.strip()
                and candidate
                and PAGE_SEPARATOR not in previous
                and PAGE_SEPARATOR not in candidate
                and not _SENTENCE_END_RE.search(previous.strip())
                and not _HEADING_LINE_RE.match(previous)
                and not _HEADING_LINE_RE.match(candidate)
                and candidate[0].islower()
            )

            if joinable:
                out[-1] = previous + " " + candidate
            else:
                out.append(stripped)

        return "\n".join(out)

    def cyrillic_to_latin(self, text: str) -> str:
        result = []
        for ch in text:
            result.append(_CYRILLIC_TO_LATIN.get(ch, ch))
        return ''.join(result)

    def remove_extra_whitespace(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text)

    def normalize_newlines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)