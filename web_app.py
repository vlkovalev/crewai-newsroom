import os
from flask import Flask
from datetime import datetime

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"

# Weather data
def get_weather():
    return {"temp": 18, "condition": "Partly Cloudy"}

# Events data
def get_events():
    return [
        {"name": "Farmers Market", "date": "Every Saturday", "location": "Downtown", "time": "10 AM - 3 PM"},
        {"name": "City Council Meeting", "date": "Monday", "location": "City Hall", "time": "7 PM"},
        {"name": "Library Story Time", "date": "Wednesday", "location": "Public Library", "time": "10:30 AM"},
        {"name": "Community Clean-Up", "date": "May 10", "location": "Various Locations", "time": "9 AM - 2 PM"}
    ]

# Photos
def get_gallery():
    return [
        {"title": "Spring Festival", "caption": "Residents enjoying the annual Spring Festival"},
        {"title": "New Business Opening", "caption": "Main Street's newest local shop"},
        {"title": "Youth Sports", "caption": "Local soccer team in action"},
        {"title": "Community Volunteers", "caption": "Volunteers beautifying the park"}
    ]

@app.route('/')
def home():
    weather = get_weather()
    events = get_events()
    gallery = get_gallery()
    
    gallery_html = ''.join([f'<div class="gallery-item"><div class="gallery-placeholder">{p["title"]}</div><p><strong>{p["title"]}</strong><br>{p["caption"]}</p></div>' for p in gallery])
    events_html = ''.join([f'<li><strong>{e["name"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    
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
            .top-bar {{ background: var(--primary); color: white; font-size: 12px; padding: 8px 0; text-align: center; }}
            .header {{ background: white; padding: 30px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
            .logo h1 {{ font-size: 48px; color: var(--primary); }}
            .logo p {{ font-size: 14px; color: #666; letter-spacing: 2px; }}
            .date-header {{ background: #f0f0e8; padding: 10px; text-align: center; font-size: 14px; }}
            .nav {{ background: var(--primary); padding: 15px; text-align: center; position: sticky; top: 0; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; text-transform: uppercase; font-size: 13px; }}
            .nav a:hover {{ color: var(--accent); }}
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 60px 20px; text-align: center; }}
            .hero h2 {{ font-size: 42px; }}
            .hero p {{ font-size: 18px; margin-top: 10px; }}
            .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
            .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
            .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 30px; text-align: center; border-radius: 10px; }}
            .stat-number {{ font-size: 36px; font-weight: bold; color: var(--primary); }}
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 40px; margin-bottom: 40px; }}
            .section-title {{ font-size: 24px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; }}
            .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; }}
            .btn {{ display: inline-block; background: var(--primary); color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            .weather-widget {{ background: linear-gradient(135deg, #1e3c72, #2a5298); border-radius: 15px; padding: 20px; color: white; margin-bottom: 30px; text-align: center; }}
            .weather-temp {{ font-size: 48px; font-weight: bold; }}
            .gallery {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
            .gallery-item {{ background: white; border-radius: 10px; padding: 15px; text-align: center; }}
            .gallery-placeholder {{ background: var(--primary-light); color: white; padding: 40px; border-radius: 8px; margin-bottom: 10px; }}
            .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 40px; border-radius: 15px; text-align: center; margin: 40px 0; }}
            .newsletter input {{ padding: 12px; width: 250px; border: none; border-radius: 5px; margin: 10px; }}
            .newsletter button {{ background: var(--accent); color: var(--primary); padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }}
            .social-section {{ background: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 40px; }}
            .social-links {{ display: flex; justify-content: center; gap: 15px; margin-top: 20px; flex-wrap: wrap; }}
            .social-btn {{ padding: 10px 20px; border-radius: 25px; text-decoration: none; color: white; }}
            .social-btn.twitter {{ background: #1DA1F2; }}
            .social-btn.facebook {{ background: #3b5998; }}
            .social-btn.email {{ background: #666; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px; margin-top: 40px; }}
            .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
            .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 14px; }}
            .copyright {{ text-align: center; padding-top: 30px; margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; }}
            @media (max-width: 768px) {{
                .stats {{ grid-template-columns: repeat(2, 1fr); }}
                .two-column {{ grid-template-columns: 1fr; }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 28px; }}
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
            <a href="#">📋 CLASSIFIEDS</a>
            <a href="#">🔍 SEARCH</a>
            <a href="#">✉️ NEWSLETTER</a>
        </div>
        
        <div class="hero">
            <h2>Your Hometown, Online.</h2>
            <p>Spruce Grove's Primary Resource for Trade & Employment</p>
            <form class="search-bar" action="/search">
                <input type="text" placeholder="Search Gazette dispatches, events, and archives...">
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
                        <i class="fas fa-sun" style="font-size: 36px;"></i>
                        <div class="weather-temp">{weather['temp']}°C</div>
                        <div>{weather['condition']}</div>
                        <div style="margin-top: 10px;">💧 Humidity: 65% | 💨 Wind: 15 km/h</div>
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
                <form>
                    <input type="email" placeholder="Enter your email address" required>
                    <button type="submit">Subscribe Free →</button>
                </form>
            </div>
            
            <div class="social-section">
                <h3>📱 Follow The Gazette</h3>
                <div class="social-links">
                    <a href="#" class="social-btn twitter"><i class="fab fa-twitter"></i> Twitter</a>
                    <a href="#" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Facebook</a>
                    <a href="#" class="social-btn email"><i class="fas fa-envelope"></i> Email</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <div class="footer-column">
                    <h4>📰 The Gazette</h4>
                    <a href="/">Home</a>
                    <a href="/latest">Latest Dispatch</a>
                    <a href="#">Classifieds</a>
                    <a href="#">Newsletter</a>
                </div>
                <div class="footer-column">
                    <h4>📬 Connect</h4>
                    <a href="#">Post an Ad</a>
                    <a href="#">Submit a Letter</a>
                    <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                </div>
                <div class="footer-column">
                    <h4>🔗 Categories</h4>
                    <a href="#">Jobs</a>
                    <a href="#">For Sale</a>
                    <a href="#">Housing</a>
                    <a href="#">Services</a>
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
        <div class="meta">📍 Spruce Grove, AB | April 24, 2026</div>
        
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)