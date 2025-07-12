import os
import requests
from datetime import datetime, timedelta
import time
import math
import schedule

# === ENV VARIABLES ===
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === NIFTY 200 SYMBOLS ===
nifty_200_symbols = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "ITC.NS",
    # ... rest of your list
]

def get_date_strings():
    today = datetime.now().date()
    return str(today - timedelta(days=1)), str(today)

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
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

def fetch_and_send_news(symbol, from_str, to_str):
    print(f"📡 Fetching news for {symbol}")
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
            for item in news_items[:2]:
                dt = datetime.fromtimestamp(item['datetime']).strftime('%d %b %Y %I:%M %p')
                msg += f"📰 <b>{item['headline']}</b>\n🕒 {dt}\n🔗 <a href='{item['url']}'>Read More</a>\n\n"
            send_to_telegram(msg)
            time.sleep(1.2)
        else:
            print(f"⚠️ No news found for {symbol}")
    except Exception as e:
        print(f"❌ Error fetching news for {symbol}: {e}")

def run_news_job():
    from_str, to_str = get_date_strings()
    batch_size = 50
    total_batches = math.ceil(len(nifty_200_symbols) / batch_size)

    for batch in range(total_batches):
        start = batch * batch_size
        end = min((batch + 1) * batch_size, len(nifty_200_symbols))
        current_batch = nifty_200_symbols[start:end]
        print(f"\n🚀 Batch {batch+1}/{total_batches} | Symbols {start + 1} to {end}")
        for symbol in current_batch:
            fetch_and_send_news(symbol, from_str, to_str)
        if batch < total_batches - 1:
            print("⏸️ Waiting 60 seconds before next batch...")
            time.sleep(60)

# ✅ Schedule every 10 minutes
schedule.every(10).minutes.do(run_news_job)

print("✅ Bot is running and will send news every 10 minutes...\n⏳ First run now...\n")
run_news_job()

while True:
    schedule.run_pending()
    time.sleep(10)
