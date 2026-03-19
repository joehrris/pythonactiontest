import requests
from bs4 import BeautifulSoup
import os

# 1. Credentials from your Vault
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. The Target
URL = "https://thepihut.com/products/raspberry-pi-zero-2"

def send_telegram_message(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(api_url, data={"chat_id": CHAT_ID, "text": message})

def check_stock():
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"Sniper aiming at: {URL}")
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text().lower()
        
        if "sold out" not in page_text:
            # The Big Alert
            send_telegram_message(f"🚨 TARGET ACQUIRED! Pi Zero 2 W is IN STOCK!\n{URL}")
        else:
            # The "I'm alive" check-in
            send_telegram_message("🔎 Sniper Status: Checked The Pi Hut. Still sold out. I'll check again later!")
            
    except Exception as e:
        send_telegram_message(f"⚠️ Sniper Error: Something went wrong with the script!\nError: {e}")

if __name__ == "__main__":
    check_stock()
