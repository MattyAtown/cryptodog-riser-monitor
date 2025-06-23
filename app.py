import os
import re
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from collections import defaultdict, deque

app = Flask(__name__)

# Load CoinGecko API key from environment
COINGECKO_API_KEY = os.getenv("COIN_GECKO_API")

# In-memory store for risers
top_risers = deque(maxlen=5)
star_risers = deque(maxlen=4)
coin_streaks = defaultdict(int)
last_star_riser_update = datetime.utcnow() - timedelta(minutes=31)

@app.route('/')
def dashboard():
    return render_template("riser_monitor.html", COIN_GECKO_API=COINGECKO_API_KEY)

@app.route('/api/coin-info/<coin_id>')
def get_coin_info(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    headers = {
        "accept": "application/json",
        "x-cg-pro-api-key": COINGECKO_API_KEY
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch coin info"}), 400

        data = res.json()
        desc_html = data.get("description", {}).get("en", "")
        desc = re.sub(r'<.*?>', '', desc_html).strip()[:300]
        info = {
            "name": data.get("name", coin_id.upper()),
            "category": data.get("categories", ["General"])[0],
            "purpose": data.get("asset_platform_id", "Blockchain"),
            "description": desc,
            "chart_url": f"https://www.coingecko.com/coins/{coin_id}/sparkline.svg"
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/top-riser')
def top_riser():
    if not top_risers:
        return jsonify({"coin": "none", "price": "0", "change": "0"})
    latest = top_risers[-1]
    return jsonify(latest)

@app.route('/api/star-riser')
def star_riser():
    if not star_risers:
        return jsonify({"coin": "none", "price": "0", "change": "0"})
    latest = star_risers[-1]
    return jsonify(latest)

@app.route('/api/crypto-news')
def crypto_news():
    return jsonify([
        {"title": "Bitcoin hits new high!", "link": "https://example.com/1"},
        {"title": "Ethereum rises sharply", "link": "https://example.com/2"},
        {"title": "Market update: DOGE climbs", "link": "https://example.com/3"},
        {"title": "Altcoin season incoming?", "link": "https://example.com/4"},
        {"title": "Regulators eye crypto", "link": "https://example.com/5"}
    ])

def monitor_risers():
    import time
    from random import choice, uniform
    coins = ['btc', 'eth', 'sol', 'ada', 'xrp', 'doge', 'matic', 'dot', 'ltc', 'link']
    while True:
        coin = choice(coins)
        price = round(uniform(0.1, 70000), 2)
        change = round(uniform(2, 10), 2)

        print(f"\U0001F50D Checking for top risers...")
        print(f"\U0001F680 New Top Riser: {coin} | Change: {change}% | Price: ${price}")

        top_risers.append({"coin": coin, "price": str(price), "change": str(change)})

        coin_streaks[coin] += 1

        global last_star_riser_update
        now = datetime.utcnow()
        update_due = (now - last_star_riser_update).total_seconds() > 1800

        if update_due or change > 5:
            print(f"\u2B50 Star Riser update: {coin} | Change: {change}% | Price: ${price}")
            star_risers.append({"coin": coin, "price": str(price), "change": str(change)})
            last_star_riser_update = now

        time.sleep(30)

threading.Thread(target=monitor_risers, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, port=10000)
