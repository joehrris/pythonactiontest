import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import base64

# Credentials from Environment Variables (Set via GitHub Vault/Secrets)
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

def get_calendar_events():
    """Fetches calendar events for today/tomorrow using a base64 env var"""
    
    # Grab the base64 string from the environment variable
    b64_secret = os.environ.get("CALENDAR_SERVICE_ACCOUNT")
    
    if not b64_secret:
        return "Calendar not configured. Missing CALENDAR_SERVICE_ACCOUNT env var."

    try:
        # Decode the base64 string back into a dictionary
        decoded_bytes = base64.b64decode(b64_secret)
        service_account_info = json.loads(decoded_bytes)

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Use _info to pass the dictionary directly (no files needed)
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )

        service = build('calendar', 'v3', credentials=creds)

        # Get events for today and tomorrow
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=(today - timedelta(days=1)).isoformat() + 'Z',
            timeMax=(tomorrow + timedelta(days=1)).isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return "No calendar events for today."

        event_list = []
        for event in events:
            summary = event.get('summary', 'Untitled')
            start = event.get('start', {})
            location = start.get('location', '')
            time_parts = start.get('dateTime', start.get('date', ''))

            if 'T' in time_parts:
                time_str = time_parts.split('T')[1].split('Z')[0][:5]
            else:
                time_str = ''

            event_text = f"• 📅 {summary}"
            if time_str:
                event_text += f" — {time_str}"
            if location:
                event_text += f" | 📍 {location}"
            event_list.append(event_text)

        return "\n".join(event_list[:8])

    except Exception as e:
        return f"Calendar error: {e}"

def generate_ai_briefing(weather_data, stock_data, calendar_data):
    """Passes the raw intel to the AI to write the message"""
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Reverting to your originally selected lightweight model
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    # Handle empty calendar edge cases cleanly
    if not calendar_data or "Calendar not configured" in calendar_data or "Calendar error" in calendar_data:
        calendar_text = "No calendar events provided."
    else:
        calendar_text = calendar_data

    prompt = f"""
    You are my highly capable personal assistant. Write a short, engaging morning text message for me.
    Keep it conversational, use a couple of emojis, and don't make it sound robotic.

    Here is the intel for today:
    - Weather in Coventry: {weather_data}
    - Raspberry Pi Zero 2 W Status: {stock_data}
    - Calendar Events: {calendar_text}

    If the Pi is in stock, make sure to emphasize it heavily so I don't miss it!
    If there are calendar events, make it sound excited about the day ahead.
    """

    response = model.generate_content(prompt)
    return response.text

def send_telegram_message(message):
    """Sends the final AI text to your phone"""
    clean_token = BOT_TOKEN.replace("bot", "").strip()
    api_url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
    
    # parse_mode set to Markdown ensures bolding/italics render properly
    requests.post(api_url, data={
        "chat_id": CHAT_ID, 
        "text": message,
        "parse_mode": "Markdown"
    })

def main():
    print("Gathering weather intel...")
    weather = get_coventry_weather()

    print("Scouting target...")
    stock = check_pi_stock()

    print("Fetching calendar events...")
    calendar = get_calendar_events()

    print("Drafting AI Briefing...")
    final_message = generate_ai_briefing(weather, stock, calendar)

    print("Dispatching to Telegram...")
    send_telegram_message(final_message)

if __name__ == "__main__":
    main()
