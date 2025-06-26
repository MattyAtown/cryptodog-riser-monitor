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
STAR_RISER_HISTORY = deque(maxlen=10)
LAST_TOP_RISER = None
LAST_TOP_RISER_TIME = datetime.min
LAST_STAR_RISER_UPDATE = datetime.min

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
def resolve_image_path(coin):
    """
    Resolves local image path for a coin using known folders.
    Returns the first match or fallback to generic icon.
    """
    import os

    coin = coin.lower()
    possible_paths = [
        f'static/coins/{coin}.png',
        f'static/cryptodog_riser_monitor/{coin}.png',
        'static/coins/generic.png'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return '/' + path
    return '/static/coins/generic.png'
    
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

COIN_DESCRIPTIONS = {}

def fetch_coin_description(coin_symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_symbol.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            desc_html = data.get("description", {}).get("en", "")
            desc = re.sub(r'<.*?>', '', desc_html).strip()
            return desc[:300]  # Trim to 300 characters
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
                        STAR_RISER = (most_common, round(freq * 1.5, 2), TOP_RISER[2])
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
        msg.body = f"Hey {first},\n\nThanks for signing up to CryptoDog! You're now subscribed to the Arnie Trading Academy."

        try:
            mail.send(msg)
            print(f"✅ Email sent to {email}")
            flash('✅ Email sent! Check your inbox.', 'success')
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            flash('❌ Failed to send email. Try again.', 'error')

        return redirect(url_for('verify_email'))

    return render_template('signup.html')
    # If GET, just show the form
    return render_template('signup.html')

def resolve_image_path(coin):
    """
    Resolves local image path for a coin using known folders.
    Returns the first match or fallback to generic icon.
    """
    import os

    coin = coin.lower()
    possible_paths = [
        f'static/coins/{coin}.png',
        f'static/cryptodog_riser_monitor/{coin}.png',
        'static/coins/generic.png'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return '/' + path
    return '/static/coins/generic.png'

@app.route("/api/top-riser")
def top_riser_api():
    return jsonify({
        "coin": TOP_RISER[0],
        "change": TOP_RISER[1],
        "price": TOP_RISER[2],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/coin-info/<coin>/<float:price>/<float:change>")
def coin_info(coin, price, change):
    if coin not in COIN_DESCRIPTIONS:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin.lower()}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                desc_html = data.get("description", {}).get("en", "")
                desc = re.sub(r'<.*?>', '', desc_html).strip()[:300]
                full_name = data.get("name", coin.upper())
                category = data.get("categories", ["N/A"])[0]
                chart_url = data.get("image", {}).get("large", "")
                volatility = data.get("market_data", {}).get("price_change_percentage_30d", 0)

                COIN_DESCRIPTIONS[coin] = {
                    "desc": desc,
                    "name": full_name,
                    "category": category,
                    "chart_url": chart_url,
                    "volatility": round(volatility, 2)
                }
            else:
                COIN_DESCRIPTIONS[coin] = {
                    "desc": "", "name": coin.upper(), "category": "N/A", "chart_url": "", "volatility": 0
                }
        except Exception as e:
            print(f"⚠️ Error fetching CoinGecko data for {coin}: {e}")
            COIN_DESCRIPTIONS[coin] = {
                "desc": "", "name": coin.upper(), "category": "N/A", "chart_url": "", "volatility": 0
            }

    meta = COIN_DESCRIPTIONS[coin]
    return jsonify({
        "coin": coin,
        "name": meta["name"],
        "category": meta["category"],
        "description": meta["desc"],
        "volatility": meta["volatility"],
        "price": f"{price:.2f}",
        "change": f"{change:.2f}",
        "image": image,
        "chart_url": meta["chart_url"]
    })

# Optional fallback route, but must not be inside the function above
@app.route("/api/coin-info")
def no_coin_info():
    return jsonify({
        "coin": "No Riser",
        "name": "N/A",
        "category": "N/A",
        "description": "",
        "volatility": 0,
        "price": "0",
        "change": "0",
        "image": "/static/coins/generic.png",
        "chart_url": ""
    })

@app.route("/api/star-riser")
def star_riser_api():
    if STAR_RISER and STAR_RISER[0] is not None:
        coin = STAR_RISER[0]
        price = STAR_RISER[2]
        change = STAR_RISER[1]
        image = resolve_image_path(coin)

        if coin not in COIN_DESCRIPTIONS:
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{coin.lower()}"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    desc_html = data.get("description", {}).get("en", "")
                    desc = re.sub(r'<.*?>', '', desc_html).strip()[:300]
                    full_name = data.get("name", coin.upper())
                    category = data.get("categories", ["N/A"])[0]
                    chart_url = data.get("image", {}).get("large", "")
                    volatility = data.get("market_data", {}).get("price_change_percentage_30d", 0)

                    COIN_DESCRIPTIONS[coin] = {
                        "desc": desc,
                        "name": full_name,
                        "category": category,
                        "chart_url": chart_url,
                        "volatility": round(volatility, 2)
                    }
                else:
                    COIN_DESCRIPTIONS[coin] = {
                        "desc": "", "name": coin.upper(), "category": "N/A", "chart_url": "", "volatility": 0
                    }
            except Exception as e:
                print(f"⚠️ Error fetching CoinGecko data for {coin}: {e}")
                COIN_DESCRIPTIONS[coin] = {
                    "desc": "", "name": coin.upper(), "category": "N/A", "chart_url": "", "volatility": 0
                }

        meta = COIN_DESCRIPTIONS[coin]
        return jsonify({
            "coin": coin,
            "name": meta["name"],
            "category": meta["category"],
            "description": meta["desc"],
            "volatility": meta["volatility"],
            "price": f"{price:.2f}",
            "change": f"{change:.2f}",
            "image": image,
            "chart_url": meta["chart_url"]
        })

    return jsonify({
        "coin": "No Star Riser",
        "name": "N/A",
        "category": "N/A",
        "description": "",
        "volatility": 0,
        "price": "0",
        "change": "0",
        "image": "/static/coins/generic.png",
        "chart_url": ""
    })
    
@app.route("/api/top-riser-history")
def top_riser_history_api():
    return jsonify(list(TOP_RISER_HISTORY))

@app.route("/api/star-riser-history")
def star_riser_history_api():
    return jsonify(list(STAR_RISER_HISTORY))

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


