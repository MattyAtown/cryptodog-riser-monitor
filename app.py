from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import random
import string
import requests
import os
from datetime import datetime
import threading
import time
import feedparser
import re
import json

app = Flask(__name__)
app.secret_key = "arnie_secret_2025_crypto_dog"  # Or pull from an environment variable

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

from collections import deque, Counter

TOP_RISER_HISTORY = deque(maxlen=50)
LAST_TOP_RISER = None
LAST_TOP_RISER_TIME = datetime.min
LAST_STAR_RISER_UPDATE = datetime.min
BUY_SESSION = {}
STAR_RISER_HISTORY = deque(maxlen=10)

def get_top_market_cap_symbols(limit=100):
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return [coin["symbol"].lower() for coin in data]
    except Exception as e:
        print(f"⚠️ Failed to fetch top coins: {e}")
    return ["btc", "eth", "xrp", "sol", "ada"]  # fallback list

# --- Function to populate metadata ---
def populate_coin_metadata(coins):
    global COIN_METADATA
    COIN_METADATA = {}
    try:
        with open("static/coin_metadata.json", "r") as f:
            all_data = json.load(f)
            for coin in coins:
                if coin in all_data:
                    COIN_METADATA[coin] = all_data[coin]
                else:
                    COIN_METADATA[coin] = {
                        "name": coin.upper(),
                        "category": "Unknown",
                        "description": "No description available."
                    }
        print(f"✅ Coin metadata populated for {len(COIN_METADATA)} coins.")
    except Exception as e:
        print(f"⚠️ Failed to populate metadata: {e}")


COIN_METADATA = {}
COINS = get_top_market_cap_symbols(100)
populate_coin_metadata(COINS)
PRICE_HISTORY = {coin: [] for coin in COINS}
TOP_RISER = (None, 0, 0.0)  # (coin, % rise, price)
STAR_RISER = (None, 0, 0.0)  # (coin, % rise, price)


def fetch_price(coin_symbol):
    try:
        # Try Coinbase first
        coinbase_url = f"https://api.coinbase.com/v2/prices/{coin_symbol.upper()}-USD/spot"
        cb_response = requests.get(coinbase_url)
        if cb_response.status_code == 200:
            return float(cb_response.json()["data"]["amount"])
    except Exception as e:
        print(f"⚠️ Coinbase error for {coin_symbol}: {e}")

    try:
        # Fallback to CoinGecko
        gecko_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_symbol.lower()}&vs_currencies=usd"
        gecko_response = requests.get(gecko_url)
        if gecko_response.status_code == 200:
            data = gecko_response.json()
            return data.get(coin_symbol.lower(), {}).get("usd")
    except Exception as e:
        print(f"⚠️ CoinGecko error for {coin_symbol}: {e}")

    print(f"❌ All APIs failed for {coin_symbol}")
    return None

def fetch_coin_description(coin_symbol):
    if coin_symbol.lower() in COIN_METADATA:
        return COIN_METADATA[coin_symbol.lower()].get("description", "")

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_symbol.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            desc_html = data.get("description", {}).get("en", "")
            desc = re.sub(r'<.*?>', '', desc_html).strip()
            return desc[:300]
    except Exception as e:
        print(f"⚠️ Failed to fetch description for {coin_symbol}: {e}")
    return ""

