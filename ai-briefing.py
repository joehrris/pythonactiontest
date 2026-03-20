import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# Credentials from GitHub Vault
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_coventry_weather():
    """Fetches raw weather data for Coventry"""
    url = "https://api.open-meteo.com/v1/forecast?latitude=52.41&longitude=-1.51&daily=temperature_2m_max,precipitation_probability_max&timezone=Europe%2FLondon"
    try:
        response = requests.get(url, timeout=10).json()
        max_temp = response['daily']['temperature_2m_max'][0]
        rain = response['daily']['precipitation_probability_max'][0]
        return f"High of {max_temp}°C, {rain}% chance of rain."
    except Exception as e:
        return f"Error fetching weather: {e}"

def check_pi_stock():
    """Scrapes The Pi Hut for Pi Zero 2 W stock"""
    url = "https://thepihut.com/products/raspberry-pi-zero-2"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text().lower()
        
        if "sold out" not in page_text:
            return f"🚨 IN STOCK! Link: {url}"
        else:
            return "Still sold out."
    except Exception as e:
        return f"Error checking stock: {e}"

def generate_ai_briefing(weather_data, stock_data):
    """Passes the raw intel to the AI to write the message"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are my highly capable personal assistant. Write a short, engaging morning text message for me.
    Keep it conversational, use a couple of emojis, and don't make it sound robotic.
    
    Here is the intel for today:
    - Weather in Coventry: {weather_data}
    - Raspberry Pi Zero 2 W Status: {stock_data}
    
    If the Pi is in stock, make sure to emphasize it heavily so I don't miss it!
    """
    
    response = model.generate_content(prompt)
    return response.text

def send_telegram_message(message):
    """Sends the final AI text to your phone"""
    clean_token = BOT_TOKEN.replace("bot", "").strip()
    api_url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
    requests.post(api_url, data={"chat_id": CHAT_ID, "text": message})

def main():
    print("Gathering weather intel...")
    weather = get_coventry_weather()
    
    print("Scouting target...")
    stock = check_pi_stock()
    
    print("Drafting AI Briefing...")
    final_message = generate_ai_briefing(weather, stock)
    
    print("Dispatching to Telegram...")
    send_telegram_message(final_message)

if __name__ == "__main__":
    main()
