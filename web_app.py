import os
import sqlite3
import smtplib
import glob
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, redirect
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'spruce-grove-gazette-secret-key-2026')

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# Database Setup
# ============================================

def init_database():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            subscribed_date DATE,
            active BOOLEAN DEFAULT 1,
            neighborhood TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supporters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            tier TEXT,
            amount INTEGER,
            start_date DATE,
            active BOOLEAN DEFAULT 1,
            paypal_subscription_id TEXT
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            date DATE,
            time TEXT,
            location TEXT,
            ticket_price TEXT,
            total_tickets INTEGER,
            tickets_sold INTEGER DEFAULT 0,
            organizer TEXT,
            email TEXT,
            approved BOOLEAN DEFAULT 0,
            date_submitted DATE
        )
    ''')
    
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
            date DATE,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
            contact_name TEXT,
            email TEXT,
            phone TEXT,
            package_interest TEXT,
            message TEXT,
            date DATE,
            status TEXT DEFAULT 'new'
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# ============================================
# Helper Functions
# ============================================

def send_email(to_email, subject, html_content):
    sender_email = os.environ.get('SENDER_EMAIL', '')
    sender_password = os.environ.get('EMAIL_PASSWORD', '')
    if not sender_email or not sender_password:
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

def get_weather():
    return {
        "current": {"temp": 18, "feels_like": 17, "condition": "Partly Cloudy", "humidity": 65, "wind": 15, "uv": 5, "icon": "🌤️"},
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
        cursor.execute("SELECT name, category, description, phone, website FROM businesses WHERE approved = 1 AND category = ? ORDER BY featured DESC LIMIT ?", (category, limit))
    else:
        cursor.execute("SELECT name, category, description, phone, website FROM businesses WHERE approved = 1 ORDER BY featured DESC LIMIT ?", (limit,))
    businesses = cursor.fetchall()
    conn.close()
    return [{"name": b[0], "category": b[1], "description": b[2], "phone": b[3], "website": b[4]} for b in businesses]

# ============================================
# NEWS ARTICLES DATA
# ============================================

news_articles = [
    {"id": 1, "title": "Province Pledges $136 Million for Parkland County Highway Upgrades", "date": "March 4, 2026", "source": "Parkland County", "summary": "The Government of Alberta's 2026 Budget confirms continued investment in Highway 60 twinning between Highways 16 and 16A, including a rail overpass to support the Acheson Industrial Area. An additional $20 million has been committed for Highway 16 improvements at Range Road 20, moving to design phase in 2026.", "category": "Infrastructure", "featured": True},
    {"id": 2, "title": "Parkland Food Bank Secures Land for New $1.2 Million Facility", "date": "January 4, 2026", "source": "Parkland Food Bank", "summary": "After 40 years of serving the Tri-Region, the Parkland Food Bank has purchased a 2.86-acre property in Spruce Grove for a new, larger facility.", "category": "Community", "featured": False},
    {"id": 3, "title": "Panthers Advance to Regional Finals After Thrilling Overtime Victory", "date": "April 23, 2026", "source": "Spruce Grove Panthers", "summary": "The Spruce Grove Panthers secured their spot in the regional finals with a dramatic 34-31 overtime victory against the St. Albert Storm. Quarterback Marcus Chen threw for 287 yards and three touchdowns.", "category": "Sports", "featured": False},
    {"id": 4, "title": "New Tech Hub Coming to Downtown Spruce Grove, Creating 150 Jobs", "date": "April 22, 2026", "source": "City of Spruce Grove", "summary": "Nexus Digital Solutions will renovate the historic Johnson Building on Main Street, transforming it into a modern workspace while preserving its heritage character. The $25 million project is expected to bring 150 high-tech jobs.", "category": "Business", "featured": False},
    {"id": 5, "title": "Parkland School Division Receives $354,000 Annual Mental Health Grant", "date": "December 18, 2025", "source": "Parkland School Division", "summary": "The division received approximately $834,000 through the Mental Health in School Pilot project. Alberta Education has now added a wellbeing and mental health grant to the funding manual, with PSD receiving approximately $354,000 annually.", "category": "Education", "featured": False},
    {"id": 6, "title": "Parkland County Secures $200,000 Grant for Sturgeon River Watershed Protection", "date": "May 27, 2025", "source": "Parkland County Council", "summary": "The funding through the Alberta Community Partnership Program supports the Sturgeon River Watershed Alliance. The grant includes $80,000 for water quality evaluation and $120,000 for an Infrastructure Management Framework.", "category": "Environment", "featured": False},
    {"id": 7, "title": "Tri Leisure Centre Receives $235,313 Grant for Boiler Replacement", "date": "December 9, 2025", "source": "Parkland County Council", "summary": "Council approved grant funds for energy reduction projects at the Tri Leisure Centre, including a boiler replacement project partially funded by a $235,313 grant.", "category": "Recreation", "featured": False},
    {"id": 8, "title": "Council Approves $250,000 for Fire Tanker Replacement", "date": "December 9, 2025", "source": "Parkland County Council", "summary": "Parkland County Council has approved $250,000 in additional funding from the Lifecycle Restricted Surplus Account for the replacement of a fire water tanker truck for Fire District 1.", "category": "Emergency Services", "featured": False},
    {"id": 9, "title": "Public Hearing Set for March 24 on Proposed Road Closure", "date": "March 10, 2026", "source": "Parkland County", "summary": "A public hearing has been scheduled for March 24, 2026, regarding Bylaw 2026-13, which proposes to close a portion of road for sale in Parkland County.", "category": "Government", "featured": False},
    {"id": 10, "title": "County Recognizes November as Family Violence Prevention Month", "date": "September 9, 2025", "source": "Parkland County Council", "summary": "Parkland County Council has officially proclaimed several awareness campaigns for November 2025, including Family Violence Prevention Month, Seniors' Fall Prevention Month, Restorative Justice Week, GIS Day, and World Pancreatic Cancer Day.", "category": "Community", "featured": False}
]

# ============================================
# TEST ARTICLE ROUTE
# ============================================

@app.route('/create-test-rss-article')
def create_test_rss_article():
    """Create a test article for RSS feed automation testing"""
    test_title = "Make.com Automation is Working!"
    test_content = """
    <h2>Make.com Automation is Working!</h2>
    <p>Spruce Grove, AB — This is a test article to confirm our automated social media posting is functioning correctly.</p>
    <p>Make.com successfully detected this new article in the RSS feed and is processing it for distribution to our social channels.</p>
    <p>— The Spruce Grove Gazette</p>
    """
    
    output_file = f"test_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head><title>{test_title} - Spruce Grove Gazette</title></head>
        <body style="font-family: Georgia; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1>📰 Spruce Grove Gazette</h1>
            <h2>{test_title}</h2>
            <div>{test_content}</div>
            <p><a href="/">Back to Home</a></p>
        </body>
        </html>
        """)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Test Article Created</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Test Article Created!</h1>
        <p>Your RSS feed should now have a new item.</p>
        <p>File created: {output_file}</p>
        <a href="/rss">View RSS Feed →</a>
        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """

# ============================================
# RSS FEED ROUTE - UPDATED with dynamic test articles
# ============================================

@app.route('/rss')
def rss_feed():
    """Generate RSS feed with newest articles first including test articles"""
    
    # Get all articles including test articles from files
    all_articles = news_articles.copy()
    
    # Look for test article files and add them to the feed
    test_files = glob.glob('test_article_*.html')
    for test_file in test_files:
        # Extract timestamp from filename
        timestamp = test_file.replace('test_article_', '').replace('.html', '')
        try:
            file_time = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
            all_articles.append({
                "id": 999,
                "title": "Make.com Automation Test Article",
                "date": file_time.strftime('%B %d, %Y'),
                "source": "Test",
                "summary": "This is a test article to verify RSS feed automation is working correctly. Make.com should detect this article and trigger social media posts.",
                "category": "Technology",
                "featured": False
            })
        except:
            pass
    
    # Sort articles by date (newest first)
    def parse_date(article):
        try:
            return datetime.strptime(article['date'], '%B %d, %Y')
        except:
            return datetime.now()
    
    sorted_articles = sorted(all_articles, key=parse_date, reverse=True)
    
    items = ""
    for article in sorted_articles[:15]:
        # Format date for RSS
        try:
            pub_date = datetime.strptime(article['date'], '%B %d, %Y').strftime('%a, %d %b %Y %H:%M:%S -0700')
        except:
            pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S -0700')
        
        # Escape XML special characters
        title = article['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        summary = article['summary'][:200].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        items += f"""
        <item>
            <title>{title}</title>
            <link>https://sprucegrovegazette.com/article/{article['id']}</link>
            <guid>https://sprucegrovegazette.com/article/{article['id']}</guid>
            <description>{summary}...</description>
            <pubDate>{pub_date}</pubDate>
        </item>
        """
    
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
    <title>{NEWSPAPER_NAME}</title>
    <link>https://sprucegrovegazette.com</link>
    <atom:link href="https://sprucegrovegazette.com/rss" rel="self" type="application/rss+xml"/>
    <description>Local news for Spruce Grove, Alberta and Parkland County</description>
    <language>en-ca</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S -0700')}</lastBuildDate>
    {items}
</channel>
</rss>"""
    return app.response_class(rss, mimetype='application/rss+xml')

# ============================================
# HOME PAGE
# ============================================

@app.route('/')
def home():
    weather = get_weather()
    events = get_events(5)
    businesses = get_businesses('all', 6)
    
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, price, contact, date, category FROM classifieds WHERE active = 1 ORDER BY date DESC LIMIT 5")
    classifieds_list = cursor.fetchall()
    conn.close()
    
    featured = news_articles[0]
    other_articles = news_articles[1:7]
    
    forecast_html = ''.join([f'<div class="forecast-day"><div class="forecast-day-name">{f["day"]}</div><div class="forecast-icon">{f["icon"]}</div><div class="forecast-temp">{f["high"]}&deg; / {f["low"]}&deg;</div></div>' for f in weather['forecast']])
    
    events_html = ''.join([f'<li><strong>{e["title"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    
    businesses_html = ''.join([f'<div class="business-card"><h4>{b["name"]}</h4><div class="business-category">{b["category"]}</div><p>{b["description"][:100]}...</p><div class="business-contact"><i class="fas fa-phone"></i> {b["phone"]}</div></div>' for b in businesses])
    
    if classifieds_list:
        classifieds_html = ''.join([f'''
            <div style="border-bottom: 1px solid #eee; padding: 12px 0;">
                <span class="classified-category-badge" style="display: inline-block; background: var(--accent); color: var(--primary); padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; margin-right: 10px;">{c[5].upper() if c[5] else "GENERAL"}</span>
                <strong>{c[0]}</strong>
                <p style="margin: 5px 0; color: #666; font-size: 13px;">{c[1][:80]}...</p>
                <div style="color: var(--accent); font-weight: bold;">{c[2] if c[2] else "Price not specified"}</div>
                <small>Contact: {c[3]} | Posted: {c[4]}</small>
            </div>
        ''' for c in classifieds_list])
    else:
        classifieds_html = '<p style="color: #666; text-align: center; padding: 20px;">No classifieds yet. <a href="/post-ad">Post an ad →</a></p>'
    
    other_articles_html = ''
    for a in other_articles:
        other_articles_html += f'''
        <div class="news-item">
            <div class="news-category">{a["category"]}</div>
            <h3><a href="/article/{a["id"]}" style="color: var(--primary); text-decoration: none;">{a["title"]}</a></h3>
            <div class="news-meta">📅 {a["date"]} | Source: {a["source"]}</div>
            <p>{a["summary"][:150]}...</p>
            <a href="/article/{a["id"]}" class="read-more">Read More →</a>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <title>{NEWSPAPER_NAME} - Serving Spruce Grove & Parkland County</title>
        <link rel="manifest" href="/manifest.json">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            .top-bar {{ background: var(--primary); color: white; font-size: 11px; padding: 8px 0; text-align: center; }}
            .header {{ background: white; padding: 25px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
            .logo h1 {{ font-size: 44px; color: var(--primary); }}
            .logo p {{ font-size: 12px; color: #666; letter-spacing: 2px; }}
            .date-header {{ background: #f0f0e8; padding: 8px; text-align: center; font-size: 13px; }}
            .nav {{ background: var(--primary); padding: 12px; text-align: center; position: sticky; top: 0; z-index: 100; overflow-x: auto; white-space: nowrap; }}
            .nav a {{ color: white; margin: 0 12px; text-decoration: none; text-transform: uppercase; font-size: 12px; display: inline-block; }}
            .nav a:hover {{ color: var(--accent); }}
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 40px 20px; text-align: center; }}
            .hero h2 {{ font-size: 32px; }}
            .hero p {{ font-size: 14px; margin-top: 8px; }}
            .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
            .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
            .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .main-content {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
            .quick-links {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 30px; }}
            .quick-link {{ background: white; padding: 12px 25px; border-radius: 30px; text-decoration: none; color: var(--primary); font-weight: bold; }}
            .quick-link:hover {{ background: var(--accent); }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 25px; text-align: center; border-radius: 10px; }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: var(--primary); }}
            .featured-article {{ background: white; border-radius: 15px; padding: 30px; margin-bottom: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .featured-badge {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 4px 12px; border-radius: 15px; font-size: 11px; font-weight: bold; margin-bottom: 15px; }}
            .featured-article h2 {{ font-size: 28px; color: var(--primary); margin-bottom: 15px; }}
            .article-meta {{ color: #999; font-size: 12px; margin-bottom: 15px; }}
            .featured-article p {{ line-height: 1.8; margin-bottom: 20px; }}
            .section-title {{ font-size: 22px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; margin-top: 30px; }}
            .news-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; margin-bottom: 40px; }}
            .news-item {{ background: white; border-radius: 10px; padding: 20px; transition: transform 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .news-item:hover {{ transform: translateY(-3px); }}
            .news-category {{ display: inline-block; background: var(--primary-light); color: white; padding: 2px 10px; border-radius: 12px; font-size: 10px; margin-bottom: 10px; }}
            .news-item h3 {{ font-size: 18px; margin-bottom: 8px; }}
            .news-meta {{ color: #999; font-size: 11px; margin-bottom: 12px; }}
            .read-more {{ color: var(--accent); font-size: 13px; font-weight: bold; text-decoration: none; }}
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 40px; }}
            .btn {{ display: inline-block; background: var(--primary); color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; font-size: 14px; }}
            .weather-widget {{ background: linear-gradient(135deg, #1e3c72, #2a5298); border-radius: 15px; padding: 20px; color: white; margin-bottom: 30px; }}
            .weather-main {{ text-align: center; }}
            .weather-icon {{ font-size: 48px; }}
            .weather-temp {{ font-size: 48px; font-weight: bold; }}
            .weather-details {{ display: flex; justify-content: space-around; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast-day {{ text-align: center; padding: 6px; background: rgba(255,255,255,0.1); border-radius: 8px; font-size: 12px; }}
            .business-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
            .business-card {{ background: white; border-radius: 10px; padding: 20px; }}
            .business-category {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 2px 8px; border-radius: 15px; font-size: 10px; margin: 8px 0; }}
            .business-contact {{ font-size: 12px; margin-top: 10px; color: #666; }}
            .ad-spot {{ background: linear-gradient(135deg, #fff8e1, #ffe082); border: 2px dashed var(--accent); border-radius: 10px; padding: 20px; text-align: center; margin: 30px 0; }}
            .ad-spot h3 {{ color: var(--primary); margin-bottom: 10px; }}
            .ad-price {{ font-size: 28px; font-weight: bold; color: var(--accent); }}
            .btn-ad {{ background: var(--primary); color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; }}
            .classifieds-preview {{ margin-bottom: 15px; }}
            .filter-chip:hover {{ background: var(--accent) !important; color: var(--primary) !important; }}
            .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 35px; border-radius: 15px; text-align: center; margin: 40px 0; }}
            .newsletter input {{ padding: 10px; width: 250px; border: none; border-radius: 5px; margin: 8px; }}
            .newsletter select {{ padding: 10px; width: 200px; border: none; border-radius: 5px; margin: 8px; }}
            .newsletter button {{ background: var(--accent); color: var(--primary); padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px 20px; margin-top: 40px; }}
            .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
            .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 13px; }}
            .footer-column a:hover {{ color: var(--accent); }}
            .copyright {{ text-align: center; padding-top: 30px; margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 11px; }}
            @media (max-width: 768px) {{
                .stats {{ grid-template-columns: repeat(2, 1fr); }}
                .news-grid {{ grid-template-columns: 1fr; }}
                .two-column {{ grid-template-columns: 1fr; }}
                .business-grid {{ grid-template-columns: 1fr; }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 24px; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">🌿 Serving Spruce Grove, Stony Plain & Parkland County | "Your Hometown, Online."</div>
        <div class="header"><div class="logo"><h1>📰 {NEWSPAPER_NAME}</h1><p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p></div></div>
        <div class="date-header">📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
        <div class="nav">
            <a href="/">🏠 HOME</a>
            <a href="/classifieds">📋 CLASSIFIEDS</a>
            <a href="/foodbank">🥫 FOOD BANK</a>
            <a href="/advertise">📢 ADVERTISE</a>
            <a href="/events">📅 EVENTS</a>
            <a href="/support" style="background: #D4A017; color: #1a3d1a; padding: 5px 12px; border-radius: 20px;">🌟 SUPPORT</a>
        </div>
        <div class="hero">
            <h2>Your Hometown, Online.</h2>
            <p>Serving Spruce Grove, Stony Plain & Parkland County</p>
            <form class="search-bar" action="/search" method="GET">
                <input type="text" name="q" placeholder="Search news, events, businesses...">
                <button type="submit"><i class="fas fa-search"></i> Search</button>
            </form>
        </div>
        <div class="quick-links">
            <a href="/submit-tip" class="quick-link">📢 News Tip</a>
            <a href="/submit-photo" class="quick-link">📸 Share Photo</a>
            <a href="/business-directory" class="quick-link">🏪 Shop Local</a>
            <a href="/events" class="quick-link">📅 Events</a>
            <a href="/classifieds" class="quick-link">📋 Buy & Sell</a>
        </div>
        <div class="main-content">
            <div class="stats">
                <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">10+</div><div>Articles</div></div>
                <div class="stat-card"><i class="fas fa-store"></i><div class="stat-number">50+</div><div>Businesses</div></div>
                <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">500+</div><div>Subscribers</div></div>
                <div class="stat-card"><i class="fas fa-calendar"></i><div class="stat-number">10+</div><div>Events</div></div>
            </div>
            
            <div class="featured-article">
                <div class="featured-badge">⭐ FEATURED STORY</div>
                <h2>{featured['title']}</h2>
                <div class="article-meta">📅 {featured['date']} | Source: {featured['source']} | Category: {featured['category']}</div>
                <p>{featured['summary']}</p>
                <a href="/article/{featured['id']}" class="btn">Read Full Story →</a>
            </div>
            
            <h2 class="section-title">📰 More Local News</h2>
            <div class="news-grid">{other_articles_html}</div>
            
            <div class="two-column">
                <div>
                    <h2 class="section-title">📋 Classifieds</h2>
                    <div class="feature-card" style="background:white;border-radius:10px;padding:25px;margin-bottom:30px">
                        <div class="category-filters" style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
                            <a href="/classifieds?category=all" class="filter-chip" style="background: var(--primary); color: white; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">📋 All</a>
                            <a href="/classifieds?category=jobs" class="filter-chip" style="background: #f0f0f0; color: #333; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">💼 Jobs</a>
                            <a href="/classifieds?category=sale" class="filter-chip" style="background: #f0f0f0; color: #333; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">🏷️ For Sale</a>
                            <a href="/classifieds?category=housing" class="filter-chip" style="background: #f0f0f0; color: #333; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">🏠 Housing</a>
                            <a href="/classifieds?category=services" class="filter-chip" style="background: #f0f0f0; color: #333; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">🔧 Services</a>
                            <a href="/classifieds?category=garage" class="filter-chip" style="background: #f0f0f0; color: #333; padding: 6px 14px; border-radius: 20px; text-decoration: none; font-size: 12px;">🏪 Garage Sales</a>
                        </div>
                        <div class="classifieds-preview">{classifieds_html}</div>
                        <div style="margin-top: 15px;">
                            <a href="/classifieds" class="btn" style="margin-right: 10px;">View All Classifieds →</a>
                            <a href="/post-ad" class="btn" style="background: var(--accent); color: var(--primary);">📝 Post an Ad →</a>
                        </div>
                    </div>
                    
                    <h2 class="section-title">📅 Upcoming Events</h2>
                    <div class="feature-card" style="background:white;border-radius:10px;padding:25px;margin-bottom:30px"><ul style="list-style: none;">{events_html}</ul><a href="/events" class="btn">View All Events →</a></div>
                    
                    <h2 class="section-title">🏪 Local Businesses</h2>
                    <div class="business-grid">{businesses_html}</div>
                    <div style="text-align: center;"><a href="/business-directory" class="btn">View All →</a></div>
                </div>
                
                <div>
                    <div class="weather-widget">
                        <div class="weather-main"><div class="weather-icon">{weather['current']['icon']}</div><div class="weather-temp">{weather['current']['temp']}<small>°C</small></div><div>{weather['current']['condition']}</div></div>
                        <div class="weather-details"><div><i class="fas fa-tint"></i><br>{weather['current']['humidity']}%</div><div><i class="fas fa-wind"></i><br>{weather['current']['wind']} km/h</div></div>
                        <div class="forecast">{forecast_html}</div>
                    </div>
                    
                    <div class="ad-spot">
                        <i class="fas fa-bullhorn" style="font-size: 36px; color: var(--primary);"></i>
                        <h3>Advertise With Us</h3>
                        <p>Reach thousands of local readers in Spruce Grove and Parkland County</p>
                        <div class="ad-price">Starting at $150/month</div>
                        <a href="/advertise" class="btn-ad">Get Started →</a>
                    </div>
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
                <div class="footer-column"><h4>📰 The Gazette</h4><a href="/">Home</a><a href="/classifieds">Classifieds</a><a href="/business-directory">Business Directory</a><a href="/subscribe">Newsletter</a></div>
                <div class="footer-column"><h4>📬 Connect</h4><a href="/submit-tip">News Tip</a><a href="/submit-photo">Share Photo</a><a href="/advertise">Advertise</a><a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a></div>
                <div class="footer-column"><h4>🤝 Community</h4><a href="/foodbank">Parkland Food Bank</a><a href="/support">Become a Supporter</a><a href="/events">Community Calendar</a></div>
                <div class="footer-column"><h4>📍 Our Region</h4><a href="#">Spruce Grove</a><a href="#">Parkland County</a><a href="#">Stony Plain</a></div>
            </div>
            <div class="copyright"><p>© {datetime.now().year} {NEWSPAPER_NAME}. All rights reserved.</p><p>Serving Spruce Grove, Stony Plain & Parkland County since {LAUNCH_DATE}</p></div>
        </div>
    </body>
    </html>
    '''

# ============================================
# ARTICLE PAGE
# ============================================

@app.route('/article/<int:article_id>')
def article_page(article_id):
    article = next((a for a in news_articles if a['id'] == article_id), None)
    if not article:
        return redirect('/')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{article['title']} - {NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: Georgia, serif; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; background: white; border-radius: 10px; margin-top: 40px; }}
            .article-title {{ font-size: 32px; color: #1a3d1a; margin-bottom: 15px; }}
            .article-meta {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 15px; margin-bottom: 25px; }}
            .article-content {{ line-height: 1.8; font-size: 18px; }}
            .article-content p {{ margin-bottom: 20px; }}
            .btn-back {{ display: inline-block; background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 30px; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            @media (max-width: 768px) {{ .container {{ margin: 20px; padding: 20px; }} .article-title {{ font-size: 24px; }} }}
        </style>
    </head>
    <body>
        <div class="header"><h1>📰 {NEWSPAPER_NAME}</h1></div>
        <div class="nav"><a href="/">Home</a><a href="/classifieds">Classifieds</a><a href="/events">Events</a></div>
        <div class="container">
            <h1 class="article-title">{article['title']}</h1>
            <div class="article-meta">📅 {article['date']} | Source: {article['source']} | Category: {article['category']}</div>
            <div class="article-content">
                <p>{article['summary']}</p>
                <p>For more details on this story, please visit the official source or contact the Spruce Grove Gazette newsroom.</p>
                <p><strong>Stay informed with the Spruce Grove Gazette.</strong> Subscribe to our free newsletter for daily updates.</p>
            </div>
            <a href="/" class="btn-back">← Back to Home</a>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME} | Serving Spruce Grove & Parkland County</p></div>
    </body>
    </html>
    '''

# ============================================
# SUPPORTER PAGE
# ============================================

@app.route('/support')
def support():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Become a Supporter - Spruce Grove Gazette</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root { --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; --donate: #e74c3c; }
            body { font-family: 'Georgia', serif; background: #f9f9f5; margin: 0; }
            .header { background: var(--primary); color: white; padding: 40px; text-align: center; }
            .header h1 { margin: 0; font-size: 42px; }
            .header p { font-size: 18px; margin-top: 10px; opacity: 0.9; }
            .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
            .pricing-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; margin: 50px 0; }
            .pricing-card { background: white; border-radius: 15px; padding: 35px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
            .pricing-card:hover { transform: translateY(-5px); }
            .pricing-card.featured { border: 2px solid var(--accent); position: relative; }
            .pricing-card.donation-card { border: 2px solid var(--donate); background: linear-gradient(135deg, white, #fff5f5); }
            .popular-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--accent); color: var(--primary); padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: bold; }
            .donation-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--donate); color: white; padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: bold; }
            .price { font-size: 48px; font-weight: bold; color: var(--primary); margin: 20px 0; }
            .price small { font-size: 16px; font-weight: normal; color: #666; }
            .features { list-style: none; text-align: left; margin: 25px 0; }
            .features li { padding: 8px 0; border-bottom: 1px solid #eee; }
            .features i { color: #27ae60; margin-right: 10px; width: 20px; }
            .btn { display: inline-block; background: var(--primary); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; font-weight: bold; cursor: pointer; border: none; }
            .btn:hover { background: #0d260d; }
            .paypal-container { margin-top: 20px; min-height: 120px; }
            .custom-amount { margin-top: 20px; }
            .custom-amount input { padding: 12px; width: 150px; border: 2px solid var(--donate); border-radius: 5px; text-align: center; font-size: 18px; margin: 10px; }
            .impact-section { background: white; border-radius: 15px; padding: 40px; text-align: center; margin-top: 50px; }
            .impact-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin-top: 30px; }
            .impact-card { text-align: center; padding: 20px; }
            .impact-card i { font-size: 48px; color: var(--accent); margin-bottom: 15px; }
            .footer { background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }
            @media (max-width: 768px) { .pricing-grid { grid-template-columns: 1fr; } .impact-grid { grid-template-columns: 1fr; } }
        </style>
        <script src="https://www.paypal.com/sdk/js?client-id=ARtcRWqbrpvaJo2wJNJewoyuPm0QlT6_FyP_X939IjMW7B1kWFDNw6t9L1rnysbeBWNemj2A-ellK7BW&currency=CAD&vault=true&intent=subscription"></script>
    </head>
    <body>
        <div class="header">
            <h1>🌟 Support Local Journalism</h1>
            <p>Help keep Spruce Grove & Parkland County informed and connected</p>
        </div>
        
        <div class="container">
            <div class="pricing-grid">
                <div class="pricing-card">
                    <h3>Free Reader</h3>
                    <div class="price">$0</div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> Daily newsletter</li>
                        <li><i class="fas fa-check"></i> Access to all articles</li>
                        <li><i class="fas fa-check"></i> Community calendar</li>
                        <li><i class="fas fa-check"></i> Business directory access</li>
                        <li><i class="fas fa-check"></i> Event listings</li>
                    </ul>
                    <a href="/subscribe" class="btn">Current Plan →</a>
                </div>
                
                <div class="pricing-card">
                    <h3>Monthly Supporter</h3>
                    <div class="price">$5<span><small>/month</small></span></div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> All free features</li>
                        <li><i class="fas fa-check"></i> Supporter badge</li>
                        <li><i class="fas fa-check"></i> Weekly exclusive content</li>
                        <li><i class="fas fa-check"></i> Behind-the-scenes updates</li>
                    </ul>
                    <div class="paypal-container" id="paypal-monthly"></div>
                </div>
                
                <div class="pricing-card donation-card">
                    <div class="donation-badge">❤️ MAKE A DONATION</div>
                    <h3>Support Local Journalism</h3>
                    <div class="price">$<span id="customAmountDisplay">10</span><span><small>/one-time</small></span></div>
                    <div class="custom-amount">
                        <input type="number" id="customAmount" min="5" max="1000" step="5" value="10">
                        <div style="font-size: 12px; color: #666;">CAD $5 - $1000</div>
                    </div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> Choose your own amount</li>
                        <li><i class="fas fa-check"></i> One-time donation</li>
                        <li><i class="fas fa-check"></i> Supporter recognition</li>
                        <li><i class="fas fa-check"></i> Tax receipt available for donations over $20</li>
                    </ul>
                    <div id="customPaypalContainer"></div>
                </div>
                
                <div class="pricing-card featured">
                    <div class="popular-badge">⭐ BEST VALUE</div>
                    <h3>Yearly Supporter</h3>
                    <div class="price">$50<span><small>/year</small></span></div>
                    <div style="font-size: 14px; color: #666; margin-top: -15px;">Save $10 compared to monthly</div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> All monthly benefits</li>
                        <li><i class="fas fa-check"></i> Name in annual supporter roll</li>
                        <li><i class="fas fa-check"></i> Exclusive Gazette merch discount</li>
                        <li><i class="fas fa-check"></i> Invitation to annual supporter event</li>
                        <li><i class="fas fa-check"></i> Direct input on coverage priorities</li>
                    </ul>
                    <div class="paypal-container" id="paypal-yearly"></div>
                </div>
            </div>
            
            <div class="impact-section">
                <h2>Your Donation Makes a Difference</h2>
                <div class="impact-grid">
                    <div class="impact-card"><i class="fas fa-newspaper"></i><h3>$10</h3><p>Funds one day of local news coverage</p></div>
                    <div class="impact-card"><i class="fas fa-camera"></i><h3>$25</h3><p>Supports community photo submissions for a week</p></div>
                    <div class="impact-card"><i class="fas fa-mobile-alt"></i><h3>$50</h3><p>Keeps the Gazette free for everyone for one month</p></div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding: 20px; background: #e8f5e9; border-radius: 10px;">
                <i class="fas fa-lock" style="margin-right: 10px;"></i>
                <strong>Secure payments by PayPal</strong> — Your payment information is encrypted and never stored on our servers.
                <br><small>You can cancel your subscription anytime from your PayPal account.</small>
                <br><br>
                <i class="fas fa-receipt"></i> <strong>Tax receipts available for donations over $20</strong>
            </div>
        </div>
        
        <div class="footer">
            <p><a href="/" style="color: white;">← Back to Home</a></p>
            <p>© 2026 The Spruce Grove Gazette | Serving Spruce Grove & Parkland County</p>
        </div>
        
        <script>
            paypal.Buttons({
                style: { shape: 'rect', color: 'gold', layout: 'vertical', label: 'subscribe', height: 40 },
                createSubscription: function(data, actions) {
                    return actions.subscription.create({
                        plan_id: 'P-8WS19802N5406432ENHWAJVY',
                        application_context: { shipping_preference: 'NO_SHIPPING' }
                    });
                },
                onApprove: function(data, actions) {
                    alert('Thank you for subscribing! You are now a Gazette Monthly Supporter.');
                    window.location.href = '/support-thank-you';
                },
                onError: function(err) {
                    console.error(err);
                    alert('Payment failed. Please try again.');
                }
            }).render('#paypal-monthly');
            
            paypal.Buttons({
                style: { shape: 'rect', color: 'gold', layout: 'vertical', label: 'subscribe', height: 40 },
                createSubscription: function(data, actions) {
                    return actions.subscription.create({
                        plan_id: 'P-9BL3287175752125FNHWAKYY',
                        application_context: { shipping_preference: 'NO_SHIPPING' }
                    });
                },
                onApprove: function(data, actions) {
                    alert('Thank you for subscribing! You are now a Gazette Yearly Supporter.');
                    window.location.href = '/support-thank-you';
                },
                onError: function(err) {
                    console.error(err);
                    alert('Payment failed. Please try again.');
                }
            }).render('#paypal-yearly');
            
            const customInput = document.getElementById('customAmount');
            const displaySpan = document.getElementById('customAmountDisplay');
            
            customInput.addEventListener('input', function() {
                displaySpan.innerText = customInput.value;
                renderCustomPaypalButton();
            });
            
            function renderCustomPaypalButton() {
                const amount = parseFloat(customInput.value);
                const container = document.getElementById('customPaypalContainer');
                if (container) {
                    container.innerHTML = '';
                    
                    paypal.Buttons({
                        style: { shape: 'rect', color: 'gold', layout: 'vertical', label: 'paypal', height: 40 },
                        createOrder: function(data, actions) {
                            return actions.order.create({
                                purchase_units: [{
                                    amount: { value: amount.toFixed(2), currency_code: 'CAD' },
                                    description: 'Gazette Supporter Donation'
                                }]
                            });
                        },
                        onApprove: function(data, actions) {
                            return actions.order.capture().then(function(details) {
                                alert('Thank you for your donation of $' + amount.toFixed(2) + '! Your support keeps local journalism alive.');
                                window.location.href = '/support-thank-you';
                            });
                        },
                        onError: function(err) {
                            console.error(err);
                            alert('Payment failed. Please try again.');
                        }
                    }).render('#customPaypalContainer');
                }
            }
            
            renderCustomPaypalButton();
        </script>
    </body>
    </html>
    '''

@app.route('/support-thank-you')
def support_thank_you():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Thank You!</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px; background: #f9f9f5;">
        <h1 style="color: #1a3d1a;">🎉 Thank You for Your Support!</h1>
        <p>You are now an official Spruce Grove Gazette Supporter.</p>
        <p>Your contribution helps keep local journalism alive in Spruce Grove and Parkland County.</p>
        <p>You'll receive a confirmation email shortly.</p>
        <a href="/" style="color: #1a3d1a;">← Back to Gazette</a>
    </body>
    </html>
    '''

# ============================================
# ADVERTISING ROUTES
# ============================================

@app.route('/advertise')
def advertise():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Advertise With Us</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: Georgia; background: #f9f9f5; margin: 0; }
        .header { background: #1a3d1a; color: white; padding: 40px; text-align: center; }
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .stats-banner { background: white; border-radius: 15px; padding: 30px; text-align: center; margin-bottom: 50px; }
        .stat-grid { display: flex; justify-content: center; gap: 50px; flex-wrap: wrap; }
        .stat-number { font-size: 42px; font-weight: bold; color: #D4A017; }
        .package-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin: 50px 0; }
        .package-card { background: white; border-radius: 15px; padding: 35px; text-align: center; }
        .package-card.featured { border: 2px solid #D4A017; position: relative; }
        .popular-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #D4A017; padding: 5px 20px; border-radius: 20px; font-size: 12px; }
        .package-price { font-size: 36px; font-weight: bold; color: #D4A017; margin: 20px 0; }
        .btn-inquire { background: #1a3d1a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; }
        .contact-form { background: white; border-radius: 15px; padding: 40px; margin: 50px 0; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #1a3d1a; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; }
        .footer { background: #0d260d; color: white; text-align: center; padding: 30px; }
        @media (max-width: 768px) { .package-grid { grid-template-columns: 1fr; } }
    </style>
    </head>
    <body>
        <div class="header"><h1>📰 Advertise With The Gazette</h1><p>Reach thousands of local readers</p></div>
        <div class="container">
            <div class="stats-banner"><div class="stat-grid"><div><div class="stat-number">10,000+</div>Monthly Readers</div><div><div class="stat-number">500+</div>Newsletter Subscribers</div><div><div class="stat-number">100%</div>Local Audience</div></div></div>
            <div class="package-grid">
                <div class="package-card"><h3>Digital Display</h3><div class="package-price">$150<span style="font-size:14px">/month</span></div><p>Banner ad on homepage</p><a href="/inquire?package=display" class="btn-inquire">Get Started →</a></div>
                <div class="package-card featured"><div class="popular-badge">MOST POPULAR</div><h3>Sponsored Article</h3><div class="package-price">$250<span style="font-size:14px">/article</span></div><p>Professional feature story</p><a href="/inquire?package=sponsored" class="btn-inquire">Get Started →</a></div>
                <div class="package-card"><h3>Community Spotlight</h3><div class="package-price">$400<span style="font-size:14px">/month</span></div><p>Weekly business feature</p><a href="/inquire?package=spotlight" class="btn-inquire">Get Started →</a></div>
            </div>
            <div class="contact-form">
                <h3>Request a Media Kit</h3>
                <form action="/inquire" method="POST">
                    <input type="text" name="business_name" placeholder="Business Name" required>
                    <input type="text" name="contact_name" placeholder="Your Name" required>
                    <input type="email" name="email" placeholder="Email Address" required>
                    <input type="tel" name="phone" placeholder="Phone Number">
                    <select name="package_interest"><option value="">I'm interested in...</option><option>Digital Display Ad</option><option>Sponsored Article</option><option>Community Spotlight</option></select>
                    <textarea name="message" rows="4" placeholder="Tell us about your business..."></textarea>
                    <button type="submit">Send Inquiry →</button>
                </form>
            </div>
        </div>
        <div class="footer"><p><a href="/" style="color: white;">← Back to Home</a></p></div>
    </body>
    </html>
    '''

@app.route('/inquire', methods=['GET', 'POST'])
def inquire():
    if request.method == 'POST':
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO ad_inquiries (business_name, contact_name, email, phone, package_interest, message, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (request.form.get('business_name'), request.form.get('contact_name'), request.form.get('email'),
             request.form.get('phone'), request.form.get('package_interest'), request.form.get('message'),
             datetime.now().date(), 'new'))
        conn.commit()
        conn.close()
        return '<html><body style="text-align:center;padding:50px"><h1>✅ Thank You!</h1><p>We will contact you within 24 hours.</p><a href="/">← Back</a></body></html>'
    
    package = request.args.get('package', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Advertising Inquiry</title>
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}.container{{max-width:600px;margin:0 auto;padding:40px20px}}.form-card{{background:white;border-radius:15px;padding:30px}}input,select,textarea{{width:100%;padding:12px;margin:10px0;border:1px solid #ddd;border-radius:5px}}button{{background:#1a3d1a;color:white;padding:12px30px;border:none;border-radius:5px;cursor:pointer}}.footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}}</style>
    </head>
    <body><div class="header"><h1>📰 Advertising Inquiry</h1></div><div class="container"><div class="form-card"><h2>Request Information</h2><form method="POST"><input type="text" name="business_name" placeholder="Business Name" required><input type="text" name="contact_name" placeholder="Your Name" required><input type="email" name="email" placeholder="Email" required><input type="tel" name="phone" placeholder="Phone"><select name="package_interest"><option value="">I'm interested in...</option><option value="Digital Display Ad" {'selected' if package == 'display' else ''}>Digital Display Ad ($150/month)</option><option value="Sponsored Article" {'selected' if package == 'sponsored' else ''}>Sponsored Article ($250/article)</option><option value="Community Spotlight" {'selected' if package == 'spotlight' else ''}>Community Spotlight ($400/month)</option></select><textarea name="message" rows="4" placeholder="Tell us about your business..."></textarea><button type="submit">Send Inquiry →</button></form><a href="/advertise">← Back</a></div></div><div class="footer"><p><a href="/" style="color:white">← Back to Home</a></p></div></body>
    </html>
    '''

# ============================================
# FOOD BANK ROUTE
# ============================================

@app.route('/foodbank')
def foodbank():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Parkland Food Bank</title>
    <style>
        body { font-family: Georgia; background: #f9f9f5; margin: 0; }
        .header { background: #1a3d1a; color: white; padding: 30px; text-align: center; }
        .stats-bar { background: #e74c3c; color: white; padding: 15px; display: flex; justify-content: space-around; flex-wrap: wrap; }
        .stat-number { font-size: 28px; font-weight: bold; }
        .container { max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
        .featured-article { background: white; border-radius: 15px; padding: 30px; margin-bottom: 30px; }
        .event-card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; display: flex; gap: 20px; align-items: center; }
        .event-date { background: #D4A017; color: #1a3d1a; padding: 15px; border-radius: 10px; text-align: center; min-width: 80px; }
        .help-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin: 30px 0; }
        .help-card { text-align: center; padding: 20px; background: white; border-radius: 10px; }
        .help-card i { font-size: 48px; color: #e74c3c; }
        .btn-website { background: #1a3d1a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
        .footer { background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }
        @media (max-width: 768px) { .event-card { flex-direction: column; } .help-grid { grid-template-columns: 1fr; } }
    </style>
    </head>
    <body>
        <div class="header"><h1>🥫 Parkland Food Bank</h1><p>Serving Spruce Grove, Stony Plain & Parkland County Since 1984</p></div>
        <div class="stats-bar"><div><div class="stat-number">40+</div>Years</div><div><div class="stat-number">5,634</div>Individuals</div><div><div class="stat-number">31,945</div>Visits</div><div><div class="stat-number">9,707</div>Hampers/Month</div></div>
        <div class="container">
            <div class="featured-article"><h2>New $1.2 Million Facility Coming to Spruce Grove</h2><p>Parkland Food Bank has purchased a 2.86-acre property for a new, larger facility.</p></div>
            <h2>📅 Upcoming Events</h2>
            <div class="event-card"><div class="event-date"><div>APR</div><div>13-17</div></div><div><h3>Food Fight '26</h3><p>Spruce Grove Composite High School's week-long food drive</p></div></div>
            <div class="event-card"><div class="event-date"><div>AUG</div><div>2026</div></div><div><h3>Corporate Food Drive Challenge</h3><p>Local businesses compete to collect food</p></div></div>
            <div class="help-grid">
                <div class="help-card"><i class="fas fa-apple-alt"></i><h3>Donate Food</h3><p>105 Madison Crescent</p></div>
                <div class="help-card"><i class="fas fa-dollar-sign"></i><h3>Monetary Donations</h3><p>parklandfoodbank.org</p></div>
                <div class="help-card"><i class="fas fa-hands-helping"></i><h3>Volunteer</h3><p>Call 780-962-4565</p></div>
            </div>
            <div style="text-align: center;"><a href="https://parklandfoodbank.org" target="_blank" class="btn-website">Visit Parkland Food Bank Website →</a></div>
        </div>
        <div class="footer"><p><a href="/" style="color: white;">← Back to Home</a></p></div>
    </body>
    </html>
    '''

# ============================================
# EVENTS ROUTES
# ============================================

@app.route('/events')
def events_list():
    events = get_events(20)
    events_html = ''.join([f'<div style="background:white;padding:20px;margin-bottom:15px;border-radius:10px"><strong>{e["title"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</div>' for e in events])
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Community Events</title>
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}.container{{max-width:800px;margin:0 auto;padding:40px 20px}}.btn{{background:#1a3d1a;color:white;padding:10px20px;text-decoration:none;border-radius:5px}}</style>
    </head>
    <body><div class="header"><h1>📅 Community Events Calendar</h1></div><div class="container">{events_html if events_html else '<p>No upcoming events.</p>'}<div style="text-align:center;margin-top:30px"><a href="/events/create" class="btn">+ Create Event</a> <a href="/" class="btn">← Back</a></div></div></body>
    </html>
    '''

@app.route('/events/create', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO events (title, description, date, time, location, ticket_price, total_tickets, organizer, email, date_submitted, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (request.form.get('title'), request.form.get('description'), request.form.get('date'),
             request.form.get('time'), request.form.get('location'), request.form.get('ticket_price', 'Free'),
             request.form.get('total_tickets'), request.form.get('organizer'), request.form.get('email'),
             datetime.now().date(), 0))
        conn.commit()
        conn.close()
        return '<html><body style="text-align:center;padding:50px"><h1>✅ Event Created!</h1><p>Pending approval.</p><a href="/events">← Back</a></body></html>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Create Event</title><style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style></head>
    <body><div class="container"><h1>📅 Create an Event</h1><form method="POST"><input type="text" name="title" placeholder="Event Title" required><textarea name="description" rows="4" placeholder="Description"></textarea><input type="date" name="date" required><input type="text" name="time" placeholder="Time"><input type="text" name="location" placeholder="Location"><input type="text" name="ticket_price" placeholder="Ticket price (or Free)"><input type="number" name="total_tickets" placeholder="Total tickets"><input type="text" name="organizer" placeholder="Organizer"><input type="email" name="email" placeholder="Contact email"><button type="submit">Create Event →</button></form><a href="/events">← Back</a></div></body>
    </html>
    '''

# ============================================
# CLASSIFIEDS ROUTES
# ============================================

@app.route('/classifieds')
def classifieds():
    category = request.args.get('category', 'all')
    
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    if category != 'all':
        cursor.execute("SELECT title, description, price, contact, date, category FROM classifieds WHERE active = 1 AND category = ? ORDER BY date DESC", (category,))
    else:
        cursor.execute("SELECT title, description, price, contact, date, category FROM classifieds WHERE active = 1 ORDER BY date DESC")
    classifieds_list = cursor.fetchall()
    conn.close()
    
    classifieds_html = ''.join([f'''
        <div style="background:white;border-radius:10px;padding:20px;margin-bottom:15px;box-shadow:0 2px 5px rgba(0,0,0,0.1)">
            <span style="display:inline-block;background:#D4A017;color:#1a3d1a;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:bold;margin-right:10px">{c[5].upper() if c[5] else "GENERAL"}</span>
            <h3>{c[0]}</h3>
            <p>{c[1]}</p>
            <div style="color:#D4A017;font-weight:bold">{c[2] if c[2] else "Price not specified"}</div>
            <small>Contact: {c[3]} | Posted: {c[4]}</small>
        </div>
    ''' for c in classifieds_list])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Classifieds - {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ font-family: Georgia; background: #f9f9f5; margin: 0; }}
        .header {{ background: #1a3d1a; color: white; padding: 30px; text-align: center; }}
        .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
        .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .category-filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; }}
        .filter-btn {{ background: white; padding: 8px 20px; border-radius: 25px; text-decoration: none; color: #333; }}
        .filter-btn.active {{ background: #1a3d1a; color: white; }}
        .btn {{ background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }}
        .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
    </style>
    </head>
    <body>
        <div class="header"><h1>📋 Classifieds</h1><p>Buy & Sell in Spruce Grove</p></div>
        <div class="nav"><a href="/">🏠 Home</a><a href="/classifieds">📋 Classifieds</a><a href="/post-ad">📝 Post an Ad</a></div>
        <div class="container">
            <div class="category-filters">
                <a href="/classifieds?category=all" class="filter-btn {"active" if category == "all" else ""}">📋 All</a>
                <a href="/classifieds?category=jobs" class="filter-btn {"active" if category == "jobs" else ""}">💼 Jobs</a>
                <a href="/classifieds?category=sale" class="filter-btn {"active" if category == "sale" else ""}">🏷️ For Sale</a>
                <a href="/classifieds?category=housing" class="filter-btn {"active" if category == "housing" else ""}">🏠 Housing</a>
                <a href="/classifieds?category=services" class="filter-btn {"active" if category == "services" else ""}">🔧 Services</a>
                <a href="/classifieds?category=garage" class="filter-btn {"active" if category == "garage" else ""}">🏪 Garage Sales</a>
            </div>
            {classifieds_html if classifieds_list else '<p style="text-align:center;color:#666">No classifieds found.</p>'}
            <div style="text-align:center;margin-top:30px"><a href="/post-ad" class="btn">📝 Post an Ad →</a> <a href="/" class="btn">← Back</a></div>
        </div>
        <div class="footer"><p>© 2026 {NEWSPAPER_NAME} | "Your Hometown, Online."</p></div>
    </body>
    </html>
    '''

@app.route('/post-ad', methods=['GET', 'POST'])
def post_ad():
    if request.method == 'POST':
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO classifieds (category, title, description, price, contact, email, phone, date, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (request.form.get('category'), request.form.get('title'), request.form.get('description'),
             request.form.get('price'), request.form.get('contact'), request.form.get('email'),
             request.form.get('phone'), datetime.now().date(), 1))
        conn.commit()
        conn.close()
        return '<html><body style="text-align:center;padding:50px"><h1>✅ Ad Posted!</h1><a href="/classifieds">View Classifieds</a></body></html>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Post an Ad</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,select,textarea{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style>
    </head>
    <body><div class="container"><h1>📝 Post a Classified Ad</h1><form method="POST"><select name="category"><option>Jobs</option><option>For Sale</option><option>Housing</option><option>Services</option><option>Garage Sale</option></select><input type="text" name="title" placeholder="Ad Title" required><textarea name="description" rows="4" placeholder="Description"></textarea><input type="text" name="price" placeholder="Price"><input type="text" name="contact" placeholder="Contact info"><input type="email" name="email" placeholder="Email"><input type="text" name="phone" placeholder="Phone"><button type="submit">Post Ad →</button></form><a href="/classifieds">← Back</a></div></body>
    </html>
    '''

# ============================================
# SUBSCRIBE & OTHER ROUTES
# ============================================

@app.route('/subscribe')
def subscribe():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribe</title>
    <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh}.container{background:white;padding:40px;border-radius:10px;max-width:400px;text-align:center}input{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style>
    </head>
    <body><div class="container"><h1>📧 Subscribe</h1><form action="/do-subscribe" method="POST"><input type="text" name="name" placeholder="Your name"><input type="email" name="email" placeholder="Email" required><button type="submit">Subscribe →</button></form><a href="/">← Back</a></div></body>
    </html>
    '''

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    email = request.form.get('email')
    name = request.form.get('name', '')
    if email:
        conn = sqlite3.connect('gazette.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO subscribers (email, name, subscribed_date, active) VALUES (?, ?, ?, 1)", (email, name, datetime.now().date()))
            conn.commit()
        except:
            pass
        conn.close()
    return '<html><body style="text-align:center;padding:50px"><h1>✅ Subscribed!</h1><a href="/">Back to Home</a></body></html>'

@app.route('/submit-tip')
def submit_tip():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Submit a News Tip</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style>
    </head>
    <body><div class="container"><h1>📢 Submit a News Tip</h1><form method="POST" action="/do-submit-tip"><input type="text" name="name" placeholder="Your name"><input type="email" name="email" placeholder="Your email"><select name="category"><option>Breaking News</option><option>Community Event</option><option>Business Opening</option></select><textarea name="tip" rows="5" placeholder="What's happening?"></textarea><button type="submit">Submit Tip →</button></form><a href="/">← Back</a></div></body>
    </html>
    '''

@app.route('/do-submit-tip', methods=['POST'])
def do_submit_tip():
    name = request.form.get('name')
    email = request.form.get('email')
    category = request.form.get('category')
    tip = request.form.get('tip')
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO news_tips (name, email, tip, category, date, status) VALUES (?, ?, ?, ?, ?, ?)", (name, email, tip, category, datetime.now().date(), 'pending'))
    conn.commit()
    conn.close()
    return '<html><body style="text-align:center;padding:50px"><h1>✅ Thank You!</h1><p>Your tip has been submitted.</p><a href="/">Back to Home</a></body></html>'

@app.route('/submit-photo')
def submit_photo():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Share Your Photo</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style>
    </head>
    <body><div class="container"><h1>📸 Share Your Community Photo</h1><form method="POST" action="/do-submit-photo" enctype="multipart/form-data"><input type="text" name="name" placeholder="Your name"><input type="email" name="email" placeholder="Your email"><input type="text" name="title" placeholder="Photo title"><textarea name="caption" rows="3" placeholder="Describe this photo..."></textarea><input type="file" name="photo" accept="image/*"><button type="submit">Submit Photo →</button></form><a href="/">← Back</a></div></body>
    </html>
    '''

@app.route('/do-submit-photo', methods=['POST'])
def do_submit_photo():
    return '<html><body style="text-align:center;padding:50px"><h1>✅ Photo Submitted!</h1><p>Thank you for sharing.</p><a href="/">Back to Home</a></body></html>'

@app.route('/business-directory')
def business_directory():
    businesses = get_businesses('all', 50)
    businesses_html = ''.join([f'<div style="background:white;border-radius:10px;padding:20px"><h3>{b["name"]}</h3><div style="background:#D4A017;display:inline-block;padding:2px8px;border-radius:15px;font-size:10px">{b["category"]}</div><p>{b["description"][:100]}...</p><div><i class="fas fa-phone"></i> {b["phone"]}</div></div>' for b in businesses])
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Business Directory</title>
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}.container{{max-width:1000px;margin:0 auto;padding:40px20px}}.business-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}.btn{{background:#1a3d1a;color:white;padding:10px20px;text-decoration:none;border-radius:5px}}@media(max-width:768px){{.business-grid{{grid-template-columns:1fr}}}}</style>
    </head>
    <body><div class="header"><h1>🏪 Local Business Directory</h1><p>Support Spruce Grove & Parkland County Businesses</p></div><div class="container"><div class="business-grid">{businesses_html if businesses_html else '<p>No businesses listed yet.</p>'}</div><div style="text-align:center;margin-top:30px"><a href="/submit-business" class="btn">➕ Add Your Business</a> <a href="/" class="btn">← Back</a></div></div></body>
    </html>
    '''

@app.route('/submit-business')
def submit_business():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Add Your Business</title>
    <style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea,select{width:100%;padding:10px;margin:10px 0}button{background:#1a3d1a;color:white;padding:12px24px;border:none;border-radius:5px}</style>
    </head>
    <body><div class="container"><h1>🏪 Add Your Business</h1><form method="POST" action="/do-submit-business"><input type="text" name="name" placeholder="Business Name" required><select name="category"><option>Restaurants</option><option>Retail</option><option>Services</option><option>Health & Wellness</option><option>Automotive</option></select><textarea name="description" rows="4" placeholder="Describe your business"></textarea><input type="text" name="phone" placeholder="Phone"><input type="email" name="email" placeholder="Email"><input type="url" name="website" placeholder="Website"><button type="submit">Submit →</button></form><a href="/business-directory">← Back</a></div></body>
    </html>
    '''

@app.route('/do-submit-business', methods=['POST'])
def do_submit_business():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO businesses (name, category, description, phone, email, website, date, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (request.form.get('name'), request.form.get('category'), request.form.get('description'),
         request.form.get('phone'), request.form.get('email'), request.form.get('website'),
         datetime.now().date(), 0))
    conn.commit()
    conn.close()
    return '<html><body style="text-align:center;padding:50px"><h1>✅ Business Submitted!</h1><p>Pending approval.</p><a href="/business-directory">← Back</a></body></html>'

@app.route('/search')
def search():
    q = request.args.get('q', '')
    return f'<html><body style="text-align:center;padding:50px"><h1>🔍 Search Results for: "{q}"</h1><p>Search coming soon.</p><a href="/">← Back</a></body></html>'

@app.route('/manifest.json')
def manifest():
    return {"name": NEWSPAPER_NAME, "short_name": "SG Gazette", "start_url": "/", "display": "standalone", "theme_color": "#1a3d1a", "background_color": "#f9f9f5"}

@app.route('/sw.js')
def sw():
    return 'self.addEventListener("fetch", () => {});'

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)