import os
import json
import requests
import time
import schedule
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
load_dotenv()

# === ENV VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# === File Paths ===
SUBSCRIBERS_FILE = "subscribers.json"
SENT_URLS_FILE = "sent_urls.json"

# === Load Subscribers ===
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

# === Load Sent URLs ===
def load_sent_urls():
    try:
        with open(SENT_URLS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent_urls(urls):
    with open(SENT_URLS_FILE, "w") as f:
        json.dump(list(urls), f)

sent_urls = load_sent_urls()

# === Telegram Send ===
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

# === Fetch News from Finnhub ===
def fetch_news(category="general"):
    try:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={NEWSAPI_KEY}"
        res = requests.get(url)
        data = res.json()

        if not isinstance(data, list):
            print("❌ Finnhub error:", data)
            return []

        return data[:5]  # Limit to latest 5 articles
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return []

# === Send News to a User ===
def send_news(chat_id, category="general"):
    global sent_urls
    articles = fetch_news(category)

    # Filter for India-related news
    india_articles = [a for a in articles if (
        "india" in a.get("headline", "").lower() or 
        "india" in a.get("summary", "").lower()
    ) and a.get("url") not in sent_urls]

    if not india_articles:
        print(f"ℹ️ No new India-related articles for {chat_id}")
        return

    for article in india_articles:
        url = article.get("url")
        if not url:
            continue

        title = article.get("headline", "No Title")
        source = article.get("source", "Unknown")
        published_ts = article.get("datetime", 0)
        published = datetime.utcfromtimestamp(published_ts).strftime('%d %b %Y %I:%M %p')
        description = article.get("summary", "No summary available.")

        message = (
            f"<b>{title}</b>\n"
            f"<i>{source}</i> | 📅 {published}\n\n"
            f"🧠 {description}\n"
            f"🔗 <a href='{url}'>Read Full</a>"
        )

        send_to_telegram(message, chat_id)
        sent_urls.add(url)
        save_sent_urls(sent_urls)
        time.sleep(1)


# === Telegram Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id not in subscribed_users:
        subscribed_users.add(user_id)
        save_subscribers(subscribed_users)
        await context.bot.send_message(chat_id=user_id, text="✅ Subscribed to daily general news!")
    else:
        await context.bot.send_message(chat_id=user_id, text="✅ You're already subscribed.")
    send_news(user_id)

# === Optional categories ===
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE, category):
    chat_id = update.effective_chat.id
    send_news(chat_id, category)

async def india(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_command(update, context, "general")

async def business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_command(update, context, "business")

async def tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_command(update, context, "technology")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_command(update, context, "healthcare")

# === Scheduled News ===
def run_news_job():
    for user_id in subscribed_users:
        print(f"🚀 Sending fresh news to {user_id}")
        send_news(user_id)
        time.sleep(1)

def schedule_runner():
    run_news_job()  # First run immediately
    schedule.every(10).minutes.do(run_news_job)
    while True:
        schedule.run_pending()
        time.sleep(10)

# === Main Bot Init ===
def main():
    if not BOT_TOKEN or not NEWSAPI_KEY:
        raise ValueError("Missing BOT_TOKEN or NEWSAPI_KEY")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("india", india))
    app.add_handler(CommandHandler("business", business))
    app.add_handler(CommandHandler("tech", tech))
    app.add_handler(CommandHandler("health", health))

    thread = threading.Thread(target=schedule_runner)
    thread.daemon = True
    thread.start()

    print("✅ General News Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
