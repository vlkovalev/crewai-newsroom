"""
Spruce Grove Gazette - Complete Newspaper
"""

import os
import sqlite3
import glob
import json
import requests
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

# Newspaper Information
NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
LAUNCH_YEAR = 2026
TAGLINE = "Spruce Grove's Primary Resource for Trade & Employment"

# Configuration
GA_MEASUREMENT_ID = os.environ.get('GA_MEASUREMENT_ID', 'G-XXXXXXXXXX')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')

# Database Setup
def init_database():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, file_path TEXT, published_date DATE, views INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, subscribed_date DATE, active BOOLEAN DEFAULT 1)')
    cursor.execute('CREATE TABLE IF NOT EXISTS letters (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, subject TEXT, content TEXT, date DATE, approved BOOLEAN DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS classifieds (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, title TEXT, description TEXT, price TEXT, contact TEXT, email TEXT, date DATE, active BOOLEAN DEFAULT 1)')
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

def get_weather_icon(icon_code):
    icon_map = {"01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️", "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️", "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️", "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️", "50d": "🌫️", "50n": "🌫️"}
    return icon_map.get(icon_code, "🌡️")

def get_weather():
    if WEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()
            forecast = []
            days_processed = set()
            for item in forecast_data['list']:
                date_str = item['dt_txt'].split()[0]
                if date_str not in days_processed and len(forecast) < 5:
                    days_processed.add(date_str)
                    forecast.append({
                        "day": datetime.strptime(date_str, '%Y-%m-%d').strftime('%a'),
                        "high": round(item['main']['temp_max']),
                        "low": round(item['main']['temp_min']),
                        "condition": item['weather'][0]['description'].title(),
                        "icon": get_weather_icon(item['weather'][0]['icon'])
                    })
            return {
                "current": {"temp": round(data['main']['temp']), "feels_like": round(data['main']['feels_like']), "condition": data['weather'][0]['description'].title(), "humidity": data['main']['humidity'], "wind": round(data['wind']['speed']), "icon": get_weather_icon(data['weather'][0]['icon'])},
                "forecast": forecast
            }
        except:
            pass
    return {"current": {"temp": 18, "feels_like": 17, "condition": "Partly Cloudy", "humidity": 65, "wind": 15, "icon": "🌤️"}, "forecast": [{"day": "Mon", "high": 20, "low": 8, "condition": "Sunny", "icon": "☀️"}, {"day": "Tue", "high": 22, "low": 10, "condition": "Partly Cloudy", "icon": "⛅"}, {"day": "Wed", "high": 19, "low": 9, "condition": "Light Rain", "icon": "🌧️"}, {"day": "Thu", "high": 21, "low": 11, "condition": "Sunny", "icon": "☀️"}, {"day": "Fri", "high": 23, "low": 12, "condition": "Sunny", "icon": "☀️"}]}

def get_events():
    return [{"name": "Farmers Market", "date": "Every Saturday", "location": "Downtown", "time": "10 AM - 3 PM"}, {"name": "City Council Meeting", "date": "Monday", "location": "City Hall", "time": "7 PM"}, {"name": "Library Story Time", "date": "Wednesday", "location": "Public Library", "time": "10:30 AM"}, {"name": "Community Clean-Up", "date": "May 10", "location": "Various Locations", "time": "9 AM - 2 PM"}]

def get_photo_gallery():
    return [{"title": "Spring Festival", "caption": "Residents enjoying the annual Spring Festival", "image": "https://picsum.photos/id/104/800/500"}, {"title": "New Business Opening", "caption": "Main Street's newest local shop", "image": "https://picsum.photos/id/20/800/500"}, {"title": "Youth Sports", "caption": "Local soccer team in action", "image": "https://picsum.photos/id/128/800/500"}, {"title": "Community Volunteers", "caption": "Volunteers beautifying the park", "image": "https://picsum.photos/id/169/800/500"}]

def get_letters():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT author, subject, content, date FROM letters WHERE approved = 1 ORDER BY date DESC LIMIT 3")
    letters = cursor.fetchall()
    conn.close()
    if letters:
        return [{"author": l[0], "subject": l[1], "content": l[2], "date": l[3]} for l in letters]
    return [{"author": "Margaret Thompson", "subject": "Thank You Volunteers", "content": "Thank you to all who made the Spring Festival a success!", "date": datetime.now().strftime("%B %d, %Y")}]

