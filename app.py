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

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['COIN_GECKO_API'] = os.getenv('MAIL_PASSWORD')

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

COIN_DESCRIPTIONS = {
    import os
from flask import render_template

@app.route('/')
def dashboard():
    coingecko_api = os.getenv("COIN_GECKO_API")  # securely loaded from Render
    return render_template('riser_monitor.html', COIN_GECKO_API=coingecko_api)

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

# Monitor top risers
def monitor_risers():
    global TOP_RISER, STAR_RISER
    MINIMUM_RISE_PERCENTAGE = 0.05
    STAR_THRESHOLD_PERCENTAGE = 5.0
    ONE_HOUR_LIMIT = 720  # 5 sec checks = 1 hour

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
                    PRICE_HISTORY[coin] = PRICE_HISTORY[coin][-ONE_HOUR_LIMIT:]

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

                    now = datetime.now()
                    global LAST_TOP_RISER, LAST_TOP_RISER_TIME, TOP_RISER_HISTORY
                    global STAR_RISER, STAR_RISER_HISTORY, LAST_STAR_RISER_UPDATE

                    # ✅ Top Riser History logic
                    if LAST_TOP_RISER != top_riser:
                        LAST_TOP_RISER = top_riser
                        LAST_TOP_RISER_TIME = now
                        TOP_RISER_HISTORY.appendleft({"coin": top_riser, "timestamp": now})
                    elif (now - LAST_TOP_RISER_TIME) >= timedelta(minutes=5):
                        LAST_TOP_RISER_TIME = now
                        TOP_RISER_HISTORY.appendleft({"coin": top_riser, "timestamp": now})

                    # ✅ Star Riser trigger logic
                    top5 = list(TOP_RISER_HISTORY)[:5]
                    coin_counts = Counter([e["coin"] for e in top5])
                    if coin_counts:
                        most_common, freq = coin_counts.most_common(1)[0]
                        if freq >= 3 or (LAST_TOP_RISER == top_riser and (now - LAST_TOP_RISER_TIME) >= timedelta(minutes=5)):
                            star_price = fetch_price(top_riser)
                            if star_price:
                                STAR_RISER = (top_riser, round(freq * 1.5, 2), round(star_price, 2))
                                print(f"⭐ STAR RISER Updated: {STAR_RISER}")

                    # ✅ Star Riser History (every 30 mins)
                    if (now - LAST_STAR_RISER_UPDATE) >= timedelta(minutes=30):
                        recent_30 = [e["coin"] for e in TOP_RISER_HISTORY if (now - e["timestamp"]) <= timedelta(minutes=30)]
                        if recent_30:
                            common_30, _ = Counter(recent_30).most_common(1)[0]
                            if not STAR_RISER_HISTORY or STAR_RISER_HISTORY[0] != common_30:
                                STAR_RISER_HISTORY.appendleft(common_30)
                                print(f"📜 Star Riser History Updated: {common_30}")
                        LAST_STAR_RISER_UPDATE = now

        except Exception as e:
            print(f"🚨 Error in riser monitor: {e}")

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
        # handle form submission
        ...
        return redirect(url_for('verify_email'))

    # If GET, just show the form
    return render_template('signup.html')

@app.route("/api/top-riser")
def top_riser_api():
    if TOP_RISER and TOP_RISER[0] is not None:
        coin = TOP_RISER[0]
        if coin not in COIN_DESCRIPTIONS:
            COIN_DESCRIPTIONS[coin] = fetch_coin_description(coin)
        return jsonify({
            "coin": coin,
            "change": f"{TOP_RISER[1]:.2f}",
            "price": f"{TOP_RISER[2]:.2f}",
            "description": COIN_DESCRIPTIONS[coin]
        })
    return jsonify({
        "coin": "No Riser",
        "change": "0",
        "price": "0",
        "description": ""
    })

@app.route("/api/star-riser")
def star_riser_api():
    if STAR_RISER and STAR_RISER[0] is not None:
        return jsonify({
            "coin": STAR_RISER[0],
            "change": f"{STAR_RISER[1]:.2f}",
            "price": f"{STAR_RISER[2]:.2f}"
        })
    return jsonify({
        "coin": "No Star Riser",
        "change": "0",
        "price": "0"
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


