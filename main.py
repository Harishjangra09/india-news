import os
import json
import requests
import time
import schedule
import threading
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
load_dotenv()

# === ENV VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# === File to Store Subscribers ===
SUBSCRIBERS_FILE = "subscribers.json"

# === Load & Save Helpers ===
def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)

subscribed_users = load_subscribers()

# === Send Telegram Message ===
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

# === News Fetching ===
def fetch_news(query, lang="en"):
    try:
        now = datetime.now(timezone.utc)
        from_time = now - timedelta(hours=24)
        from_str = from_time.isoformat()

        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={query}&"
            f"from={from_str}&"
            f"language={lang}&"
            f"pageSize=5&"
            f"sortBy=publishedAt&"
            f"apiKey={NEWSAPI_KEY}"
        )

        res = requests.get(url)
        data = res.json()

        if data.get("status") != "ok":
            print("❌ NewsAPI error:", data)
            return []

        return data.get("articles", [])

    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return []

# === Send News to User ===
def send_news(chat_id, query, lang="en"):
    articles = fetch_news(query, lang)
    if not articles:
        send_to_telegram("⚠️ No fresh news available right now.", chat_id)
        return

    for article in articles:
        title = article.get("title", "No Title")
        source = article.get("source", {}).get("name", "")
        published = article.get("publishedAt", "")[:10]
        description = article.get("description", "No summary available.")
        url = article.get("url")

        message = (
            f"<b>{title}</b>\n"
            f"<i>{source}</i> | 📅 {published}\n\n"
            f"🧠 {description}\n"
            f"🔗 <a href='{url}'>Read Full</a>"
        )

        send_to_telegram(message, chat_id)
        time.sleep(1)

# === Telegram Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id not in subscribed_users:
        subscribed_users.add(user_id)
        save_subscribers(subscribed_users)
        await context.bot.send_message(chat_id=user_id, text="✅ Subscribed to daily general news!")
        send_news(user_id, "India OR World OR Breaking News")
    else:
        await context.bot.send_message(chat_id=user_id, text="✅ You're already subscribed.")

async def send_category(update: Update, context: ContextTypes.DEFAULT_TYPE, query="India", lang="en"):
    chat_id = update.effective_chat.id
    send_news(chat_id, query, lang)

async def india(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "India")

async def world(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "World")

async def sports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "Sports")

async def business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "Business OR Finance")

async def tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "Technology")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "Health")

async def hindi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_category(update, context, "India", lang="hi")

# === Background Job to Send News to All Subscribers ===
def run_news_job():
    for user_id in subscribed_users:
        print(f"🚀 Sending scheduled news to {user_id}")
        send_news(user_id, "India OR World OR Breaking News")
        time.sleep(1)

def schedule_runner():
    schedule.every(2).hours.do(run_news_job)
    while True:
        schedule.run_pending()
        time.sleep(10)

# === Bot Main Function ===
def main():
    if not BOT_TOKEN or not NEWSAPI_KEY:
        raise ValueError("Missing BOT_TOKEN or NEWSAPI_KEY")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("india", india))
    app.add_handler(CommandHandler("world", world))
    app.add_handler(CommandHandler("sports", sports))
    app.add_handler(CommandHandler("business", business))
    app.add_handler(CommandHandler("tech", tech))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("hindi", hindi))

    # Start background scheduler thread
    thread = threading.Thread(target=schedule_runner)
    thread.daemon = True
    thread.start()

    print("✅ General News Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
