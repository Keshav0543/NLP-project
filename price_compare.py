import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def search_flipkart(product_name):
    import requests
    from bs4 import BeautifulSoup

    HEADERS = {"User-Agent": "Mozilla/5.0"}

    # Try original search
    search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '%20')}"

    res = requests.get(search_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    price_tag = soup.select_one("div._30jeq3, div._1_WHN1")
    title_tag = soup.select_one("div._4rR01T, a.s1Q9rs")

    # 🔥 fallback if not found
    if not price_tag:
        alt_name = product_name.split()[0:2]  # very short search
        alt_query = "%20".join(alt_name)

        res = requests.get(f"https://www.flipkart.com/search?q={alt_query}", headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        price_tag = soup.select_one("div._30jeq3, div._1_WHN1")
        title_tag = soup.select_one("div._4rR01T, a.s1Q9rs")

    price = price_tag.text if price_tag else "Unavailable"
    title = title_tag.text if title_tag else "Not found"

    return {
        "platform": "Flipkart",
        "title": title,
        "price": price,
        "link": search_url
    }