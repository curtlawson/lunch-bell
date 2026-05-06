"""
Parse a monthly school lunch menu PDF and return structured daily menu data.

The PDFs use a 5-column (Mon-Fri) calendar grid where date numbers are embedded
in a background image and cannot be extracted as text. Dates are computed from
the month/year header and each word's (col, row) grid position.
"""

import re
from calendar import monthrange
from datetime import date
from typing import Optional

import pdfplumber

HEADER_Y_CUTOFF = 90.0   # page title + "Other Options" sidebar legend
FOOTER_Y_CUTOFF = 540.0  # footnotes about milk and meal components
N_COLS = 5               # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4
LINE_Y_TOLERANCE = 3.0   # max vertical gap (pts) for words to be on the same line
# Within-cell line spacing is ~14 pts; between-row gap is ~18+ pts.
# Using 16 ensures all within-cell gaps (~≤15) stay together while row gaps (≥18) split.
ROW_GAP_MIN = 16.0

NO_LUNCH_KEYWORDS = frozenset({
    "NO SCHOOL",
    "DISTRICT CLOSED",
    "SUMMER BREAK",
    "SPRING BREAK",
    "FALL BREAK",
    "WINTER BREAK",
    "MEMORIAL DAY",
    "THANKSGIVING",
    "CHRISTMAS",
    "NEW YEAR",
    "E-LEARNING",
})

# Annotations that appear in calendar cells but are not menu items
NOISE_PATTERN = re.compile(
    r"(?:\bSACK LUNCH\b|\bUPON REQUEST\b|½ DAY"
    r"|\bLAST STUDENT\b|\bTEACHER WORKDAY\b|\bBJHS\b|\bJCHS\b|\bGRADUATION\b"
    r"|\bWORLD BEE\b|\bNATIONAL SCHOOL\b|\bLUNCH HERO\b|\bHERO\b|\bSTUDENT ½\b)",
    re.IGNORECASE,
)

# Standalone words that are always annotation noise (never food item names)
NOISE_STANDALONE = frozenset({"DAY", "OBSERVED", "AVAILABLE", "REQUEST", "STUDENTS", "ALL", "FOR"})

MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}


def _parse_month_year(words: list) -> tuple[int, int]:
    header_text = " ".join(w["text"].upper() for w in words if w["top"] < HEADER_Y_CUTOFF)
    for name, num in MONTHS.items():
        m = re.search(rf"{name}\s+(\d{{4}})", header_text)
        if m:
            return num, int(m.group(1))
    raise ValueError(f"Could not find month/year in header: {header_text[:200]}")


def _col_boundaries(page_width: float) -> list[float]:
    left = 14.0
    right = page_width - 14.0
    w = (right - left) / N_COLS
    return [left + i * w for i in range(N_COLS + 1)]


def _detect_col_boundaries(words: list, page_width: float) -> list[float]:
    """
    Derive column boundaries from the 4 largest gaps in word-center x-distribution.
    Using word centers (x0+x1)/2 rather than x0 avoids misclassifying words that
    happen to be typeset near a column edge.
    Falls back to equal-width columns when insufficient data.
    """
    centers = sorted(
        (w["x0"] + w["x1"]) / 2
        for w in words
        if HEADER_Y_CUTOFF < w["top"] < FOOTER_Y_CUTOFF
    )
    if len(centers) < 10:
        return _col_boundaries(page_width)

    unique = sorted(set(round(c, 1) for c in centers))
    gaps = [(unique[i + 1] - unique[i], unique[i], unique[i + 1]) for i in range(len(unique) - 1)]
    top4 = sorted(gaps, reverse=True)[: N_COLS - 1]
    top4.sort(key=lambda g: g[1])  # re-sort left-to-right

    boundaries = [14.0] + [(a + b) / 2 for _, a, b in top4] + [page_width - 14.0]
    if len(boundaries) != N_COLS + 1:
        return _col_boundaries(page_width)
    return boundaries


