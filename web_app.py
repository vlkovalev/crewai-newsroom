import os
from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"

# ============================================
# Weather Data - Enhanced Version
# ============================================

def get_weather():
    """Get weather data - enhanced version"""
    # In production, replace with actual API call to OpenWeatherMap
    # For now, return enhanced mock data
    return {
        "current": {
            "temp": 18,
            "feels_like": 17,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind": 15,
            "uv": 5,
            "visibility": 16,
            "icon": "🌤️"
        },
        "forecast": [
            {"day": "Mon", "high": 20, "low": 8, "condition": "Sunny", "icon": "☀️"},
            {"day": "Tue", "high": 22, "low": 10, "condition": "Partly Cloudy", "icon": "⛅"},
            {"day": "Wed", "high": 19, "low": 9, "condition": "Light Rain", "icon": "🌧️"},
            {"day": "Thu", "high": 21, "low": 11, "condition": "Sunny", "icon": "☀️"},
            {"day": "Fri", "high": 23, "low": 12, "condition": "Sunny", "icon": "☀️"}
        ]
    }

def get_events():
    return [
        {"name": "Farmers Market", "date": "Every Saturday", "location": "Downtown", "time": "10 AM - 3 PM"},
        {"name": "City Council Meeting", "date": "Monday", "location": "City Hall", "time": "7 PM"},
        {"name": "Library Story Time", "date": "Wednesday", "location": "Public Library", "time": "10:30 AM"},
        {"name": "Community Clean-Up", "date": "May 10", "location": "Various Locations", "time": "9 AM - 2 PM"}
    ]

def get_gallery():
    return [
        {"title": "Spring Festival", "caption": "Residents enjoying the annual Spring Festival"},
        {"title": "New Business Opening", "caption": "Main Street's newest local shop"},
        {"title": "Youth Sports", "caption": "Local soccer team in action"},
        {"title": "Community Volunteers", "caption": "Volunteers beautifying the park"}
    ]

# In-memory classifieds storage
classifieds = [
    {"id": 1, "category": "jobs", "title": "Store Associate Wanted", "description": "Looking for friendly store associate. Full-time position available.", "price": "$16-20/hour", "contact": "jobs@localbusiness.com", "date": "Apr 24, 2026"},
    {"id": 2, "category": "sale", "title": "Dining Table for Sale", "description": "Solid wood dining table, excellent condition.", "price": "$250", "contact": "seller@email.com", "date": "Apr 23, 2026"},
    {"id": 3, "category": "housing", "title": "2 BR Apartment for Rent", "description": "Downtown location, utilities included.", "price": "$1200/month", "contact": "rent@email.com", "date": "Apr 22, 2026"},
    {"id": 4, "category": "services", "title": "Lawn Care Services", "description": "Professional lawn maintenance, weekly or bi-weekly.", "price": "$40/visit", "contact": "lawn@service.com", "date": "Apr 21, 2026"},
    {"id": 5, "category": "garage", "title": "Multi-family Garage Sale", "description": "Furniture, clothes, toys, books. Saturday 8am-2pm.", "price": "Various prices", "contact": "555-0123", "date": "Apr 20, 2026"}
]

# Subscribers storage
subscribers = []