def monitor_risers():
    global TOP_RISER, STAR_RISER
    global LAST_TOP_RISER, LAST_TOP_RISER_TIME, LAST_STAR_RISER_UPDATE
    global TOP_RISER_HISTORY, STAR_RISER_HISTORY

    STEP_LIMIT = 3  # 3 checks = 15 seconds
    MIN_STEP = 0.000000000001  # Minimum rise per step
    STAR_RISER_MIN_PERCENT = 1.0  # Min total % rise for Star Riser eligibility

    print("🚀 CryptoDog Riser Monitor started.")

    while True:
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            top_riser_candidate = None
            max_rise_pct = 0.0
            final_price = 0.0

            for coin in COINS:
                price = fetch_price(coin)
                if price is None:
                    continue

                PRICE_HISTORY[coin].append(price)
                PRICE_HISTORY[coin] = PRICE_HISTORY[coin][-STEP_LIMIT:]

                if len(PRICE_HISTORY[coin]) == STEP_LIMIT:
                    p1, p2, p3 = PRICE_HISTORY[coin]

                    if (p2 > p1 + MIN_STEP) and (p3 > p2 + MIN_STEP):
                        rise_pct = ((p3 - p1) / p1) * 100

                        print(f"[{timestamp}] ✅ {coin.upper()} rose 3x | t1: {p1:.6f} → t3: {p3:.6f} | Δ%: {rise_pct:.5f}")

                        if rise_pct > max_rise_pct:
                            top_riser_candidate = coin
                            max_rise_pct = rise_pct
                            final_price = p3

            if top_riser_candidate:
                TOP_RISER = (top_riser_candidate, round(max_rise_pct, 5), round(final_price, 5))
                print(f"[{timestamp}] 🔝 TOP RISER: {TOP_RISER[0].upper()} | +{TOP_RISER[1]}% | ${TOP_RISER[2]}")

                # Update Top Riser History
                if LAST_TOP_RISER != TOP_RISER[0]:
                    LAST_TOP_RISER = TOP_RISER[0]
                    LAST_TOP_RISER_TIME = now
                    TOP_RISER_HISTORY.appendleft({"coin": TOP_RISER[0], "timestamp": now})
                elif (now - LAST_TOP_RISER_TIME) >= timedelta(seconds=15):
                    LAST_TOP_RISER_TIME = now
                    TOP_RISER_HISTORY.appendleft({"coin": TOP_RISER[0], "timestamp": now})

                # Star Riser logic
                recent_top_risers = [entry["coin"] for entry in TOP_RISER_HISTORY if (now - entry["timestamp"]) <= timedelta(seconds=60)]
                coin_counts = Counter(recent_top_risers)

                if coin_counts:
                    most_common, freq = coin_counts.most_common(1)[0]

                    if TOP_RISER[0] == most_common and TOP_RISER[1] >= STAR_RISER_MIN_PERCENT:
                        STAR_RISER = (most_common, round(freq * 1.5, 2), TOP_RISER[2], timestamp)
                        print(f"[{timestamp}] 🌟 STAR RISER: {STAR_RISER[0].upper()} | Score: {STAR_RISER[1]} | Price: ${STAR_RISER[2]}")

                # Star Riser History update every 30 mins
                if (now - LAST_STAR_RISER_UPDATE) >= timedelta(minutes=30):
                    recent_30 = [e["coin"] for e in TOP_RISER_HISTORY if (now - e["timestamp"]) <= timedelta(minutes=30)]
                    if recent_30:
                        common_30, _ = Counter(recent_30).most_common(1)[0]
                        if not STAR_RISER_HISTORY or STAR_RISER_HISTORY[0] != common_30:
                            STAR_RISER_HISTORY.appendleft(common_30)
                            print(f"[{timestamp}] 📜 Star Riser History Updated: {common_30}")
                    LAST_STAR_RISER_UPDATE = now

        except Exception as e:
            print(f"[{timestamp}] 🚨 Error in monitor_risers(): {e}")

        time.sleep(5)
        
@app.route("/")
def index():
    return render_template("riser_monitor.html", top_riser=TOP_RISER, star_riser=STAR_RISER)

@app.route('/verify_email')
def verify_email():
    return render_template('verify.html')

