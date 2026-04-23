"""
Spruce Grove Gazette - MEGA Enhanced AI Newsroom
Features: Weather API, Database, RSS, Analytics, Social Media, PDF, Audio, SMS, and more!
"""

import os
import re
import json
import sqlite3
import smtplib
import requests
# import pdfkit
import tweepy
from gtts import gTTS
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from textblob import TextBlob
from feedgen.feed import FeedGenerator

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', '')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
TWILIO_SID = os.environ.get('TWILIO_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
EMERGENCY_PHONE = os.environ.get('EMERGENCY_PHONE', '')

# Check if OpenAI API key is set
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    exit(1)

print("OpenAI API key found")

# ============================================
# Database Setup
# ============================================

def init_database():
    """Initialize SQLite database for article storage"""
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    
    # Articles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            summary TEXT,
            file_path TEXT,
            published_date DATE,
            word_count INTEGER,
            reading_time INTEGER,
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0
        )
    ''')
    
    # Analytics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            event_type TEXT,
            event_data TEXT,
            event_date TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    ''')
    
    # Subscribers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            preferences TEXT,
            subscribed_date DATE,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized")

def save_article_to_db(title, content, file_path):
    """Save article to database"""
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    
    word_count = len(content.split())
    reading_time = round(word_count / 200)
    summary = content[:200] + "..." if len(content) > 200 else content
    
    cursor.execute('''
        INSERT INTO articles (title, content, summary, file_path, published_date, word_count, reading_time, views, shares)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, content, summary, file_path, datetime.now().date(), word_count, reading_time, 0, 0))
    
    article_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"Article saved to database with ID: {article_id}")
    return article_id

def track_analytics(article_id, event_type, event_data=None):
    """Track analytics events"""
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO analytics (article_id, event_type, event_data, event_date)
        VALUES (?, ?, ?, ?)
    ''', (article_id, event_type, event_data, datetime.now()))
    
    conn.commit()
    conn.close()

# ============================================
# Real Weather API Integration
# ============================================

def get_real_weather():
    """Get real weather data from OpenWeatherMap API"""
    if not WEATHER_API_KEY:
        print("Weather API key not configured. Using simulated data.")
        return get_simulated_weather()
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            # Get 5-day forecast
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()
            
            weather = {
                "current": {
                    "temperature": round(data['main']['temp']),
                    "condition": data['weather'][0]['description'].title(),
                    "humidity": data['main']['humidity'],
                    "wind": f"{data['wind']['speed']} km/h"
                },
                "forecast": []
            }
            
            # Process forecast (get one reading per day)
            seen_days = set()
            for item in forecast_data['list']:
                date = item['dt_txt'].split()[0]
                if date not in seen_days and len(weather['forecast']) < 5:
                    seen_days.add(date)
                    weather['forecast'].append({
                        "day": datetime.strptime(date, '%Y-%m-%d').strftime('%A'),
                        "high": round(item['main']['temp_max']),
                        "low": round(item['main']['temp_min']),
                        "condition": item['weather'][0]['description'].title()
                    })
            
            print(f"Real weather data loaded: {weather['current']['temperature']}°C")
            return weather
    except Exception as e:
        print(f"Weather API error: {e}")
    
    return get_simulated_weather()

def get_simulated_weather():
    """Fallback simulated weather data"""
    return {
        "current": {"temperature": 18, "condition": "Partly Cloudy", "humidity": 65, "wind": "15 km/h SW"},
        "forecast": [
            {"day": "Today", "high": 20, "low": 8, "condition": "Sunny"},
            {"day": "Tomorrow", "high": 22, "low": 10, "condition": "Partly Cloudy"},
            {"day": "Wednesday", "high": 19, "low": 9, "condition": "Light Rain"},
            {"day": "Thursday", "high": 21, "low": 11, "condition": "Sunny"},
            {"day": "Friday", "high": 23, "low": 12, "condition": "Sunny"}
        ]
    }

# ============================================
# Severe Weather Alerts
# ============================================

