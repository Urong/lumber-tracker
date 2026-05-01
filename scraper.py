"""
Lumber price scraper using curl_cffi to bypass Cloudflare.
Reads existing data.json, appends new readings, and saves back.
"""

import json
import os
import re  # still used in parse_price
from datetime import datetime, timezone
from curl_cffi import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Add or remove products here.
# "id" is just a short label used as the key in data.json.
# --------------------------------------------------------------------------
PRODUCTS = [
    {
        "id": "cedar_4x4x10",
        "name": '4"x4"x10\' Western Red Cedar',
        "url": "https://www.rona.ca/en/product/4-in-x-4-in-x-10-ft-western-red-cedar-rcd4410ap-10555019",
    },
    # Add more products below, same format:
    # {
    #     "id": "cedar_2x4x8",
    #     "name": '2"x4"x8\' Western Red Cedar',
    #     "url": "https://www.rona.ca/en/product/...",
    # },
]

DATA_FILE = "data.json"


def fetch_price(url: str) -> str | None:
    """Fetch a Rona product page and extract the price string."""
    try:
        response = requests.get(
            url,
            impersonate="chrome120",
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        print(f"  Request failed: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    integer = soup.select_one(".price-box__price__amount__integer")
    decimal = soup.select_one(".price-box__price__amount__decimal")

    if integer:
        dec = decimal.get_text(strip=True) if decimal else "00"
        raw = f"${integer.get_text(strip=True)}.{dec}"
        print(f"  Found: {raw}")
        return raw

    print("  Price element not found — page structure may have changed.")
    print("  Tip: inspect the page in your browser and look for the price element's class.")
    return None


def parse_price(raw: str) -> float | None:
    """Convert a string like '$59.32' to a float."""
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d.,]", "", raw).replace(",", ".")
    match = re.search(r"\d+\.\d{1,2}", cleaned)
    if match:
        return float(match.group())
    try:
        return float(cleaned)
    except ValueError:
        return None


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    data = load_data()
    timestamp = datetime.now(timezone.utc).isoformat()

    for product in PRODUCTS:
        pid = product["id"]
        print(f"\nScraping: {product['name']}")

        raw = fetch_price(product["url"])
        price = parse_price(raw)

        if pid not in data:
            data[pid] = {
                "name": product["name"],
                "url": product["url"],
                "readings": [],
            }

        data[pid]["readings"].append({
            "timestamp": timestamp,
            "raw": raw,
            "price": price,
        })

        # Keep only the last 180 readings (~3 months of twice-daily checks)
        data[pid]["readings"] = data[pid]["readings"][-180:]

        status = f"${price:.2f}" if price else "FAILED"
        print(f"  → {status}")

    save_data(data)
    print(f"\nSaved {DATA_FILE}")


if __name__ == "__main__":
    main()
