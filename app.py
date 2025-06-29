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
import re

app = Flask(__name__)
app.secret_key = "arnie_secret_2025_crypto_dog"  # Or pull from an environment variable

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

PRICE_HISTORY = defaultdict(list)
TOP_RISER = (None, 0, 0.0)  # (coin, % rise, price)
STAR_RISER = (None, 0, 0.0)  # (coin, % rise, price)

from collections import deque, Counter

TOP_RISER_HISTORY = deque(maxlen=50)
LAST_TOP_RISER = None
LAST_TOP_RISER_TIME = datetime.min
LAST_STAR_RISER_UPDATE = datetime.min
BUY_SESSION = {}
STAR_RISER_HISTORY = deque(maxlen=10)

# Hardcoded verified list of Coinbase USD pairs
COINS = [
    "0xbtc", "1inch", "1st", "aave", "abbc", "abt", "ac3", "act", "ada", "adb", "adx",
    "ae", "aeon", "aergo", "agi", "aion", "ait", "akro", "akt", "alcx", "aleph", "algo",
    "alis", "alpha", "alx", "amb", "amlt", "amp", "ampl", "anc", "anj", "ankr", "ant",
    "aph", "apl", "appc", "apw", "apy", "ar", "ardr", "ark", "armor", "arn", "aro",
    "arrr", "ast", "atmi", "atom", "auc", "aura", "auto", "avax", "awc", "axp", "bac",
    "bal", "band", "bao", "bat", "bay", "bbr", "bcd", "bch", "bcha", "bcn", "bco", "bel",
    "beta", "bf", "bifi", "bix", "blk", "block", "blt", "blue", "blz", "bnb", "bnt",
    "bond", "bondly", "bora", "box", "bpt", "brd", "btc++", "btc", "btcd", "btcp", "btg",
    "btmx", "bto", "bts", "btt", "btu", "bu", "bunny", "busd", "bwt", "bz", "bznt",
    "bzrx", "c20", "c98", "cake", "capp", "car", "card", "cbat", "cbt", "cdai", "cdt",
    "cel", "celo", "celr", "cennz", "ceth", "cfx", "chai", "chat", "chsb", "chz", "ckb",
    "clo", "cloak", "clout", "cmt", "cnd", "cnx", "comp", "coni", "cosm", "coti", "cov",
    "cova", "cover", "cpc", "cre", "cream", "cred", "crep", "cro", "crpt", "crv", "cs",
    "csai", "csc", "ctc", "ctxc", "cusdc", "cv", "cvc", "cvp", "cvt", "cvx", "cwbtc",
    "czrx", "dadi", "dafi", "dag", "dai", "dash", "dat", "data", "datx", "dbc", "dcn",
    "dcr", "dct", "ddd", "dent", "deri", "dfi", "dft", "dfyn", "dgb", "dgd", "dgtx",
    "divi", "dlt", "dmt", "dnt", "dock", "dodo", "doge", "dor", "dot", "drgn", "drop",
    "dta", "dtr", "dtx", "dvf", "dxd", "dxt", "edg", "edo", "efi", "efx", "egld", "egt",
    "ekg", "ekt", "ela", "elec", "elf", "emc", "emc2", "eng", "enj", "eos", "eosdac",
    "ern", "esd", "esp", "ess", "etc", "eth", "etn", "etp", "etz", "evx", "ewt", "exrn",
    "exy", "fab", "fct", "feed", "fei", "fet", "fida", "fil", "filda", "flow", "fota",
    "fox", "frax", "frm", "front", "fsn", "ft", "ftc", "ftm", "ftt", "fuel", "fun",
    "fxc", "fxt", "gala", "gdc", "gem", "gen", "gno", "gnt", "gnx", "go", "goc", "got",
    "grin", "grs", "grt", "gsc", "gswap", "gt", "gtc", "gto", "gusd", "gvt", "gxs",
    "hakka", "happy", "hbar", "hc", "hedg", "her", "hex", "high", "hive", "hnt",
    "hot-x", "hot", "hpb", "hsr", "ht", "hum", "husd", "hvn", "hydro", "hyn", "hzn",
    "ibat", "icn", "icp", "icx", "idai", "idex", "ieth", "ignis", "iknc", "ilink", "inb",
    "ins", "iost", "iota", "iotx", "iq", "irep", "iris", "isusd", "iusdc", "iwbtc",
    "izrx", "jnt", "jst", "juno", "kava", "kcs", "kda", "keep", "key", "kick", "kin",
    "klay", "klv", "kmd", "knc", "ksm", "lamb", "land", "lba", "lcx", "ldo", "lend",
    "leo", "link", "lit", "lky", "ln", "logo", "loki", "lon", "looks", "loom", "lpt",
    "lqd", "lqty", "lrc", "lsk", "ltc", "lto", "lun", "luna", "lxt", "lym", "maha",
    "maid", "man", "mana", "mars", "math", "matic", "matter", "mbc", "mco", "mcx",
    "mda", "mds", "med", "medx", "met", "mfg", "mft", "mim", "mir", "mith", "mkr",
    "mln", "mngo", "mod", "mot", "mpl", "mta", "mth", "mtl", "mtn", "mvc", "mvl",
    "mvp", "mwat", "mwc", "mxm", "myb", "nano", "nas", "nav", "ncash", "nct", "near",
    "nebl", "nec", "neo", "new", "nex", "nexxo", "nft", "ngc", "niox", "nkn", "nlg",
    "nmr", "noia", "nper", "npxs", "nrg", "nrve", "nu", "nuls", "nxs", "nxt", "oag",
    "oax", "ocean", "ocn", "ode", "ogn", "ohm", "okb", "olt", "omg", "one", "onion",
    "ont", "open", "opium", "orbs", "orc", "orn", "osmo", "ost", "ovc", "oxt", "pai",
    "pal", "par", "part", "pax", "paxg", "pay", "pbr", "pBTC", "pendle", "perl",
    "perp", "pickle", "pivx", "play", "plDAI", "plr", "plUSDC", "png", "pnk", "pnt",
    "poa", "poe", "pokt", "pols", "poly", "pond", "pool", "powr", "ppay", "ppc", "ppp",
    "ppt", "pre", "premia", "prl", "pro", "pros", "prq", "pst", "qash", "qbit", "qi",
    "qkc", "qlc", "qnt", "qsp", "qtum", "quick", "r", "rae", "rari", "ray", "rcn",
    "rdd", "rdn", "ren", "rep", "req", "rev", "rfox", "rhoc", "rif", "rlc", "rook",
    "rose", "rpx", "rsr", "rsv", "rune", "rvn", "s", "sai", "salt", "san", "sand",
    "sar", "scrl", "scrt", "sdt", "seele", "sefi", "sem", "sfi", "sfp", "shib", "shr",
    "shuf", "sia", "skl", "sky", "slt", "smart", "snc", "sngls", "snm", "snt", "snx",
    "sol", "soul", "sov", "spn", "srm", "stake", "steem", "step", "steth", "stmx",
    "storj", "storm", "stpt", "strat", "stx", "sub", "super", "suqa", "sushi",
    "suter", "swap", "swth", "sxdt", "sxp", "sys", "tbtc", "tct", "tel", "tfuel",
    "thc", "theta", "thr", "tio", "titan", "tkn", "tky", "tnb", "tnc", "tnt", "tomo",
    "torn", "tpay", "trac", "trb", "tribe", "trig", "trtl", "tru", "trx", "tryb",
    "tube", "tusd", "twt", "ubq", "ubt", "uft", "ult", "uma", "uncx", "unfi", "uni",
    "unn", "uos", "upp", "usdc", "usdp", "usds", "usdt", "utk", "uuu", "value",
    "veri", "vest", "vet", "vgx", "via", "vib", "vibe", "vidt", "vikky", "vin", "vite",
    "viu", "vlx", "vrs", "vsp", "vsys", "vtc", "wabi", "wan", "waves", "wbtc", "wct",
    "wexpoly", "whale", "wib", "wing", "wings", "woo", "wpr", "wrx", "wtc", "wxt",
    "xas", "xchf", "xem", "xhv", "xin", "xlm", "xlq", "xmark", "xmr", "xmx", "xnk",
    "xns", "xor", "xrd", "xrp", "xsn", "xsr", "xtz", "xvg", "xyo", "xzc", "yfi",
    "yoyo", "zai", "zb", "zco", "zec", "zen", "zil", "zks", "zrx"
]