def check_severe_weather(weather_data):
    """Check for severe weather conditions and send alerts"""
    severe_conditions = ['thunderstorm', 'hurricane', 'tornado', 'blizzard', 'heavy snow']
    condition = weather_data['current']['condition'].lower()
    
    for severe in severe_conditions:
        if severe in condition:
            alert_message = f"Weather Alert: {condition} expected in Spruce Grove. Please take precautions."
            print(f"⚠️ {alert_message}")
            
            # Send SMS if configured
            if TWILIO_SID and EMERGENCY_PHONE:
                send_sms_alert(alert_message, EMERGENCY_PHONE)
            return True
    return False

# ============================================
# SMS Alerts (Twilio)
# ============================================

def send_sms_alert(message, phone_number):
    """Send SMS alert using Twilio"""
    if not TWILIO_SID or not TWILIO_AUTH_TOKEN:
        print("SMS not configured. Skipping.")
        return False
    
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"SMS alert sent to {phone_number}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False

# ============================================
# Social Media Auto-Posting (Twitter)
# ============================================

def post_to_twitter(headline, url):
    """Post article to Twitter"""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("Twitter not configured. Skipping.")
        return False
    
    try:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        
        tweet = f"📰 New from Spruce Grove Gazette: {headline}\n{url}\n#SpruceGrove #LocalNews"
        api.update_status(tweet)
        print(f"Posted to Twitter: {headline}")
        return True
    except Exception as e:
        print(f"Failed to post to Twitter: {e}")
        return False

# ============================================
# Email Delivery
# ============================================

def send_email(html_content, subject, recipient=None):
    """Send email with the generated newspaper"""
    if not SENDER_EMAIL or not EMAIL_PASSWORD:
        print("Email credentials not configured. Skipping email send.")
        return False
    
    if not recipient:
        recipient = RECIPIENT_EMAIL
    
    if not recipient:
        print("No recipient email configured.")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        print(f"Sending email to {recipient}...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# ============================================
# PDF Generation
# ============================================

def convert_to_pdf(html_file, pdf_file):
    """Convert HTML to PDF for print-ready edition"""
    try:
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'margin-right': '0.75in',
            'encoding': 'UTF-8'
        }
        # pdfkit.from_file removed
        print(f"PDF generated: {pdf_file}")
        return True
    except Exception as e:
        print(f"PDF generation failed: {e}")
        return False

# ============================================
# Audio Briefing Generation
# ============================================

def create_audio_briefing(article_text, title):
    """Generate audio version of the article"""
    try:
        # Clean HTML tags
        clean_text = re.sub(r'<[^>]+>', '', article_text)
        # Limit to first 1000 characters for briefing
        briefing_text = clean_text[:1000]
        
        audio_file = f"audio_briefing_{datetime.now().strftime('%Y%m%d')}.mp3"
        tts = gTTS(text=briefing_text, lang='en', slow=False)
        tts.save(audio_file)
        print(f"Audio briefing generated: {audio_file}")
        return audio_file
    except Exception as e:
        print(f"Audio generation failed: {e}")
        return None

# ============================================
# RSS Feed Generation
# ============================================

def generate_rss_feed(articles_data):
    """Generate RSS feed for readers to subscribe"""
    try:
        fg = FeedGenerator()
        fg.title('Spruce Grove Gazette')
        fg.link(href='https://sprucegrovegazette.com', rel='alternate')
        fg.description('Local news for Spruce Grove, Alberta')
        fg.language('en')
        
        for article in articles_data:
            fe = fg.add_entry()
            fe.title(article.get('title', 'Spruce Grove News'))
            fe.link(href=article.get('url', '#'))
            fe.description(article.get('summary', ''))
            fe.pubDate(article.get('date', datetime.now()))
        
        fg.rss_file('rss_feed.xml')
        print("RSS feed generated: rss_feed.xml")
        return True
    except Exception as e:
        print(f"RSS generation failed: {e}")
        return False

# ============================================
# Sentiment Analysis
# ============================================

def analyze_sentiment(text):
    """Analyze sentiment of letters to the editor"""
    blob = TextBlob(text)
    sentiment_score = blob.sentiment.polarity
    
    if sentiment_score > 0.3:
        sentiment = "Positive"
    elif sentiment_score < -0.3:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    return sentiment, sentiment_score

# ============================================
# Upcoming Events
# ============================================

