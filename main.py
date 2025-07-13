import os
import requests
import time
import math
import schedule
import threading
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === ENV VARIABLES ===
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
# CHAT_ID no longer needed globally; we'll use dynamic user_id
subscribed_users = set()

# === NIFTY 200 SYMBOLS ===
# === NIFTY 200 SYMBOLS ===
nifty_200_symbols = [
    "3MINDIA.NS", "AARTIIND.NS", "ABB.NS", "ACC.NS", "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ADANIPOWER.NS",
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "AUROPHARMA.NS",
    "AVANTIFEED.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BANDHANBNK.NS",
    "BANKBARODA.NS", "BATAINDIA.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BIOCON.NS", "BOSCHLTD.NS",
    "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS",
    "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUB.NS", "CUMMINSIND.NS", "DABUR.NS",
    "DALBHARAT.NS", "DEEPAKNTR.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS",
    "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GLAND.NS", "GMRINFRA.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS",
    "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFC.NS", "HDFCAMC.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDPETRO.NS", "HINDUNILVR.NS", "HONAUT.NS", "ICICIBANK.NS",
    "ICICIGI.NS", "ICICIPRULI.NS", "IDEA.NS", "IDFC.NS", "IDFCFIRSTB.NS", "IEX.NS", "IGL.NS", "INDHOTEL.NS", "INDIGO.NS",
    "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "INTELLECT.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS",
    "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LT.NS", "LTI.NS",
    "LTTS.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCDOWELL-N.NS", "MCX.NS",
    "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MINDTREE.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NAM-INDIA.NS",
    "NATIONALUM.NS", "NAUKRI.NS", "NAVINFLUOR.NS", "NBCC.NS", "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS",
    "OFSS.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PETRONET.NS", "PFIZER.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS",
    "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RBLBANK.NS", "RECLTD.NS", "RELAXO.NS", "RELIANCE.NS",
    "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SCHAEFFLER.NS", "SHREECEM.NS", "SIEMENS.NS", "SRF.NS", "SRTRANSFIN.NS",
    "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TATACHEM.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATAPOWER.NS",
    "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TORNTPOWER.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS",
    "ULTRACEMCO.NS", "UNIONBANK.NS", "UPL.NS", "VBL.NS", "VEDL.NS", "VOLTAS.NS", "WHIRLPOOL.NS", "WIPRO.NS", "ZEEL.NS",
    "ZYDUSLIFE.NS"
]  # Short for testing; use full list in production

# === Utilities ===
def get_date_strings():
    today = datetime.now().date()
    return str(today - timedelta(days=1)), str(today)

def send_to_telegram(text, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"❌ Telegram send failed: {res.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

def fetch_and_send_news(symbol, from_str, to_str, chat_id):
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        'symbol': symbol,
        'from': from_str,
        'to': to_str,
        'token': FINNHUB_API_KEY
    }
    try:
        res = requests.get(url, params=params)
        news_items = res.json()
        if isinstance(news_items, list) and len(news_items) > 0:
            msg = f"<b>{symbol}</b>\n"
            for item in news_items[:1]:  # 1 news item per symbol
                dt = datetime.fromtimestamp(item['datetime']).strftime('%d %b %Y %I:%M %p')
                msg += f"📰 <b>{item['headline']}</b>\n🕒 {dt}\n🔗 <a href='{item['url']}'>Read More</a>\n\n"
            send_to_telegram(msg, chat_id)
            time.sleep(1)
    except Exception as e:
        print(f"❌ Error fetching news for {symbol} to {chat_id}: {e}")

# === Telegram Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id not in subscribed_users:
        subscribed_users.add(user_id)
        await context.bot.send_message(chat_id=user_id, text="📡 Welcome! You've subscribed to Nifty 200 stock news.")
        await send_latest_news_to_user(user_id)
    else:
        await context.bot.send_message(chat_id=user_id, text="✅ You're already subscribed.")

async def send_latest_news_to_user(user_id):
    from_str, to_str = get_date_strings()
    for symbol in nifty_200_symbols[:5]:  # Send news from top 5 stocks
        fetch_and_send_news(symbol, from_str, to_str, user_id)

# === Background Job ===
def run_news_job():
    from_str, to_str = get_date_strings()
    for user_id in subscribed_users:
        print(f"🚀 Sending news to user {user_id}")
        for symbol in nifty_200_symbols[:5]:  # Control volume
            fetch_and_send_news(symbol, from_str, to_str, user_id)
        time.sleep(1)

def schedule_runner():
    schedule.every(10).minutes.do(run_news_job)
    while True:
        schedule.run_pending()
        time.sleep(10)

# === Run Bot ===
def main():
    if not FINNHUB_API_KEY or not BOT_TOKEN:
        raise ValueError("Missing FINNHUB_API_KEY or BOT_TOKEN environment variable.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Start scheduler in background thread
    thread = threading.Thread(target=schedule_runner)
    thread.daemon = True
    thread.start()

    print("✅ Bot started. Listening for /start and sending news...")
    app.run_polling()

if __name__ == "__main__":
    main()
