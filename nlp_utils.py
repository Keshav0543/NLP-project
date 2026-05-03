import re
from collections import Counter

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "is", "it", "this", "that",
    "in", "on", "with", "my", "was", "are", "as", "but", "have", "had", "very", "so",
    "be", "at", "if", "from", "by", "i", "we", "they", "you", "our", "their", "me",
    "its", "them", "after", "before", "can", "could", "would", "should", "just", "too",
    "also", "product", "amazon", "item", "buy", "bought", "use", "used", "using", "one",
}

ASPECT_HINTS = {
    "quality": ["quality", "build", "material", "durable", "cheap", "sturdy", "solid"],
    "battery": ["battery", "charge", "charging", "backup"],
    "price": ["price", "cost", "value", "worth", "expensive", "cheap"],
    "performance": ["fast", "slow", "performance", "speed", "lag", "smooth"],
    "design": ["design", "look", "beautiful", "size", "fit", "compact"],
    "delivery": ["delivery", "packaging", "packed", "shipping", "arrived"],
    "sound": ["sound", "audio", "bass", "noise", "speaker"],
    "display": ["screen", "display", "brightness", "resolution"],
    "comfort": ["comfort", "comfortable", "weight", "lightweight"],
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]{3,}", text.lower())


def _extract_keywords(reviews: list[str]) -> list[tuple[str, int]]:
    words = []
    for review in reviews:
        words.extend([w for w in _tokenize(review) if w not in STOPWORDS])
    return Counter(words).most_common(12)


def _extract_aspects(reviews: list[str]) -> tuple[list[str], list[str]]:
    positives = Counter()
    negatives = Counter()

    for review in reviews:
        score = analyzer.polarity_scores(review)["compound"]
        lower = review.lower()
        for aspect, hints in ASPECT_HINTS.items():
            if any(h in lower for h in hints):
                if score >= 0.2:
                    positives[aspect] += 1
                elif score <= -0.2:
                    negatives[aspect] += 1

    pros = [f"{aspect.title()} is praised in multiple reviews" for aspect, _ in positives.most_common(5)]
    cons = [f"Some buyers complain about {aspect}" for aspect, _ in negatives.most_common(5)]
    return pros, cons


def _verdict(positive: int, negative: int, neutral: int) -> tuple[str, str]:
    total = max(positive + negative + neutral, 1)
    pos_ratio = positive / total
    neg_ratio = negative / total

    if pos_ratio >= 0.6 and neg_ratio <= 0.2:
        return "Recommended", "Most reviews are positive. This looks like a good buy for many users."
    if neg_ratio >= 0.4:
        return "Buy with Caution", "There are several negative reviews. Compare alternatives before buying."
    return "Mixed", "The product has mixed feedback. Check the pros and cons carefully."


def analyze_reviews(product_data: dict) -> dict:
    reviews = product_data["reviews"]
    pos = neg = neu = 0

    detailed_reviews = []
    for review in reviews:
        score = analyzer.polarity_scores(review)["compound"]
        if score >= 0.05:
            label = "Positive"
            pos += 1
        elif score <= -0.05:
            label = "Negative"
            neg += 1
        else:
            label = "Neutral"
            neu += 1

        detailed_reviews.append({
            "text": review,
            "score": round(score, 3),
            "label": label,
        })

    pros, cons = _extract_aspects(reviews)
    verdict, verdict_reason = _verdict(pos, neg, neu)

    return {
        "title": product_data.get("title", "Product"),
        "rating": product_data.get("rating"),
        "product_url": product_data.get("url"),
        "review_url": product_data.get("review_url"),
        "features": product_data.get("features", []),
        "total": len(reviews),
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "keywords": _extract_keywords(reviews),
        "pros": pros or ["Many users mention overall satisfaction"],
        "cons": cons or ["No strong repeated complaint was detected"],
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "sample": detailed_reviews[:8],
    }
