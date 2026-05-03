import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

AMAZON_REVIEW_SELECTORS = [
    "span[data-hook='review-body'] span",
    "span[data-hook='review-body']",
    "div[data-hook='review-collapsed'] span",
    ".review-text-content span",
    ".review-text",
]

TITLE_SELECTORS = [
    "#productTitle",
    "span#productTitle",
    "h1.a-size-large.a-spacing-none",
    "title",
]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_asin(url: str) -> str | None:
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
        r"/ASIN/([A-Z0-9]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.I)
        if match:
            return match.group(1).upper()
    return None


def _get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_title(soup: BeautifulSoup) -> str:
    for selector in TITLE_SELECTORS:
        node = soup.select_one(selector)
        if node:
            title = _clean_text(node.get_text(" ", strip=True))
            if title:
                return title
    return "Product"


# ✅ PRICE EXTRACTION (robust selectors + regex fallback)
def _extract_price(soup: BeautifulSoup) -> str:
    selectors = [
        # Modern Amazon India selectors (2024+)
        ".priceToPay span.a-price-whole",
        "#corePriceDisplay_desktop_feature_div span.a-price-whole",
        "#apex_offerDisplay_desktop span.a-price-whole",
        ".a-price[data-a-size='xl'] .a-offscreen",
        ".a-price[data-a-size='b'] .a-offscreen",
        # Older / fallback selectors
        "span.a-offscreen",
        "span.a-price-whole",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#priceblock_saleprice",
        "#price_inside_buybox",
    ]
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag:
            text = _clean_text(tag.get_text())
            if text and any(ch.isdigit() for ch in text):
                return text

    # Last resort: regex scan for ₹ price in page text
    match = re.search(r"₹[\d,]+", soup.get_text())
    if match:
        return match.group()

    return "Not found"


def _extract_reviews_from_soup(soup: BeautifulSoup) -> list[str]:
    reviews: list[str] = []
    seen = set()
    for selector in AMAZON_REVIEW_SELECTORS:
        for node in soup.select(selector):
            text = _clean_text(node.get_text(" ", strip=True))
            if len(text) >= 20 and text not in seen:
                seen.add(text)
                reviews.append(text)
    return reviews


def _extract_rating(soup: BeautifulSoup) -> str | None:
    candidates = [
        soup.select_one("span[data-hook='rating-out-of-text']"),
        soup.select_one("i[data-hook='average-star-rating'] span"),
        soup.select_one("span.a-icon-alt"),
    ]
    for node in candidates:
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    return None


def _extract_feature_bullets(soup: BeautifulSoup) -> list[str]:
    bullets = []
    for node in soup.select("#feature-bullets li span"):
        text = _clean_text(node.get_text(" ", strip=True))
        if len(text) > 8 and text.lower() != "see more":
            bullets.append(text)
    return bullets[:8]


def _build_amazon_review_url(product_url: str) -> str | None:
    asin = _extract_asin(product_url)
    parsed = urlparse(product_url)
    if not asin or not parsed.netloc:
        return None
    return f"{parsed.scheme or 'https'}://{parsed.netloc}/product-reviews/{asin}?reviewerType=all_reviews"


def scrape_product_reviews(url: str) -> dict:
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("Please enter a valid product URL starting with http:// or https://")

    parsed = urlparse(url)
    if "amazon." not in parsed.netloc.lower():
        raise ValueError("Currently this project supports Amazon product links only.")

    product_soup = _get_soup(url)

    title = _extract_title(product_soup)
    rating = _extract_rating(product_soup)
    price = _extract_price(product_soup)  # ✅ NEW
    features = _extract_feature_bullets(product_soup)

    reviews = _extract_reviews_from_soup(product_soup)

    review_url = _build_amazon_review_url(url)
    if review_url:
        try:
            review_soup = _get_soup(review_url)
            more_reviews = _extract_reviews_from_soup(review_soup)
            for review in more_reviews:
                if review not in reviews:
                    reviews.append(review)
        except requests.RequestException:
            pass

    if not reviews:
        raise Exception(
            "Reviews could not be fetched from this link. Amazon may be blocking the request, "
            "the product may have no visible reviews, or the page structure changed."
        )

    return {
        "url": url,
        "review_url": review_url,
        "title": title,
        "rating": rating,
        "price": price,  # ✅ IMPORTANT
        "features": features,
        "reviews": reviews[:30],
    }