@app.route('/verify_complete')
def verify_complete():
    session['verified'] = True
    flash("✅ Email verified! Now choose your subscription.", "success")
    return redirect('/subscribe')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        first = request.form.get('first')

        msg = Message(
            subject="Welcome to CryptoDog | Learn with Arnie",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"""Hey {first},

Thanks for signing up to CryptoDog! You're now subscribed to the Arnie Trading Academy.

👉 Click here to confirm your subscription and begin your journey:
https://cryptodoglive.onrender.com/thank-you

See you inside!
– Arnie 🐶"""

        try:
            mail.send(msg)
            print(f"✅ Email sent to {email}")
            flash('✅ Email sent! Check your inbox.', 'success')
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            flash('❌ Failed to send email. Try again.', 'error')

        return redirect(url_for('verify_email'))  # ✅ keeps user experience flowing

    return render_template('signup.html')  # ✅ necessary for showing form on GET request



@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if not session.get('verified'):
        flash("⚠️ Please verify your email before subscribing.", "error")
        return redirect('/verify_email')
import os

# Optional global cache to avoid repeated API calls
COINGECKO_IMAGE_CACHE = {}

def resolve_image_path(coin):
    if not coin:
        return '/static/coins/generic.png'

    # Try local image
    local_path = f"static/coins/{coin.lower()}.png"
    if os.path.isfile(local_path):
        return f"/static/coins/{coin.lower()}.png"

    # Try CoinGecko logo fallback
    if coin.lower() in COINGECKO_IMAGE_CACHE:
        return COINGECKO_IMAGE_CACHE[coin.lower()]

    try:
        # Fetch from CoinGecko by symbol → id mapping
        search_url = f"https://api.coingecko.com/api/v3/coins/list"
        response = requests.get(search_url)
        if response.status_code == 200:
            coins = response.json()
            coin_entry = next((c for c in coins if c['symbol'].lower() == coin.lower()), None)
            if coin_entry:
                coin_id = coin_entry['id']
                coin_data_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                coin_data = requests.get(coin_data_url).json()
                image_url = coin_data.get("image", {}).get("thumb")
                if image_url:
                    COINGECKO_IMAGE_CACHE[coin.lower()] = image_url  # Cache it
                    return image_url
    except Exception as e:
        print(f"⚠️ CoinGecko logo fallback failed for {coin}: {e}")

    # Final fallback
    return '/static/coins/generic.png'
    if request.method == 'POST':
        tier = request.form.get('tier')
        session['subscription'] = tier

        if tier == 'Tier 1':
            flash('✅ Tier 1 Activated! You can now begin your free training.', 'success')
            return redirect('/')  # ✅ Go to dashboard, NOT tier1 directly

        payment_method = request.form.get('payment')
        if not payment_method:
            flash('❌ Please select a payment method.', 'error')
            return redirect('/subscribe')

        session['payment_method'] = payment_method
        return redirect('/payment_crypto')

    return render_template('subscribe.html')

@app.route('/tier1')
def tier1():
    if 'user_email' not in session or session.get('subscription') != 'Tier 1' or not session.get('verified'):
        flash("⛔ Please sign up, verify your email, and activate Tier 1 to access.", "error")
        return redirect('/signup')
    return render_template('tier_1_crypto_intro.html')

@app.route("/api/top-riser")
def top_riser_api():
    return jsonify({
        "coin": TOP_RISER[0],
        "change": TOP_RISER[1],
        "price": TOP_RISER[2],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/star-riser")
def star_riser_api():
    return jsonify({
        "coin": STAR_RISER[0],
        "change": STAR_RISER[1],
        "price": STAR_RISER[2],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/price/<coin>')
def get_price(coin):
    price_data = fetch_price(coin.upper())  # This is your own function fetching the price
    
    if price_data is None:
        return jsonify({"error": "Price not available"}), 404

    return jsonify({"price": round(price_data, 6)})

import json

# Load or initialize coin metadata
try:
    with open("coin_metadata.json", "r") as f:
        COIN_METADATA = json.load(f)
except Exception as e:
    print(f"⚠️ Failed to load coin_metadata.json: {e}")
    COIN_METADATA = {}

# Helper to fetch and save metadata
def fetch_and_save_coin_metadata(coins):
    updated_data = {}

    for coin in coins:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin.lower()}"
            headers = {"x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY")}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                desc_html = data.get("description", {}).get("en", "")
                desc = re.sub(r'<.*?>', '', desc_html).strip().split('.')[0]
                name = data.get("name", coin.upper())
                categories = data.get("categories", [])
                homepage = data.get("links", {}).get("homepage", [""])[0]

                updated_data[coin.lower()] = {
                    "name": name,
                    "category": categories[0] if categories else "N/A",
                    "description": desc,
                    "homepage": homepage,
                    "chart_url": "",  # Optional future enhancement
                    "volatility": 0   # Placeholder for future metrics
                }
        except Exception as e:
            print(f"❌ Error updating metadata for {coin}: {e}")

    # Update and persist
    COIN_METADATA.update(updated_data)
    with open("coin_metadata.json", "w") as f:
        json.dump(COIN_METADATA, f, indent=2)

    return updated_data

# POST route to bulk-update metadata
@app.route("/api/coin_metadata", methods=["POST"])
def coin_metadata():
    coin_ids = request.json.get("coins", [])
    updated = fetch_and_save_coin_metadata(coin_ids)
    return jsonify(updated)

# Coin info endpoint with on-the-fly fallback
@app.route("/api/coin-info/<coin>/<price>/<change>")
def coin_info(coin, price, change):
    try:
        price = float(price)
        change = float(change)
    except ValueError:
        return jsonify({"error": "Invalid price or change format"}), 400

    coin_lower = coin.lower()
    coin_data = COIN_METADATA.get(coin_lower)

    if not coin_data:
        print(f"⚠️ Metadata for {coin} not found. Fetching on-the-fly...")
        fetched = fetch_and_save_coin_metadata([coin_lower])
        coin_data = fetched.get(coin_lower, {
            "name": coin.upper(),
            "category": "N/A",
            "description": "",
            "chart_url": "",
            "volatility": 0
        })

    return jsonify({
        "coin": coin,
        "name": coin_data.get("name", coin.upper()),
        "category": coin_data.get("category", "N/A"),
        "description": coin_data.get("description", ""),
        "volatility": coin_data.get("volatility", 0),
        "price": f"{price:.2f}",
        "change": f"{change:.2f}",
        "image": resolve_image_path(coin),
        "chart_url": coin_data.get("chart_url", "")
    })

    
@app.route("/api/top-riser-history")
def top_riser_history_api():
    return jsonify(list(TOP_RISER_HISTORY))

@app.route("/api/buy", methods=["POST"])
def simulate_buy():
    data = request.get_json()
    coin = data.get("coin")
    amount = float(data.get("amount", 0))

    price = fetch_price(coin)
    if price is None:
        return jsonify({"error": "Price not available"}), 400

    now = datetime.utcnow()
    BUY_SESSION[coin] = {
        "amount": amount,
        "buy_price": price,
        "timestamp": now
    }
    return jsonify({
        "status": "buy_confirmed",
        "coin": coin,
        "amount": amount,
        "buy_price": price,
        "timestamp": now.isoformat()
    })

@app.route("/api/buy-summary", methods=["POST"])
def buy_summary():
    data = request.get_json()
    coin = data.get("coin")

    if coin not in BUY_SESSION:
        return jsonify({"error": "No active buy session for this coin"}), 400

    session = BUY_SESSION[coin]
    current_price = fetch_price(coin)
    if current_price is None:
        return jsonify({"error": "Current price not available"}), 400

    bought_amount = session["amount"]
    buy_price = session["buy_price"]
    buy_time = session["timestamp"]

    # Calculate gain/loss
    coins_bought = bought_amount / buy_price
    current_value = coins_bought * current_price
    difference = round(current_value - bought_amount, 2)
    percentage = round((difference / bought_amount) * 100, 2)

    return jsonify({
        "coin": coin.upper(),
        "initial_investment": bought_amount,
        "buy_price": buy_price,
        "current_price": current_price,
        "current_value": round(current_value, 2),
        "gain_loss": difference,
        "percent_change": percentage,
        "since": buy_time.isoformat()
    })

@app.route('/thank-you')
def thank_you():
    if 'user_email' not in session:
        return redirect('/signup')  # Or login page if more appropriate

    # Only allow if verified and on Tier 1
    if session.get('subscription') != 'Tier 1' or not session.get('verified'):
        return redirect('/subscribe')


@app.route('/tier-1')
def tier_one():
    return render_template('tier_1_crypto_intro.html')

@app.route("/api/star-riser-history")
def star_riser_history_api():
    return jsonify(list(STAR_RISER_HISTORY))

@app.route('/pay/crypto')
def pay_crypto():
    tier = request.args.get('tier', 'Tier Unknown')
    return render_template('payment_crypto.html', tier=tier)

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
