import requests
import os

# 1. Credentials for Telegram
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    clean_token = BOT_TOKEN.replace("bot", "").strip()
    api_url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
    requests.post(api_url, data={"chat_id": CHAT_ID, "text": message})

def get_coventry_weather():
    # Coventry coordinates: 52.41, -1.51
    url = "https://api.open-meteo.com/v1/forecast?latitude=52.41&longitude=-1.51&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FLondon"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # Index [1] is 'tomorrow' since [0] is today
        tomorrow_date = data['daily']['time'][1]
        max_temp = data['daily']['temperature_2m_max'][1]
        min_temp = data['daily']['temperature_2m_min'][1]
        rain_chance = data['daily']['precipitation_probability_max'][1]
        
        report = (
            f"📅 *Forecast for Coventry ({tomorrow_date})*\n"
            f"🌡️ High: {max_temp}°C\n"
            f"❄️ Low: {min_temp}°C\n"
            f"🌧️ Rain Chance: {rain_chance}%"
        )
        
        send_telegram_message(report)
        print("Weather report sent!")
        
    except Exception as e:
        print(f"Weather Error: {e}")

if __name__ == "__main__":
    get_coventry_weather()
