from flask import Flask, render_template, jsonify
import requests
from datetime import datetime
from collections import defaultdict
import threading
import time

app = Flask(__name__)

# Coinbase-compatible top 50 symbols
COINS = [
    "BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "DOGE", "TON", "ADA", "AVAX",
    "SHIB", "WETH", "DOT", "LINK", "MATIC", "WBTC", "TRX", "BCH", "NEAR", "UNI",
    "LTC", "ICP", "LEO", "DAI", "ETC", "APT", "FIL", "STX", "RNDR", "OKB", "CRO",
    "ATOM", "IMX", "FDUSD", "ARB", "HBAR", "TAO", "INJ", "VET", "MKR", "MNT",
    "THETA", "PEPE", "LDO", "QNT", "AAVE", "GRT", "SUI", "USDC", "XLM", "OP"
]

PRICE_HISTORY = defaultdict(list)
TOP_RISER = (None, 0, 0.0)  # Now includes coin, % rise, and price

# Fetch price from Coinbase
def fetch_price(coin_symbol):
    try:
        url = f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return round(float(data['data']['amount']), 2)
    except Exception as e:
        print(f"🚨 Error fetching price for {coin_symbol}: {e}")
    return None

# Monitor top riser every 15 seconds
def monitor_risers():
    global TOP_RISER
    MINIMUM_RISE_PERCENTAGE = 0.05  # 0.05% threshold

    while True:
        try:
            top_riser = None
            top_change = 0
            print("🔍 Checking for top risers...")

            for coin in COINS:
                price = fetch_price(coin)
                if price is not None:
                    PRICE_HISTORY[coin].append(price)
                    PRICE_HISTORY[coin] = PRICE_HISTORY[coin][-10:]  # Keep last 10 prices

                    if len(PRICE_HISTORY[coin]) >= 2:
                        initial = PRICE_HISTORY[coin][0]
                        min_price = min(PRICE_HISTORY[coin])
                        if initial > 0 and min_price > 0:
                            initial_change = ((price - initial) / initial) * 100
                            min_change = ((price - min_price) / min_price) * 100
                            average_change = ((price - (initial + min_price) / 2) / ((initial + min_price) / 2)) * 100
                            change = max(initial_change, min_change, average_change)

                            print(f"📊 {coin}: {change:.2f}% over last 1 minute | Price: ${price:.2f}")

                            if change > top_change and change >= MINIMUM_RISE_PERCENTAGE:
                                top_riser = coin
                                top_change = change

            if top_riser:
                price = fetch_price(top_riser)
                if price is not None:
                    TOP_RISER = (top_riser, round(top_change, 2), round(price, 2))
                    print(f"🚀 New Top Riser: {top_riser} | Change: {top_change:.2f}% | Price: ${price:.2f}")
                else:
                    print(f"⚠️ Could not fetch price for {top_riser}")

        except Exception as e:
            print(f"🚨 Error in riser monitor: {e}")

        time.sleep(15)

@app.route("/")
def index():
    return render_template("riser_monitor.html", top_riser=TOP_RISER)

@app.route("/api/top-riser")
def top_riser_api():
    if TOP_RISER and TOP_RISER[0] is not None:
        return jsonify({
            "coin": TOP_RISER[0],
            "change": f"{TOP_RISER[1]:.2f}%",
            "price": f"${TOP_RISER[2]:.2f}"
        })
    return jsonify({
        "coin": "No Riser",
        "change": "0%",
        "price": "N/A"
    })

import feedparser

@app.route("/api/crypto-news")
def crypto_news():
    try:
        feed = feedparser.parse("https://cointelegraph.com/rss")
        top_items = feed.entries[:5]
        news = []

        for item in top_items:
            news.append({
                "title": item.title,
                "link": item.link,
                "published": item.published
            })

        return jsonify(news)
    except Exception as e:
        print(f"🚨 Failed to fetch RSS feed: {e}")
        return jsonify([])

# Start the monitor in a background thread
threading.Thread(target=monitor_risers, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
