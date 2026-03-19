import requests
from bs4 import BeautifulSoup
import os
import sys

# 1. Credentials
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(api_url, data={"chat_id": CHAT_ID, "text": message})
        # This will tell us if Telegram rejected the message
        print(f"Telegram Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to talk to Telegram: {e}")

def check_stock():
    # Adding more "human" headers to try and bypass bot detection
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    url = "https://thepihut.com/products/raspberry-pi-zero-2"
    print(f"--- Sniper Start ---")
    print(f"Target: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Website Response Code: {response.status_code}")
        
        # Check if the website actually gave us content
        if len(response.text) < 500:
            print("⚠️ WARNING: The website returned a very short page. We might be blocked!")
            send_telegram_message("⚠️ Sniper Warning: The website is blocking me! I need a better disguise.")
            return

        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text().lower()
        
        # Look for the specific 'Sold Out' button text
        if "sold out" not in page_text:
            msg = f"🚨 PI ZERO 2 W IN STOCK?\n{url}"
            print(msg)
            send_telegram_message(msg)
        else:
            status = "🔎 Sniper Report: Verified 'Sold Out' on page. No action needed."
            print(status)
            send_telegram_message(status)
            
    except Exception as e:
        error_msg = f"❌ Sniper Crash: {e}"
        print(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    check_stock()
