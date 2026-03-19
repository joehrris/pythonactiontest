import requests
from bs4 import BeautifulSoup
import os

# 1. Grab the secure keys you just put in the GitHub vault
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. The Target URL (The Pi Hut)
URL = "https://thepihut.com/products/raspberry-pi-zero-2"

def send_telegram_message(message):
    """Sends a push notification via Telegram API"""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(api_url, data=payload)

def check_stock():
    """Scrapes the webpage to check for stock"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print(f"Sniper aiming at: {URL}")
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text().lower()
        
        # If "sold out" isn't found, it's likely in stock!
        if "sold out" not in page_text:
            msg = f"🚨 Pi Zero 2 W might be IN STOCK!\nCheck here: {URL}"
            print(msg)
            send_telegram_message(msg)
        else:
            print("Target not found. Still out of stock.")
            # Optional: send a message just to confirm the bot is alive
            # send_telegram_message("Sniper check: Still out of stock.")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    check_stock()