def _row_bands(words: list, min_gap: float = ROW_GAP_MIN) -> list[tuple[float, float]]:
    """Return list of (y_start, y_end) bands for each calendar week row."""
    ys = sorted({
        round(w["top"])
        for w in words
        if HEADER_Y_CUTOFF < w["top"] < FOOTER_Y_CUTOFF
    })
    if not ys:
        return []

    bands: list[tuple[float, float]] = []
    band_start = float(ys[0])
    prev_y = float(ys[0])

    for y in ys[1:]:
        if y - prev_y > min_gap:
            bands.append((band_start - 5, prev_y + 5))
            band_start = float(y)
        prev_y = float(y)
    bands.append((band_start - 5, prev_y + 5))

    return bands


def _assign_col(word: dict, col_bounds: list[float]) -> Optional[int]:
    center = (word["x0"] + word["x1"]) / 2
    for i in range(N_COLS):
        if col_bounds[i] <= center < col_bounds[i + 1]:
            return i
    return None


def _assign_row(top: float, bands: list[tuple[float, float]]) -> Optional[int]:
    for i, (y0, y1) in enumerate(bands):
        if y0 <= top <= y1:
            return i
    return None


def _words_to_lines(word_dicts: list) -> list[str]:
    """Group words by y-line and join into strings (one line = one menu item)."""
    if not word_dicts:
        return []

    sorted_words = sorted(word_dicts, key=lambda w: (w["top"], w["x0"]))

    lines: list[list] = []
    current: list = [sorted_words[0]]

    for w in sorted_words[1:]:
        if abs(w["top"] - current[-1]["top"]) <= LINE_Y_TOLERANCE:
            current.append(w)
        else:
            lines.append(current)
            current = [w]
    lines.append(current)

    return [
        " ".join(ww["text"] for ww in sorted(line, key=lambda ww: ww["x0"]))
        for line in lines
    ]


def _is_no_school(lines: list[str]) -> bool:
    combined = " ".join(lines).upper()
    return any(kw in combined for kw in NO_LUNCH_KEYWORDS)


def _filter_noise(lines: list[str]) -> list[str]:
    result = []
    for ln in lines:
        if NOISE_PATTERN.search(ln):
            continue
        if ln.strip().upper() in NOISE_STANDALONE:
            continue
        result.append(ln)
    return result


def parse_menu(pdf_path: str) -> list[dict]:
    """
    Parse one school level's lunch PDF.

    Returns a sorted list of dicts:
        {"date": datetime.date, "items": [str, ...]}

    Only school days with a regular lunch menu are included; no-school days
    (Memorial Day, Summer Break, etc.) are silently skipped.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        page_width = page.width

    month_num, year = _parse_month_year(words)
    col_bounds = _detect_col_boundaries(words, page_width)
    bands = _row_bands(words)

    cells: dict[tuple[int, int], list] = {}
    for w in words:
        if not (HEADER_Y_CUTOFF < w["top"] < FOOTER_Y_CUTOFF):
            continue
        col = _assign_col(w, col_bounds)
        row = _assign_row(w["top"], bands)
        if col is None or row is None:
            continue
        cells.setdefault((row, col), []).append(w)

    first_day = date(year, month_num, 1)
    first_weekday = first_day.weekday()  # 0=Mon, 4=Fri
    days_in_month = monthrange(year, month_num)[1]

    results: list[dict] = []

    for (row_idx, col_idx), word_dicts in cells.items():
        day_offset = row_idx * 7 + col_idx - first_weekday
        if day_offset < 0 or day_offset >= days_in_month:
            continue

        day_num = 1 + day_offset
        lunch_date = date(year, month_num, day_num)

        if lunch_date.weekday() > 4:
            continue

        lines = _words_to_lines(word_dicts)

        if _is_no_school(lines):
            continue

        items = _filter_noise(lines)
        if not items:
            continue

        results.append({"date": lunch_date, "items": items})

    return sorted(results, key=lambda r: r["date"])


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/elementary.pdf"
    menu = parse_menu(path)
    for entry in menu:
        print(f"\n{entry['date'].strftime('%a %b %d, %Y')}")
        for item in entry["items"]:
            print(f"  - {item}")
