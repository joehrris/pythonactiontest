import os
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime, timedelta
import json
import base64
import pytz

# Credentials
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_CALENDAR = os.environ.get("GOOGLE_CALENDAR_ID")

def get_coventry_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=52.41&longitude=-1.51&daily=temperature_2m_max,precipitation_probability_max&timezone=Europe%2FLondon"
    try:
        response = requests.get(url, timeout=10).json()
        max_temp = response['daily']['temperature_2m_max'][0]
        rain = response['daily']['precipitation_probability_max'][0]
        return f"High of {max_temp}°C, {rain}% chance of rain."
    except Exception as e:
        return f"Error fetching weather: {e}"

def check_pi_stock():
    url = "https://thepihut.com/products/raspberry-pi-zero-2"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text().lower()
        return f"🚨 IN STOCK! Link: {url}" if "sold out" not in page_text else "Still sold out."
    except Exception as e:
        return f"Error checking stock: {e}"

def get_calendar_events():
    b64_secret = os.environ.get("CALENDAR_SERVICE_ACCOUNT")
    if not b64_secret or not TARGET_CALENDAR:
        return "Calendar credentials missing."

    try:
        decoded_bytes = base64.b64decode(b64_secret)
        service_account_info = json.loads(decoded_bytes)

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=creds)

        # FIX: Set specific timezone for UK
        uk_tz = pytz.timezone("Europe/London")
        now_uk = datetime.now(uk_tz)
        today_date = now_uk.date()
        tomorrow_date = today_date + timedelta(days=1)
        two_months_later = now_uk + timedelta(days=60)

        events_result = service.events().list(
            calendarId=TARGET_CALENDAR, 
            timeMin=now_uk.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            timeMax=two_months_later.isoformat(),
            maxResults=150,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        recent_events, deadline_events = [], []

        for event in events:
            summary = event.get('summary', 'Untitled')
            start = event.get('start', {})
            start_str = start.get('dateTime', start.get('date', ''))
            
            # Parse the event date correctly
            if 'T' in start_str:
                dt_obj = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(uk_tz)
                event_date = dt_obj.date()
                time_part = dt_obj.strftime('%H:%M')
            else:
                event_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                time_part = 'All Day'

            day_name = event_date.strftime('%A') # e.g., "Monday"
            date_display = event_date.strftime('%b %d')

            # Logic for Today/Tomorrow
            if event_date == today_date:
                label = "TODAY"
            elif event_date == tomorrow_date:
                label = "TOMORROW"
            else:
                label = day_name

            if event_date <= tomorrow_date:
                icon = "💼 WORK SHIFT" if "shift" in summary.lower() or "work" in summary.lower() else "📅 EVENT"
                recent_events.append(f"• {label} ({day_name}): {icon}: {summary} at {time_part}")

            if "deadline" in summary.lower() or "due" in summary.lower():
                deadline_events.append(f"• {day_name}, {date_display}: {summary}")

        final_intel = f"Current UK Time: {now_uk.strftime('%A, %H:%M')}\n\n"
        final_intel += "=== IMMEDIATE SCHEDULE ===\n"
        final_intel += "\n".join(recent_events) if recent_events else "No immediate events."
        final_intel += "\n\n=== DEADLINES ===\n"
        final_intel += "\n".join(deadline_events) if deadline_events else "No upcoming deadlines."

        return final_intel

    except Exception as e:
        return f"Calendar error: {e}"

def get_reddit_drama():
    # Using old.reddit.com is often more reliable for scraping
    url = "https://old.reddit.com/r/youtubedrama/new.json?limit=10"
    headers = {
        # Reddit aggressively blocks generic browser user-agents from datacenters like GitHub Actions. 
        # Using their official API format bypasses most of these blocks.
        "User-Agent": "script:morning-briefing-bot:v1.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        posts = data.get("data", {}).get("children", [])
        drama_titles = [f"• {post['data']['title']}" for post in posts if 'data' in post and 'title' in post['data']]
        
        return "\n".join(drama_titles) if drama_titles else "No recent YouTube drama found."
    except Exception as e:
        return f"Error fetching Reddit drama: {e}"

def generate_ai_briefing(weather_data, stock_data, calendar_data, drama_data):
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    You are my personal assistant. Write a short morning briefing.
    
    Current Intel:
    - Weather: {weather_data}
    - Pi Stock: {stock_data}
    - Calendar Info: {calendar_data}
    - r/YouTubeDrama Post Titles: {drama_data}

    IMPORTANT: 
    - Pay extremely close attention to the labels "TODAY" and "TOMORROW" in the calendar info. 
    - If a WORK SHIFT is labeled as TOMORROW, do not say it is today.
    - List deadlines clearly as requested: "Just a heads up, your deadlines are on the following dates:..."
    - The YouTube Drama list contains recent post titles from the r/youtubedrama subreddit. Pick 3 to 5 of the most interesting ones, summarize the tea, and add a little witty or sarcastic commentary. Have fun with it.
    - Use HTML for Telegram (<b>bold</b>, <i>italic</i>).
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash-lite',
        contents=prompt,
    )
    return response.text

def send_telegram_message(message):
    token = BOT_TOKEN.strip()
    if token.lower().startswith("bot"): token = token[3:]
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(api_url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=15)
        print("✅ Sent" if response.status_code == 200 else f"❌ Error: {response.text}")
    except Exception as e:
        print(f"🚨 Dispatch Error: {e}")

def main():
    weather = get_coventry_weather()
    stock = check_pi_stock()
    calendar = get_calendar_events()
    drama = get_reddit_drama()
    final_message = generate_ai_briefing(weather, stock, calendar, drama)
    send_telegram_message(final_message)

if __name__ == "__main__":
    main()
