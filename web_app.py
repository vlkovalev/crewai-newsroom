"""
Spruce Grove Gazette - Progressive Web App (PWA)
Complete newspaper website with installable mobile app functionality
"""

import os
import sqlite3
import glob
import json
import requests
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

# ============================================
# Configuration
# ============================================

GA_MEASUREMENT_ID = os.environ.get('GA_MEASUREMENT_ID', 'G-XXXXXXXXXX')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')

# ============================================
# Database Setup
# ============================================

def init_database():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            file_path TEXT,
            published_date DATE,
            views INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            subscribed_date DATE,
            active BOOLEAN DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT,
            subject TEXT,
            content TEXT,
            date DATE,
            approved BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_database()

def get_latest_article():
    html_files = glob.glob('spruce_grove_gazette_*.html')
    if html_files:
        return max(html_files, key=os.path.getctime)
    return None

def get_article_count():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_subscriber_count():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE active = 1")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_weather():
    if WEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            return {"temp": round(data['main']['temp']), "condition": data['weather'][0]['description'].title(), "humidity": data['main']['humidity']}
        except:
            pass
    return {"temp": 18, "condition": "Partly Cloudy", "humidity": 65}

def get_events():
    return [
        {"name": "Farmers Market", "date": "Every Saturday", "location": "Downtown", "time": "10 AM - 3 PM"},
        {"name": "City Council Meeting", "date": "Monday", "location": "City Hall", "time": "7 PM"},
        {"name": "Library Story Time", "date": "Wednesday", "location": "Public Library", "time": "10:30 AM"},
        {"name": "Community Clean-Up", "date": "May 10", "location": "Various Locations", "time": "9 AM - 2 PM"}
    ]

def get_photo_gallery():
    return [
        {"title": "Spring Festival", "caption": "Residents enjoying the annual Spring Festival", "image": "https://picsum.photos/id/104/800/500"},
        {"title": "New Business Opening", "caption": "Main Street's newest local shop", "image": "https://picsum.photos/id/20/800/500"},
        {"title": "Youth Sports", "caption": "Local soccer team in action", "image": "https://picsum.photos/id/128/800/500"},
        {"title": "Community Volunteers", "caption": "Volunteers beautifying the park", "image": "https://picsum.photos/id/169/800/500"}
    ]

def get_letters():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT author, subject, content, date FROM letters WHERE approved = 1 ORDER BY date DESC LIMIT 3")
    letters = cursor.fetchall()
    conn.close()
    if letters:
        return [{"author": l[0], "subject": l[1], "content": l[2], "date": l[3]} for l in letters]
    return [{"author": "Margaret Thompson", "subject": "Thank You Volunteers", "content": "Thank you to all who made the Spring Festival a success!", "date": datetime.now().strftime("%B %d, %Y")}]

# ============================================
# PWA Routes - Service Worker & Manifest
# ============================================