def get_local_coin_list():
    image_dir = os.path.join("static", "coins")
    try:
        return [f.split(".")[0] for f in os.listdir(image_dir) if f.endswith(".png")]
    except Exception as e:
        print(f"⚠️ Error reading local coin icons: {e}")
        return []
        
def fetch_price(coin_symbol):
    try:
        # First try Coinbase
        url = f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return round(float(data['data']['amount']), 6)
    except Exception as e:
        print(f"⚠️ Coinbase error for {coin_symbol}: {e}")

    # Fallback to CoinGecko
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_symbol.lower()}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            price = data.get(coin_symbol.lower(), {}).get("usd")
            if price:
                return round(float(price), 6)
    except Exception as e:
        print(f"❌ CoinGecko fallback failed for {coin_symbol}: {e}")

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

from datetime import datetime, timedelta
from collections import Counter

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

def resolve_image_path(coin):
    """
    Returns the accessible URL path to the coin image.
    Searches known folders and falls back to generic image if not found.
    """
    if not coin or coin.lower() in ['no riser', 'no star riser']:
        return '/static/coins/generic.png'

    coin = coin.lower()

    search_paths = [
        f'static/coins/{coin}.png',
        f'static/cryptodog_riser_monitor/{coin}.png'
    ]

    for path in search_paths:
        if os.path.isfile(path):
            return '/' + path  # URL-relative

    return '/static/coins/generic.png'

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

