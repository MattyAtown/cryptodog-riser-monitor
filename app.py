import os
import re
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Load CoinGecko API key from environment
COINGECKO_API_KEY = os.getenv("COIN_GECKO_API")

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
    # Replace this with your real-time logic or Coinbase API pull
    data = {
        "coin": "btc",
        "price": "68000",
        "change": "3.12"
    }
    return jsonify(data)

@app.route('/api/star-riser')
def star_riser():
    # Replace this with your real-time logic or aggregate logic
    data = {
        "coin": "eth",
        "price": "3200",
        "change": "5.44"
    }
    return jsonify(data)

@app.route('/api/crypto-news')
def crypto_news():
    # This could pull from a separate API or mock
    return jsonify([
        {"title": "Bitcoin hits new high!", "link": "https://example.com/1"},
        {"title": "Ethereum rises sharply", "link": "https://example.com/2"},
        {"title": "Market update: DOGE climbs", "link": "https://example.com/3"},
        {"title": "Altcoin season incoming?", "link": "https://example.com/4"},
        {"title": "Regulators eye crypto", "link": "https://example.com/5"}
    ])

if __name__ == '__main__':
    app.run(debug=True, port=10000)