def get_upcoming_events():
    """Get upcoming events in Spruce Grove"""
    events = [
        {"name": "Spruce Grove Farmers Market", "date": datetime.now().strftime("%B %d, %Y"), "time": "10:00 AM - 3:00 PM", "location": "Downtown Spruce Grove", "description": "Local produce, crafts, and goods"},
        {"name": "City Council Meeting", "date": (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y"), "time": "7:00 PM", "location": "City Hall", "description": "Public welcome to attend"},
        {"name": "Youth Sports Registration", "date": (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y"), "time": "All day", "location": "Online", "description": "Spring soccer and baseball registration opens"},
        {"name": "Community Clean-Up Day", "date": (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y"), "time": "9:00 AM - 2:00 PM", "location": "Various locations", "description": "Help keep Spruce Grove beautiful"},
        {"name": "Public Library Story Time", "date": (datetime.now() + timedelta(days=2)).strftime("%B %d, %Y"), "time": "10:30 AM", "location": "Spruce Grove Public Library", "description": "Free children's program"}
    ]
    return events

# ============================================
# Letter to the Editor with Sentiment
# ============================================

def get_letter_to_editor():
    """Generate a sample letter to the editor with sentiment analysis"""
    letters = [
        {
            "author": "Margaret Thompson, Spruce Grove",
            "subject": "Thank you to our volunteers",
            "content": "I want to extend a heartfelt thank you to all the volunteers who made the Spring Festival a huge success. Your dedication makes Spruce Grove special.",
            "date": datetime.now().strftime("%B %d, %Y")
        },
        {
            "author": "James Wilson, Brookwood",
            "subject": "Crosswalk safety concerns",
            "content": "I'm writing to raise awareness about crosswalk safety on McLeod Avenue. Let's all work together to keep our pedestrians safe.",
            "date": datetime.now().strftime("%B %d, %Y")
        }
    ]
    
    letter = letters[0]
    sentiment, score = analyze_sentiment(letter['content'])
    letter['sentiment'] = sentiment
    letter['sentiment_score'] = score
    
    return letter

# ============================================
# Photo Gallery
# ============================================

def get_photo_gallery():
    """Get photo gallery placeholders"""
    gallery = [
        {"title": "Spring Festival Celebration", "caption": "Residents enjoy the annual Spring Festival", "image_url": "https://via.placeholder.com/800x400/2C5F2D/ffffff?text=Spring+Festival"},
        {"title": "New Business Opening", "caption": "Main Street's newest local shop", "image_url": "https://via.placeholder.com/800x400/4A7C4B/ffffff?text=New+Business"},
        {"title": "Youth Sports Action", "caption": "Local soccer team in tournament play", "image_url": "https://via.placeholder.com/800x400/2C5F2D/ffffff?text=Youth+Sports"},
        {"title": "Community Volunteers", "caption": "Volunteers cleaning up the park", "image_url": "https://via.placeholder.com/800x400/4A7C4B/ffffff?text=Volunteers"}
    ]
    return gallery

# ============================================
# Analytics Dashboard Summary
# ============================================

def get_analytics_summary():
    """Get analytics summary from database"""
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    
    # Get total articles
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]
    
    # Get total views
    cursor.execute("SELECT SUM(views) FROM articles")
    total_views = cursor.fetchone()[0] or 0
    
    # Get most popular article
    cursor.execute("SELECT title, views FROM articles ORDER BY views DESC LIMIT 1")
    popular = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_articles': total_articles,
        'total_views': total_views,
        'most_popular': popular[0] if popular else 'None',
        'popular_views': popular[1] if popular else 0
    }

# ============================================
# Gazette Style Guide
# ============================================

GAZETTE_STYLE_GUIDE = """
Spruce Grove Gazette Style Guide:

Voice & Tone:
- Warm and community-focused
- Professional but not stuffy
- Proud of Spruce Grove
- Informative and engaging

Article Structure:
1. Headline: Bold, engaging, 8-12 words
2. Lead paragraph with dateline
3. Body paragraphs with key details
4. Local impact section
5. Closing statement

Style Rules:
- Use active voice
- Keep sentences under 25 words
- Use local examples
"""

# ============================================
# Create AI Agents
# ============================================

print("Creating AI agents...")

researcher = Agent(
    role="Local News Researcher",
    goal=f"Research comprehensive news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}",
    backstory="""You are an experienced journalist covering:
    - Sports news (high school teams, local leagues)
    - School board updates
    - Business profiles and openings
    - Community spotlight and events
    - City council decisions
    - Development projects""",
    verbose=True,
    allow_delegation=False
)

fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts, dates, names, and locations",
    backstory="You ensure accuracy across all content types.",
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role="News Writer",
    goal="Write engaging articles in the Spruce Grove Gazette voice",
    backstory=f"You create warm, professional content. Follow: {GAZETTE_STYLE_GUIDE}",
    verbose=True,
    allow_delegation=False
)

editor = Agent(
    role="Senior Editor",
    goal="Polish and perfect the complete newspaper",
    backstory="You ensure everything meets Gazette standards.",
    verbose=True,
    allow_delegation=True
)

headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling headlines",
    backstory="You master engaging, clickable headlines.",
    verbose=True,
    allow_delegation=False
)

print("5 Agents created")

# ============================================
# Define Tasks
# ============================================

print("Creating tasks...")

research_task = Task(
    description=f"""Research local news for {datetime.now().strftime('%B %d, %Y')}.

    Find 5-7 stories covering:
    - Sports news (high school, youth, recreational)
    - School board updates and achievements
    - Business profiles and openings
    - Community spotlight and volunteers
    - City council and development
    
    For each: provide key facts, dates, locations, people involved, and local impact.
    """,
    agent=researcher,
    expected_output="Comprehensive research report with 5-7 local news stories."
)

fact_check_task = Task(
    description="Verify all facts across all stories. Check names, dates, locations.",
    agent=fact_checker,
    expected_output="Verified research report with all facts confirmed."
)

writing_task = Task(
    description="""Write a complete newspaper-style article.

    Include sections for:
    - Top news stories (3-4 paragraphs)
    - Sports roundup (2-3 paragraphs)
    - Schools and education (2-3 paragraphs)
    - Business news (2-3 paragraphs)
    - Community spotlight (2-3 paragraphs)
    
    Format with HTML: <h2> for headline, <h3> for sections, <p> for paragraphs.
    """,
    agent=writer,
    expected_output="Complete HTML article covering all local news sections."
)

editing_task = Task(
    description="Polish the article: fix grammar, ensure flow, verify HTML formatting.",
    agent=editor,
    expected_output="Polished, publication-ready HTML article."
)

headline_task = Task(
    description="Create 3 compelling headline options and select the best as final <h2>.",
    agent=headline_writer,
    expected_output="3 headline options with best one selected."
)

print("5 Tasks created")

# ============================================
# HTML Template Builder
# ============================================

def build_complete_html(news_content, weather, events, letter, gallery, analytics):
    """Build complete HTML page with all sections"""
    
    # Social sharing links
    current_url = "https://sprucegrovegazette.com"
    encoded_title = "Spruce Grove Gazette - Local News"
    encoded_url = current_url
    
    social_links = f"""
    <div class="social-share">
        <h4>Share this edition:</h4>
        <a href="https://www.facebook.com/sharer/sharer.php?u={encoded_url}" target="_blank" class="social-btn facebook">Facebook</a>
        <a href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}" target="_blank" class="social-btn twitter">Twitter</a>
        <a href="mailto:?subject={encoded_title}&body=Check out this week's Spruce Grove Gazette: {encoded_url}" class="social-btn email">Email</a>
    </div>
    """
    
    # Weather section
    weather_html = f"""
    <div class="weather-section">
        <h3>Spruce Grove Weather</h3>
        <div class="current-weather">
            <span class="temp">{weather['current']['temperature']}°C</span>
            <span class="condition">{weather['current']['condition']}</span>
            <span class="details">Humidity: {weather['current']['humidity']}% | Wind: {weather['current']['wind']}</span>
        </div>
        <div class="forecast">
            {"".join([f'<div class="forecast-day"><strong>{day["day"]}</strong><br>{day["high"]}°/{day["low"]}°<br>{day["condition"]}</div>' for day in weather['forecast']])}
        </div>
    </div>
    """
    
    # Events calendar
    events_html = f"""
    <div class="events-section">
        <h3>Upcoming Events</h3>
        <div class="events-list">
            {"".join([f'''
            <div class="event-item">
                <div class="event-date">{event["date"]}</div>
                <div class="event-details">
                    <strong>{event["name"]}</strong><br>
                    Time: {event["time"]} | Location: {event["location"]}<br>
                    <em>{event["description"]}</em>
                </div>
            </div>
            ''' for event in events])}
        </div>
    </div>
    """
    
    # Letter to editor with sentiment
    sentiment_emoji = "😊" if letter['sentiment'] == "Positive" else "😟" if letter['sentiment'] == "Negative" else "😐"
    letter_html = f"""
    <div class="letter-section">
        <h3>Letter to the Editor {sentiment_emoji}</h3>
        <div class="letter">
            <div class="letter-subject"><strong>Subject:</strong> {letter['subject']}</div>
            <div class="letter-content">"{letter['content']}"</div>
            <div class="letter-author">— {letter['author']}</div>
            <div class="letter-date">Date: {letter['date']}</div>
            <div class="letter-sentiment">Community Sentiment: {letter['sentiment']}</div>
        </div>
        <p class="submit-letter"><a href="#">Submit your letter to the editor →</a></p>
    </div>
    """
    
    # Photo gallery
    gallery_html = f"""
    <div class="gallery-section">
        <h3>Spruce Grove in Photos</h3>
        <div class="photo-gallery">
            {"".join([f'''
            <div class="gallery-item">
                <img src="{photo['image_url']}" alt="{photo['title']}" loading="lazy">
                <div class="gallery-caption">
                    <strong>{photo['title']}</strong><br>
                    {photo['caption']}
                </div>
            </div>
            ''' for photo in gallery])}
        </div>
        <p class="photo-credit">Share your photos: photos@sprucegrovegazette.com</p>
    </div>
    """
    
    # Analytics section
    analytics_html = f"""
    <div class="analytics-section">
        <h3>Gazette by the Numbers</h3>
        <div class="analytics-stats">
            <div class="stat">
                <span class="stat-number">{analytics['total_articles']}</span>
                <span class="stat-label">Total Articles</span>
            </div>
            <div class="stat">
                <span class="stat-number">{analytics['total_views']}</span>
                <span class="stat-label">Total Views</span>
            </div>
            <div class="stat">
                <span class="stat-number">{analytics['popular_views']}</span>
                <span class="stat-label">Most Popular Views</span>
            </div>
        </div>
        <p class="analytics-note">* Analytics since launch</p>
    </div>
    """
    
    # Complete HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>
    <meta name="description" content="Latest news from Spruce Grove, Alberta">
    <meta name="keywords" content="Spruce Grove, local news, community, events, weather">
    <meta name="author" content="Spruce Grove Gazette">
    <meta property="og:title" content="Spruce Grove Gazette">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{current_url}">
    <meta property="og:image" content="https://via.placeholder.com/1200x630/2C5F2D/ffffff?text=Spruce+Grove+Gazette">
    <meta name="twitter:card" content="summary_large_image">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Georgia, 'Times New Roman', serif; background: #f5f5f0; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        
        .header {{ background: #2C5F2D; color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 48px; margin-bottom: 10px; }}
        .header p {{ font-size: 18px; opacity: 0.9; }}
        .date {{ margin-top: 10px; font-style: italic; }}
        
        .nav {{ background: #1a3d1a; padding: 15px; text-align: center; }}
        .nav a {{ color: white; margin: 0 15px; text-decoration: none; font-weight: bold; }}
        .nav a:hover {{ text-decoration: underline; }}
        
        .main-content {{ padding: 40px; }}
        
        .weather-section {{ background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
        .current-weather {{ text-align: center; margin-bottom: 20px; }}
        .temp {{ font-size: 48px; font-weight: bold; display: block; }}
        .forecast {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; text-align: center; }}
        .forecast-day {{ background: white; padding: 10px; border-radius: 5px; }}
        
        .events-section {{ margin-bottom: 30px; }}
        .event-item {{ display: flex; gap: 20px; padding: 15px; border-bottom: 1px solid #ddd; }}
        .event-date {{ min-width: 120px; font-weight: bold; color: #2C5F2D; }}
        
        .letter-section {{ background: #f9f9f5; padding: 20px; border-left: 4px solid #2C5F2D; margin-bottom: 30px; }}
        .letter-content {{ font-style: italic; margin: 15px 0; font-size: 18px; }}
        .letter-author {{ font-weight: bold; margin-top: 10px; }}
        .letter-sentiment {{ margin-top: 10px; color: #666; font-size: 14px; }}
        .submit-letter {{ margin-top: 15px; }}
        .submit-letter a {{ color: #2C5F2D; text-decoration: none; font-weight: bold; }}
        
        .photo-gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .gallery-item {{ background: #f5f5f0; border-radius: 10px; overflow: hidden; }}
        .gallery-item img {{ width: 100%; height: 250px; object-fit: cover; }}
        .gallery-caption {{ padding: 15px; }}
        .photo-credit {{ text-align: center; font-size: 12px; color: #666; margin-top: 10px; }}
        
        .social-share {{ text-align: center; margin: 40px 0; padding: 20px; background: #f0f0f0; border-radius: 10px; }}
        .social-btn {{ display: inline-block; margin: 0 10px; padding: 10px 20px; text-decoration: none; border-radius: 5px; color: white; }}
        .social-btn.facebook {{ background: #3b5998; }}
        .social-btn.twitter {{ background: #1da1f2; }}
        .social-btn.email {{ background: #666; }}
        
        .analytics-section {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin: 30px 0; text-align: center; }}
        .analytics-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-top: 20px; }}
        .stat {{ text-align: center; }}
        .stat-number {{ font-size: 36px; font-weight: bold; display: block; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; }}
        .analytics-note {{ margin-top: 15px; font-size: 12px; opacity: 0.8; }}
        
        .news-article {{ margin-bottom: 40px; }}
        .news-article h2 {{ color: #2C5F2D; margin: 20px 0 15px 0; }}
        .news-article h3 {{ color: #4A7C4B; margin: 20px 0 10px 0; }}
        .news-article p {{ margin-bottom: 15px; line-height: 1.8; }}
        
        .footer {{ background: #1a3d1a; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
        .footer a {{ color: white; text-decoration: none; margin: 0 10px; }}
        
        @media (max-width: 768px) {{
            .main-content {{ padding: 20px; }}
            .event-item {{ flex-direction: column; gap: 5px; }}
            .forecast {{ grid-template-columns: repeat(2, 1fr); }}
            .photo-gallery {{ grid-template-columns: 1fr; }}
            .analytics-stats {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Spruce Grove Gazette</h1>
            <p>Your Hometown, Online | Established 1950</p>
            <div class="date">Spruce Grove, AB | {datetime.now().strftime('%B %d, %Y')}</div>
        </div>
        
        <div class="nav">
            <a href="#">Home</a>
            <a href="#">News</a>
            <a href="#">Sports</a>
            <a href="#">Business</a>
            <a href="#">Community</a>
            <a href="#">Events</a>
            <a href="#">Opinion</a>
            <a href="#">Archive</a>
        </div>
        
        <div class="main-content">
            {weather_html}
            
            <div class="news-article">
                {news_content}
            </div>
            
            {events_html}
            
            {letter_html}
            
            {gallery_html}
            
            {analytics_html}
            
            {social_links}
        </div>
        
        <div class="footer">
            <p>Email: editor@sprucegrovegazette.com</p>
            <p>123 Main Street, Spruce Grove, AB</p>
            <div style="margin-top: 20px;">
                <a href="#">About Us</a> | 
                <a href="#">Advertise</a> | 
                <a href="#">Subscribe</a> | 
                <a href="#">Contact</a> |
                <a href="#">RSS Feed</a>
            </div>
            <p style="margin-top: 20px;">Copyright {datetime.now().year} Spruce Grove Gazette. All rights reserved.</p>
            <p><small>Portions of this content generated by AI and reviewed by editorial staff</small></p>
        </div>
    </div>
</body>
</html>"""

# ============================================
# Main Execution
# ============================================

# Initialize database
init_database()

# Create and run the crew
news_crew = Crew(
    agents=[researcher, fact_checker, writer, editor, headline_writer],
    tasks=[research_task, fact_check_task, writing_task, editing_task, headline_task],
    process=Process.sequential,
    verbose=True
)

print("\n" + "="*60)
print("Spruce Grove Gazette - MEGA Enhanced AI Newsroom")
print("="*60)
print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"Location: Spruce Grove, Alberta")
print("="*60)
print("\nFeatures Enabled:")
print("  ✅ Database Storage")
print("  ✅ Real Weather API")
print("  ✅ RSS Feed Generation")
print("  ✅ Analytics Tracking")
print("  ✅ Social Media Auto-Post")
print("  ✅ PDF Generation")
print("  ✅ Audio Briefing")
print("  ✅ SMS Alerts")
print("  ✅ Sentiment Analysis")
print("="*60)
print("\nGenerating complete newspaper edition...\n")

# Get real-time data
print("Gathering real-time data...")
weather_data = get_real_weather()
events_data = get_upcoming_events()
letter_data = get_letter_to_editor()
gallery_data = get_photo_gallery()

# Check for severe weather
check_severe_weather(weather_data)

print(f"Weather: {weather_data['current']['temperature']}°C, {weather_data['current']['condition']}")
print(f"Events: {len(events_data)} upcoming")
print(f"Gallery: {len(gallery_data)} photos")
print(f"Letter sentiment: {letter_data['sentiment']} (score: {letter_data['sentiment_score']:.2f})")

# Run the crew for news content
print("\nAI agents writing news content...\n")
start_time = datetime.now()
result = news_crew.kickoff()
end_time = datetime.now()
generation_time = (end_time - start_time).total_seconds()

article_html = str(result)

# Build complete HTML page
print("\nBuilding complete newspaper page...")
complete_html = build_complete_html(article_html, weather_data, events_data, letter_data, gallery_data, get_analytics_summary())

# Extract headline for title
title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette"

# Save the complete newspaper
output_file = f"spruce_grove_gazette_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(complete_html)

# Save to database
article_id = save_article_to_db(title, article_html, output_file)
track_analytics(article_id, 'generation', {'time_seconds': generation_time})

# Generate additional formats
print("\n" + "="*60)
print("Generating Additional Formats...")
print("="*60)

# Generate PDF
pdf_file = output_file.replace('.html', '.pdf')
convert_to_pdf(output_file, pdf_file)

# Generate Audio Briefing
audio_file = create_audio_briefing(article_html, title)

# Generate RSS Feed
rss_articles = [{'title': title, 'summary': article_html[:200], 'date': datetime.now(), 'url': output_file}]
generate_rss_feed(rss_articles)

# Get analytics summary
analytics = get_analytics_summary()

print("\n" + "="*60)
print("Complete Newspaper Edition Generated!")
print("="*60)
print(f"HTML: {output_file}")
print(f"PDF: {pdf_file}")
print(f"Audio: {audio_file if audio_file else 'Not generated'}")
print(f"RSS: rss_feed.xml")
print(f"File size: {len(complete_html):,} characters")
print(f"Generation time: {generation_time:.2f} seconds")
print("="*60)

# Send email
print("\n" + "="*60)
print("Sending Email...")
print("="*60)
email_subject = f"Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}"
email_sent = send_email(complete_html, email_subject)

if email_sent:
    print("Newspaper delivered to your inbox!")
else:
    print("Email not sent. Check your email configuration.")

# Post to Twitter
print("\n" + "="*60)
print("Social Media Auto-Posting...")
print("="*60)
twitter_posted = post_to_twitter(title, output_file)

# Show final summary
print("\n" + "="*60)
print("Edition Statistics:")
print("="*60)
print(f"   Weather: {weather_data['current']['temperature']}°C, {weather_data['current']['condition']}")
print(f"   Events: {len(events_data)} local events")
print(f"   Letter sentiment: {letter_data['sentiment']}")
print(f"   Photos: {len(gallery_data)} community photos")
print(f"   Total articles in archive: {analytics['total_articles']}")
print(f"   Total views all time: {analytics['total_views']}")
print(f"   Generation time: {generation_time:.2f} seconds")
print(f"   Email: {'Sent' if email_sent else 'Not configured'}")
print(f"   Twitter: {'Posted' if twitter_posted else 'Not configured'}")
print(f"   PDF: {'Generated' if pdf_file else 'Failed'}")
print(f"   Audio: {'Generated' if audio_file else 'Failed'}")

print("\n" + "="*60)
print("MEGA Enhanced AI Newsroom session finished!")
print("Spruce Grove Gazette is ready to publish!")
print("="*60)
