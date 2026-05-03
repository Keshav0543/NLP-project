import re
import requests
from bs4 import BeautifulSoup

# Richer headers to reduce chance of being blocked
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Ordered from most-likely to least-likely; Flipkart rotates class names
PRICE_SELECTORS = [
    "div._30jeq3",       # classic
    "div._1_WHN1",       # classic alternate
    "div.Nx9bqj",        # ~2024 variant
    "div.CEmiEU",        # newer variant
    "div._16Jk6d",       # older grid view
    "div._25b18c ._30jeq3",
    "div[class*='_30jeq3']",  # partial-class match
]

TITLE_SELECTORS = [
    "div._4rR01T",
    "a.s1Q9rs",
    "div.KzDlHZ",        # ~2024 grid title
    "a.WKTcLC",
    "div._2WkVRV",
]


def _first_match(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """Return the first non-empty text hit from a list of CSS selectors."""
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag and tag.get_text(strip=True):
            return tag.get_text(strip=True)
    return None


def _regex_price(soup: BeautifulSoup) -> str | None:
    """
    Last-resort: scan every text node for a ₹ price pattern.
    Picks the first one found (usually the cheapest listing at the top).
    """
    pattern = re.compile(r"₹[\d,]{3,}")
    for node in soup.find_all(string=pattern):
        text = node.strip()
        match = pattern.search(text)
        if match:
            return match.group()
    return None


def _flipkart_fetch(query: str) -> tuple[BeautifulSoup, str]:
    """Fetch a Flipkart search page and return (soup, search_url)."""
    search_url = (
        "https://www.flipkart.com/search?q="
        + query.replace(" ", "%20")
    )
    res = requests.get(search_url, headers=HEADERS, timeout=15)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser"), search_url


def search_flipkart(product_name: str) -> dict:
    search_url = (
        "https://www.flipkart.com/search?q="
        + product_name.replace(" ", "%20")
    )

    try:
        # --- Attempt 1: full product name ---
        soup, search_url = _flipkart_fetch(product_name)
        price = _first_match(soup, PRICE_SELECTORS)
        title = _first_match(soup, TITLE_SELECTORS)

        # --- Attempt 2: shorter fallback query (first 3 words) ---
        if not price:
            short_query = " ".join(product_name.split()[:3])
            soup, _ = _flipkart_fetch(short_query)
            price = _first_match(soup, PRICE_SELECTORS)
            title = title or _first_match(soup, TITLE_SELECTORS)

        # --- Attempt 3: regex scan for any ₹ price in the page ---
        if not price:
            price = _regex_price(soup)

        return {
            "platform": "Flipkart",
            "title": title or "Not found",
            "price": price or "Unavailable",
            "link": search_url,
        }

    except requests.RequestException as exc:
        # Network / HTTP error — return gracefully so the rest of the app still works
        return {
            "platform": "Flipkart",
            "title": "Error fetching",
            "price": "Unavailable",
            "link": search_url,
            "error": str(exc),
        }