@app.route('/manifest.json')
def manifest():
    """Web App Manifest for PWA installation"""
    manifest_data = {
        "name": "Spruce Grove Gazette",
        "short_name": "SG Gazette",
        "description": "Spruce Grove's trusted local news source",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#1a3d1a",
        "background_color": "#f9f9f5",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icons/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icons/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return app.response_class(json.dumps(manifest_data), mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    """Service Worker for offline functionality"""
    sw_js = '''
const CACHE_NAME = 'gazette-v1';
const urlsToCache = [
    '/',
    '/latest',
    '/offline'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request).then(
                    response => {
                        if(!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        return response;
                    }
                ).catch(() => {
                    if (event.request.mode === 'navigate') {
                        return caches.match('/offline');
                    }
                });
            })
    );
});

self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
    '''
    return app.response_class(sw_js, mimetype='application/javascript')

@app.route('/offline')
def offline():
    """Offline fallback page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Offline - Spruce Grove Gazette</title>
    <style>
        body { font-family: Georgia, serif; text-align: center; padding: 50px; background: #f9f9f5; }
        h1 { color: #1a3d1a; }
        .btn { display: inline-block; background: #1a3d1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }
    </style>
    </head>
    <body>
        <h1>📰 You're Offline</h1>
        <p>Please check your internet connection.</p>
        <a href="/" class="btn">Try Again</a>
    </body>
    </html>
    '''

@app.route('/static/icons/<path:filename>')
def serve_icon(filename):
    """Serve PWA icons - using emoji fallback"""
    # For now, return a simple SVG icon
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" fill="#1a3d1a"/>
        <text x="50" y="50" text-anchor="middle" dy=".3em" fill="white" font-size="40">📰</text>
    </svg>'''
    return app.response_class(svg, mimetype='image/svg+xml')

# ============================================
# Main Route - PWA Enabled Homepage
# ============================================

@app.route('/')
def home():
    total_articles = get_article_count()
    subscriber_count = get_subscriber_count()
    weather = get_weather()
    events = get_events()
    gallery = get_photo_gallery()
    letters = get_letters()
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Spruce Grove Gazette - Spruce Grove's Trusted News Source</title>
    <meta name="description" content="Spruce Grove's premier local news source. Breaking news, community events, sports, business, and weather for Spruce Grove, Alberta.">
    <meta name="keywords" content="Spruce Grove, local news, Alberta news, community news">
    <meta name="author" content="Spruce Grove Gazette">
    
    <!-- PWA Meta Tags -->
    <link rel="manifest" href="/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="SG Gazette">
    <meta name="theme-color" content="#1a3d1a">
    <link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Spruce Grove Gazette">
    <meta property="og:description" content="Your trusted source for Spruce Grove local news">
    <meta property="og:url" content="https://sprucegrovegazette.com">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_MEASUREMENT_ID}');
    </script>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {{
            --primary: #1a3d1a;
            --primary-light: #2C5F2D;
            --accent: #D4A017;
            --text-dark: #1a1a1a;
            --text-light: #666;
            --bg-light: #f9f9f5;
            --white: #ffffff;
            --shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background: var(--bg-light);
            color: var(--text-dark);
            line-height: 1.6;
        }}
        
        /* PWA Install Prompt */
        .install-prompt {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--primary);
            color: white;
            padding: 15px 25px;
            border-radius: 50px;
            display: none;
            align-items: center;
            gap: 15px;
            z-index: 1001;
            box-shadow: var(--shadow);
            cursor: pointer;
        }}
        
        .install-prompt.show {{ display: flex; }}
        .install-prompt button {{
            background: var(--accent);
            color: var(--primary);
            border: none;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        .top-bar {{
            background: var(--primary);
            color: white;
            font-size: 12px;
            padding: 8px 0;
            text-align: center;
        }}
        
        .header {{
            background: var(--white);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 3px solid var(--accent);
        }}
        
        .logo h1 {{
            font-size: 64px;
            color: var(--primary);
            font-family: 'Times New Roman', serif;
        }}
        
        .logo p {{
            font-size: 16px;
            color: var(--text-light);
            letter-spacing: 3px;
        }}
        
        .date-header {{
            background: #f0f0e8;
            padding: 10px;
            text-align: center;
            font-size: 14px;
        }}
        
        .nav {{
            background: var(--primary);
            padding: 15px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 1000;
            overflow-x: auto;
            white-space: nowrap;
        }}
        
        .nav a {{
            color: white;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 14px;
            display: inline-block;
        }}
        
        .nav a:hover {{ color: var(--accent); }}
        
        .hero {{
            background: linear-gradient(135deg, #1a3d1a, #2C5F2D);
            color: white;
            padding: 50px 20px;
            text-align: center;
        }}
        
        .hero h2 {{ font-size: 42px; margin-bottom: 15px; }}
        
        .main-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .stat-card {{
            background: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px;
            box-shadow: var(--shadow);
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card i {{ font-size: 48px; color: var(--primary-light); }}
        .stat-number {{ font-size: 42px; font-weight: bold; color: var(--primary); }}
        
        .two-column {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 40px;
            margin-bottom: 50px;
        }}
        
        .section-title {{
            font-size: 28px;
            color: var(--primary);
            border-left: 4px solid var(--accent);
            padding-left: 15px;
            margin-bottom: 25px;
        }}
        
        .feature-card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: var(--shadow);
        }}
        
        .btn {{
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin-top: 15px;
        }}
        
        .weather-card {{
            background: linear-gradient(135deg, #2C5F2D, #1a3d1a);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .weather-temp {{ font-size: 48px; font-weight: bold; }}
        
        .events-list li, .letters-list li {{
            padding: 15px;
            border-bottom: 1px solid #eee;
            list-style: none;
        }}
        
        .photo-gallery {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        
        .gallery-item img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 10px;
        }}
        
        .newsletter-section {{
            background: linear-gradient(135deg, var(--primary), #0d260d);
            color: white;
            padding: 50px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 50px;
        }}
        
        .newsletter-form {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 25px;
            flex-wrap: wrap;
        }}
        
        .newsletter-form input {{
            padding: 15px;
            width: 300px;
            border: none;
            border-radius: 5px;
        }}
        
        .newsletter-form button {{
            background: var(--accent);
            color: var(--primary);
            padding: 15px 30px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        .social-section {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 50px;
        }}
        
        .social-links {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 25px;
            flex-wrap: wrap;
        }}
        
        .social-btn {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 12px 25px;
            border-radius: 50px;
            text-decoration: none;
            color: white;
            font-weight: bold;
        }}
        
        .social-btn.twitter {{ background: #1DA1F2; }}
        .social-btn.facebook {{ background: #3b5998; }}
        .social-btn.linkedin {{ background: #0077b5; }}
        .social-btn.email {{ background: #666; }}
        
        .footer {{
            background: #0d260d;
            color: white;
            padding: 50px 20px 30px;
        }}
        
        .footer-content {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 40px;
        }}
        
        .footer-column a {{
            color: #ccc;
            text-decoration: none;
            display: block;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .footer-column a:hover {{ color: var(--accent); }}
        
        .copyright {{
            text-align: center;
            padding-top: 40px;
            margin-top: 40px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 12px;
        }}
        
        /* Mobile Optimizations */
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); gap: 15px; }}
            .two-column {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
            .photo-gallery {{ grid-template-columns: 1fr; }}
            .logo h1 {{ font-size: 36px; }}
            .hero h2 {{ font-size: 28px; }}
            .section-title {{ font-size: 24px; }}
            .stat-number {{ font-size: 28px; }}
            .nav a {{ margin: 0 10px; font-size: 11px; }}
            .newsletter-section, .social-section {{ padding: 30px 20px; }}
        }}
        
        @media (max-width: 480px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: 1fr; text-align: center; }}
        }}
    </style>
</head>
<body>
    <div class="top-bar">
        🌿 Spruce Grove's Trusted News Source Since 1950
    </div>
    
    <div class="install-prompt" id="installPrompt">
        <span>📱 Install the Gazette app on your phone</span>
        <button id="installBtn">Install</button>
    </div>
    
    <div class="header">
        <div class="logo">
            <h1>📰 The Spruce Grove Gazette</h1>
            <p>ESTABLISHED 1950 | INDEPENDENT & LOCAL</p>
        </div>
    </div>
    
    <div class="date-header">
        📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}
    </div>
    
    <div class="nav">
        <a href="/">🏠 HOME</a>
        <a href="/latest">📰 LATEST</a>
        <a href="/rss">📡 RSS</a>
        <a href="/subscribe">✉️ NEWSLETTER</a>
    </div>
    
    <div class="hero">
        <h2>Your Hometown, Online.</h2>
        <p>Delivering the news that matters to Spruce Grove residents since 1950.</p>
    </div>
    
    <div class="main-content">
        <div class="stats-grid">
            <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">{total_articles}</div><div>Articles</div></div>
            <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">{subscriber_count}</div><div>Subscribers</div></div>
            <div class="stat-card"><i class="fas fa-calendar-week"></i><div class="stat-number">6</div><div>Weekly Editions</div></div>
            <div class="stat-card"><i class="fas fa-clock"></i><div class="stat-number">8 AM</div><div>Daily Delivery</div></div>
        </div>
        
        <div class="two-column">
            <div>
                <h2 class="section-title">📰 This Week's Edition</h2>
                <div class="feature-card">
                    <h3>Welcome to the Spruce Grove Gazette</h3>
                    <p>Serving Spruce Grove with trusted local news coverage. From city council to high school sports, community events to business openings — we've got Spruce Grove covered.</p>
                    <a href="/latest" class="btn">Read Latest Edition →</a>
                </div>
                
                <h2 class="section-title">📸 Community Photos</h2>
                <div class="photo-gallery">
                    {"".join([f'<div class="gallery-item"><img src="{p["image"]}" alt="{p["title"]}" loading="lazy"><p><strong>{p["title"]}</strong><br>{p["caption"]}</p></div>' for p in gallery])}
                </div>
                
                <h2 class="section-title">✉️ Letters to the Editor</h2>
                <div class="feature-card">
                    {"".join([f'<div style="margin-bottom: 20px;"><strong>{l["subject"]}</strong><br>"{l["content"]}"<br><em>— {l["author"]}</em><br><small>{l["date"]}</small></div>' for l in letters])}
                    <a href="/submit-letter" class="btn" style="background: var(--accent); color: var(--primary);">Submit a Letter →</a>
                </div>
            </div>
            
            <div>
                <div class="weather-card">
                    <i class="fas fa-sun" style="font-size: 36px;"></i>
                    <div class="weather-temp">{weather['temp']}°C</div>
                    <div>{weather['condition']}</div>
                    <div>Humidity: {weather['humidity']}%</div>
                </div>
                
                <h2 class="section-title">📅 Upcoming Events</h2>
                <div class="feature-card">
                    <ul class="events-list" style="list-style: none;">
                        {"".join([f'<li><strong>{e["name"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])}
                    </ul>
                </div>
                
                <h2 class="section-title">📱 Install Our App</h2>
                <div class="feature-card" style="text-align: center;">
                    <i class="fas fa-mobile-alt" style="font-size: 48px; color: var(--primary);"></i>
                    <p>Add the Gazette to your home screen for quick access, offline reading, and push notifications.</p>
                    <button id="mobileInstallBtn" class="btn" style="background: var(--accent); color: var(--primary);">📲 Install App</button>
                </div>
            </div>
        </div>
        
        <div class="newsletter-section">
            <h3>✉️ Never Miss an Edition</h3>
            <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
            <form class="newsletter-form" action="/subscribe" method="GET">
                <input type="email" name="email" placeholder="Enter your email address" required>
                <button type="submit">Subscribe Free →</button>
            </form>
        </div>
        
        <div class="social-section">
            <h3>📱 Follow The Gazette</h3>
            <div class="social-links">
                <a href="https://twitter.com/intent/tweet?text=Spruce Grove Gazette&url=https://sprucegrovegazette.com" class="social-btn twitter"><i class="fab fa-twitter"></i> Twitter</a>
                <a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Facebook</a>
                <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://sprucegrovegazette.com" class="social-btn linkedin"><i class="fab fa-linkedin-in"></i> LinkedIn</a>
                <a href="mailto:?subject=Spruce Grove Gazette&body=Check this out: https://sprucegrovegazette.com" class="social-btn email"><i class="fas fa-envelope"></i> Email</a>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <div class="footer-content">
            <div class="footer-column">
                <h4>📰 The Gazette</h4>
                <a href="/">Home</a>
                <a href="/latest">Latest Edition</a>
                <a href="/subscribe">Newsletter</a>
                <a href="/rss">RSS Feed</a>
            </div>
            <div class="footer-column">
                <h4>📬 Connect</h4>
                <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                <a href="/submit-letter">Submit a Letter</a>
                <a href="#">Advertising</a>
            </div>
            <div class="footer-column">
                <h4>🔗 Resources</h4>
                <a href="#">About Us</a>
                <a href="#">Privacy Policy</a>
                <a href="/sitemap.xml">Sitemap</a>
            </div>
            <div class="footer-column">
                <h4>📍 Location</h4>
                <a href="#">Spruce Grove, Alberta</a>
                <a href="#">Canada T7X 0A1</a>
            </div>
        </div>
        <div class="copyright">
            <p>© {datetime.now().year} The Spruce Grove Gazette. All rights reserved.</p>
            <p>Proudly serving Spruce Grove since 1950</p>
        </div>
    </div>
    
    <script>
        // PWA Installation
        let deferredPrompt;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            document.getElementById('installPrompt').classList.add('show');
        });
        
        document.getElementById('installBtn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') {
                    console.log('App installed');
                }
                deferredPrompt = null;
                document.getElementById('installPrompt').classList.remove('show');
            }
        });
        
        document.getElementById('mobileInstallBtn')?.addEventListener('click', () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
            } else {
                alert('To install: Tap the Share button and select "Add to Home Screen"');
            }
        });
        
        // Register Service Worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('Service Worker registered', reg))
                .catch(err => console.log('Service Worker failed', err));
        }
    </script>
</body>
</html>
'''

# ============================================
# Additional Routes
# ============================================

@app.route('/latest')
def latest_article():
    latest = get_latest_article()
    if latest:
        return send_file(latest)
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Latest Edition - Spruce Grove Gazette</title></head>
    <body style="font-family: Georgia, serif; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">📰 First Edition Coming Soon</h1>
        <p>Our first edition is being prepared. Check back soon!</p>
        <a href="/" style="color: #1a3d1a;">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/rss')
def rss_feed():
    articles = []
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, published_date FROM articles ORDER BY published_date DESC LIMIT 10")
    articles = cursor.fetchall()
    conn.close()
    
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Spruce Grove Gazette</title>
    <link>https://sprucegrovegazette.com</link>
    <description>Local news for Spruce Grove, Alberta</description>
    <language>en-ca</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>
    {"".join([f'<item><title>{a[0]}</title><link>https://sprucegrovegazette.com/latest</link><description>{a[1][:200]}...</description><pubDate>{a[2]}</pubDate></item>' for a in articles])}
</channel>
</rss>'''
    return app.response_class(rss, mimetype='application/rss+xml')

@app.route('/submit-letter', methods=['GET', 'POST'])
def submit_letter():
    if request.method == 'POST':
        author = request.form.get('author')
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        conn = sqlite3.connect('gazette_archive.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO letters (author, subject, content, date, approved) VALUES (?, ?, ?, ?, 0)",
            (author, subject, content, date.today())
        )
        conn.commit()
        conn.close()
        
        return '''
        <html><body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1 style="color: #1a3d1a;">✅ Letter Submitted</h1>
            <p>Thank you for your letter. Our editorial team will review it for publication.</p>
            <a href="/">← Back to Gazette</a>
        </body></html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Submit a Letter - Spruce Grove Gazette</title>
    <style>
        body { font-family: Georgia, serif; background: #f0f0e8; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>✉️ Submit a Letter to the Editor</h1>
            <p>Share your thoughts with the Spruce Grove community.</p>
            <form method="POST">
                <input type="text" name="author" placeholder="Your name" required>
                <input type="text" name="subject" placeholder="Subject" required>
                <textarea name="content" rows="6" placeholder="Write your letter here..." required></textarea>
                <button type="submit">Submit Letter →</button>
            </form>
            <p><a href="/">← Back to Gazette</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name', '')
        
        if email:
            conn = sqlite3.connect('gazette_archive.db')
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO subscribers (email, name, subscribed_date, active) VALUES (?, ?, ?, 1)",
                    (email, name, date.today())
                )
                conn.commit()
            except:
                pass
            conn.close()
            
            return '''
            <html><body style="font-family: Georgia; text-align: center; padding: 50px;">
                <h1 style="color: #1a3d1a;">✅ Subscribed!</h1>
                <p>Thank you for subscribing to the Spruce Grove Gazette.</p>
                <a href="/">← Back to Gazette</a>
            </body></html>
            '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribe - Spruce Grove Gazette</title>
    <style>
        body { font-family: Georgia, serif; background: #f0f0e8; padding: 50px; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to The Gazette</h1>
            <p>Get local news delivered to your inbox every morning.</p>
            <form method="POST">
                <input type="text" name="name" placeholder="Your name">
                <input type="email" name="email" placeholder="Your email" required>
                <button type="submit">Subscribe →</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

@app.route('/api/status')
def api_status():
    return jsonify({
        "name": "Spruce Grove Gazette",
        "schedule": "Daily at 8:00 AM MT",
        "total_articles": get_article_count(),
        "subscribers": get_subscriber_count()
    })

@app.route('/sitemap.xml')
def sitemap():
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://sprucegrovegazette.com/</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><priority>1.0</priority></url>
    <url><loc>https://sprucegrovegazette.com/latest</loc><priority>0.9</priority></url>
    <url><loc>https://sprucegrovegazette.com/subscribe</loc><priority>0.8</priority></url>
</urlset>'''
    return app.response_class(sitemap, mimetype='application/xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)