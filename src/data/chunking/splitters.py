"""Shared text-splitting helpers used by the chunking strategies.

Everything here works on *characters*, not tokens: nothing in this project is
token-aware, and the corpus (Serbian faculty rulebooks, OCR'd) is >95% prose.
Sizes given in tokens elsewhere are converted at roughly 3.5 chars/token.
"""

from typing import List, Optional, Sequence, Tuple
import re

#: Inserted between PDF pages by the loaders so page numbers survive to chunking.
PAGE_SEPARATOR = "\f"

# Section cues that survive in this corpus.  "Clan N." is the article marker in
# every pravilnik; the rest catch roman-numeral parts, numbered items and the
# all-caps document titles.
HEADING_PATTERNS = (
    r"^[ \t]*(?:Clan|Član|Члан)[ \t]+\d+[a-zA-Z]?\.?[ \t]*$",
    r"^[ \t]*[IVXLC]+\.[ \t]+\S.*$",
    r"^[ \t]*\d+\.[ \t]+[A-ZŠĐČĆŽ][^\n]*$",
    r"^[ \t]*[A-ZŠĐČĆŽ][A-ZŠĐČĆŽ0-9 .,\-()/]{7,}$",
)
HEADING_RE = re.compile("|".join(HEADING_PATTERNS), re.MULTILINE)

# Characters that mark formula / tabular material rather than prose.
_SYMBOL_CHARS = set("0123456789=+-*/^%<>()[]{}|±×÷·∑∫√≤≥≈∞")
_ATOMIC_DENSITY = 0.35
_ATOMIC_MIN_LINE_LEN = 3


def _line_is_dense(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < _ATOMIC_MIN_LINE_LEN:
        return False
    symbols = sum(1 for ch in stripped if ch in _SYMBOL_CHARS)
    non_space = sum(1 for ch in stripped if not ch.isspace())
    if not non_space:
        return False
    return symbols / non_space >= _ATOMIC_DENSITY


def find_atomic_spans(text: str, min_lines: int = 2) -> List[Tuple[int, int]]:
    """Character spans that must never be split through.

    A span is a run of at least ``min_lines`` consecutive lines whose
    symbol/digit density exceeds the prose threshold -- formula blocks and the
    ECTS/hours tables in the rulebooks.
    """
    spans: List[Tuple[int, int]] = []
    offset = 0
    run_start: Optional[int] = None
    run_lines = 0

    for line in text.splitlines(keepends=True):
        if _line_is_dense(line):
            if run_start is None:
                run_start = offset
            run_lines += 1
        else:
            if run_start is not None and run_lines >= min_lines:
                spans.append((run_start, offset))
            run_start = None
            run_lines = 0
        offset += len(line)

    if run_start is not None and run_lines >= min_lines:
        spans.append((run_start, offset))

    return spans


def in_atomic_span(position: int, spans: Sequence[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Return the atomic span containing ``position``, if any."""
    for start, end in spans:
        if start < position < end:
            return (start, end)
    return None


def adjust_split_point(position: int, spans: Sequence[Tuple[int, int]], limit: int) -> int:
    """Nudge a split point out of an atomic span.

    Prefers the span's start (keeping the block whole in the *next* piece); if
    that would produce an empty piece, pushes past the span's end instead, even
    though that overshoots ``limit`` -- an oversized chunk beats a bisected
    formula.
    """
    span = in_atomic_span(position, spans)
    if span is None:
        return position
    start, end = span
    if start > 0:
        return start
    return min(end, limit)


def _separator_positions(text: str, separator: str) -> List[int]:
    """Offsets just *after* each occurrence of ``separator``."""
    if separator == "__heading__":
        return [m.start() for m in HEADING_RE.finditer(text) if m.start() > 0]

    positions = []
    start = 0
    while True:
        idx = text.find(separator, start)
        if idx == -1:
            break
        positions.append(idx + len(separator))
        start = idx + len(separator)
    return positions


#: Tried in order; the first that yields an acceptable break point wins.
SEPARATORS = (PAGE_SEPARATOR, "__heading__", "\n\n", "\n", ". ", " ")


def recursive_split(
    text: str,
    target: int,
    min_size: int,
    atomic_spans: Sequence[Tuple[int, int]] = (),
    offset: int = 0,
) -> List[Tuple[int, int]]:
    """Split ``text`` into ``(start, end)`` spans of at most ~``target`` chars.

    Prefers page breaks, then headings, then paragraph, line and sentence
    boundaries, falling back to a hard character cut only when no separator
    produces a break at or after ``min_size``.  Offsets are absolute when
    ``offset`` is supplied.
    """
    if not text:
        return []
    if len(text) <= target:
        return [(offset, offset + len(text))]

    spans: List[Tuple[int, int]] = []
    cursor = 0

    while cursor < len(text):
        remaining = len(text) - cursor
        if remaining <= target:
            spans.append((offset + cursor, offset + len(text)))
            break

        window = text[cursor : cursor + target]
        split_at = None

        for separator in SEPARATORS:
            candidates = [p for p in _separator_positions(window, separator) if p >= min_size]
            if candidates:
                split_at = candidates[-1]
                break

        if split_at is None:
            split_at = target

        absolute = adjust_split_point(
            offset + cursor + split_at, atomic_spans, offset + len(text)
        )
        split_at = absolute - offset - cursor

        # Guarantee forward progress even if the atomic adjustment collapsed the piece.
        if split_at <= 0:
            split_at = min(target, remaining)

        spans.append((offset + cursor, offset + cursor + split_at))
        cursor += split_at

    return spans


def page_for_offset(text: str, position: int) -> int:
    """1-based page number for a character offset, counting page separators."""
    return text.count(PAGE_SEPARATOR, 0, position) + 1


def section_for_offset(text: str, position: int) -> Optional[str]:
    """The most recent heading at or before ``position``."""
    heading = None
    for match in HEADING_RE.finditer(text, 0, max(position, 1)):
        heading = match.group(0).strip()
    return heading
