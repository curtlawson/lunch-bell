"""
Discover the current month's lunch menu PDF URLs from the district menu page.
Returns a dict mapping school level -> PDF URL for use by the parser step.
"""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

MENU_PAGE_URL = "https://www.madisoncity.k12.al.us/Page/3656"

# Maps a canonical level key to substrings that appear in the PDF filename.
# Adjust these if the district ever changes their naming convention.
LEVEL_PATTERNS = {
    "elementary": ["elementary"],
    "middle": ["middle"],
    "high": ["hs", "high school", "high"],
}


def _month_label(dt: datetime) -> str:
    """Return the month+year string the district uses in PDF filenames, e.g. 'May 2026'."""
    return dt.strftime("%B %Y")


def _match_level(filename: str) -> Optional[str]:
    """Return the canonical level key if the filename matches any known pattern."""
    lower = filename.lower()
    for level, patterns in LEVEL_PATTERNS.items():
        if any(p in lower for p in patterns):
            return level
    return None


def discover_lunch_pdfs(
    page_url: str = MENU_PAGE_URL,
    month: Optional[datetime] = None,
) -> dict[str, str]:
    """
    Fetch *page_url*, find all PDF links for the given month's lunch menus,
    and return ``{level: absolute_url}`` for each recognised school level.

    Args:
        page_url: The district menu page to scrape.
        month: The target month/year (defaults to the current month).

    Returns:
        A dict such as::

            {
                "elementary": "https://...Elementary.pdf",
                "middle":     "https://...Middle.pdf",
                "high":       "https://...HS.pdf",
            }

    Raises:
        requests.HTTPError: if the page cannot be fetched.
        ValueError: if no matching PDFs are found for the requested month.
    """
    if month is None:
        month = datetime.now()

    label = _month_label(month)  # e.g. "May 2026"

    response = requests.get(page_url, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    found: dict[str, str] = {}

    for tag in soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE)):
        href: str = tag["href"]
        filename = href.rsplit("/", 1)[-1]

        # Must be a lunch PDF for the target month.
        if label.lower() not in filename.lower():
            continue
        if "lunch" not in filename.lower():
            continue

        level = _match_level(filename)
        if level is None:
            continue

        absolute_url = urljoin(page_url, href)
        # Keep the first match per level (page lists months newest-first).
        found.setdefault(level, absolute_url)

    if not found:
        raise ValueError(
            f"No lunch PDF links found for '{label}' on {page_url}. "
            "The district may not have posted this month's menus yet."
        )

    return found


if __name__ == "__main__":
    results = discover_lunch_pdfs()
    label = _month_label(datetime.now())
    print(f"Lunch menus for {label}:")
    for level, url in sorted(results.items()):
        print(f"  {level:12s} {url}")
