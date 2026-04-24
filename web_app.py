import os
import re
import json
import sqlite3
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# Database Setup
# ============================================

def init_database():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    
    # Subscribers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            subscribed_date DATE,
            active BOOLEAN DEFAULT 1,
            verification_token TEXT,
            neighborhood TEXT
        )
    ''')
    
    # News tips table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            tip TEXT,
            category TEXT,
            date DATE,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # Photo submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            title TEXT,
            caption TEXT,
            filename TEXT,
            date DATE,
            approved BOOLEAN DEFAULT 0
        )
    ''')
    
    # Business directory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            description TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            logo TEXT,
            featured BOOLEAN DEFAULT 0,
            approved BOOLEAN DEFAULT 0,
            date DATE
        )
    ''')
    
    # Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            date DATE,
            time TEXT,
            location TEXT,
            organizer TEXT,
            email TEXT,
            approved BOOLEAN DEFAULT 0,
            date_submitted DATE
        )
    ''')
    
    # Comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            author TEXT,
            email TEXT,
            comment TEXT,
            date DATE,
            approved BOOLEAN DEFAULT 0
        )
    ''')
    
    # Polls table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            option1 TEXT,
            option2 TEXT,
            option3 TEXT,
            option4 TEXT,
            votes1 INTEGER DEFAULT 0,
            votes2 INTEGER DEFAULT 0,
            votes3 INTEGER DEFAULT 0,
            votes4 INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            created_date DATE
        )
    ''')
    
    # Classifieds table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classifieds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            description TEXT,
            price TEXT,
            contact TEXT,
            email TEXT,
            phone TEXT,
            photo TEXT,
            featured BOOLEAN DEFAULT 0,
            expiry_date DATE,
            date DATE,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# ============================================
