from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import random
import string
import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque, Counter
import threading
import time
import feedparser
import re

app = Flask(__name__)

# Mail config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

# CoinGecko API for descriptions
COINGECKO_API = os.getenv("COIN_GECKO_API")

# Price tracking and history
PRICE_HISTORY = defaultdict(list)
TOP_RISER = (None, 0, 0.0)
STAR_RISER = (None, 0, 0.0)
TOP_RISER_HISTORY = deque(maxlen=50)
STAR_RISER_HISTORY = deque(maxlen=10)
LAST_TOP_RISER = None
LAST_TOP_RISER_TIME = datetime.min
LAST_STAR_RISER_UPDATE = datetime.min
COIN_DESCRIPTIONS = {}

# ✅ Coinbase-tracked coin list
COINS = ["btc", "eth", "sol", "ada", "xrp", "doge", "matic", "link", "dot", "ltc"]

# === Utility: Coinbase price fetch ===
def fetch_price(coin_symbol):
    try:
        url = f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot"
        response = requests.get(url)
        if response.status_code == 200:
            return round(float(response.json()['data']['amount']), 2)
    except Exception as e:
        print(f"🚨 Coinbase price error: {e}")
    return None

# === Utility: CoinGecko description fetch ===
def fetch_coin_description(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            desc_html = data.get("description", {}).get("en", "")
            desc = re.sub(r'<.*?>', '', desc_html).strip()
            return desc[:300]
    except Exception as e:
        print(f"⚠️ Description error for {coin_id}: {e}")
    return ""

# === Monitor coin prices ===
def monitor_risers():
    global TOP_RISER, STAR_RISER
    MIN_RISE = 0.05
    STAR_THRESHOLD = 5.0
    LIMIT = 720

    while True:
        try:
            top_riser, top_change = None, 0
            star_riser, star_change = None, 0

            for coin in COINS:
                price = fetch_price(coin)
                if price is not None:
                    PRICE_HISTORY[coin].append(price)
                    PRICE_HISTORY[coin] = PRICE_HISTORY[coin][-LIMIT:]

                    if len(PRICE_HISTORY[coin]) >= 2:
                        initial = PRICE_HISTORY[coin][0]
                        min_price = min(PRICE_HISTORY[coin])
                        change = max(
                            ((price - initial) / initial) * 100,
                            ((price - min_price) / min_price) * 100
                        )

                        if change > top_change and change >= MIN_RISE:
                            top_riser, top_change = coin, change
                        if change >= STAR_THRESHOLD and change > star_change:
                            star_riser, star_change = coin, change

            if top_riser:
                price = fetch_price(top_riser)
                now = datetime.now()
                if price:
                    TOP_RISER = (top_riser, round(top_change, 2), round(price, 2))
                    if LAST_TOP_RISER != top_riser:
                        TOP_RISER_HISTORY.appendleft({"coin": top_riser, "timestamp": now})
                    global LAST_TOP_RISER, LAST_TOP_RISER_TIME
                    LAST_TOP_RISER, LAST_TOP_RISER_TIME = top_riser, now

                    if top_riser not in COIN_DESCRIPTIONS:
                        COIN_DESCRIPTIONS[top_riser] = fetch_coin_description(top_riser)

                    if (now - LAST_STAR_RISER_UPDATE) >= timedelta(minutes=30):
                        recent_30 = [e["coin"] for e in TOP_RISER_HISTORY if (now - e["timestamp"]) <= timedelta(minutes=30)]
                        if recent_30:
                            common_30, _ = Counter(recent_30).most_common(1)[0]
                            if not STAR_RISER_HISTORY or STAR_RISER_HISTORY[0] != common_30:
                                STAR_RISER_HISTORY.appendleft(common_30)
                                print(f"📜 Star Riser History Updated: {common_30}")
                        global LAST_STAR_RISER_UPDATE
                        LAST_STAR_RISER_UPDATE = now
                        STAR_RISER = (top_riser, round(top_change, 2), round(price, 2))

        except Exception as e:
            print(f"🚨 Monitor error: {e}")
        time.sleep(5)

# === ROUTES ===
@app.route("/")
def index():
    return render_template("riser_monitor.html", COIN_GECKO_API=COINGECKO_API)

@app.route("/api/top-riser")
def top_riser_api():
    if TOP_RISER and TOP_RISER[0]:
        coin = TOP_RISER[0]
        return jsonify({
            "coin": coin,
            "change": f"{TOP_RISER[1]:.2f}",
            "price": f"{TOP_RISER[2]:.2f}",
            "description": COIN_DESCRIPTIONS.get(coin, "")
        })
    return jsonify({"coin": "none", "change": "0", "price": "0", "description": ""})

@app.route("/api/star-riser")
def star_riser_api():
    if STAR_RISER and STAR_RISER[0]:
        return jsonify({
            "coin": STAR_RISER[0],
            "change": f"{STAR_RISER[1]:.2f}",
            "price": f"{STAR_RISER[2]:.2f}"
        })
    return jsonify({"coin": "none", "change": "0", "price": "0"})

@app.route("/api/crypto-news")
def crypto_news():
    try:
        feed = feedparser.parse("https://cointelegraph.com/rss")
        news = [{"title": e.title, "link": e.link, "published": e.published} for e in feed.entries[:5]]
        return jsonify(news)
    except Exception as e:
        print(f"📰 RSS error: {e}")
        return jsonify([])

@app.route("/api/top-riser-history")
def top_riser_history_api():
    return jsonify(list(TOP_RISER_HISTORY))

@app.route("/api/star-riser-history")
def star_riser_history_api():
    return jsonify(list(STAR_RISER_HISTORY))

# === Background monitor ===
threading.Thread(target=monitor_risers, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
