import os
import re
import time
import threading
import requests
from flask import Flask, jsonify, render_template
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASSWORD")
mail = Mail(app)

COIN_GECKO_API = os.getenv("COIN_GECKO_API")

RISERS = {}
HISTORY = {"top": [], "star": []}

COIN_DESCRIPTIONS = {}

HEADERS = {"accept": "application/json"}

def fetch_coin_description(symbol):
    if symbol.lower() in COIN_DESCRIPTIONS:
        return COIN_DESCRIPTIONS[symbol.lower()]
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            desc_html = data.get("description", {}).get("en", "")
            desc = re.sub(r'<.*?>', '', desc_html).strip()
            trimmed = desc[:300]
            COIN_DESCRIPTIONS[symbol.lower()] = trimmed
            return trimmed
    except Exception as e:
        print(f"⚠️ Failed to fetch description for {symbol}: {e}")
    return ""

def monitor_risers():
    while True:
        try:
            url = "https://api.coinbase.com/v2/exchange-rates?currency=USD"
            r = requests.get(url)
            if r.status_code != 200:
                time.sleep(10)
                continue
            data = r.json()['data']['rates']
            sorted_data = sorted(data.items(), key=lambda x: float(x[1]))[:10]  # simulate top risers
            if sorted_data:
                top = sorted_data[0]
                coin = top[0]
                change = round((1 / float(top[1])) * 100, 2)
                price = round(float(top[1]), 4)
                now = datetime.utcnow().strftime("%H:%M:%S")
                entry = {
                    "coin": coin,
                    "change": change,
                    "price": price,
                    "timestamp": now,
                    "stars": RISERS.get(coin, 0) + 1
                }
                RISERS[coin] = entry["stars"]
                HISTORY["top"].insert(0, entry)
                if len(HISTORY["top"]) > 5:
                    HISTORY["top"].pop()
                # Star logic
                if entry["stars"] >= 3 or entry["change"] > 5:
                    HISTORY["star"].insert(0, entry)
                    if len(HISTORY["star"]) > 5:
                        HISTORY["star"].pop()
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(5)

@app.route('/')
def dashboard():
    return render_template("riser_monitor.html", COIN_GECKO_API=COIN_GECKO_API)

@app.route('/api/top-riser')
def get_top_riser():
    if HISTORY['top']:
        latest = HISTORY['top'][0]
        latest['description'] = fetch_coin_description(latest['coin'])
        return jsonify(latest)
    return jsonify({"coin": "none", "change": 0, "price": 0})

@app.route('/api/star-riser')
def get_star_riser():
    if HISTORY['star']:
        latest = HISTORY['star'][0]
        latest['description'] = fetch_coin_description(latest['coin'])
        return jsonify(latest)
    return jsonify({"coin": "none", "change": 0, "price": 0})

@app.route('/api/top-riser-history')
def top_riser_history():
    return jsonify(HISTORY['top'])

@app.route('/api/star-riser-history')
def star_riser_history():
    return jsonify(HISTORY['star'])

@app.route('/api/crypto-news')
def crypto_news():
    try:
        r = requests.get("https://min-api.cryptocompare.com/data/v2/news/?lang=EN")
        articles = r.json().get("Data", [])[:5]
        return jsonify([{"title": a["title"], "link": a["url"]} for a in articles])
    except:
        return jsonify([])

if __name__ == '__main__':
    threading.Thread(target=monitor_risers, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