# Helper Functions
# ============================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(to_email, subject, html_content):
    """Send email using SMTP"""
    sender_email = os.environ.get('SENDER_EMAIL', '')
    sender_password = os.environ.get('EMAIL_PASSWORD', '')
    
    if not sender_email or not sender_password:
        print("Email not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def send_daily_newsletter():
    """Send daily newsletter to all subscribers"""
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, name, neighborhood FROM subscribers WHERE active = 1")
    subscribers = cursor.fetchall()
    conn.close()
    
    # Get latest article
    latest_article = get_latest_article()
    
    sent_count = 0
    for email, name, neighborhood in subscribers:
        personalized_html = f"""
        <html>
        <body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #1a3d1a;">📰 The Spruce Grove Gazette</h1>
            <p>Dear {name if name else 'Reader'},</p>
            <h2>{latest_article['title']}</h2>
            <p>{latest_article['summary']}</p>
            <a href="https://sprucegrovegazette.com/latest" style="background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none;">Read Full Story →</a>
            <hr>
            <p><small>You received this because you subscribed to the Spruce Grove Gazette. <a href="https://sprucegrovegazette.com/unsubscribe?email={email}">Unsubscribe</a></small></p>
        </body>
        </html>
        """
        if send_email(email, f"Your Daily Gazette - {datetime.now().strftime('%B %d, %Y')}", personalized_html):
            sent_count += 1
    
    return sent_count

def get_latest_article():
    """Get the latest article content"""
    return {
        "title": "Spruce Grove & Parkland County: Major Infrastructure Investment Announced",
        "summary": "The Alberta government has committed $136 million for highway improvements in Parkland County, including twinning Highway 60 and upgrading Highway 16..."
    }

def get_active_poll():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM polls WHERE active = 1 ORDER BY created_date DESC LIMIT 1")
    poll = cursor.fetchone()
    conn.close()
    if poll:
        return {
            "id": poll[0], "question": poll[1], "option1": poll[2], "option2": poll[3],
            "option3": poll[4], "option4": poll[5], "votes1": poll[6], "votes2": poll[7],
            "votes3": poll[8], "votes4": poll[9]
        }
    return None

def get_weather():
    return {
        "current": {"temp": 18, "feels_like": 17, "condition": "Partly Cloudy", "humidity": 65, "wind": 15, "uv": 5, "visibility": 16, "icon": "🌤️"},
        "forecast": [
            {"day": "Mon", "high": 20, "low": 8, "condition": "Sunny", "icon": "☀️"},
            {"day": "Tue", "high": 22, "low": 10, "condition": "Partly Cloudy", "icon": "⛅"},
            {"day": "Wed", "high": 19, "low": 9, "condition": "Light Rain", "icon": "🌧️"},
            {"day": "Thu", "high": 21, "low": 11, "condition": "Sunny", "icon": "☀️"},
            {"day": "Fri", "high": 23, "low": 12, "condition": "Sunny", "icon": "☀️"}
        ]
    }

def get_events(limit=5):
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, date, time, location FROM events WHERE approved = 1 AND date >= date('now') ORDER BY date LIMIT ?", (limit,))
    events = cursor.fetchall()
    conn.close()
    return [{"title": e[0], "description": e[1], "date": e[2], "time": e[3], "location": e[4]} for e in events]

def get_businesses(category=None, limit=6):
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    if category and category != 'all':
        cursor.execute("SELECT name, category, description, phone, website, logo FROM businesses WHERE approved = 1 AND category = ? ORDER BY featured DESC LIMIT ?", (category, limit))
    else:
        cursor.execute("SELECT name, category, description, phone, website, logo FROM businesses WHERE approved = 1 ORDER BY featured DESC LIMIT ?", (limit,))
    businesses = cursor.fetchall()
    conn.close()
    return [{"name": b[0], "category": b[1], "description": b[2], "phone": b[3], "website": b[4], "logo": b[5]} for b in businesses]

def get_gallery():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, caption, filename FROM photo_submissions WHERE approved = 1 ORDER BY date DESC LIMIT 8")
    photos = cursor.fetchall()
    conn.close()
    if photos:
        return [{"title": p[0], "caption": p[1], "filename": p[2]} for p in photos]
    return [
        {"title": "Earth Day Tree Planting", "caption": "Volunteers planting trees", "filename": None},
        {"title": "Panthers Victory", "caption": "Team celebrates", "filename": None},
        {"title": "New Tech Hub", "caption": "Innovation center rendering", "filename": None},
        {"title": "Food Bank Celebration", "caption": "25 years serving community", "filename": None}
    ]

# ============================================
# Routes
# ============================================

@app.route('/')
def home():
    weather = get_weather()
    events = get_events(5)
    gallery = get_gallery()
    businesses = get_businesses('all', 6)
    poll = get_active_poll()
    
    forecast_html = ''.join([f'''
        <div class="forecast-day">
            <div class="forecast-day-name">{f["day"]}</div>
            <div class="forecast-icon">{f["icon"]}</div>
            <div class="forecast-temp">{f["high"]}° / {f["low"]}°</div>
        </div>
    ''' for f in weather['forecast']])
    
    events_html = ''.join([f'<li><strong>{e["title"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    
    businesses_html = ''.join([f'''
        <div class="business-card">
            <h4>{b["name"]}</h4>
            <div class="business-category">{b["category"]}</div>
            <p>{b["description"][:100]}...</p>
            <div class="business-contact">
                <i class="fas fa-phone"></i> {b["phone"]}<br>
                <i class="fas fa-globe"></i> <a href="{b["website"]}" target="_blank">Website</a>
            </div>
        </div>
    ''' for b in businesses])
    
    gallery_html = ''.join([f'''
        <div class="gallery-item">
            <div class="gallery-placeholder">{p["title"]}</div>
            <p><strong>{p["title"]}</strong><br>{p["caption"]}</p>
        </div>
    ''' for p in gallery])
    
    poll_html = ''
    if poll:
        poll_html = f'''
        <div class="poll-section">
            <h3>📊 Poll of the Week</h3>
            <p><strong>{poll["question"]}</strong></p>
            <form action="/vote" method="POST">
                <div class="poll-options">
                    <label><input type="radio" name="vote" value="1"> {poll["option1"]}</label><br>
                    <label><input type="radio" name="vote" value="2"> {poll["option2"]}</label><br>
                    {'<label><input type="radio" name="vote" value="3"> ' + poll["option3"] + '</label><br>' if poll["option3"] else ''}
                    {'<label><input type="radio" name="vote" value="4"> ' + poll["option4"] + '</label><br>' if poll["option4"] else ''}
                </div>
                <button type="submit" class="btn" style="margin-top: 10px;">Vote →</button>
                <input type="hidden" name="poll_id" value="{poll["id"]}">
            </form>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <title>{NEWSPAPER_NAME} - Parkland County's Trusted News Source</title>
        <link rel="manifest" href="/manifest.json">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            
            /* Header */
            .top-bar {{ background: var(--primary); color: white; font-size: 11px; padding: 8px 0; text-align: center; }}
            .header {{ background: white; padding: 25px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
            .logo h1 {{ font-size: 44px; color: var(--primary); }}
            .logo p {{ font-size: 12px; color: #666; letter-spacing: 2px; }}
            .date-header {{ background: #f0f0e8; padding: 8px; text-align: center; font-size: 13px; }}
            
            /* Navigation */
            .nav {{ background: var(--primary); padding: 12px; text-align: center; position: sticky; top: 0; z-index: 100; overflow-x: auto; white-space: nowrap; }}
            .nav a {{ color: white; margin: 0 12px; text-decoration: none; text-transform: uppercase; font-size: 12px; display: inline-block; }}
            .nav a:hover {{ color: var(--accent); }}
            
            /* Hero */
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 40px 20px; text-align: center; }}
            .hero h2 {{ font-size: 32px; }}
            .hero p {{ font-size: 14px; margin-top: 8px; }}
            .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
            .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
            .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            
            /* Main Content */
            .main-content {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
            
            /* Quick Links */
            .quick-links {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 30px; }}
            .quick-link {{ background: white; padding: 12px 25px; border-radius: 30px; text-decoration: none; color: var(--primary); font-weight: bold; }}
            .quick-link:hover {{ background: var(--accent); color: var(--primary); }}
            
            /* Stats */
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 25px; text-align: center; border-radius: 10px; transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: var(--primary); }}
            
            /* Feature Sections */
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 40px; }}
            .section-title {{ font-size: 22px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; }}
            .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; background: var(--primary); color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; font-size: 14px; }}
            
            /* Weather */
            .weather-widget {{ background: linear-gradient(135deg, #1e3c72, #2a5298); border-radius: 15px; padding: 20px; color: white; margin-bottom: 30px; }}
            .weather-main {{ text-align: center; }}
            .weather-icon {{ font-size: 48px; }}
            .weather-temp {{ font-size: 48px; font-weight: bold; }}
            .weather-details {{ display: flex; justify-content: space-around; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast-day {{ text-align: center; padding: 6px; background: rgba(255,255,255,0.1); border-radius: 8px; font-size: 12px; }}
            
            /* Business Directory */
            .business-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
            .business-card {{ background: white; border-radius: 10px; padding: 20px; }}
            .business-category {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 2px 8px; border-radius: 15px; font-size: 10px; margin: 8px 0; }}
            .business-contact {{ font-size: 12px; margin-top: 10px; color: #666; }}
            
            /* Gallery */
            .gallery {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .gallery-item {{ background: white; border-radius: 10px; padding: 12px; text-align: center; }}
            .gallery-placeholder {{ background: var(--primary-light); color: white; padding: 30px; border-radius: 8px; margin-bottom: 8px; font-size: 12px; }}
            
            /* Poll */
            .poll-section {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 30px; }}
            .poll-options label {{ display: block; margin: 8px 0; cursor: pointer; }}
            
            /* Newsletter */
            .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 35px; border-radius: 15px; text-align: center; margin: 40px 0; }}
            .newsletter input {{ padding: 10px; width: 250px; border: none; border-radius: 5px; margin: 8px; }}
            .newsletter select {{ padding: 10px; width: 200px; border: none; border-radius: 5px; margin: 8px; }}
            .newsletter button {{ background: var(--accent); color: var(--primary); padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            
            /* Footer */
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px 20px; margin-top: 40px; }}
            .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
            .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 13px; }}
            .footer-column a:hover {{ color: var(--accent); }}
            .copyright {{ text-align: center; padding-top: 30px; margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 11px; }}
            
            @media (max-width: 768px) {{
                .stats {{ grid-template-columns: repeat(2, 1fr); }}
                .two-column {{ grid-template-columns: 1fr; }}
                .business-grid {{ grid-template-columns: 1fr; }}
                .gallery {{ grid-template-columns: repeat(2, 1fr); }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 24px; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">🌿 Serving Spruce Grove & Parkland County | "Your Hometown, Online." | Since 2026</div>
        
        <div class="header">
            <div class="logo">
                <h1>📰 {NEWSPAPER_NAME}</h1>
                <p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p>
            </div>
        </div>
        
        <div class="date-header">📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
        
        <div class="nav">
            <a href="/">🏠 HOME</a>
            <a href="/classifieds">📋 CLASSIFIEDS</a>
            <a href="/post-ad">📝 POST AN AD</a>
            <a href="/submit-tip">💡 NEWS TIP</a>
            <a href="/submit-photo">📸 SUBMIT PHOTO</a>
            <a href="/business-directory">🏪 BUSINESS DIRECTORY</a>
            <a href="/events-calendar">📅 EVENTS</a>
            <a href="/subscribe">✉️ NEWSLETTER</a>
        </div>
        
        <div class="hero">
            <h2>Your Hometown, Online.</h2>
            <p>Serving Spruce Grove, Parkland County, Stony Plain and surrounding areas</p>
            <form class="search-bar" action="/search" method="GET">
                <input type="text" name="q" placeholder="Search news, events, businesses...">
                <button type="submit"><i class="fas fa-search"></i> Search</button>
            </form>
        </div>
        
        <div class="quick-links">
            <a href="/submit-tip" class="quick-link">📢 Submit News Tip</a>
            <a href="/submit-photo" class="quick-link">📸 Share Your Photo</a>
            <a href="/business-directory" class="quick-link">🏪 Shop Local</a>
            <a href="/events-calendar" class="quick-link">📅 Community Events</a>
            <a href="/classifieds" class="quick-link">📋 Buy & Sell</a>
        </div>
        
        <div class="main-content">
            <div class="stats">
                <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">25+</div><div>Articles</div></div>
                <div class="stat-card"><i class="fas fa-store"></i><div class="stat-number">50+</div><div>Local Businesses</div></div>
                <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">500+</div><div>Subscribers</div></div>
                <div class="stat-card"><i class="fas fa-camera"></i><div class="stat-number">100+</div><div>Photos</div></div>
            </div>
            
            <div class="two-column">
                <div>
                    <h2 class="section-title">📰 Top Story</h2>
                    <div class="feature-card">
                        <h3>Province Pledges $136 Million for Parkland County Highway Upgrades</h3>
                        <div style="color: #999; font-size: 12px;">📅 March 4, 2026 | Source: Parkland County</div>
                        <p>The Government of Alberta's 2026 Budget confirms continued investment in Highway 60 twinning and Highway 16 improvements, essential for regional safety and economic growth.</p>
                        <a href="/article/1" class="btn">Read Full Story →</a>
                    </div>
                    
                    <h2 class="section-title">📸 Community Photos</h2>
                    <div class="gallery">{gallery_html}</div>
                    <div style="text-align: center;"><a href="/submit-photo" class="btn" style="background: var(--accent); color: var(--primary);">📸 Share Your Photos →</a></div>
                </div>
                
                <div>
                    <div class="weather-widget">
                        <div class="weather-main">
                            <div class="weather-icon">{weather['current']['icon']}</div>
                            <div class="weather-temp">{weather['current']['temp']}<small>°C</small></div>
                            <div>{weather['current']['condition']}</div>
                            <div style="font-size: 12px;">Feels like {weather['current']['feels_like']}°C</div>
                        </div>
                        <div class="weather-details">
                            <div><i class="fas fa-tint"></i><br>{weather['current']['humidity']}%</div>
                            <div><i class="fas fa-wind"></i><br>{weather['current']['wind']} km/h</div>
                            <div><i class="fas fa-sun"></i><br>UV {weather['current']['uv']}</div>
                        </div>
                        <div class="forecast">{forecast_html}</div>
                    </div>
                    
                    <h2 class="section-title">📅 Upcoming Events</h2>
                    <div class="feature-card"><ul style="list-style: none;">{events_html}</ul><a href="/events-calendar" class="btn" style="margin-top: 10px;">View All Events →</a></div>
                    
                    {poll_html}
                    
                    <h2 class="section-title">🏪 Shop Local</h2>
                    <div class="business-grid">{businesses_html}</div>
                    <div style="text-align: center;"><a href="/business-directory" class="btn">View All Businesses →</a></div>
                </div>
            </div>
            
            <div class="newsletter">
                <h3>✉️ Never Miss an Edition</h3>
                <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
                <form action="/do-subscribe" method="POST">
                    <input type="text" name="name" placeholder="Your name">
                    <input type="email" name="email" placeholder="Your email address" required>
                    <select name="neighborhood">
                        <option value="">Select your neighborhood</option>
                        <option>Spruce Grove - Downtown</option>
                        <option>Spruce Grove - West</option>
                        <option>Spruce Grove - East</option>
                        <option>Parkland County</option>
                        <option>Stony Plain</option>
                    </select>
                    <button type="submit">Subscribe Free →</button>
                </form>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <div class="footer-column">
                    <h4>📰 The Gazette</h4>
                    <a href="/">Home</a>
                    <a href="/classifieds">Classifieds</a>
                    <a href="/business-directory">Business Directory</a>
                    <a href="/subscribe">Newsletter</a>
                </div>
                <div class="footer-column">
                    <h4>📬 Connect</h4>
                    <a href="/post-ad">Post an Ad</a>
                    <a href="/submit-tip">Submit a News Tip</a>
                    <a href="/submit-photo">Share a Photo</a>
                    <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                </div>
                <div class="footer-column">
                    <h4>🔗 Resources</h4>
                    <a href="https://www.parklandcounty.com" target="_blank">Parkland County</a>
                    <a href="https://www.psd.ca" target="_blank">Parkland School Division</a>
                    <a href="https://www.sprucegrove.org" target="_blank">City of Spruce Grove</a>
                </div>
                <div class="footer-column">
                    <h4>📍 Our Region</h4>
                    <a href="#">Spruce Grove</a>
                    <a href="#">Parkland County</a>
                    <a href="#">Stony Plain</a>
                </div>
            </div>
            <div class="copyright">
                <p>© {datetime.now().year} {NEWSPAPER_NAME}. All rights reserved.</p>
                <p>Serving Spruce Grove, Parkland County, and surrounding areas since {LAUNCH_DATE}</p>
            </div>
        </div>
        
        <script>
            // PWA Installation
            let deferredPrompt;
            window.addEventListener('beforeinstallprompt', (e) => {{
                e.preventDefault();
                deferredPrompt = e;
                const banner = document.getElementById('installBanner');
                if(banner) banner.style.display = 'flex';
            }});
            
            if ('serviceWorker' in navigator) {{
                navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW failed', err));
            }}
        </script>
    </body>
    </html>
    '''

# ============================================
# Additional Routes for All Features
# ============================================

@app.route('/submit-tip', methods=['GET', 'POST'])
def submit_tip():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        tip = request.form.get('tip')
        category = request.form.get('category')
        
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO news_tips (name, email, tip, category, date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, tip, category, datetime.now().date(), 'pending'))
        conn.commit()
        conn.close()
        
        # Send notification email
        send_email(os.environ.get('EDITOR_EMAIL', 'editor@sprucegrovegazette.com'),
                  f"New News Tip: {category}", f"From: {name} ({email})\n\n{tip}")
        
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Tip Submitted</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1 style="color: #1a3d1a;">✅ Thank You!</h1>
            <p>Your news tip has been submitted. Our editorial team will review it.</p>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Submit a News Tip</title>
        <style>
            body { font-family: Georgia; background: #f9f9f5; padding: 40px; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            input, select, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📢 Submit a News Tip</h1>
            <p>Seen something newsworthy in Spruce Grove or Parkland County? Let us know!</p>
            <form method="POST">
                <input type="text" name="name" placeholder="Your name" required>
                <input type="email" name="email" placeholder="Your email" required>
                <select name="category" required>
                    <option value="">Select Category</option>
                    <option>Breaking News</option>
                    <option>Community Event</option>
                    <option>Business Opening</option>
                    <option>Road Closure</option>
                    <option>Other</option>
                </select>
                <textarea name="tip" rows="6" placeholder="What's happening?" required></textarea>
                <button type="submit">Submit Tip →</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/submit-photo', methods=['GET', 'POST'])
def submit_photo():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        title = request.form.get('title')
        caption = request.form.get('caption')
        
        file = request.files.get('photo')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO photo_submissions (name, email, title, caption, filename, date, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, title, caption, filename, datetime.now().date(), 0))
        conn.commit()
        conn.close()
        
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Photo Submitted</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1 style="color: #1a3d1a;">📸 Thank You!</h1>
            <p>Your photo has been submitted for review. If approved, it will appear in our community gallery.</p>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Share Your Photo</title>
        <style>
            body { font-family: Georgia; background: #f9f9f5; padding: 40px; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📸 Share Your Community Photo</h1>
            <p>Show us what's happening in Spruce Grove and Parkland County!</p>
            <form method="POST" enctype="multipart/form-data">
                <input type="text" name="name" placeholder="Your name" required>
                <input type="email" name="email" placeholder="Your email" required>
                <input type="text" name="title" placeholder="Photo title" required>
                <textarea name="caption" rows="3" placeholder="Tell us about this photo..."></textarea>
                <input type="file" name="photo" accept="image/*" required>
                <button type="submit">Submit Photo →</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/business-directory')
def business_directory():
    category = request.args.get('category', 'all')
    businesses = get_businesses(category, 20)
    
    categories = ['all', 'Restaurants', 'Retail', 'Services', 'Health & Wellness', 'Automotive', 'Home Services']
    categories_html = ''.join([f'<a href="/business-directory?category={c}" class="filter-btn {"active" if category == c else ""}">{c.title()}</a>' for c in categories])
    
    businesses_html = ''.join([f'''
        <div class="business-card">
            <h3>{b["name"]}</h3>
            <div class="business-category">{b["category"]}</div>
            <p>{b["description"]}</p>
            <div class="business-contact">
                <i class="fas fa-phone"></i> {b["phone"]}<br>
                <i class="fas fa-globe"></i> <a href="{b["website"]}" target="_blank">Visit Website</a>
            </div>
        </div>
    ''' for b in businesses])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Business Directory - {NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: Georgia; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .filter-buttons {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; }}
            .filter-btn {{ background: white; padding: 8px 20px; border-radius: 25px; text-decoration: none; color: #333; }}
            .filter-btn.active {{ background: #1a3d1a; color: white; }}
            .business-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
            .business-card {{ background: white; border-radius: 10px; padding: 20px; }}
            .business-category {{ display: inline-block; background: #D4A017; padding: 2px 8px; border-radius: 15px; font-size: 10px; margin: 8px 0; }}
            .business-contact {{ font-size: 12px; margin-top: 10px; color: #666; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            @media (max-width: 768px) {{ .business-grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="header"><h1>🏪 Business Directory</h1><p>Support Local - Shop Spruce Grove & Parkland County</p></div>
        <div class="nav"><a href="/">Home</a><a href="/business-directory">Business Directory</a><a href="/">← Back</a></div>
        <div class="container">
            <div class="filter-buttons">{categories_html}</div>
            <div class="business-grid">{businesses_html if businesses else '<p>No businesses found. <a href="/submit-business">Add your business →</a></p>'}</div>
            <div style="text-align: center; margin-top: 30px;"><a href="/submit-business" class="btn" style="background: #1a3d1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">➕ Add Your Business →</a></div>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
    </body>
    </html>
    '''

@app.route('/submit-business', methods=['GET', 'POST'])
def submit_business():
    if request.method == 'POST':
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO businesses (name, category, description, address, phone, email, website, date, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request.form.get('name'), request.form.get('category'), request.form.get('description'),
              request.form.get('address'), request.form.get('phone'), request.form.get('email'),
              request.form.get('website'), datetime.now().date(), 0))
        conn.commit()
        conn.close()
        return '<html><body style="text-align:center;padding:50px;"><h1>✅ Business Submitted!</h1><p>We will review your listing.</p><a href="/">← Back</a></body></html>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Add Your Business</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea,select{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px}button{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer}</style>
    </head>
    <body><div class="container"><h1>🏪 Add Your Business</h1><p>Get listed in our community business directory.</p><form method="POST"><input type="text" name="name" placeholder="Business Name" required><select name="category"><option>Restaurants</option><option>Retail</option><option>Services</option><option>Health & Wellness</option><option>Automotive</option><option>Home Services</option></select><textarea name="description" rows="3" placeholder="Describe your business..."></textarea><input type="text" name="phone" placeholder="Phone number"><input type="email" name="email" placeholder="Email"><input type="url" name="website" placeholder="Website URL"><button type="submit">Submit Business →</button></form><p><a href="/business-directory">← Back to Directory</a></p></div></body>
    </html>
    '''

@app.route('/events-calendar')
def events_calendar():
    events = get_events(20)
    events_html = ''.join([f'''
        <div class="event-card">
            <div class="event-date">{e["date"]}</div>
            <h3>{e["title"]}</h3>
            <p>{e["description"]}</p>
            <div><i class="fas fa-clock"></i> {e["time"]} | <i class="fas fa-location-dot"></i> {e["location"]}</div>
        </div>
    ''' for e in events])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Community Calendar - {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ font-family: Georgia; background: #f9f9f5; margin: 0; }}
        .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
        .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
        .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .event-card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
        .event-date {{ color: #D4A017; font-weight: bold; margin-bottom: 8px; }}
        .btn {{ background: #1a3d1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
        .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
    </style>
    </head>
    <body>
        <div class="header"><h1>📅 Community Calendar</h1><p>What's happening in Spruce Grove & Parkland County</p></div>
        <div class="nav"><a href="/">Home</a><a href="/events-calendar">Events</a><a href="/submit-event">Submit Event</a><a href="/">← Back</a></div>
        <div class="container">{events_html if events else '<p>No upcoming events. <a href="/submit-event">Add an event →</a></p>'}</div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
    </body>
    </html>
    '''

@app.route('/submit-event', methods=['GET', 'POST'])
def submit_event():
    if request.method == 'POST':
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (title, description, date, time, location, organizer, email, date_submitted, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request.form.get('title'), request.form.get('description'), request.form.get('date'),
              request.form.get('time'), request.form.get('location'), request.form.get('organizer'),
              request.form.get('email'), datetime.now().date(), 0))
        conn.commit()
        conn.close()
        return '<html><body style="text-align:center;padding:50px;"><h1>✅ Event Submitted!</h1><p>We will review your event.</p><a href="/">← Back</a></body></html>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Submit Event</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px}button{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer}</style>
    </head>
    <body><div class="container"><h1>📅 Add an Event</h1><p>Share your community event with Spruce Grove and Parkland County.</p><form method="POST"><input type="text" name="title" placeholder="Event Title" required><textarea name="description" rows="3" placeholder="Event description..."></textarea><input type="date" name="date" required><input type="text" name="time" placeholder="Time"><input type="text" name="location" placeholder="Location"><input type="text" name="organizer" placeholder="Organizer name"><input type="email" name="email" placeholder="Contact email"><button type="submit">Submit Event →</button></form><p><a href="/events-calendar">← Back to Calendar</a></p></div></body>
    </html>
    '''

@app.route('/vote', methods=['POST'])
def vote():
    poll_id = request.form.get('poll_id')
    vote_option = request.form.get('vote')
    
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute(f"UPDATE polls SET votes{vote_option} = votes{vote_option} + 1 WHERE id = ?", (poll_id,))
    conn.commit()
    conn.close()
    
    return '<html><body style="text-align:center;padding:50px;"><h1>✅ Vote Recorded!</h1><p>Thank you for participating in our poll.</p><a href="/">← Back</a></body></html>'

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    email = request.form.get('email')
    name = request.form.get('name', '')
    neighborhood = request.form.get('neighborhood', '')
    
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO subscribers (email, name, subscribed_date, active, neighborhood)
            VALUES (?, ?, ?, 1, ?)
        ''', (email, name, datetime.now().date(), neighborhood))
        conn.commit()
    except:
        pass
    conn.close()
    
    # Send welcome email
    send_email(email, f"Welcome to {NEWSPAPER_NAME}!", f"<h1>Welcome!</h1><p>You're now subscribed to receive daily news from Spruce Grove and Parkland County.</p>")
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribed</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Subscribed!</h1>
        <p>Thank you for subscribing to the Spruce Grove Gazette.</p>
        <p>You'll receive our daily newsletter every morning.</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

# PWA Routes
@app.route('/manifest.json')
def manifest():
    return {
        "name": NEWSPAPER_NAME,
        "short_name": "SG Gazette",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#1a3d1a",
        "background_color": "#f9f9f5",
        "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"}]
    }

@app.route('/sw.js')
def sw():
    return '''self.addEventListener("fetch", () => {});'''

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)