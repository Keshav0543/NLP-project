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

            # ✅ Step 3: Smart keyword extraction (FIXED INDENTATION)
            title = results["title"].lower()
            keywords = []

            for word in title.split():
                if any(x in word for x in ["lg", "samsung", "sony", "whirlpool"]):
                    keywords.append(word)
                if "l" in word or "litre" in word:
                    keywords.append(word)

            # fallback
            if len(keywords) < 2:
                keywords = title.split()[:3]

            product_name = " ".join(keywords)

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