@app.route("/api/coin_metadata", methods=["POST"])
def coin_metadata():
    import re
    from flask import request
    coin_ids = request.json.get("coins", [])

    results = {}
    for coin in coin_ids:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin.lower()}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                desc_html = data.get("description", {}).get("en", "")
                desc = re.sub(r'<.*?>', '', desc_html).strip().split('.')[0]
                name = data.get("name", coin.upper())
                categories = data.get("categories", [])
                homepage = data.get("links", {}).get("homepage", [""])[0]

                results[coin] = {
                    "name": name,
                    "category": categories[0] if categories else "N/A",
                    "description": desc,
                    "homepage": homepage
                }
            else:
                results[coin] = {
                    "name": coin.upper(),
                    "category": "N/A",
                    "description": "",
                    "homepage": ""
                }
        except Exception as e:
            results[coin] = {
                "name": coin.upper(),
                "category": "N/A",
                "description": "",
                "homepage": ""
            }

    return jsonify(results)
    
import json  # Make sure this is in your imports if not already

# Load the metadata once when the app starts
with open("coin_metadata.json", "r") as f:
    COIN_METADATA = json.load(f)

@app.route("/api/coin-info/<coin>/<float:price>/<float:change>")
def coin_info(coin, price, change):
    coin_data = COIN_METADATA.get(coin.lower(), {})

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
    session['verified'] = True
    session['subscription'] = 'Tier 1'  # 👈 auto-assign Tier 1 access after verifying
    return render_template('thank_you.html')

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        tier = request.form.get('tier')
        payment_method = request.form.get('payment')

        # Store, process, or route accordingly
        if payment_method == 'crypto':
            return render_template('payment_crypto.html', tier=tier)
        elif payment_method == 'card':
            return render_template('payment_card.html', tier=tier)
        elif payment_method == 'bank':
            return render_template('payment_bank.html', tier=tier)
        else:
            flash("Please choose a valid payment method.", "error")
            return redirect(url_for('subscribe'))

    return render_template('subscribe.html')

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