def get_classifieds_by_category(category=None):
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    if category and category != 'all':
        cursor.execute("SELECT id, category, title, description, price, contact, date FROM classifieds WHERE category = ? AND active = 1 ORDER BY date DESC", (category,))
    else:
        cursor.execute("SELECT id, category, title, description, price, contact, date FROM classifieds WHERE active = 1 ORDER BY date DESC LIMIT 20")
    classifieds = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "category": c[1], "title": c[2], "description": c[3], "price": c[4], "contact": c[5], "date": c[6]} for c in classifieds]

def search_articles(query):
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, published_date, file_path FROM articles WHERE title LIKE ? OR content LIKE ? ORDER BY published_date DESC", (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    conn.close()
    return [{"title": r[0], "content": r[1][:200], "date": r[2], "file_path": r[3]} for r in results]

# PWA Routes
@app.route('/manifest.json')
def manifest():
    manifest_data = {"name": NEWSPAPER_NAME, "short_name": "SG Gazette", "description": "Spruce Grove's trusted local news source", "start_url": "/", "display": "standalone", "theme_color": "#1a3d1a", "background_color": "#f9f9f5", "orientation": "portrait-primary", "icons": [{"src": "/static/icons/icon-72x72.png", "sizes": "72x72", "type": "image/png"}, {"src": "/static/icons/icon-96x96.png", "sizes": "96x96", "type": "image/png"}, {"src": "/static/icons/icon-128x128.png", "sizes": "128x128", "type": "image/png"}, {"src": "/static/icons/icon-144x144.png", "sizes": "144x144", "type": "image/png"}, {"src": "/static/icons/icon-152x152.png", "sizes": "152x152", "type": "image/png"}, {"src": "/static/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/static/icons/icon-384x384.png", "sizes": "384x384", "type": "image/png"}, {"src": "/static/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png"}]}
    return app.response_class(json.dumps(manifest_data), mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    sw_js = 'const CACHE_NAME = "gazette-v1"; const urlsToCache = ["/", "/latest", "/classifieds", "/search", "/offline"]; self.addEventListener("install", event => { event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))); }); self.addEventListener("fetch", event => { event.respondWith(caches.match(event.request).then(response => { return response || fetch(event.request).then(response => { const responseToCache = response.clone(); caches.open(CACHE_NAME).then(cache => { cache.put(event.request, responseToCache); }); return response; }).catch(() => { if (event.request.mode === "navigate") { return caches.match("/offline"); } }); })); }); self.addEventListener("activate", event => { const cacheWhitelist = [CACHE_NAME]; event.waitUntil(caches.keys().then(cacheNames => { return Promise.all(cacheNames.map(cacheName => { if (cacheWhitelist.indexOf(cacheName) === -1) { return caches.delete(cacheName); } })); })); });'
    return app.response_class(sw_js, mimetype='application/javascript')

@app.route('/offline')
def offline():
    return '<!DOCTYPE html><html><head><title>Offline</title></head><body><h1>📰 You are Offline</h1><p>Please check your connection.</p><a href="/">Try Again</a></body></html>'

@app.route('/static/icons/<path:filename>')
def serve_icon(filename):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#1a3d1a"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="white" font-size="40">📰</text></svg>'
    return app.response_class(svg, mimetype='image/svg+xml')

# Main Route
@app.route('/')
def home():
    total_articles = get_article_count()
    subscriber_count = get_subscriber_count()
    weather = get_weather()
    events = get_events()
    gallery = get_photo_gallery()
    letters = get_letters()
    recent_classifieds = get_classifieds_by_category('all')[:4]
    
    forecast_html = ''.join([f'<div class="forecast-day"><div class="forecast-day-name">{f["day"]}</div><div class="forecast-icon">{f["icon"]}</div><div class="forecast-temp">{f["high"]}&deg; / {f["low"]}&deg;</div><div style="font-size: 10px; opacity: 0.8;">{f["condition"][:10]}</div></div>' for f in weather['forecast']])
    gallery_html = ''.join([f'<div class="gallery-item"><img src="{p["image"]}" alt="{p["title"]}" loading="lazy"><p><strong>{p["title"]}</strong><br>{p["caption"]}</p></div>' for p in gallery])
    letters_html = ''.join([f'<div style="margin-bottom: 20px;"><strong>{l["subject"]}</strong><br>"{l["content"]}"<br><em>— {l["author"]}</em><br><small>{l["date"]}</small></div>' for l in letters])
    events_html = ''.join([f'<li style="padding: 10px 0; border-bottom: 1px solid #eee;"><strong>{e["name"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    classifieds_html = ''.join([f'<div class="classified-item"><strong>{c["title"]}</strong> <span class="classified-category">{c["category"]}</span><br>{c["description"][:100]}...<br><span class="classified-price">{c["price"] if c["price"] else "Price not specified"}</span><br><small>Posted: {c["date"]}</small></div>' for c in recent_classifieds])
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>{NEWSPAPER_NAME}</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="SG Gazette">
    <meta name="theme-color" content="#1a3d1a">
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
    <script>window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}} gtag('js', new Date()); gtag('config', '{GA_MEASUREMENT_ID}');</script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; --text-dark: #1a1a1a; --text-light: #666; --bg-light: #f9f9f5; --white: #ffffff; --shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Georgia', 'Times New Roman', serif; background: var(--bg-light); color: var(--text-dark); line-height: 1.6; }}
        .install-prompt {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--primary); color: white; padding: 15px 25px; border-radius: 50px; display: none; align-items: center; gap: 15px; z-index: 1001; cursor: pointer; }}
        .install-prompt.show {{ display: flex; }}
        .install-prompt button {{ background: var(--accent); color: var(--primary); border: none; padding: 8px 20px; border-radius: 25px; font-weight: bold; cursor: pointer; }}
        .top-bar {{ background: var(--primary); color: white; font-size: 12px; padding: 8px 0; text-align: center; }}
        .header {{ background: var(--white); padding: 30px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
        .logo h1 {{ font-size: 64px; color: var(--primary); font-family: 'Times New Roman', serif; }}
        .logo p {{ font-size: 16px; color: var(--text-light); letter-spacing: 3px; }}
        .tagline {{ font-size: 14px; color: var(--accent); margin-top: 5px; font-style: italic; }}
        .date-header {{ background: #f0f0e8; padding: 10px; text-align: center; font-size: 14px; }}
        .nav {{ background: var(--primary); padding: 15px; text-align: center; position: sticky; top: 0; z-index: 1000; overflow-x: auto; white-space: nowrap; }}
        .nav a {{ color: white; text-decoration: none; margin: 0 15px; font-weight: 600; text-transform: uppercase; font-size: 13px; display: inline-block; }}
        .nav a:hover {{ color: var(--accent); }}
        .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 40px 20px; text-align: center; }}
        .hero h2 {{ font-size: 42px; margin-bottom: 15px; }}
        .search-bar {{ max-width: 600px; margin: 20px auto 0; display: flex; gap: 10px; }}
        .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; font-size: 16px; }}
        .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 24px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; }}
        .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-bottom: 50px; }}
        .stat-card {{ background: white; padding: 30px; text-align: center; border-radius: 10px; box-shadow: var(--shadow); transition: transform 0.3s; }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card i {{ font-size: 48px; color: var(--primary-light); }}
        .stat-number {{ font-size: 42px; font-weight: bold; color: var(--primary); }}
        .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 40px; margin-bottom: 50px; }}
        .section-title {{ font-size: 28px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 25px; }}
        .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; box-shadow: var(--shadow); }}
        .btn {{ display: inline-block; background: var(--primary); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 15px; }}
        .btn-small {{ padding: 8px 20px; font-size: 14px; }}
        .weather-widget {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); border-radius: 20px; padding: 25px; color: white; margin-bottom: 30px; box-shadow: var(--shadow); position: relative; overflow: hidden; }}
        .weather-widget::before {{ content: ''; position: absolute; top: -50%; right: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%); pointer-events: none; }}
        .weather-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.2); }}
        .weather-header h3 {{ font-size: 18px; font-weight: normal; margin: 0; }}
        .weather-header span {{ font-size: 12px; opacity: 0.8; }}
        .current-weather {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; }}
        .weather-main {{ text-align: center; }}
        .weather-icon {{ font-size: 64px; margin-bottom: 5px; }}
        .weather-temp {{ font-size: 56px; font-weight: bold; line-height: 1; }}
        .weather-temp small {{ font-size: 24px; font-weight: normal; }}
        .feels-like {{ font-size: 14px; opacity: 0.8; margin-top: 5px; }}
        .weather-details {{ text-align: right; }}
        .weather-detail-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; }}
        .weather-condition {{ font-size: 18px; margin-top: 5px; }}
        .forecast-container {{ margin-top: 20px; }}
        .forecast-title {{ font-size: 14px; margin-bottom: 15px; opacity: 0.8; text-align: center; }}
        .forecast-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
        .forecast-day {{ text-align: center; padding: 10px 5px; background: rgba(255,255,255,0.1); border-radius: 10px; transition: transform 0.3s; }}
        .forecast-day:hover {{ transform: translateY(-3px); background: rgba(255,255,255,0.2); }}
        .forecast-day-name {{ font-size: 13px; font-weight: bold; margin-bottom: 8px; }}
        .forecast-icon {{ font-size: 24px; margin-bottom: 8px; }}
        .forecast-temp {{ font-size: 14px; font-weight: bold; }}
        .classified-item {{ padding: 15px; border-bottom: 1px solid #eee; }}
        .classified-price {{ color: var(--accent); font-weight: bold; }}
        .classified-category {{ display: inline-block; background: var(--primary-light); color: white; font-size: 10px; padding: 2px 8px; border-radius: 10px; margin-left: 10px; }}
        .photo-gallery {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
        .gallery-item img {{ width: 100%; height: 200px; object-fit: cover; border-radius: 10px; }}
        .newsletter-section {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 50px; border-radius: 15px; text-align: center; margin-bottom: 50px; }}
        .newsletter-form {{ display: flex; justify-content: center; gap: 15px; margin-top: 25px; flex-wrap: wrap; }}
        .newsletter-form input {{ padding: 15px; width: 300px; border: none; border-radius: 5px; }}
        .newsletter-form button {{ background: var(--accent); color: var(--primary); padding: 15px 30px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; }}
        .social-section {{ background: white; padding: 40px; border-radius: 10px; text-align: center; margin-bottom: 50px; }}
        .social-links {{ display: flex; justify-content: center; gap: 20px; margin-top: 25px; flex-wrap: wrap; }}
        .social-btn {{ display: inline-flex; align-items: center; gap: 10px; padding: 12px 25px; border-radius: 50px; text-decoration: none; color: white; font-weight: bold; }}
        .social-btn.twitter {{ background: #1DA1F2; }}
        .social-btn.facebook {{ background: #3b5998; }}
        .social-btn.linkedin {{ background: #0077b5; }}
        .social-btn.email {{ background: #666; }}
        .footer {{ background: #0d260d; color: white; padding: 50px 20px 30px; }}
        .footer-content {{ max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(4, 1fr); gap: 40px; }}
        .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 10px; font-size: 14px; }}
        .footer-column a:hover {{ color: var(--accent); }}
        .copyright {{ text-align: center; padding-top: 40px; margin-top: 40px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; }}
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .two-column {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
            .photo-gallery {{ grid-template-columns: 1fr; }}
            .logo h1 {{ font-size: 36px; }}
            .hero h2 {{ font-size: 28px; }}
            .current-weather {{ flex-direction: column; text-align: center; gap: 20px; }}
            .weather-details {{ text-align: center; }}
            .weather-detail-item {{ justify-content: center; }}
            .forecast-grid {{ grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); }}
        }}
        @media (max-width: 480px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: 1fr; text-align: center; }}
        }}
    </style>
</head>
<body>
    <div class="install-prompt" id="installPrompt"><span>📱 Install the Gazette app</span><button id="installBtn">Install</button></div>
    <div class="top-bar">🌿 Spruce Grove's Primary Resource for Trade & Employment | "Your Hometown, Online."</div>
    <div class="header"><div class="logo"><h1>📰 {NEWSPAPER_NAME}</h1><p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p><div class="tagline">"Your Hometown, Online." • Spruce Grove's Primary Resource for Trade & Employment</div></div></div>
    <div class="date-header">📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
    <div class="nav"><a href="/">🏠 HOME</a><a href="/latest">📰 GAZETTE DISPATCHES</a><a href="/classifieds">📋 CLASSIFIEDS</a><a href="/search">🔍 SEARCH</a><a href="/post-ad">📝 POST AN AD</a><a href="/subscribe">✉️ NEWSLETTER</a></div>
    <div class="hero"><h2>Your Hometown, Online.</h2><p>Spruce Grove's Primary Resource for Trade & Employment</p><form class="search-bar" action="/search" method="GET"><input type="text" name="q" placeholder="Search Gazette dispatches, events, and archives..." required><button type="submit"><i class="fas fa-search"></i> Search</button></form></div>
    <div class="main-content">
        <div class="stats-grid"><div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">{total_articles}</div><div>Dispatches</div></div><div class="stat-card"><i class="fas fa-tags"></i><div class="stat-number">5</div><div>Categories</div></div><div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">{subscriber_count}</div><div>Readers</div></div><div class="stat-card"><i class="fas fa-clock"></i><div class="stat-number">8 AM</div><div>Daily Delivery</div></div></div>
        <div class="two-column">
            <div>
                <h2 class="section-title">📰 Latest Gazette Dispatches</h2>
                <div class="feature-card"><h3>Welcome to the Spruce Grove Gazette</h3><p>Serving Spruce Grove with trusted local news coverage.</p><a href="/latest" class="btn">Read Latest Dispatch →</a></div>
                <h2 class="section-title">📸 Community Photos</h2>
                <div class="photo-gallery">{gallery_html}</div>
                <h2 class="section-title">✉️ Letters to the Editor</h2>
                <div class="feature-card">{letters_html}<a href="/submit-letter" class="btn btn-small" style="background: var(--accent); color: var(--primary);">Submit a Letter →</a></div>
            </div>
            <div>
                <div class="weather-widget">
                    <div class="weather-header"><h3><i class="fas fa-map-marker-alt"></i> Spruce Grove, AB</h3><span>{datetime.now().strftime('%A, %B %d')}</span></div>
                    <div class="current-weather">
                        <div class="weather-main"><div class="weather-icon">{weather['current']['icon']}</div><div class="weather-temp">{weather['current']['temp']}<small>°C</small></div><div class="feels-like">Feels like {weather['current']['feels_like']}°C</div><div class="weather-condition">{weather['current']['condition']}</div></div>
                        <div class="weather-details"><div class="weather-detail-item"><i class="fas fa-tint"></i><span>Humidity: {weather['current']['humidity']}%</span></div><div class="weather-detail-item"><i class="fas fa-wind"></i><span>Wind: {weather['current']['wind']} km/h</span></div><div class="weather-detail-item"><i class="fas fa-sun"></i><span>UV Index: Moderate</span></div><div class="weather-detail-item"><i class="fas fa-eye"></i><span>Visibility: 16 km</span></div></div>
                    </div>
                    <div class="forecast-container"><div class="forecast-title">5-DAY FORECAST</div><div class="forecast-grid">{forecast_html}</div></div>
                </div>
                <h2 class="section-title">📅 Upcoming Events</h2>
                <div class="feature-card"><ul style="list-style: none;">{events_html}</ul></div>
                <h2 class="section-title">📋 Recent Classifieds</h2>
                <div class="feature-card">{classifieds_html}<a href="/classifieds" class="btn btn-small" style="margin-top: 10px;">View All Classifieds →</a><a href="/post-ad" class="btn btn-small" style="margin-top: 10px; background: var(--accent); color: var(--primary);">Post an Ad →</a></div>
                <h2 class="section-title">📱 Install Our App</h2>
                <div class="feature-card" style="text-align: center;"><i class="fas fa-mobile-alt" style="font-size: 48px; color: var(--primary);"></i><p>Add the Gazette to your home screen for quick access.</p><button id="mobileInstallBtn" class="btn" style="background: var(--accent); color: var(--primary);">📲 Install App</button></div>
            </div>
        </div>
        <div class="newsletter-section"><h3>✉️ Never Miss an Edition</h3><p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p><form class="newsletter-form" action="/subscribe" method="GET"><input type="email" name="email" placeholder="Enter your email address" required><button type="submit">Subscribe Free →</button></form></div>
        <div class="social-section"><h3>📱 Follow The Gazette</h3><div class="social-links"><a href="https://twitter.com/intent/tweet?text=Spruce Grove Gazette&url=https://sprucegrovegazette.com" class="social-btn twitter"><i class="fab fa-twitter"></i> Twitter</a><a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Facebook</a><a href="https://www.linkedin.com/sharing/share-offsite/?url=https://sprucegrovegazette.com" class="social-btn linkedin"><i class="fab fa-linkedin-in"></i> LinkedIn</a><a href="mailto:?subject=Spruce Grove Gazette&body=Check this out: https://sprucegrovegazette.com" class="social-btn email"><i class="fas fa-envelope"></i> Email</a></div></div>
    </div>
    <div class="footer">
        <div class="footer-content"><div class="footer-column"><h4>📰 The Gazette</h4><a href="/">Home</a><a href="/latest">Dispatches</a><a href="/classifieds">Classifieds</a><a href="/search">Search Archives</a><a href="/subscribe">Newsletter</a></div><div class="footer-column"><h4>📬 Connect</h4><a href="/post-ad">Post an Ad</a><a href="/submit-letter">Submit a Letter</a><a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a><a href="#">Advertising</a></div><div class="footer-column"><h4>🔗 Categories</h4><a href="/classifieds?category=jobs">Jobs</a><a href="/classifieds?category=sale">For Sale</a><a href="/classifieds?category=housing">Housing</a><a href="/classifieds?category=services">Services</a><a href="/classifieds?category=garage">Garage Sales</a></div><div class="footer-column"><h4>📍 Location</h4><a href="#">Spruce Grove, Alberta</a><a href="#">Canada T7X 0A1</a><a href="#">"Your Hometown, Online."</a></div></div>
        <div class="copyright"><p>© {LAUNCH_YEAR} {NEWSPAPER_NAME}. All rights reserved.</p><p>Proudly serving Spruce Grove since {LAUNCH_DATE} | {TAGLINE}</p></div>
    </div>
    <script>
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {{ e.preventDefault(); deferredPrompt = e; document.getElementById('installPrompt').classList.add('show'); }});
        document.getElementById('installBtn').addEventListener('click', async () => {{ if (deferredPrompt) {{ deferredPrompt.prompt(); const {{ outcome }} = await deferredPrompt.userChoice; if (outcome === 'accepted') {{ console.log('App installed'); }} deferredPrompt = null; document.getElementById('installPrompt').classList.remove('show'); }} }});
        document.getElementById('mobileInstallBtn')?.addEventListener('click', () => {{ if (deferredPrompt) {{ deferredPrompt.prompt(); }} else {{ alert('To install: Tap the Share button and select "Add to Home Screen"'); }} }});
        if ('serviceWorker' in navigator) {{ navigator.serviceWorker.register('/sw.js').then(reg => console.log('Service Worker registered', reg)).catch(err => console.log('Service Worker failed', err)); }}
    </script>
</body>
</html>'''

# Additional Routes
@app.route('/latest')
def latest_article():
    latest = get_latest_article()
    if latest:
        return send_file(latest)
    return '<h1>First Dispatch Coming Soon</h1><p>Check back soon!</p><a href="/">Back to Home</a>'

@app.route('/classifieds')
def classifieds():
    category = request.args.get('category', 'all')
    classifieds_list = get_classifieds_by_category(category)
    categories = [{"id": "all", "name": "All Categories", "icon": "📋"}, {"id": "jobs", "name": "Jobs", "icon": "💼"}, {"id": "sale", "name": "For Sale", "icon": "🏷️"}, {"id": "housing", "name": "Housing", "icon": "🏠"}, {"id": "services", "name": "Services", "icon": "🔧"}, {"id": "garage", "name": "Garage Sales", "icon": "🏪"}]
    classifieds_html = ''.join([f'<div class="classified-card"><span class="category-badge">{c["category"].upper()}</span><h3>{c["title"]}</h3><p>{c["description"]}</p><div class="price">{c["price"] if c["price"] else "Price not specified"}</div><small>Contact: {c["contact"]} | Posted: {c["date"]}</small></div>' for c in classifieds_list])
    categories_html = ''.join([f'<a href="/classifieds?category={c["id"]}" class="category-btn {"active" if category == c["id"] else ""}">{c["icon"]} {c["name"]}</a>' for c in categories])
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Classifieds - {NEWSPAPER_NAME}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>body{{font-family:Georgia;background:#f9f9f5;margin:0;}}.header{{background:#1a3d1a;color:white;padding:20px;text-align:center;}}.nav{{background:#2C5F2D;padding:15px;text-align:center;}}.nav a{{color:white;margin:0 15px;text-decoration:none;}}.container{{max-width:1200px;margin:0 auto;padding:40px 20px;}}.categories{{display:flex;gap:15px;flex-wrap:wrap;margin-bottom:30px;}}.category-btn{{background:white;padding:10px 20px;border-radius:25px;text-decoration:none;color:#1a3d1a;border:1px solid #ddd;}}.category-btn.active{{background:#1a3d1a;color:white;}}.classified-card{{background:white;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,0.1);}}.category-badge{{display:inline-block;background:#D4A017;color:#1a3d1a;padding:4px 12px;border-radius:15px;font-size:12px;font-weight:bold;}}.price{{color:#D4A017;font-size:20px;font-weight:bold;}}.btn{{display:inline-block;background:#1a3d1a;color:white;padding:12px 24px;text-decoration:none;border-radius:5px;margin-top:10px;}}.footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px;}}</style></head><body><div class="header"><h1>📰 {NEWSPAPER_NAME}</h1><p>Classifieds • Trade • Employment</p></div><div class="nav"><a href="/">🏠 Home</a><a href="/classifieds">📋 Classifieds</a><a href="/post-ad">📝 Post an Ad</a><a href="/search">🔍 Search</a></div><div class="container"><h2>📋 Classifieds</h2><div class="categories">{categories_html}</div>{classifieds_html if classifieds_list else '<p>No classifieds found. <a href="/post-ad">Post an ad →</a></p>'}<div style="text-align:center;margin-top:30px;"><a href="/post-ad" class="btn">📝 Post an Ad →</a></div></div><div class="footer"><p>© {LAUNCH_YEAR} {NEWSPAPER_NAME} | "Your Hometown, Online."</p></div></body></html>'''

@app.route('/post-ad', methods=['GET', 'POST'])
def post_ad():
    if request.method == 'POST':
        category = request.form.get('category')
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        contact = request.form.get('contact')
        email = request.form.get('email')
        conn = sqlite3.connect('gazette_archive.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO classifieds (category, title, description, price, contact, email, date, active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)", (category, title, description, price, contact, email, date.today()))
        conn.commit()
        conn.close()
        return f'<html><body style="font-family:Georgia;text-align:center;padding:50px;"><h1>✅ Ad Posted!</h1><a href="/classifieds">View Classifieds</a></body></html>'
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Post an Ad - {NEWSPAPER_NAME}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>body{{font-family:Georgia;background:#f9f9f5;margin:0;}}.header{{background:#1a3d1a;color:white;padding:20px;text-align:center;}}.container{{max-width:600px;margin:0 auto;padding:40px 20px;}}.form-card{{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1);}}input,select,textarea{{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:5px;font-family:inherit;}}button{{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;font-size:16px;}}.footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px;}}</style></head><body><div class="header"><h1>📰 {NEWSPAPER_NAME}</h1><p>Post a Classified Ad</p></div><div class="container"><div class="form-card"><h2>📝 Post an Ad</h2><form method="POST"><select name="category" required><option value="">Select Category</option><option value="jobs">💼 Jobs / Employment</option><option value="sale">🏷️ For Sale</option><option value="housing">🏠 Housing / Rentals</option><option value="services">🔧 Services</option><option value="garage">🏪 Garage Sale</option></select><input type="text" name="title" placeholder="Ad Title" required><textarea name="description" rows="5" placeholder="Describe what you are offering..." required></textarea><input type="text" name="price" placeholder="Price (or leave blank)"><input type="text" name="contact" placeholder="Contact info (phone, email)" required><input type="email" name="email" placeholder="Your email for confirmation"><button type="submit">📢 Post Ad →</button></form><a href="/classifieds">← Back to Classifieds</a></div></div><div class="footer"><p>© {LAUNCH_YEAR} {NEWSPAPER_NAME} | "Your Hometown, Online."</p></div></body></html>'''

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = search_articles(query) if query else []
    results_html = ''.join([f'<div class="result-card"><h3>{r["title"]}</h3><p>{r["content"]}...</p><div class="result-date">Date: {r["date"]}</div><a href="{r["file_path"]}" class="btn">Read Dispatch →</a></div>' for r in results])
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Search - {NEWSPAPER_NAME}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>body{{font-family:Georgia;background:#f9f9f5;margin:0;}}.header{{background:#1a3d1a;color:white;padding:20px;text-align:center;}}.nav{{background:#2C5F2D;padding:15px;text-align:center;}}.nav a{{color:white;margin:0 15px;text-decoration:none;}}.container{{max-width:800px;margin:0 auto;padding:40px 20px;}}.search-box{{background:white;padding:30px;border-radius:10px;margin-bottom:30px;}}.search-box input{{width:70%;padding:12px;border:1px solid #ddd;border-radius:5px;}}.search-box button{{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;}}.result-card{{background:white;padding:20px;border-radius:10px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,0.1);}}.result-date{{color:#666;font-size:12px;}}.btn{{display:inline-block;background:#1a3d1a;color:white;padding:8px 16px;text-decoration:none;border-radius:5px;margin-top:10px;}}.footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px;}}</style></head><body><div class="header"><h1>📰 {NEWSPAPER_NAME}</h1><p>Search Dispatches and Archives</p></div><div class="nav"><a href="/">🏠 Home</a><a href="/latest">📰 Dispatches</a><a href="/classifieds">📋 Classifieds</a></div><div class="container"><div class="search-box"><form method="GET"><input type="text" name="q" value="{query}" placeholder="Search Gazette dispatches, events, and archives..." required><button type="submit"><i class="fas fa-search"></i> Search</button></form></div>{results_html if results else f'<p style="text-align:center;">{"No results found. Try different keywords." if query else "Enter search terms above."}</p>'}</div><div class="footer"><p>© {LAUNCH_YEAR} {NEWSPAPER_NAME} | "Your Hometown, Online."</p></div></body></html>'''

@app.route('/submit-letter', methods=['GET', 'POST'])
def submit_letter():
    if request.method == 'POST':
        author = request.form.get('author')
        subject = request.form.get('subject')
        content = request.form.get('content')
        conn = sqlite3.connect('gazette_archive.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO letters (author, subject, content, date, approved) VALUES (?, ?, ?, ?, 0)", (author, subject, content, date.today()))
        conn.commit()
        conn.close()
        return '<html><body style="font-family:Georgia;text-align:center;padding:50px;"><h1>✅ Letter Submitted</h1><a href="/">Back to Gazette</a></body></html>'
    return f'''<!DOCTYPE html><html><head><title>Submit a Letter</title><style>body{{font-family:Georgia;background:#f0f0e8;padding:50px;}}.container{{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px;}}input,textarea{{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px;}}button{{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;}}</style></head><body><div class="container"><h1>✉️ Submit a Letter</h1><form method="POST"><input type="text" name="author" placeholder="Your name" required><input type="text" name="subject" placeholder="Subject" required><textarea name="content" rows="6" placeholder="Write your letter..." required></textarea><button type="submit">Submit →</button></form><p><a href="/">← Back to Gazette</a></p></div></body></html>'''

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name', '')
        if email:
            conn = sqlite3.connect('gazette_archive.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO subscribers (email, name, subscribed_date, active) VALUES (?, ?, ?, 1)", (email, name, date.today()))
                conn.commit()
            except:
                pass
            conn.close()
        return '<html><body style="font-family:Georgia;text-align:center;padding:50px;"><h1>✅ Subscribed!</h1><a href="/">Back to Gazette</a></body></html>'
    return f'''<!DOCTYPE html><html><head><title>Subscribe</title><style>body{{font-family:Georgia;background:#f0f0e8;padding:50px;}}.container{{max-width:500px;margin:0 auto;background:white;padding:40px;border-radius:10px;}}input{{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:5px;}}button{{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;}}</style></head><body><div class="container"><h1>📧 Subscribe</h1><form method="POST"><input type="text" name="name" placeholder="Your name"><input type="email" name="email" placeholder="Your email" required><button type="submit">Subscribe →</button></form><p><a href="/">← Back to Gazette</a></p></div></body></html>'''

@app.route('/rss')
def rss_feed():
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, published_date FROM articles ORDER BY published_date DESC LIMIT 10")
    articles = cursor.fetchall()
    conn.close()
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{NEWSPAPER_NAME}</title><link>https://sprucegrovegazette.com</link><description>Local news for Spruce Grove, Alberta</description><language>en-ca</language><lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate>{"".join([f"<item><title>{a[0]}</title><link>https://sprucegrovegazette.com/latest</link><description>{a[1][:200]}...</description><pubDate>{a[2]}</pubDate></item>" for a in articles])}</channel></rss>'
    return app.response_class(rss, mimetype='application/rss+xml')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

@app.route('/api/status')
def api_status():
    return jsonify({"name": NEWSPAPER_NAME, "schedule": "Daily at 8:00 AM MT", "total_articles": get_article_count(), "subscribers": get_subscriber_count()})

@app.route('/sitemap.xml')
def sitemap():
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://sprucegrovegazette.com/</loc><lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod><priority>1.0</priority></url><url><loc>https://sprucegrovegazette.com/latest</loc><priority>0.9</priority></url><url><loc>https://sprucegrovegazette.com/classifieds</loc><priority>0.8</priority></url><url><loc>https://sprucegrovegazette.com/search</loc><priority>0.8</priority></url></urlset>'
    return app.response_class(sitemap, mimetype='application/xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)