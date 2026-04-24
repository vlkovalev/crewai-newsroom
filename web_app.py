import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, redirect, session
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
    
    # Subscribers table
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
    
    # Supporters table (paid members)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supporters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            tier TEXT,
            amount INTEGER,
            start_date DATE,
            active BOOLEAN DEFAULT 1
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
    
    # Businesses table
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
    
    # Events table with ticketing
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
    
    # Classifieds table
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

def get_latest_article():
    return {
        "title": "Province Pledges $136 Million for Parkland County Highway Upgrades",
        "summary": "The Government of Alberta's 2026 Budget confirms continued investment in Highway 60 twinning and Highway 16 improvements..."
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
# HOME PAGE
# ============================================

@app.route('/')
def home():
    weather = get_weather()
    events = get_events(5)
    businesses = get_businesses('all', 6)
    
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
            <div class="business-contact"><i class="fas fa-phone"></i> {b["phone"]}</div>
        </div>
    ''' for b in businesses])
    
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
            
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 40px; }}
            .section-title {{ font-size: 22px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; }}
            .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
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
                .two-column {{ grid-template-columns: 1fr; }}
                .business-grid {{ grid-template-columns: 1fr; }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 24px; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">🌿 Serving Spruce Grove, Stony Plain & Parkland County | "Your Hometown, Online."</div>
        
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
            <a href="/foodbank">🥫 FOOD BANK</a>
            <a href="/sponsor">📢 ADVERTISE</a>
            <a href="/events">📅 EVENTS</a>
            <a href="/shop">🛍️ MARKETPLACE</a>
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
                <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">25+</div><div>Articles</div></div>
                <div class="stat-card"><i class="fas fa-store"></i><div class="stat-number">50+</div><div>Businesses</div></div>
                <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">500+</div><div>Subscribers</div></div>
                <div class="stat-card"><i class="fas fa-calendar"></i><div class="stat-number">10+</div><div>Events</div></div>
            </div>
            
            <div class="two-column">
                <div>
                    <h2 class="section-title">📰 Latest News</h2>
                    <div class="feature-card">
                        <h3>Province Pledges $136 Million for Parkland County Highway Upgrades</h3>
                        <div style="color: #999; font-size: 12px;">March 4, 2026 | Source: Parkland County</div>
                        <p>The Government of Alberta's 2026 Budget confirms continued investment in Highway 60 twinning and Highway 16 improvements, essential for regional safety and economic growth.</p>
                        <a href="/article/1" class="btn">Read Full Story →</a>
                    </div>
                    
                    <div class="feature-card">
                        <h3>Parkland Food Bank Secures Land for New $1.2 Million Facility</h3>
                        <div style="color: #999; font-size: 12px;">January 4, 2026 | Source: Parkland Food Bank</div>
                        <p>After 40 years of serving the Tri-Region, the Parkland Food Bank has purchased a 2.86-acre property in Spruce Grove for a new, larger facility.</p>
                        <a href="/foodbank" class="btn">Read Full Story →</a>
                    </div>
                </div>
                
                <div>
                    <div class="weather-widget">
                        <div class="weather-main">
                            <div class="weather-icon">{weather['current']['icon']}</div>
                            <div class="weather-temp">{weather['current']['temp']}<small>°C</small></div>
                            <div>{weather['current']['condition']}</div>
                        </div>
                        <div class="weather-details">
                            <div><i class="fas fa-tint"></i><br>{weather['current']['humidity']}%</div>
                            <div><i class="fas fa-wind"></i><br>{weather['current']['wind']} km/h</div>
                        </div>
                        <div class="forecast">{forecast_html}</div>
                    </div>
                    
                    <h2 class="section-title">📅 Upcoming Events</h2>
                    <div class="feature-card"><ul style="list-style: none;">{events_html}</ul><a href="/events" class="btn">View All Events →</a></div>
                    
                    <h2 class="section-title">🏪 Local Businesses</h2>
                    <div class="business-grid">{businesses_html}</div>
                    <div style="text-align: center;"><a href="/business-directory" class="btn">View All →</a></div>
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
                    <a href="/submit-tip">News Tip</a>
                    <a href="/submit-photo">Share Photo</a>
                    <a href="/sponsor">Advertise</a>
                    <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                </div>
                <div class="footer-column">
                    <h4>🤝 Community</h4>
                    <a href="/foodbank">Parkland Food Bank</a>
                    <a href="/support">Become a Supporter</a>
                    <a href="/events">Community Calendar</a>
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
                <p>Serving Spruce Grove, Stony Plain & Parkland County since {LAUNCH_DATE}</p>
            </div>
        </div>
    </body>
    </html>
    '''

# ============================================
# SUPPORTER ROUTES
# ============================================

@app.route('/support')
def support():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Become a Supporter</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: Georgia; background: #f9f9f5; margin: 0; }
        .header { background: #1a3d1a; color: white; padding: 30px; text-align: center; }
        .container { max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
        .pricing-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; }
        .pricing-card { background: white; border-radius: 15px; padding: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .pricing-card.featured { border: 2px solid #D4A017; position: relative; }
        .popular-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #D4A017; padding: 5px 15px; border-radius: 20px; font-size: 12px; }
        .price { font-size: 48px; font-weight: bold; color: #1a3d1a; margin: 20px 0; }
        .btn { display: inline-block; background: #1a3d1a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
        @media (max-width: 768px) { .pricing-grid { grid-template-columns: 1fr; } }
    </style>
    </head>
    <body>
        <div class="header"><h1>🌟 Support Local Journalism</h1><p>Keep Spruce Grove & Parkland County informed</p></div>
        <div class="container"><div class="pricing-grid">
            <div class="pricing-card"><h3>Free Reader</h3><div class="price">$0</div><ul style="list-style:none"><li>✓ Daily newsletter</li><li>✓ All articles</li><li>✓ Community calendar</li></ul><a href="/subscribe" class="btn">Current Plan</a></div>
            <div class="pricing-card featured"><div class="popular-badge">MOST POPULAR</div><h3>Monthly Supporter</h3><div class="price">$5<span style="font-size:14px">/month</span></div><ul style="list-style:none"><li>✓ All free features</li><li>✓ Supporter badge</li><li>✓ Weekly exclusive content</li><li>✓ Early event access</li></ul><a href="#" class="btn" onclick="alert('Payment coming soon! Thank you for your support.')">Become a Supporter</a></div>
            <div class="pricing-card"><h3>Yearly Supporter</h3><div class="price">$50<span style="font-size:14px">/year</span></div><ul style="list-style:none"><li>✓ All monthly benefits</li><li>✓ Name in supporter roll</li><li>✓ Exclusive merch discount</li></ul><a href="#" class="btn" onclick="alert('Payment coming soon! Thank you for your support.')">Join Yearly</a></div>
        </div><p style="text-align:center;margin-top:40px"><a href="/">← Back to Home</a></p></div>
    </body>
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
    <head><title>Parkland Food Bank - Spruce Grove Gazette</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: Georgia; background: #f9f9f5; margin: 0; }
        .header { background: #1a3d1a; color: white; padding: 30px; text-align: center; }
        .stats-bar { background: #e74c3c; color: white; padding: 15px; display: flex; justify-content: space-around; flex-wrap: wrap; }
        .stat-number { font-size: 28px; font-weight: bold; }
        .container { max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
        .featured-article { background: white; border-radius: 15px; padding: 30px; margin-bottom: 30px; }
        .event-card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; display: flex; gap: 20px; align-items: center; }
        .event-date { background: #D4A017; color: #1a3d1a; padding: 15px; border-radius: 10px; text-align: center; min-width: 80px; }
        .btn-donate { background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
        @media (max-width: 768px) { .event-card { flex-direction: column; text-align: center; } }
    </style>
    </head>
    <body>
        <div class="header"><h1>🥫 Parkland Food Bank</h1><p>Serving Spruce Grove, Stony Plain & Parkland County Since 1984</p></div>
        <div class="stats-bar">
            <div><div class="stat-number">40+</div>Years</div>
            <div><div class="stat-number">5,634</div>Individuals</div>
            <div><div class="stat-number">31,945</div>Visits</div>
            <div><div class="stat-number">9,707</div>Hampers/Month</div>
        </div>
        <div class="container">
            <div class="featured-article"><h2>New $1.2 Million Facility Coming to Spruce Grove</h2><p>Parkland Food Bank has purchased a 2.86-acre property for a new, larger facility. "This is the first step to ensure that as long as there is need, Parkland Food Bank will be here," said Executive Director Sheri Ratsoy.</p></div>
            <h2>📅 Upcoming Events</h2>
            <div class="event-card"><div class="event-date"><div>APR</div><div style="font-size:28px">13-17</div></div><div><h3>Food Fight '26</h3><p>Spruce Grove Composite High School's week-long food drive</p></div></div>
            <div class="event-card"><div class="event-date"><div>AUG</div><div>2026</div></div><div><h3>Corporate Food Drive Challenge</h3><p>Local businesses compete to collect food. Register your team!</p></div></div>
            <div class="featured-article"><h2>🤝 How to Help</h2><p><strong>Donate Food:</strong> 105 Madison Crescent, Spruce Grove<br><strong>Volunteer:</strong> Call Sheri Ratsoy at 780-962-4565<br><strong>Monetary Donations:</strong> Visit parklandfoodbank.org</p><a href="#" class="btn-donate" onclick="alert('Visit parklandfoodbank.org to donate')">Donate Now →</a></div>
        </div>
        <div style="background:#0d260d;color:white;text-align:center;padding:30px"><a href="/" style="color:white">← Back to Home</a></div>
    </body>
    </html>
    '''

# ============================================
# SPONSOR ROUTE
# ============================================

@app.route('/sponsor')
def sponsor():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Advertise With Us</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: Georgia; background: #f9f9f5; margin: 0; }
        .header { background: #1a3d1a; color: white; padding: 30px; text-align: center; }
        .container { max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
        .package-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; }
        .package-card { background: white; border-radius: 15px; padding: 30px; text-align: center; }
        .price { font-size: 36px; font-weight: bold; color: #1a3d1a; }
        .btn { background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
        @media (max-width: 768px) { .package-grid { grid-template-columns: 1fr; } }
    </style>
    </head>
    <body>
        <div class="header"><h1>📰 Advertise With The Gazette</h1><p>Reach thousands of local readers</p></div>
        <div class="container"><div class="package-grid">
            <div class="package-card"><h3>Digital Display Ad</h3><div class="price">$150<span style="font-size:14px">/month</span></div><p>Banner ad on homepage</p><a href="/inquire" class="btn">Inquire</a></div>
            <div class="package-card"><h3>Sponsored Article</h3><div class="price">$250<span style="font-size:14px">/article</span></div><p>Professional feature story + social promotion</p><a href="/inquire" class="btn">Inquire</a></div>
            <div class="package-card"><h3>Community Spotlight</h3><div class="price">$400<span style="font-size:14px">/month</span></div><p>Weekly business feature + newsletter</p><a href="/inquire" class="btn">Inquire</a></div>
        </div><p style="text-align:center;margin-top:40px"><a href="/">← Back to Home</a></p></div>
    </body>
    </html>
    '''

@app.route('/inquire')
def inquire():
    return '<html><body style="text-align:center;padding:50px"><h1>📧 Thank you!</h1><p>An advertising specialist will contact you within 24 hours.</p><a href="/">← Back</a></body></html>'

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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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
# SHOP / AFFILIATE MARKETING ROUTE
# ============================================

affiliate_products = [
    {"id": 1, "name": "Snow Joe 21" 2-Stage Snow Blower", "description": "Perfect for Spruce Grove winters", "price": "$499", "category": "Winter Gear", "merchant": "Amazon"},
    {"id": 2, "name": "Greenworks 40V Cordless Lawn Mower", "description": "Quiet, zero-emission mowing", "price": "$329", "category": "Lawn & Garden", "merchant": "Amazon"},
    {"id": 3, "name": "Ring Video Doorbell 4", "description": "Keep your home safe", "price": "$199", "category": "Home Security", "merchant": "Amazon"},
    {"id": 4, "name": "Yeti Rambler 14 oz Mug", "description": "Keep coffee hot during commutes", "price": "$35", "category": "Everyday Essentials", "merchant": "Amazon"},
    {"id": 5, "name": "Canadian Tire $50 Gift Card", "description": "Shop local", "price": "$50", "category": "Gift Cards", "merchant": "Canadian Tire"},
]

@app.route('/shop')
def shop():
    products_html = ''.join([f'<div style="background:white;border-radius:10px;padding:20px"><h3>{p["name"]}</h3><p>{p["description"]}</p><div style="font-size:24px;color:#D4A017">{p["price"]}</div><div style="color:#666;font-size:12px">{p["merchant"]}</div><a href="#" class="btn" style="display:inline-block;margin-top:10px" onclick="alert(\'Affiliate link would open {p["merchant"]}\')">Shop Now →</a></div>' for p in affiliate_products])
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Gazette Marketplace</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}.disclaimer{{background:#e8f5e9;padding:10px;text-align:center;font-size:12px}}.container{{max-width:1000px;margin:0 auto;padding:40px20px}}.products-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}.btn{{background:#1a3d1a;color:white;padding:10px20px;text-decoration:none;border-radius:5px}}@media(max-width:768px){{.products-grid{{grid-template-columns:1fr}}}}</style>
    </head>
    <body><div class="header"><h1>🛍️ Gazette Marketplace</h1><p>Products recommended for Spruce Grove residents</p></div><div class="disclaimer"><i class="fas fa-info-circle"></i> We earn a commission on purchases, at no extra cost to you.</div><div class="container"><div class="products-grid">{products_html}</div><p style="text-align:center;margin-top:40px"><a href="/" class="btn">← Back to Home</a></p></div></body>
    </html>
    '''

# ============================================
# CLASSIFIEDS ROUTES
# ============================================

@app.route('/classifieds')
def classifieds():
    conn = sqlite3.connect('gazette.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, price, contact, date FROM classifieds WHERE active = 1 ORDER BY date DESC LIMIT 20")
    classifieds_list = cursor.fetchall()
    conn.close()
    
    classifieds_html = ''.join([f'<div style="background:white;padding:20px;margin-bottom:15px;border-radius:10px"><h3>{c[0]}</h3><p>{c[1]}</p><div style="color:#D4A017;font-weight:bold">{c[2]}</div><small>Contact: {c[3]} | Posted: {c[4]}</small></div>' for c in classifieds_list])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Classifieds - Spruce Grove Gazette</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}.container{{max-width:800px;margin:0 auto;padding:40px20px}}.btn{{background:#1a3d1a;color:white;padding:10px20px;text-decoration:none;border-radius:5px}}</style>
    </head>
    <body><div class="header"><h1>📋 Classifieds</h1><p>Buy & Sell in Spruce Grove</p></div><div class="container">{classifieds_html if classifieds_html else '<p>No classifieds yet.</p>'}<div style="text-align:center;margin-top:30px"><a href="/post-ad" class="btn">📝 Post an Ad</a> <a href="/" class="btn">← Back</a></div></div></body>
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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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
    return f'<html><body style="text-align:center;padding:50px"><h1>🔍 Search Results for: "{q}"</h1><p>Search feature coming soon.</p><a href="/">← Back</a></body></html>'

@app.route('/article/<int:article_id>')
def article(article_id):
    return redirect('/')

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