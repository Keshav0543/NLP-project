import re
from flask import Flask, render_template, request
from scraper import scrape_product_reviews
from nlp_utils import analyze_reviews
from price_compare import search_flipkart

app = Flask(__name__)


# 🔥 helper: convert price string → number
def extract_numeric_price(price_str):
    if not price_str:
        return None
    try:
        cleaned = price_str.replace("₹", "").replace(",", "").strip()
        return int("".join(filter(str.isdigit, cleaned)))
    except:
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    error = None

    if request.method == 'POST':
        url = request.form.get('url')

        try:
            # ✅ Step 1: Scrape data
            product_data = scrape_product_reviews(url)

            # ✅ Step 2: Analyze reviews
            results = analyze_reviews(product_data)

            # ✅ Step 3: Smart keyword extraction — keep brand + model + key specs
            title = results["title"]
            title_lower = title.lower()
            words = title.split()

            keywords = []

            # Always keep brand name
            for word in words:
                if any(brand in word.lower() for brand in [
                    "lg", "samsung", "sony", "whirlpool", "bosch", "haier",
                    "godrej", "voltas", "carrier", "daikin", "panasonic",
                    "apple", "oneplus", "realme", "xiaomi", "oppo", "vivo",
                ]):
                    keywords.append(word)

            # Keep capacity / size tokens (e.g. 265L, 1.5ton, 55inch)
            for word in words:
                if re.search(r'\d+\.?\d*\s*(l|litre|liter|ton|kg|inch|gb|tb|mp)', word.lower()):
                    keywords.append(word)

            # Keep model numbers (mix of letters + digits)
            for word in words:
                if re.search(r'[a-zA-Z]+\d+|\d+[a-zA-Z]+', word):
                    keywords.append(word)

            # Deduplicate while preserving order
            seen_kw = set()
            unique_kw = []
            for w in keywords:
                if w.lower() not in seen_kw:
                    seen_kw.add(w.lower())
                    unique_kw.append(w)
            keywords = unique_kw

            # Fallback: use first 4 words of title
            if len(keywords) < 2:
                keywords = words[:4]

            product_name = " ".join(keywords[:6])  # cap at 6 tokens

            # ✅ Step 4: Get Flipkart price
            flipkart_data = search_flipkart(product_name)

            if not flipkart_data.get("price"):
                flipkart_data["price"] = "Unavailable"

            # ✅ Step 5: Price comparison
            amazon_price = product_data.get("price", "Not found")

            results["price_comparison"] = [
                {
                    "platform": "Amazon",
                    "price": amazon_price,
                    "link": product_data.get("url")
                },
                flipkart_data
            ]

            # 🔥 Step 6: Find BEST DEAL
            prices = []

            for item in results["price_comparison"]:
                numeric = extract_numeric_price(item["price"])
                if numeric:
                    prices.append((numeric, item["platform"]))

            if prices:
                best_price, best_platform = min(prices)
                results["best_deal"] = f"{best_platform} ₹{best_price}"
            else:
                results["best_deal"] = "Not available"

        except Exception as e:
            error = str(e)

    return render_template('index.html', results=results, error=error)


if __name__ == '__main__':
    app.run(debug=True)