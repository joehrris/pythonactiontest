import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import base64
import pytz

# Credentials
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_CALENDAR = os.environ.get("GOOGLE_CALENDAR_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

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

def get_tech_news():
    if not NEWS_API_KEY:
        return "News API key missing."
        
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": '("artificial intelligence" OR "AI" OR "computing")',
        "sortBy": "relevancy",
        "pageSize": 3,
        "language": "en",
        "apiKey": NEWS_API_KEY
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10).json()
        if response.get("status") != "ok":
            return f"News API error: {response.get('message', 'Unknown error')}"
            
        articles = response.get("articles", [])
        news_items = []
        for article in articles:
            title = article.get("title", "No Title")
            source = article.get("source", {}).get("name", "Unknown Source")
            article_url = article.get("url", "")
            news_items.append(f"• {title} ({source}) - {article_url}")
            
        return "\n".join(news_items) if news_items else "No recent computing/AI news found."
    except Exception as e:
        return f"Error fetching news: {e}"

def generate_ai_briefing(weather_data, stock_data, calendar_data, news_data):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    prompt = f"""
    You are my personal assistant. Write a short morning briefing.
    
    Current Intel:
    - Weather: {weather_data}
    - Pi Stock: {stock_data}
    - Calendar Info: {calendar_data}
    - Top Tech/AI News: {news_data}

    IMPORTANT: 
    - Pay extremely close attention to the labels "TODAY" and "TOMORROW" in the calendar info. 
    - If a WORK SHIFT is labeled as TOMORROW, do not say it is today.
    - List deadlines clearly as requested: "Just a heads up, your deadlines are on the following dates:..."
    - Include brief bullet points reviewing the top 3 tech/AI news stories provided. Make them short and punchy.
    - Use HTML for Telegram (<b>bold</b>, <i>italic</i>, <a href="...">links</a> for news articles if provided).
    """
    response = model.generate_content(prompt)
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
    trends = get_x_trending()
    final_message = generate_ai_briefing(weather, stock, calendar, trends)
    send_telegram_message(final_message)

if __name__ == "__main__":
    main()