@app.route('/')
def home():
    weather = get_weather()
    events = get_events()
    gallery = get_gallery()
    
    gallery_html = ''.join([f'<div class="gallery-item"><div class="gallery-placeholder">{p["title"]}</div><p><strong>{p["title"]}</strong><br>{p["caption"]}</p></div>' for p in gallery])
    events_html = ''.join([f'<li><strong>{e["name"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    
    # Build forecast HTML
    forecast_html = ''.join([f'''
        <div class="forecast-day">
            <div class="forecast-day-name">{f["day"]}</div>
            <div class="forecast-icon">{f["icon"]}</div>
            <div class="forecast-temp">{f["high"]}° / {f["low"]}°</div>
        </div>
    ''' for f in weather['forecast']])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            
            /* Header */
            .top-bar {{ background: var(--primary); color: white; font-size: 12px; padding: 8px 0; text-align: center; }}
            .header {{ background: white; padding: 30px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
            .logo h1 {{ font-size: 48px; color: var(--primary); }}
            .logo p {{ font-size: 14px; color: #666; letter-spacing: 2px; }}
            .date-header {{ background: #f0f0e8; padding: 10px; text-align: center; font-size: 14px; }}
            
            /* Navigation */
            .nav {{ background: var(--primary); padding: 15px; text-align: center; position: sticky; top: 0; z-index: 100; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; text-transform: uppercase; font-size: 13px; }}
            .nav a:hover {{ color: var(--accent); }}
            
            /* Hero */
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 60px 20px; text-align: center; }}
            .hero h2 {{ font-size: 42px; }}
            .hero p {{ font-size: 18px; margin-top: 10px; }}
            .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
            .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
            .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            
            /* Main Content */
            .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 30px; text-align: center; border-radius: 10px; transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-number {{ font-size: 36px; font-weight: bold; color: var(--primary); }}
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 40px; margin-bottom: 40px; }}
            .section-title {{ font-size: 24px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; }}
            .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; background: var(--primary); color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-top: 15px; transition: background 0.3s; }}
            .btn:hover {{ background: #0d260d; }}
            
            /* Weather Widget - Enhanced */
            .weather-widget {{ background: linear-gradient(135deg, #1e3c72, #2a5298); border-radius: 15px; padding: 20px; color: white; margin-bottom: 30px; }}
            .weather-header {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            .weather-main {{ text-align: center; }}
            .weather-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .weather-temp {{ font-size: 48px; font-weight: bold; }}
            .weather-temp small {{ font-size: 18px; }}
            .weather-details {{ display: flex; justify-content: space-around; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .weather-detail {{ text-align: center; }}
            .forecast {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast-day {{ text-align: center; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 8px; }}
            .forecast-day-name {{ font-weight: bold; margin-bottom: 5px; }}
            .forecast-icon {{ font-size: 24px; }}
            .forecast-temp {{ font-size: 12px; }}
            
            /* Gallery */
            .gallery {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
            .gallery-item {{ background: white; border-radius: 10px; padding: 15px; text-align: center; }}
            .gallery-placeholder {{ background: var(--primary-light); color: white; padding: 40px; border-radius: 8px; margin-bottom: 10px; }}
            
            /* Newsletter */
            .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 40px; border-radius: 15px; text-align: center; margin: 40px 0; }}
            .newsletter input {{ padding: 12px; width: 250px; border: none; border-radius: 5px; margin: 10px; }}
            .newsletter button {{ background: var(--accent); color: var(--primary); padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }}
            
            /* Social */
            .social-section {{ background: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 40px; }}
            .social-links {{ display: flex; justify-content: center; gap: 15px; margin-top: 20px; flex-wrap: wrap; }}
            .social-btn {{ padding: 10px 20px; border-radius: 25px; text-decoration: none; color: white; }}
            .social-btn.twitter {{ background: #1DA1F2; }}
            .social-btn.facebook {{ background: #3b5998; }}
            .social-btn.email {{ background: #666; }}
            
            /* Footer */
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px; margin-top: 40px; }}
            .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
            .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 14px; }}
            .footer-column a:hover {{ color: var(--accent); }}
            .copyright {{ text-align: center; padding-top: 30px; margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; }}
            
            /* Classifieds Page */
            .classifieds-container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .category-filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; }}
            .filter-btn {{ background: white; padding: 10px 20px; border: 1px solid #ddd; border-radius: 25px; cursor: pointer; text-decoration: none; color: #333; }}
            .filter-btn.active {{ background: var(--primary); color: white; border-color: var(--primary); }}
            .classified-card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .classified-category {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 3px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; }}
            .classified-price {{ color: var(--accent); font-size: 20px; font-weight: bold; margin: 10px 0; }}
            .post-ad-btn {{ background: var(--accent); color: var(--primary); padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }}
            
            @media (max-width: 768px) {{
                .stats {{ grid-template-columns: repeat(2, 1fr); }}
                .two-column {{ grid-template-columns: 1fr; }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 28px; }}
                .gallery {{ grid-template-columns: 1fr; }}
                .forecast {{ grid-template-columns: repeat(auto-fit, minmax(60px, 1fr)); }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">🌿 Spruce Grove's Primary Resource for Trade & Employment | "Your Hometown, Online."</div>
        
        <div class="header">
            <div class="logo">
                <h1>📰 {NEWSPAPER_NAME}</h1>
                <p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p>
                <div style="font-size: 12px; color: #D4A017; margin-top: 5px;">"Your Hometown, Online." • Spruce Grove's Primary Resource for Trade & Employment</div>
            </div>
        </div>
        
        <div class="date-header">📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
        
        <div class="nav">
            <a href="/">🏠 HOME</a>
            <a href="/latest">📰 LATEST DISPATCH</a>
            <a href="/classifieds">📋 CLASSIFIEDS</a>
            <a href="/post-ad">📝 POST AN AD</a>
            <a href="/subscribe">✉️ NEWSLETTER</a>
        </div>
        
        <div class="hero">
            <h2>Your Hometown, Online.</h2>
            <p>Spruce Grove's Primary Resource for Trade & Employment</p>
            <form class="search-bar" action="/search" method="GET">
                <input type="text" name="q" placeholder="Search Gazette dispatches, events, and archives...">
                <button type="submit"><i class="fas fa-search"></i> Search</button>
            </form>
        </div>
        
        <div class="main-content">
            <div class="stats">
                <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">1</div><div>Dispatch</div></div>
                <div class="stat-card"><i class="fas fa-tags"></i><div class="stat-number">5</div><div>Categories</div></div>
                <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">0</div><div>Subscribers</div></div>
                <div class="stat-card"><i class="fas fa-clock"></i><div class="stat-number">5 AM</div><div>Daily Delivery</div></div>
            </div>
            
            <div class="two-column">
                <div>
                    <h2 class="section-title">📰 Latest Gazette Dispatch</h2>
                    <div class="feature-card">
                        <h3>Welcome to the Spruce Grove Gazette</h3>
                        <p>Serving Spruce Grove with trusted local news coverage. From city council to high school sports, community events to business openings — we have got Spruce Grove covered.</p>
                        <a href="/latest" class="btn">Read Latest Dispatch →</a>
                    </div>
                    
                    <h2 class="section-title">📸 Community Photos</h2>
                    <div class="gallery">{gallery_html}</div>
                </div>
                
                <div>
                    <div class="weather-widget">
                        <div class="weather-header">
                            <span><i class="fas fa-map-marker-alt"></i> Spruce Grove, AB</span>
                            <span>{datetime.now().strftime('%A')}</span>
                        </div>
                        <div class="weather-main">
                            <div class="weather-icon">{weather['current']['icon']}</div>
                            <div class="weather-temp">{weather['current']['temp']}<small>°C</small></div>
                            <div>{weather['current']['condition']}</div>
                            <div style="font-size: 14px; opacity: 0.8;">Feels like {weather['current']['feels_like']}°C</div>
                        </div>
                        <div class="weather-details">
                            <div class="weather-detail"><i class="fas fa-tint"></i><br>{weather['current']['humidity']}%<br><small>Humidity</small></div>
                            <div class="weather-detail"><i class="fas fa-wind"></i><br>{weather['current']['wind']}<br><small>km/h</small></div>
                            <div class="weather-detail"><i class="fas fa-sun"></i><br>{weather['current']['uv']}<br><small>UV Index</small></div>
                            <div class="weather-detail"><i class="fas fa-eye"></i><br>{weather['current']['visibility']}<br><small>km</small></div>
                        </div>
                        <div class="forecast">
                            {forecast_html}
                        </div>
                    </div>
                    
                    <h2 class="section-title">📅 Upcoming Events</h2>
                    <div class="feature-card">
                        <ul style="list-style: none;">{events_html}</ul>
                    </div>
                    
                    <h2 class="section-title">📱 Install Our App</h2>
                    <div class="feature-card" style="text-align: center;">
                        <i class="fas fa-mobile-alt" style="font-size: 48px; color: var(--primary);"></i>
                        <p>Add the Gazette to your home screen for quick access.</p>
                        <button class="btn" onclick="alert('To install: Tap Share then Add to Home Screen')">📲 Install App</button>
                    </div>
                </div>
            </div>
            
            <div class="newsletter">
                <h3>✉️ Never Miss an Edition</h3>
                <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
                <form action="/do-subscribe" method="POST">
                    <input type="email" name="email" placeholder="Enter your email address" required>
                    <button type="submit">Subscribe Free →</button>
                </form>
            </div>
            
            <div class="social-section">
                <h3>📱 Follow The Gazette</h3>
                <div class="social-links">
                    <a href="https://twitter.com/intent/tweet?text=Spruce Grove Gazette&url=https://sprucegrovegazette.com" target="_blank" class="social-btn twitter"><i class="fab fa-twitter"></i> Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" target="_blank" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Facebook</a>
                    <a href="mailto:?subject=Spruce Grove Gazette&body=Check out this local news source: https://sprucegrovegazette.com" class="social-btn email"><i class="fas fa-envelope"></i> Email</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <div class="footer-column">
                    <h4>📰 The Gazette</h4>
                    <a href="/">Home</a>
                    <a href="/latest">Latest Dispatch</a>
                    <a href="/classifieds">Classifieds</a>
                    <a href="/subscribe">Newsletter</a>
                </div>
                <div class="footer-column">
                    <h4>📬 Connect</h4>
                    <a href="/post-ad">Post an Ad</a>
                    <a href="/submit-letter">Submit a Letter</a>
                    <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                </div>
                <div class="footer-column">
                    <h4>🔗 Categories</h4>
                    <a href="/classifieds?category=jobs">Jobs</a>
                    <a href="/classifieds?category=sale">For Sale</a>
                    <a href="/classifieds?category=housing">Housing</a>
                    <a href="/classifieds?category=services">Services</a>
                </div>
                <div class="footer-column">
                    <h4>📍 Location</h4>
                    <a href="#">Spruce Grove, Alberta</a>
                    <a href="#">"Your Hometown, Online."</a>
                </div>
            </div>
            <div class="copyright">
                <p>© {datetime.now().year} {NEWSPAPER_NAME}. All rights reserved.</p>
                <p>Proudly serving Spruce Grove since {LAUNCH_DATE}</p>
            </div>
        </div>
    </body>
    </html>
    '''

# ============================================
# Classifieds Routes
# ============================================

@app.route('/classifieds')
def classifieds_page():
    category = request.args.get('category', 'all')
    
    filtered = classifieds
    if category != 'all':
        filtered = [c for c in classifieds if c['category'] == category]
    
    categories = [
        {"id": "all", "name": "All Categories", "icon": "📋"},
        {"id": "jobs", "name": "Jobs", "icon": "💼"},
        {"id": "sale", "name": "For Sale", "icon": "🏷️"},
        {"id": "housing", "name": "Housing", "icon": "🏠"},
        {"id": "services", "name": "Services", "icon": "🔧"},
        {"id": "garage", "name": "Garage Sales", "icon": "🏪"}
    ]
    
    categories_html = ''.join([f'<a href="/classifieds?category={c["id"]}" class="filter-btn {"active" if category == c["id"] else ""}">{c["icon"]} {c["name"]}</a>' for c in categories])
    
    classifieds_html = ''.join([f'''
        <div class="classified-card">
            <span class="classified-category">{c["category"].upper()}</span>
            <h3>{c["title"]}</h3>
            <p>{c["description"]}</p>
            <div class="classified-price">{c["price"]}</div>
            <small>Contact: {c["contact"]} | Posted: {c["date"]}</small>
        </div>
    ''' for c in filtered])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Classifieds - {NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: Georgia, serif; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .category-filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; }}
            .filter-btn {{ background: white; padding: 10px 20px; border: 1px solid #ddd; border-radius: 25px; text-decoration: none; color: #333; }}
            .filter-btn.active {{ background: #1a3d1a; color: white; border-color: #1a3d1a; }}
            .classified-card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .classified-category {{ display: inline-block; background: #D4A017; color: #1a3d1a; padding: 3px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; }}
            .classified-price {{ color: #D4A017; font-size: 20px; font-weight: bold; margin: 10px 0; }}
            .post-ad-btn {{ background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            .btn-back {{ display: inline-block; background: #666; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
            @media (max-width: 768px) {{
                .container {{ padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <p>Classifieds • Trade • Employment</p>
        </div>
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/classifieds">📋 Classifieds</a>
            <a href="/post-ad">📝 Post an Ad</a>
            <a href="/">← Back</a>
        </div>
        <div class="container">
            <h2>📋 Classifieds</h2>
            <div class="category-filters">{categories_html}</div>
            {classifieds_html if filtered else '<p>No classifieds found in this category.</p>'}
            <div style="text-align: center; margin-top: 30px;">
                <a href="/post-ad" class="post-ad-btn">📝 Post an Ad →</a>
            </div>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} {NEWSPAPER_NAME} | "Your Hometown, Online."</p>
        </div>
    </body>
    </html>
    '''

@app.route('/post-ad', methods=['GET', 'POST'])
def post_ad():
    if request.method == 'POST':
        new_ad = {
            "id": len(classifieds) + 1,
            "category": request.form.get('category'),
            "title": request.form.get('title'),
            "description": request.form.get('description'),
            "price": request.form.get('price'),
            "contact": request.form.get('contact'),
            "date": datetime.now().strftime('%b %d, %Y')
        }
        classifieds.insert(0, new_ad)
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Ad Posted</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1 style="color: #1a3d1a;">✅ Ad Posted Successfully!</h1>
            <p>Your classified ad has been submitted.</p>
            <a href="/classifieds" style="color: #1a3d1a;">← View Classifieds</a>
        </body>
        </html>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Post an Ad - {NEWSPAPER_NAME}</title>
        <style>
            body {{ font-family: Georgia, serif; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .form-card {{ background: white; padding: 30px; border-radius: 10px; }}
            input, select, textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; font-family: inherit; }}
            button {{ background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <p>Post a Classified Ad</p>
        </div>
        <div class="container">
            <div class="form-card">
                <h2>📝 Post an Ad</h2>
                <form method="POST">
                    <select name="category" required>
                        <option value="">Select Category</option>
                        <option value="jobs">💼 Jobs / Employment</option>
                        <option value="sale">🏷️ For Sale</option>
                        <option value="housing">🏠 Housing / Rentals</option>
                        <option value="services">🔧 Services</option>
                        <option value="garage">🏪 Garage Sale</option>
                    </select>
                    <input type="text" name="title" placeholder="Ad Title" required>
                    <textarea name="description" rows="5" placeholder="Describe what you are offering..." required></textarea>
                    <input type="text" name="price" placeholder="Price (or leave blank)">
                    <input type="text" name="contact" placeholder="Contact info (phone, email)" required>
                    <button type="submit">📢 Post Ad →</button>
                </form>
                <a href="/classifieds">← Back to Classifieds</a>
            </div>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} {NEWSPAPER_NAME} | "Your Hometown, Online."</p>
        </div>
    </body>
    </html>
    '''

# ============================================
# Other Routes
# ============================================

@app.route('/latest')
def latest():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Latest Dispatch - Spruce Grove Gazette</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; background: #f9f9f5; }
            h1 { color: #1a3d1a; border-bottom: 3px solid #D4A017; padding-bottom: 10px; }
            h2 { color: #2C5F2D; }
            h3 { color: #4A7C4B; }
            .meta { color: #666; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }
            .footer { margin-top: 40px; text-align: center; }
            .btn { background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>📰 The Spruce Grove Gazette</h1>
        <div class="meta">📍 Spruce Grove, AB | {datetime.now().strftime('%B %d, %Y')}</div>
        
        <h2>Welcome to the Spruce Grove Gazette!</h2>
        <p>Spruce Grove, AB — The Spruce Grove Gazette is officially launching today, bringing local news to our community.</p>
        
        <h3>What We Cover</h3>
        <p>Our newsroom delivers daily articles on:</p>
        <ul>
            <li>Local sports and recreation highlights</li>
            <li>School board decisions and student achievements</li>
            <li>New business openings and local entrepreneurs</li>
            <li>Community events and volunteer spotlights</li>
            <li>City council updates and development projects</li>
        </ul>
        
        <p>— The Spruce Grove Gazette</p>
        
        <div class="footer">
            <a href="/" class="btn">← Back to Home</a>
        </div>
    </body>
    </html>
    '''

@app.route('/subscribe')
def subscribe():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subscribe - Spruce Grove Gazette</title>
        <style>
            body { font-family: Georgia, serif; background: #f9f9f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .container { background: white; padding: 40px; border-radius: 10px; max-width: 400px; text-align: center; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to The Gazette</h1>
            <p>Get local news delivered to your inbox every morning.</p>
            <form action="/do-subscribe" method="POST">
                <input type="email" name="email" placeholder="Your email address" required>
                <button type="submit">Subscribe →</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    email = request.form.get('email')
    if email:
        subscribers.append({"email": email, "date": datetime.now().strftime('%Y-%m-%d')})
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribed</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Subscribed!</h1>
        <p>Thank you for subscribing to the Spruce Grove Gazette.</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/search')
def search():
    query = request.args.get('q', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Search Results</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1>🔍 Search Results for: "{query}"</h1>
        <p>Search functionality coming soon. Check back later!</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/submit-letter')
def submit_letter():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Submit a Letter</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1>✉️ Submit a Letter to the Editor</h1>
        <p>Coming soon! Check back later.</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)