from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import random
import string
import requests
import os
from datetime import datetime
from collections import defaultdict
import threading
import time
import feedparser

app = Flask(__name__)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

PRICE_HISTORY = defaultdict(list)
TOP_RISER = (None, 0, 0.0)  # (coin, % rise, price)
STAR_RISER = (None, 0, 0.0)  # (coin, % rise, price)

# Hardcoded verified list of Coinbase USD pairs
COINS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT", "LINK",
    "MATIC", "TRX", "BCH", "NEAR", "UNI", "LTC", "ICP", "DAI", "ETC", "APT",
    "FIL", "STX", "RNDR", "ATOM", "ARB", "HBAR", "INJ", "VET", "MKR", "THETA",
    "PEPE", "LDO", "QNT", "AAVE", "GRT", "SUI", "USDC", "XLM", "OP", "AGIX",
    "ALGO", "BAT", "BAL", "BNT", "CVC", "COMP", "ENS", "FTM", "GALA", "IMX",
    "KNC", "LRC", "MANA", "MASK", "NMR", "OXT", "RLC", "SKL", "SNX", "SAND",
    "ZRX", "ZIL", "YFI", "UMA", "TUSD"
]

# Fetch spot price from Coinbase for a given coin
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

# Monitor top risers
def monitor_risers():
    global TOP_RISER, STAR_RISER
    MINIMUM_RISE_PERCENTAGE = 0.05  # 0.05% threshold for short-term
    STAR_THRESHOLD_PERCENTAGE = 5.0  # 5% threshold for 1-hour change

    ONE_HOUR_LIMIT = 720  # 5 sec checks = 720 in 1 hour

    while True:
        try:
            top_riser = None
            top_change = 0
            star_riser = None
            star_change = 0

            print("🔍 Checking for top risers...")

            for coin in COINS:
                price = fetch_price(coin)
                if price is not None:
                    PRICE_HISTORY[coin].append(price)
                    PRICE_HISTORY[coin] = PRICE_HISTORY[coin][-ONE_HOUR_LIMIT:]  # Up to 1 hour

                    if len(PRICE_HISTORY[coin]) >= 2:
                        initial = PRICE_HISTORY[coin][0]
                        min_price = min(PRICE_HISTORY[coin])
                        if initial > 0 and min_price > 0:
                            initial_change = ((price - initial) / initial) * 100
                            min_change = ((price - min_price) / min_price) * 100
                            average_change = ((price - (initial + min_price) / 2) / ((initial + min_price) / 2)) * 100
                            change = max(initial_change, min_change, average_change)

                            if change > top_change and change >= MINIMUM_RISE_PERCENTAGE:
                                top_riser = coin
                                top_change = change

                            if change >= STAR_THRESHOLD_PERCENTAGE and change > star_change:
                                star_riser = coin
                                star_change = change

            if top_riser:
                price = fetch_price(top_riser)
                if price is not None:
                    TOP_RISER = (top_riser, round(top_change, 2), round(price, 2))
                    print(f"🚀 New Top Riser: {top_riser} | Change: {top_change:.2f}% | Price: ${price:.2f}")

            if star_riser:
                price = fetch_price(star_riser)
                if price is not None:
                    STAR_RISER = (star_riser, round(star_change, 2), round(price, 2))
                    print(f"🌟 STAR RISER: {star_riser} | Change: {star_change:.2f}% | Price: ${price:.2f}")

        except Exception as e:
            print(f"🚨 Error in riser monitor: {e}")

        time.sleep(5)

@app.route("/")
def index():
    return render_template("riser_monitor.html", top_riser=TOP_RISER, star_riser=STAR_RISER)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # your logic here
        ...

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

@app.route("/api/star-riser")
def star_riser_api():
    if STAR_RISER and STAR_RISER[0] is not None:
        return jsonify({
            "coin": STAR_RISER[0],
            "change": f"{STAR_RISER[1]:.2f}%",
            "price": f"${STAR_RISER[2]:.2f}"
        })
    return jsonify({
        "coin": "No Star Riser",
        "change": "0%",
        "price": "N/A"
    })

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
