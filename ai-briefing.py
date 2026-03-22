import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import base64

# Credentials from Environment Variables
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_CALENDAR = os.environ.get("GOOGLE_CALENDAR_ID")

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
    """Fetches events for 48 hours AND deadlines for 60 days"""
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

        today = datetime.now()
        two_months_later = today + timedelta(days=60)

        events_result = service.events().list(
            calendarId=TARGET_CALENDAR, 
            timeMin=(today - timedelta(days=1)).isoformat() + 'Z',
            timeMax=two_months_later.isoformat() + 'Z',
            maxResults=150,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        recent_events = []
        deadline_events = []
        
        today_date = today.date()
        tomorrow_date = today_date + timedelta(days=1)

        for event in events:
            summary = event.get('summary', 'Untitled')
            summary_lower = summary.lower()
            start = event.get('start', {})
            
            start_date_str = start.get('dateTime', start.get('date', ''))
            if 'T' in start_date_str:
                date_part = start_date_str.split('T')[0]
                time_part = start_date_str.split('T')[1].split('+')[0].split('Z')[0][:5]
            else:
                date_part = start_date_str
                time_part = 'All Day'
                
            event_date = datetime.strptime(date_part, '%Y-%m-%d').date()
            date_formatted = event_date.strftime('%b %d')

            if today_date <= event_date <= tomorrow_date:
                if "shift" in summary_lower or "work" in summary_lower:
                    recent_events.append(f"• 💼 WORK SHIFT: {summary} ({time_part})")
                else:
                    recent_events.append(f"• 📅 {summary} ({time_part})")

            if "deadline" in summary_lower or "due" in summary_lower:
                deadline_events.append(f"• {date_formatted} - {summary}")

        final_intel = "=== TODAY & TOMORROW ===\n"
        final_intel += "\n".join(recent_events) if recent_events else "No immediate events."
        
        final_intel += "\n\n=== UPCOMING DEADLINES (Next 2 Months) ===\n"
        final_intel += "\n".join(deadline_events) if deadline_events else "No upcoming deadlines."

        return final_intel

    except Exception as e:
        return f"Calendar error: {e}"

def generate_ai_briefing(weather_data, stock_data, calendar_data):
    """Passes the sorted intel to the AI to write the message using HTML tags"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    prompt = f"""
    You are my highly capable personal assistant. Write a short, engaging morning text message for me.
    Keep it conversational and use emojis naturally.

    Format the message using HTML tags ONLY for Telegram:
    - Use <b>text</b> for bolding.
    - Use <i>text</i> for italics.
    Do NOT use Markdown (like ** or [link](url)).

    Here is the raw intel for today:
    - Weather in Coventry: {weather_data}
    - Raspberry Pi Zero 2 W Status: {stock_data}
    - Calendar Data:
    {calendar_data}

    CRITICAL INSTRUCTIONS:
    1. Check if I have a WORK SHIFT today or tomorrow. Highlight it (e.g., using <b>) so I don't miss it.
    2. Mention any other regular events happening today/tomorrow.
    3. If I have upcoming deadlines, you MUST inform me and prioritise them by date using this exact wording: "Just a heads up, your deadlines are on the following dates: [List them]".
    4. If the Pi is in stock, emphasize it heavily!
    """

    response = model.generate_content(prompt)
    return response.text

def send_telegram_message(message):
    """Sends the final AI text with heavy debugging"""
    if not BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN environment variable is missing!")
        return

    # Clean the token: Remove 'bot' only if it's at the start
    token = BOT_TOKEN.strip()
    if token.lower().startswith("bot"):
        token = token[3:]
    
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    print(f"📡 Attempting to send to Telegram (URL: https://api.telegram.org/bot{token[:5]}.../sendMessage)")
    
    try:
        payload = {
            "chat_id": CHAT_ID, 
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(api_url, data=payload, timeout=15)
        print(f"📥 Response Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Telegram API Refused: {response.text}")
        else:
            print("✅ Success! Message sent to Telegram.")
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Telegram request timed out after 15 seconds.")
    except Exception as e:
        print(f"🚨 ERROR during Telegram dispatch: {e}")

def main():
    print("Gathering weather intel...")
    weather = get_coventry_weather()

    print("Scouting target...")
    stock = check_pi_stock()

    print("Fetching and sorting calendar events...")
    calendar = get_calendar_events()

    print("Drafting AI Briefing...")
    final_message = generate_ai_briefing(weather, stock, calendar)

    print("Dispatching to Telegram...")
    send_telegram_message(final_message)

if __name__ == "__main__":
    main()
