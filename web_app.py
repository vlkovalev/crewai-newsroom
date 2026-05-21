import os
import psycopg2
import psycopg2.extras
import requests
import json
import traceback
import random
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, redirect, render_template_string
from werkzeug.utils import secure_filename
# Add these lines
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'spruce-grove-gazette-secret-key-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API Keys from environment variables
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', 'sb')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
GAZETTE_API_KEY = os.environ.get('GAZETTE_API_KEY', '')

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def init_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        id SERIAL PRIMARY KEY, email TEXT UNIQUE, name TEXT,
        subscribed_date DATE, active BOOLEAN DEFAULT TRUE, neighborhood TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS supporters (
        id SERIAL PRIMARY KEY, email TEXT UNIQUE, name TEXT,
        tier TEXT, amount INTEGER, start_date DATE, active BOOLEAN DEFAULT TRUE,
        paypal_subscription_id TEXT, transaction_id TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS news_articles (
        id SERIAL PRIMARY KEY, title TEXT, content TEXT,
        summary TEXT, source TEXT, author TEXT, date TIMESTAMP, category TEXT,
        featured BOOLEAN DEFAULT FALSE, active BOOLEAN DEFAULT TRUE,
        url TEXT, image_url TEXT, views INTEGER DEFAULT 0)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY, title TEXT, description TEXT,
        date DATE, time TEXT, location TEXT, ticket_price TEXT,
        total_tickets INTEGER, tickets_sold INTEGER DEFAULT 0,
        organizer TEXT, email TEXT, approved BOOLEAN DEFAULT TRUE,
        date_submitted DATE, recurring TEXT, expiry_date DATE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS classifieds (
        id SERIAL PRIMARY KEY, category TEXT, title TEXT,
        description TEXT, price TEXT, contact TEXT, email TEXT, phone TEXT,
        photo TEXT, featured BOOLEAN DEFAULT FALSE, date DATE, expiry_date DATE,
        renewed_count INTEGER DEFAULT 0, active BOOLEAN DEFAULT TRUE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS businesses (
        id SERIAL PRIMARY KEY, name TEXT, category TEXT,
        description TEXT, address TEXT, phone TEXT, email TEXT, website TEXT,
        logo TEXT, featured BOOLEAN DEFAULT FALSE, approved BOOLEAN DEFAULT TRUE,
        date DATE, views INTEGER DEFAULT 0)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS news_tips (
        id SERIAL PRIMARY KEY, name TEXT, email TEXT, tip TEXT,
        category TEXT, date DATE, status TEXT DEFAULT 'pending')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS photo_submissions (
        id SERIAL PRIMARY KEY, name TEXT, email TEXT, title TEXT,
        caption TEXT, filename TEXT, date DATE, approved BOOLEAN DEFAULT FALSE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ad_inquiries (
        id SERIAL PRIMARY KEY, business_name TEXT, contact_name TEXT,
        email TEXT, phone TEXT, package_interest TEXT, message TEXT,
        date DATE, status TEXT DEFAULT 'new')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY, email TEXT, name TEXT,
        amount INTEGER, tier TEXT, transaction_id TEXT,
        payment_date DATE, status TEXT DEFAULT 'completed')''')

    for sql in [
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS recurring TEXT",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS expiry_date DATE",
        "ALTER TABLE classifieds ADD COLUMN IF NOT EXISTS expiry_date DATE",
        "ALTER TABLE classifieds ADD COLUMN IF NOT EXISTS renewed_count INTEGER DEFAULT 0",
        # Phase 1 editorial columns
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS urgent BOOLEAN DEFAULT FALSE",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT FALSE",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 50",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS story_type TEXT DEFAULT 'standard'",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS expires_from_front DATE",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS source_label TEXT DEFAULT 'Staff'",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS correction TEXT",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP",
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS search_vector tsvector",
    ]:
        cursor.execute(sql)

    cursor.execute("UPDATE classifieds SET expiry_date = CURRENT_DATE + INTERVAL '30 days' WHERE expiry_date IS NULL")

    # Set default expires_from_front for existing articles that don't have it
    cursor.execute("""
        UPDATE news_articles
        SET expires_from_front = date + INTERVAL '7 days'
        WHERE expires_from_front IS NULL AND date IS NOT NULL
    """)

    # Populate FTS vector for existing rows
    cursor.execute("""
        UPDATE news_articles
        SET search_vector = to_tsvector('english',
            coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(content,''))
        WHERE search_vector IS NULL
    """)

    # GIN index for fast FTS queries (safe to re-run)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_fts ON news_articles USING GIN(search_vector)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_score ON news_articles(score DESC, date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_urgent ON news_articles(urgent, date DESC)")

    # Source registry table
    cursor.execute('''CREATE TABLE IF NOT EXISTS source_registry (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        org_type TEXT DEFAULT 'media',
        url TEXT,
        region TEXT DEFAULT 'local',
        topics TEXT[],
        reliability INTEGER DEFAULT 3,
        ingestion_type TEXT DEFAULT 'manual',
        rss_url TEXT,
        last_checked TIMESTAMP,
        active BOOLEAN DEFAULT TRUE,
        notes TEXT
    )''')

    # Seed default sources if table is empty
    cursor.execute("SELECT COUNT(*) FROM source_registry")
    if cursor.fetchone()['count'] == 0:
        sources = [
            ('Gazette AI',          'staff',       'https://sprucegrovegazette.com', 'local',      5, 'AI-generated, editor-reviewed'),
            ('City of Spruce Grove','government',  'https://sprucegrove.ca',         'local',      5, 'Official city news and press releases'),
            ('Parkland County',     'government',  'https://parklandcounty.com',     'local',      5, 'Regional government'),
            ('RCMP K-Division',     'government',  'https://rcmp-grc.gc.ca',         'provincial', 5, 'Police press releases'),
            ('CBC Edmonton',        'media',       'https://cbc.ca/edmonton',        'provincial', 5, 'National public broadcaster'),
            ('CTV Edmonton',        'media',       'https://edmonton.ctvnews.ca',    'provincial', 4, 'National private broadcaster'),
            ('Edmonton Journal',    'media',       'https://edmontonjournal.com',    'provincial', 4, 'Daily newspaper'),
            ('Spruce Grove Examiner','media',      'https://sprucegroveexaminer.com','local',      4, 'Local paper'),
        ]
        for s in sources:
            cursor.execute(
                """INSERT INTO source_registry (name, org_type, url, region, reliability, notes)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                s
            )

    conn.commit()
    conn.close()

def get_weather_icon(icon_code):
    icon_map = {
        "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️",
        "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
        "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
        "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
        "50d": "🌫️", "50n": "🌫️"
    }
    return icon_map.get(icon_code, "🌡️")

def get_weather_forecast():
    if OPENWEATHER_API_KEY:
        try:
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q=Spruce Grove,CA&appid={OPENWEATHER_API_KEY}&units=metric"
            forecast_resp = requests.get(forecast_url, timeout=10)
            forecast_data = forecast_resp.json()
            
            forecast = []
            seen_days = set()
            for item in forecast_data['list']:
                date_str = item['dt_txt'].split()[0]
                if date_str not in seen_days and len(forecast) < 5:
                    seen_days.add(date_str)
                    forecast.append({
                        "day": datetime.strptime(date_str, '%Y-%m-%d').strftime('%a'),
                        "high": round(item['main']['temp_max']),
                        "low": round(item['main']['temp_min']),
                        "condition": item['weather'][0]['description'].title(),
                        "icon": get_weather_icon(item['weather'][0]['icon'])
                    })
            return forecast
        except Exception as e:
            print(f"Forecast API error: {e}")
    
    return [
        {"day": "Mon", "high": 20, "low": 8, "condition": "Sunny", "icon": "☀️"},
        {"day": "Tue", "high": 22, "low": 10, "condition": "Partly Cloudy", "icon": "⛅"},
        {"day": "Wed", "high": 19, "low": 9, "condition": "Light Rain", "icon": "🌧️"},
        {"day": "Thu", "high": 21, "low": 11, "condition": "Sunny", "icon": "☀️"},
        {"day": "Fri", "high": 23, "low": 12, "condition": "Sunny", "icon": "☀️"}
    ]

def get_weather():
    if OPENWEATHER_API_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q=Spruce Grove,CA&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=10)
            data = response.json()
            if response.status_code == 200 and 'main' in data:
                current = {
                    "temp": round(data['main']['temp']),
                    "feels_like": round(data['main']['feels_like']),
                    "condition": data['weather'][0]['description'].title(),
                    "humidity": data['main']['humidity'],
                    "wind": round(data['wind']['speed']),
                    "pressure": data['main']['pressure'],
                    "uv": 5,
                    "visibility": round(data.get('visibility', 10000) / 1000),
                    "icon": get_weather_icon(data['weather'][0]['icon'])
                }
                return current
        except Exception as e:
            print(f"Weather API error: {e}")
    
    return {
        "temp": 18, "feels_like": 17, "condition": "Partly Cloudy", 
        "humidity": 65, "wind": 15, "pressure": 1012, "uv": 5, 
        "visibility": 16, "icon": "🌤️"
    }

def get_news_articles(limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, title, summary, source, date, category, views,
                  coalesce(score,50) - EXTRACT(EPOCH FROM (NOW()-date))/7200 AS eff_score,
                  urgent, pinned, story_type, source_label, correction
           FROM news_articles
           WHERE active = TRUE
             AND (expires_from_front IS NULL OR expires_from_front >= CURRENT_DATE)
             AND date >= NOW() - INTERVAL '7 days'
           ORDER BY pinned DESC, eff_score DESC, date DESC
           LIMIT %s""",
        (limit,)
    )
    articles = cursor.fetchall()
    conn.close()
    return [dict(a) for a in articles]


def get_urgent_articles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, title, summary, source, date, category, source_label
           FROM news_articles
           WHERE active = TRUE AND urgent = TRUE
             AND date >= NOW() - INTERVAL '6 hours'
           ORDER BY date DESC LIMIT 3"""
    )
    articles = cursor.fetchall()
    conn.close()
    return [dict(a) for a in articles]


def get_regional_news(category, limit=4):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, title, summary, source, date, source_label
           FROM news_articles
           WHERE active = TRUE AND category = %s
             AND (expires_from_front IS NULL OR expires_from_front >= CURRENT_DATE)
           ORDER BY date DESC LIMIT %s""",
        (category, limit)
    )
    articles = cursor.fetchall()
    conn.close()
    return [dict(a) for a in articles]


def get_top_stories():
    conn = get_db()
    cursor = conn.cursor()
    # Fetch more than needed so we can enforce per-category cap after sorting
    cursor.execute(
        """SELECT id, title, summary, source, date, category, views,
                  coalesce(score,50) AS score, source_label, story_type
           FROM news_articles
           WHERE active = TRUE AND urgent = FALSE
             AND coalesce(score,50) >= 60
             AND date >= NOW() - INTERVAL '72 hours'
             AND (expires_from_front IS NULL OR expires_from_front >= CURRENT_DATE)
           ORDER BY pinned DESC, score DESC, date DESC
           LIMIT 20"""
    )
    rows = cursor.fetchall()
    conn.close()
    # Enforce diversity: max 2 per category, 5 total
    seen_cats = {}
    result = []
    for row in rows:
        cat = row['category'] or 'News'
        if seen_cats.get(cat, 0) < 2:
            result.append(dict(row))
            seen_cats[cat] = seen_cats.get(cat, 0) + 1
        if len(result) == 5:
            break
    return result

def get_article_by_id(article_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, title, content, summary, source, author, date, category,
                  url, source_label, correction, urgent, views, score
           FROM news_articles WHERE id = %s AND active = TRUE""",
        (article_id,)
    )
    article = cursor.fetchone()
    if article:
        cursor.execute("UPDATE news_articles SET views = views + 1 WHERE id = %s", (article_id,))
        conn.commit()
    conn.close()
    return dict(article) if article else None

def get_events(limit=12):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, date, time, location, ticket_price FROM events WHERE approved = TRUE AND date >= CURRENT_DATE ORDER BY date LIMIT %s", (limit,))
    events = cursor.fetchall()
    conn.close()
    return [dict(e) for e in events]

def get_businesses(limit=6):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, description, phone, website FROM businesses WHERE approved = TRUE LIMIT %s", (limit,))
    businesses = cursor.fetchall()
    conn.close()
    return [dict(b) for b in businesses]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    url = DATABASE_URL
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

# Initialize database
init_database()

# ============= AUTOMATED SCHEDULER =============
# All jobs write directly to Postgres — no self-HTTP calls, no deadlock risk.
# Times are UTC. Spruce Grove is UTC-6 (MDT) / UTC-7 (MST).
#   07:00 UTC = 1 AM MDT  (overnight AI batch)
#   13:00 UTC = 7 AM MDT  (morning AI + RSS)
#   18:00 UTC = 12 PM MDT (noon RSS)
#   23:00 UTC = 5 PM MDT  (evening AI + RSS)
#   05:00 UTC = 11 PM MDT (nightly maintenance)

def _job_ai_generation():
    """Generate AI articles using OpenAI. Writes directly to DB."""
    print(f'[SCHEDULER] AI generation starting at {datetime.utcnow().isoformat()}')
    try:
        from news_crew_enhanced import generate_daily_articles
        generate_daily_articles()
    except Exception as e:
        print(f'[SCHEDULER] AI generation error: {e}')


def _job_rss_scraper():
    """Fetch and publish RSS news from regional sources."""
    print(f'[SCHEDULER] RSS scraper starting at {datetime.utcnow().isoformat()}')
    try:
        from news_scraper import run_scraper
        count = run_scraper()
        print(f'[SCHEDULER] RSS scraper done: {count} articles')
    except Exception as e:
        print(f'[SCHEDULER] RSS scraper error: {e}')


def _job_maintenance():
    """Score decay, FTS update, stats."""
    print(f'[SCHEDULER] Maintenance starting at {datetime.utcnow().isoformat()}')
    try:
        from maintenance import run_maintenance
        run_maintenance()
    except Exception as e:
        print(f'[SCHEDULER] Maintenance error: {e}')


if os.environ.get('SCHEDULER_ENABLED', '0') == '1':
    scheduler = BackgroundScheduler(timezone='UTC')

    # RSS scraping — 3× daily from real sources only (no AI-generated content)
    scheduler.add_job(_job_rss_scraper,   CronTrigger(hour=9,  minute=0),  id='rss_morning', replace_existing=True)
    scheduler.add_job(_job_rss_scraper,   CronTrigger(hour=15, minute=0),  id='rss_afternoon',replace_existing=True)
    scheduler.add_job(_job_rss_scraper,   CronTrigger(hour=20, minute=0),  id='rss_evening', replace_existing=True)

    # Nightly maintenance — 11 PM MDT
    scheduler.add_job(_job_maintenance,   CronTrigger(hour=5,  minute=0),  id='maintenance', replace_existing=True)

    scheduler.start()
    print('[SCHEDULER] Started — AI 3×/day, RSS 3×/day, maintenance nightly')
# ============= END SCHEDULER =============

# ============= ROUTES =============

_HEAD_INJECT = (
    b'<link rel="icon" href="data:image/svg+xml,'
    b'%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 100 100%27%3E'
    b'%3Ctext y=%27.9em%27 font-size=%2790%27%3E%F0%9F%93%B0%3C/text%3E%3C/svg%3E">'
    b'<script>if("serviceWorker"in navigator){'
    b'navigator.serviceWorker.getRegistrations()'
    b'.then(function(r){for(var s of r)s.unregister();});'
    b'if("caches"in window)caches.keys()'
    b'.then(function(k){for(var n of k)caches.delete(n);});'
    b'}</script>'
)

@app.after_request
def inject_head(response):
    if 'text/html' in response.content_type:
        response.data = response.data.replace(b'</head>', _HEAD_INJECT + b'</head>', 1)
    return response


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'ts': datetime.utcnow().isoformat()}), 200


@app.route('/')
def home():
    try:
        weather = get_weather()
        forecast = get_weather_forecast()
        events = get_events(6)
        businesses = get_businesses(3)
        news_articles = get_news_articles(12)
        urgent_articles = get_urgent_articles()
        top_stories = get_top_stories()
        edmonton_news = get_regional_news('Edmonton Area', 4)
        alberta_news  = get_regional_news('Alberta', 4)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, price, contact, date, category FROM classifieds WHERE active = TRUE AND expiry_date >= CURRENT_DATE ORDER BY date DESC LIMIT 3")
        classifieds_list = cursor.fetchall()
        conn.close()

        # Build forecast HTML
        forecast_html = ""
        for f in forecast:
            forecast_html += f'<div class="forecast-card"><div class="forecast-day">{f["day"]}</div><div class="forecast-icon">{f["icon"]}</div><div class="forecast-temp">{f["high"]}° / {f["low"]}°</div></div>'

        # Build events HTML
        events_html = ""
        if events:
            for e in events[:3]:
                events_html += f'<li class="event-item"><strong>{e["title"]}</strong><br><i class="fas fa-calendar-alt"></i> {e["date"]} at {e["time"]}<br><i class="fas fa-map-marker-alt"></i> {e["location"]}</li>'
        else:
            events_html = '<li>No upcoming events. <a href="/events/create">Create one!</a></li>'

        # Build urgent banner HTML
        urgent_html = ""
        for a in urgent_articles:
            mins_ago = ""
            if a.get("date"):
                delta = datetime.utcnow() - a["date"].replace(tzinfo=None)
                mins = int(delta.total_seconds() / 60)
                mins_ago = f'{mins}m ago' if mins < 60 else f'{mins//60}h ago'
            urgent_html += f'<div class="urgent-item"><span class="urgent-dot">●</span><a href="/article/{a["id"]}">{a["title"]}</a><span class="urgent-time">{mins_ago}</span></div>'

        # Build top stories HTML
        top_ids = {a["id"] for a in top_stories}
        top_html = ""
        for a in top_stories:
            label = a.get("source_label") or "Staff"
            label_class = {"Official":"badge-official","Media":"badge-media","AI Draft":"badge-ai"}.get(label,"badge-staff")
            top_html += f'''<div class="top-story-card">
                <div class="top-story-meta"><span class="source-badge {label_class}">{label}</span><span class="top-cat">{a["category"]}</span></div>
                <h3><a href="/article/{a["id"]}">{a["title"]}</a></h3>
                <p>{(a["summary"] or "")[:130]}...</p>
                <div class="top-story-footer"><i class="fas fa-calendar-alt"></i> {str(a["date"])[:10] if a["date"] else "Recent"}</div>
            </div>'''

        # Build news HTML (exclude top story IDs to avoid duplication)
        news_html = ""
        shown = 0
        for a in news_articles:
            if a["id"] in top_ids:
                continue
            if shown >= 6:
                break
            news_html += f'<div class="news-item"><div class="news-category">{a["category"]}</div><h3><a href="/article/{a["id"]}">{a["title"]}</a></h3><div class="news-meta"><i class="fas fa-calendar-alt"></i> {str(a["date"])[:10] if a["date"] else "Recent"}</div><p>{(a["summary"] or "")[:150]}...</p><a href="/article/{a["id"]}" class="read-more">Read Full Story →</a></div>'
            shown += 1
        if not news_html:
            news_html = '<p>No news articles yet. Check back soon!</p>'

        def _regional_cards(articles):
            if not articles:
                return '<p style="color:#888">Check back soon for regional updates.</p>'
            html = ''
            for a in articles:
                label = a.get('source_label') or 'Media'
                lc = {'Official':'#3498db','Media':'#7f8c8d','AI Draft':'#9b59b6'}.get(label,'#2ecc71')
                html += (
                    f'<div class="regional-card">'
                    f'<span class="regional-label" style="background:{lc}">{label}</span>'
                    f'<h4><a href="/article/{a["id"]}">{a["title"]}</a></h4>'
                    f'<div class="regional-meta"><i class="fas fa-newspaper"></i> {a["source"]} &nbsp;'
                    f'<i class="fas fa-calendar-alt"></i> {str(a["date"])[:10] if a["date"] else "Recent"}</div>'
                    f'</div>'
                )
            return html

        edmonton_html = _regional_cards(edmonton_news)
        alberta_html  = _regional_cards(alberta_news)

        urgent_section = (
            '<div class="urgent-banner"><div class="urgent-banner-title">&#x1F6A8; Breaking News</div>'
            + urgent_html + '</div>'
        ) if urgent_html else ''

        top_section = (
            '<h2 class="section-title"><i class="fas fa-star"></i> Top Stories</h2>'
            '<div class="top-stories-grid">' + top_html + '</div>'
        ) if top_html else ''
        
        # Build classifieds HTML
        classifieds_html = ""
        if classifieds_list:
            for c in classifieds_list:
                classifieds_html += f'<div class="classified-item"><span class="classified-category-badge">{c["category"].upper() if c["category"] else "GENERAL"}</span><strong>{c["title"]}</strong><p>{c["description"][:80]}...</p><div class="classified-price">{c["price"] if c["price"] else "Call for price"}</div></div>'
        else:
            classifieds_html = '<p>No classifieds yet. <a href="/post-ad">Post an ad</a></p>'
        
        # Build businesses HTML
        businesses_html = ""
        if businesses:
            for b in businesses[:3]:
                businesses_html += f'<div class="business-card"><h4>{b["name"]}</h4><div class="business-category">{b["category"]}</div><p>{b["description"][:100]}...</p><div class="business-contact"><i class="fas fa-phone"></i> {b["phone"]}</div></div>'
        else:
            businesses_html = '<p>No businesses listed yet. <a href="/submit-business">Add your business</a></p>'
        
        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{NEWSPAPER_NAME}</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                :root {{--primary:#1a3d1a;--primary-light:#2C5F2D;--accent:#D4A017;}}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
                .top-bar {{ background: var(--primary); color: white; font-size: 11px; padding: 8px 0; text-align: center; }}
                .header {{ background: white; padding: 25px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
                .logo h1 {{ font-size: 44px; color: var(--primary); }}
                .logo p {{ font-size: 12px; color: #666; letter-spacing: 2px; }}
                .date-header {{ background: #f0f0e8; padding: 8px; text-align: center; font-size: 13px; }}
                .nav {{ background: var(--primary); padding: 12px; text-align: center; position: sticky; top: 0; overflow-x: auto; white-space: nowrap; z-index: 100; }}
                .nav a {{ color: white; margin: 0 12px; text-decoration: none; text-transform: uppercase; font-size: 12px; font-weight: bold; display: inline-block; }}
                .nav a:hover {{ color: var(--accent); }}
                .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 40px 20px; text-align: center; }}
                .hero h2 {{ font-size: 32px; }}
                .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
                .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
                .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
                .quick-links {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin: 30px 0; }}
                .quick-link {{ background: white; padding: 12px 25px; border-radius: 30px; text-decoration: none; color: var(--primary); font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .quick-link:hover {{ background: var(--accent); transform: translateY(-2px); }}
                .main-content {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
                .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
                .stat-card {{ background: white; padding: 25px; text-align: center; border-radius: 10px; cursor: pointer; transition: all 0.3s; }}
                .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
                .stat-card i {{ font-size: 32px; color: var(--accent); margin-bottom: 10px; }}
                .stat-number {{ font-size: 32px; font-weight: bold; color: var(--primary); }}
                .weather-widget {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); border-radius: 20px; padding: 25px; color: white; margin-bottom: 30px; }}
                .forecast-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 15px; }}
                .forecast-card {{ background: rgba(255,255,255,0.15); border-radius: 12px; padding: 10px; text-align: center; }}
                .forecast-day {{ font-size: 12px; font-weight: bold; }}
                .forecast-icon {{ font-size: 28px; margin: 8px 0; }}
                .forecast-temp {{ font-size: 14px; font-weight: bold; }}
                .featured-article {{ background: white; border-radius: 15px; padding: 30px; margin-bottom: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .featured-badge {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 4px 12px; border-radius: 15px; font-size: 11px; margin-bottom: 15px; }}
                .section-title {{ font-size: 22px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin: 30px 0 20px; }}
                .news-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; margin-bottom: 40px; }}
                .news-item {{ background: white; border-radius: 10px; padding: 20px; transition: transform 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .news-item:hover {{ transform: translateY(-3px); }}
                .news-category {{ display: inline-block; background: var(--primary-light); color: white; padding: 2px 10px; border-radius: 12px; font-size: 10px; margin-bottom: 10px; }}
                .read-more {{ color: var(--accent); font-size: 13px; font-weight: bold; text-decoration: none; display: inline-block; margin-top: 10px; }}
                .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 40px; }}
                .business-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
                .business-card {{ background: white; border-radius: 10px; padding: 20px; transition: all 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .business-card:hover {{ transform: translateY(-5px); }}
                .business-category {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 2px 8px; border-radius: 15px; font-size: 10px; margin: 8px 0; }}
                .business-contact {{ font-size: 12px; margin-top: 10px; color: #666; }}
                .classified-item {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
                .classified-category-badge {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; margin-right: 10px; }}
                .classified-price {{ color: var(--accent); font-weight: bold; margin: 8px 0; }}
                .btn {{ display: inline-block; background: var(--primary); color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; transition: all 0.3s; border: none; cursor: pointer; }}
                .btn:hover {{ transform: translateY(-2px); background: #0d260d; }}
                .ad-spot {{ background: linear-gradient(135deg, #fff8e1, #ffe082); border: 2px dashed var(--accent); border-radius: 10px; padding: 25px; text-align: center; margin: 30px 0; cursor: pointer; transition: all 0.3s; }}
                .ad-spot:hover {{ transform: scale(1.02); }}
                .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 40px; border-radius: 15px; text-align: center; margin: 40px 0; }}
                .newsletter input, .newsletter select {{ padding: 12px; width: 250px; border: none; border-radius: 5px; margin: 10px; }}
                .newsletter button {{ background: var(--accent); color: var(--primary); padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
                .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px 20px; margin-top: 40px; }}
                .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
                .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 13px; }}
                .footer-column a:hover {{ color: var(--accent); }}
                .dark-mode-toggle {{ position: fixed; bottom: 20px; right: 20px; background: var(--primary); color: white; border: none; border-radius: 50px; padding: 12px 18px; cursor: pointer; z-index: 1000; }}
                body.dark-mode {{ background: #1a1a2e; color: #eee; }}
                body.dark-mode .header, body.dark-mode .featured-article, body.dark-mode .news-item, body.dark-mode .business-card, body.dark-mode .stat-card {{ background: #16213e; color: #eee; }}
                @media (max-width: 768px) {{ .stats, .news-grid, .two-column, .business-grid {{ grid-template-columns: 1fr; }} .footer-content {{ grid-template-columns: repeat(2, 1fr); }} .top-stories-grid, .regional-grid {{ grid-template-columns: 1fr; }} }}
                /* ── Regional news strips ── */
                .regional-grid {{ display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:30px; }}
                .regional-card {{ background:white;border-radius:8px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.08);transition:transform .2s; }}
                .regional-card:hover {{ transform:translateY(-2px); }}
                .regional-card h4 {{ font-size:14px;margin:6px 0 8px;line-height:1.4; }}
                .regional-card h4 a {{ color:var(--primary);text-decoration:none; }}
                .regional-card h4 a:hover {{ text-decoration:underline; }}
                .regional-label {{ font-size:9px;font-weight:bold;padding:2px 7px;border-radius:10px;text-transform:uppercase;color:white; }}
                .regional-meta {{ font-size:11px;color:#999; }}
                /* ── Breaking / Urgent banner ── */
                .urgent-banner {{ background:#c0392b;color:white;padding:12px 20px;display:flex;flex-direction:column;gap:6px; }}
                .urgent-banner-title {{ font-size:11px;font-weight:900;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px; }}
                .urgent-item {{ display:flex;align-items:center;gap:10px;font-size:14px; }}
                .urgent-item a {{ color:white;font-weight:bold;text-decoration:none; }}
                .urgent-item a:hover {{ text-decoration:underline; }}
                .urgent-dot {{ color:#ff6b6b;font-size:18px;animation:blink 1s step-start infinite; }}
                .urgent-time {{ margin-left:auto;font-size:11px;opacity:0.8;white-space:nowrap; }}
                @keyframes blink {{ 50% {{ opacity:0; }} }}
                /* ── Top Stories ── */
                .top-stories-grid {{ display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px; }}
                .top-story-card {{ background:white;border-radius:10px;padding:20px;box-shadow:0 3px 10px rgba(0,0,0,0.12);border-top:3px solid var(--accent);transition:transform .2s; }}
                .top-story-card:hover {{ transform:translateY(-3px); }}
                .top-story-card h3 {{ font-size:16px;margin:8px 0; }}
                .top-story-card h3 a {{ color:var(--primary);text-decoration:none; }}
                .top-story-card h3 a:hover {{ text-decoration:underline; }}
                .top-story-card p {{ color:#555;font-size:13px;margin:0 0 10px; }}
                .top-story-meta {{ display:flex;gap:6px;align-items:center;margin-bottom:6px; }}
                .top-cat {{ font-size:10px;background:var(--primary-light);color:white;padding:2px 8px;border-radius:10px; }}
                .top-story-footer {{ font-size:11px;color:#888; }}
                /* ── Source badges ── */
                .source-badge {{ font-size:9px;font-weight:bold;padding:2px 7px;border-radius:10px;text-transform:uppercase; }}
                .badge-staff {{ background:#2ecc71;color:white; }}
                .badge-official {{ background:#3498db;color:white; }}
                .badge-media {{ background:#95a5a6;color:white; }}
                .badge-ai {{ background:#9b59b6;color:white; }}
            </style>
        </head>
        <body>
            <div class="top-bar"><i class="fas fa-leaf"></i> Serving Spruce Grove, Stony Plain & Parkland County | "Your Hometown, Online."</div>
            <div class="header"><div class="logo"><h1><i class="fas fa-newspaper"></i> {NEWSPAPER_NAME}</h1><p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p></div></div>
            <div class="date-header"><i class="fas fa-map-marker-alt"></i> Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
            <div class="nav">
                <a href="/"><i class="fas fa-home"></i> HOME</a>
                <a href="/news"><i class="fas fa-newspaper"></i> NEWS</a>
                <a href="/events"><i class="fas fa-calendar-alt"></i> EVENTS</a>
                <a href="/classifieds"><i class="fas fa-list"></i> CLASSIFIEDS</a>
                <a href="/business-directory"><i class="fas fa-store"></i> BUSINESSES</a>
                <a href="/foodbank"><i class="fas fa-hand-holding-heart"></i> FOOD BANK</a>
                <a href="/advertise"><i class="fas fa-bullhorn"></i> ADVERTISE</a>
                <a href="/support" style="background:#D4A017;color:#1a3d1a;padding:5px 12px;border-radius:20px;"><i class="fas fa-star"></i> SUPPORT</a>
            </div>
            {urgent_section}
            <div class="hero">
                <h2>Your Hometown, Online.</h2>
                <p>Serving Spruce Grove, Stony Plain & Parkland County</p>
                <form class="search-bar" action="/search" method="GET">
                    <input type="text" name="q" placeholder="Search news, events, businesses...">
                    <button type="submit"><i class="fas fa-search"></i> Search</button>
                </form>
            </div>
            <div class="quick-links">
                <a href="/submit-tip" class="quick-link"><i class="fas fa-lightbulb"></i> News Tip</a>
                <a href="/submit-photo" class="quick-link"><i class="fas fa-camera"></i> Share Photo</a>
                <a href="/business-directory" class="quick-link"><i class="fas fa-store"></i> Shop Local</a>
                <a href="/events" class="quick-link"><i class="fas fa-calendar-week"></i> Events</a>
                <a href="/classifieds" class="quick-link"><i class="fas fa-tags"></i> Buy & Sell</a>
            </div>
            <div class="main-content">
                <div class="stats">
                    <div class="stat-card" onclick="location.href='/news'"><i class="fas fa-newspaper"></i><div class="stat-number">{len(news_articles)}+</div><div>Local Stories</div></div>
                    <div class="stat-card" onclick="location.href='/business-directory'"><i class="fas fa-store"></i><div class="stat-number">{len(businesses)}+</div><div>Businesses</div></div>
                    <div class="stat-card" onclick="location.href='/subscribe'"><i class="fas fa-users"></i><div class="stat-number">500+</div><div>Subscribers</div></div>
                    <div class="stat-card" onclick="location.href='/events'"><i class="fas fa-calendar-alt"></i><div class="stat-number">{len(events)}+</div><div>Events</div></div>
                </div>
                
                <div class="weather-widget">
                    <div style="display:flex;justify-content:space-between">
                        <div><i class="fas fa-map-marker-alt"></i> Spruce Grove, AB</div>
                        <div class="weather-temp-large">{weather['temp']}°C</div>
                    </div>
                    <div style="text-align:center;margin:15px 0">
                        <div style="font-size:64px">{weather['icon']}</div>
                        <div class="weather-condition">{weather['condition']}</div>
                        <div>Feels like {weather['feels_like']}°C</div>
                    </div>
                    <div class="forecast-grid">{forecast_html}</div>
                </div>
                
                <div class="featured-article">
                    <div class="featured-badge"><i class="fas fa-star"></i> Welcome to {NEWSPAPER_NAME}</div>
                    <h2>Your Community Newspaper</h2>
                    <p>Welcome to The Spruce Grove Gazette - your source for local news, events, classifieds, and community information. Post your classified ads, create events, share news tips, and support local journalism.</p>
                    <a href="/subscribe" class="btn"><i class="fas fa-envelope"></i> Subscribe to Newsletter →</a>
                </div>
                
                {top_section}
                <h2 class="section-title"><i class="fas fa-building"></i> Latest News</h2>
                <div class="news-grid">{news_html}</div>
                
                <div class="two-column">
                    <div>
                        <h2 class="section-title"><i class="fas fa-list"></i> Classifieds</h2>
                        <div style="background:white;border-radius:10px;padding:25px;margin-bottom:30px">
                            {classifieds_html}
                            <div style="margin-top:15px;">
                                <a href="/classifieds" class="btn">View All →</a>
                                <a href="/post-ad" class="btn" style="background:var(--accent);color:var(--primary);margin-left:10px;">Post an Ad →</a>
                            </div>
                        </div>
                        <h2 class="section-title"><i class="fas fa-calendar-alt"></i> Upcoming Events</h2>
                        <div style="background:white;border-radius:10px;padding:25px;margin-bottom:30px">
                            <ul style="list-style:none;">{events_html}</ul>
                            <a href="/events" class="btn">View All Events →</a>
                            <a href="/events/create" class="btn" style="background:var(--accent);color:var(--primary);margin-left:10px;"><i class="fas fa-plus"></i> Create Event</a>
                        </div>
                        <h2 class="section-title"><i class="fas fa-store"></i> Local Businesses</h2>
                        <div class="business-grid">{businesses_html}</div>
                        <div style="text-align:center;"><a href="/business-directory" class="btn">View All →</a><a href="/submit-business" class="btn" style="background:var(--accent);color:var(--primary);margin-left:10px;">Add Your Business</a></div>
                    </div>
                    <div>
                        <div class="ad-spot" onclick="location.href='/advertise'">
                            <i class="fas fa-bullhorn" style="font-size:48px;color:var(--primary)"></i>
                            <h3>Advertise With Us</h3>
                            <p>Reach thousands of local readers</p>
                            <div style="font-size:28px;font-weight:bold;color:var(--accent);margin:15px 0">Starting at $100/month</div>
                            <button class="btn">Get Started →</button>
                        </div>
                    </div>
                </div>
                
                {('<h2 class="section-title"><i class="fas fa-city"></i> Edmonton Area</h2><div class="regional-grid">' + edmonton_html + '</div>') if edmonton_news else ''}
                {('<h2 class="section-title"><i class="fas fa-map"></i> Alberta</h2><div class="regional-grid">' + alberta_html + '</div>') if alberta_news else ''}

                <div class="newsletter">
                    <i class="fas fa-envelope" style="font-size:48px;margin-bottom:15px"></i>
                    <h3>✉️ Never Miss an Edition</h3>
                    <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
                    <form action="/do-subscribe" method="POST">
                        <input type="text" name="name" placeholder="Your name">
                        <input type="email" name="email" placeholder="Your email" required>
                        <select name="neighborhood">
                            <option value="">Select your neighborhood</option>
                            <option>Spruce Grove - Downtown</option>
                            <option>Spruce Grove - West</option>
                            <option>Spruce Grove - East</option>
                            <option>Parkland County</option>
                            <option>Stony Plain</option>
                        </select>
                        <button type="submit"><i class="fas fa-paper-plane"></i> Subscribe Free →</button>
                    </form>
                </div>
            </div>
            
            <div class="footer">
                <div class="footer-content">
                    <div class="footer-column">
                        <h4><i class="fas fa-newspaper"></i> The Gazette</h4>
                        <a href="/">Home</a>
                        <a href="/news">News</a>
                        <a href="/classifieds">Classifieds</a>
                        <a href="/business-directory">Business Directory</a>
                        <a href="/subscribe">Newsletter</a>
                    </div>
                    <div class="footer-column">
                        <h4><i class="fas fa-envelope"></i> Connect</h4>
                        <a href="/submit-tip">News Tip</a>
                        <a href="/submit-photo">Share Photo</a>
                        <a href="/advertise">Advertise</a>
                        <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                    </div>
                    <div class="footer-column">
                        <h4><i class="fas fa-hand-holding-heart"></i> Community</h4>
                        <a href="/foodbank">Parkland Food Bank</a>
                        <a href="/support">Become a Supporter</a>
                        <a href="/events">Community Calendar</a>
                    </div>
                    <div class="footer-column">
                        <h4><i class="fas fa-map-marked-alt"></i> Our Region</h4>
                        <a href="#">Spruce Grove</a>
                        <a href="#">Parkland County</a>
                        <a href="#">Stony Plain</a>
                    </div>
                </div>
                <div class="copyright"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
            </div>
            <button class="dark-mode-toggle" onclick="toggleDarkMode()"><i class="fas fa-moon"></i> Dark Mode</button>
            <script>
                function toggleDarkMode() {{
                    document.body.classList.toggle('dark-mode');
                    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
                }}
                if(localStorage.getItem('darkMode') === 'true') {{
                    document.body.classList.add('dark-mode');
                }}
            </script>
        </body>
        </html>
        '''
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1><pre>{traceback.format_exc()}</pre>", 500

# ============= REMAINING ROUTES =============

@app.route('/news')
def news_index():
    articles = get_news_articles(50)
    articles_html = ""
    if articles:
        for a in articles:
            articles_html += f'''
            <div class="news-article">
                <a href="/category/{a['category']}" class="article-category">{a["category"]}</a>
                <h2><a href="/article/{a["id"]}">{a["title"]}</a></h2>
                <div class="article-meta"><i class="fas fa-calendar-alt"></i> {str(a["date"])[:10] if a["date"] else "Recent"} | <i class="fas fa-newspaper"></i> {a["source"]} | <i class="fas fa-eye"></i> {a["views"]} views</div>
                <p>{a["summary"]}...</p>
                <a href="/article/{a["id"]}" class="read-more">Read Full Story →</a>
            </div>
            '''
    else:
        articles_html = '<p>No news articles yet. Check back soon!</p>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>News - {NEWSPAPER_NAME}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{{font-family:Georgia;background:#f9f9f5;margin:0}}
        .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
        .nav{{background:#2C5F2D;padding:12px;text-align:center}}
        .nav a{{color:white;margin:0 15px;text-decoration:none}}
        .container{{max-width:800px;margin:0 auto;padding:40px 20px}}
        .news-article{{background:white;border-radius:10px;padding:30px;margin-bottom:30px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}
        .article-category{{display:inline-block;background:#D4A017;color:#1a3d1a;padding:4px 12px;border-radius:15px;font-size:11px;margin-bottom:15px}}
        .article-meta{{color:#666;margin:15px 0}}
        .read-more{{color:#D4A017;font-weight:bold;text-decoration:none;display:inline-block;margin-top:15px}}
        .btn{{background:#1a3d1a;color:white;padding:12px 24px;border-radius:5px;text-decoration:none;display:inline-block}}
        .footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}}
    </style>
    </head>
    <body>
        <div class="header"><h1><i class="fas fa-newspaper"></i> Spruce Grove Gazette News</h1><p>Local news that matters to you</p></div>
        <div class="nav"><a href="/">Home</a><a href="/events">Events</a><a href="/classifieds">Classifieds</a><a href="/support">Support</a></div>
        <div class="container">
            <h1>Latest News</h1>
            {articles_html}
            <a href="/" class="btn">← Back to Home</a>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
    </body>
    </html>
    '''

@app.route('/category/<category>')
def category_page(category):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, summary, source, date, category, views FROM news_articles "
        "WHERE active = TRUE AND LOWER(category) = LOWER(%s) ORDER BY date DESC LIMIT 50",
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()

    articles_html = ""
    if rows:
        for row in rows:
            aid, title, summary, source, date, cat, views = row['id'], row['title'], row['summary'], row['source'], row['date'], row['category'], row['views']
            date_str = str(date or "")[:10] or "Recent"
            articles_html += f'''
            <div class="news-article">
                <a href="/category/{cat}" class="article-category">{cat}</a>
                <h2><a href="/article/{aid}">{title}</a></h2>
                <div class="article-meta"><i class="fas fa-calendar-alt"></i> {date_str} | <i class="fas fa-newspaper"></i> {source} | <i class="fas fa-eye"></i> {views} views</div>
                <p>{(summary or "")[:200]}...</p>
                <a href="/article/{aid}" class="read-more">Read Full Story →</a>
            </div>'''
    else:
        articles_html = f'<p>No articles in <strong>{category}</strong> yet. Check back soon!</p>'

    return f'''<!DOCTYPE html>
    <html>
    <head><title>{category} - {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{{font-family:Georgia;background:#f9f9f5;margin:0}}
        .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
        .nav{{background:#2C5F2D;padding:12px;text-align:center}}
        .nav a{{color:white;margin:0 15px;text-decoration:none}}
        .container{{max-width:800px;margin:0 auto;padding:40px 20px}}
        .news-article{{background:white;border-radius:10px;padding:30px;margin-bottom:30px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}
        .article-category{{display:inline-block;background:#D4A017;color:#1a3d1a;padding:4px 12px;border-radius:15px;font-size:11px;margin-bottom:15px;text-decoration:none}}
        .article-meta{{color:#666;margin:15px 0}}
        .read-more{{color:#D4A017;font-weight:bold;text-decoration:none;display:inline-block;margin-top:15px}}
        .btn{{background:#1a3d1a;color:white;padding:12px 24px;border-radius:5px;text-decoration:none;display:inline-block}}
        .footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}}
    </style>
    </head>
    <body>
        <div class="header"><h1><i class="fas fa-tag"></i> {category}</h1><p>All {category} stories from the Spruce Grove Gazette</p></div>
        <div class="nav"><a href="/">Home</a><a href="/news">All News</a><a href="/events">Events</a><a href="/classifieds">Classifieds</a></div>
        <div class="container">
            <h1>{category} Stories</h1>
            {articles_html}
            <a href="/news" class="btn">← All News</a>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
    </body>
    </html>'''


@app.route('/article/<int:article_id>')
def article_page(article_id):
    article = get_article_by_id(article_id)
    if not article:
        return redirect('/news')

    paragraphs = (article['content'] or '').split('\n\n')
    formatted_content = ''.join([f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs if p.strip()])

    label = article.get('source_label') or 'Staff'
    label_colors = {'Official': '#3498db', 'Media': '#7f8c8d', 'AI Draft': '#9b59b6', 'Staff': '#2ecc71'}
    label_color = label_colors.get(label, '#2ecc71')

    original_btn = ''
    if article.get('url'):
        original_btn = f'<a href="{article["url"]}" target="_blank" rel="noopener" class="btn-original"><i class="fas fa-external-link-alt"></i> Read Full Article at {article["source"]}</a>'

    correction_banner = ''
    if article.get('correction'):
        correction_banner = f'<div class="correction-banner"><strong>Correction:</strong> {article["correction"]}</div>'

    urgent_banner = '<div class="urgent-article-banner"><i class="fas fa-exclamation-triangle"></i> Breaking News</div>' if article.get('urgent') else ''

    return f'''<!DOCTYPE html>
    <html>
    <head><title>{article["title"]} – {NEWSPAPER_NAME}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{{font-family:Georgia,serif;background:#f9f9f5;margin:0}}
        .header{{background:#1a3d1a;color:white;padding:20px;text-align:center}}
        .nav{{background:#2C5F2D;padding:12px;text-align:center}}
        .nav a{{color:white;margin:0 15px;text-decoration:none;font-size:13px}}
        .nav a:hover{{color:#D4A017}}
        .container{{max-width:780px;margin:30px auto;padding:0 20px}}
        .article-card{{background:white;border-radius:12px;padding:40px;box-shadow:0 4px 15px rgba(0,0,0,.1)}}
        .urgent-article-banner{{background:#c0392b;color:white;padding:10px 16px;border-radius:6px;margin-bottom:16px;font-weight:bold;font-size:13px}}
        .correction-banner{{background:#fff3cd;border-left:4px solid #ffc107;padding:12px 16px;margin-bottom:16px;border-radius:0 6px 6px 0;font-size:14px}}
        .badges{{display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap}}
        .badge-cat{{background:#1a3d1a;color:white;padding:3px 12px;border-radius:12px;font-size:11px;text-decoration:none}}
        .badge-cat:hover{{background:#2C5F2D}}
        .badge-label{{padding:3px 10px;border-radius:12px;font-size:10px;font-weight:bold;color:white}}
        h1{{font-size:28px;color:#1a3d1a;margin:0 0 16px;line-height:1.3}}
        .article-meta{{color:#888;font-size:13px;border-bottom:1px solid #eee;padding-bottom:14px;margin-bottom:24px}}
        .article-meta span{{margin-right:14px}}
        .article-content{{line-height:1.9;font-size:17px;color:#333}}
        .article-content p{{margin-bottom:18px}}
        .btn-original{{display:block;background:#D4A017;color:#1a3d1a;padding:14px 24px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:15px;text-align:center;margin:28px 0 10px;transition:background .2s}}
        .btn-original:hover{{background:#c49015}}
        .btn-back{{color:#1a3d1a;text-decoration:none;font-size:14px;display:inline-block;margin-top:10px}}
        .btn-back:hover{{text-decoration:underline}}
        .source-note{{background:#f0f0e8;border-radius:8px;padding:14px;font-size:13px;color:#666;margin-top:20px}}
        .footer{{background:#0d260d;color:white;text-align:center;padding:24px;margin-top:40px;font-size:13px}}
        @media(max-width:600px){{.article-card{{padding:24px}}h1{{font-size:22px}}}}
    </style>
    </head>
    <body>
    <div class="header"><h1 style="font-size:22px;margin:0">{NEWSPAPER_NAME}</h1></div>
    <div class="nav">
        <a href="/"><i class="fas fa-home"></i> Home</a>
        <a href="/news"><i class="fas fa-newspaper"></i> News</a>
        <a href="/events"><i class="fas fa-calendar"></i> Events</a>
        <a href="/classifieds"><i class="fas fa-list"></i> Classifieds</a>
    </div>
    <div class="container">
        <div class="article-card">
            {urgent_banner}
            {correction_banner}
            <div class="badges">
                <a href="/category/{article["category"] or "News"}" class="badge-cat">{article["category"] or "News"}</a>
                <span class="badge-label" style="background:{label_color}">{label}</span>
            </div>
            <h1>{article["title"]}</h1>
            <div class="article-meta">
                <span><i class="fas fa-calendar-alt"></i> {str(article["date"])[:10] if article["date"] else "Recent"}</span>
                <span><i class="fas fa-newspaper"></i> {article["source"]}</span>
                <span><i class="fas fa-eye"></i> {article["views"]} views</span>
            </div>
            {original_btn}
            <div class="article-content">{formatted_content}</div>
            {original_btn}
            <div class="source-note">
                <i class="fas fa-info-circle"></i>
                This is a summary. For the complete story, use the button above to read the full article at <strong>{article["source"]}</strong>.
            </div>
            <a href="/news" class="btn-back"><i class="fas fa-arrow-left"></i> Back to News</a>
        </div>
    </div>
    <div class="footer">© {datetime.now().year} {NEWSPAPER_NAME}</div>
    </body></html>'''

@app.route('/events')
def events_list():
    events = get_events(50)
    events_html = ""
    if events:
        for e in events:
            events_html += f'''
            <div class="event-card">
                <h2>{e["title"]}</h2>
                <p>{e["description"]}</p>
                <div class="event-details">
                    <p><i class="fas fa-calendar-alt"></i> <strong>Date:</strong> {e["date"]} at {e["time"]}</p>
                    <p><i class="fas fa-map-marker-alt"></i> <strong>Location:</strong> {e["location"]}</p>
                    <p><i class="fas fa-ticket-alt"></i> <strong>Tickets:</strong> {e["ticket_price"] if e["ticket_price"] else "Free"}</p>
                </div>
            </div>
            '''
    else:
        events_html = '<p>No upcoming events. <a href="/events/create">Create one!</a></p>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Events - {NEWSPAPER_NAME}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{{font-family:Georgia;background:#f9f9f5;margin:0}}
        .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
        .nav{{background:#2C5F2D;padding:12px;text-align:center}}
        .nav a{{color:white;margin:0 15px;text-decoration:none}}
        .container{{max-width:800px;margin:0 auto;padding:40px 20px}}
        .event-card{{background:white;border-radius:10px;padding:25px;margin-bottom:25px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}
        .event-details{{margin:15px 0;padding:10px 0;border-top:1px solid #eee;border-bottom:1px solid #eee}}
        .event-details i{{color:#D4A017;width:25px}}
        .btn{{background:#1a3d1a;color:white;padding:12px 24px;border-radius:5px;text-decoration:none;display:inline-block}}
        .btn-accent{{background:#D4A017;color:#1a3d1a}}
        .footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}}
    </style>
    </head>
    <body>
        <div class="header"><h1><i class="fas fa-calendar-alt"></i> Community Events Calendar</h1><p>Discover what's happening in Spruce Grove and Parkland County</p></div>
        <div class="nav"><a href="/">Home</a><a href="/news">News</a><a href="/classifieds">Classifieds</a><a href="/foodbank">Food Bank</a></div>
        <div class="container">
            <h1>Upcoming Events</h1>
            {events_html}
            <div style="text-align:center;margin-top:30px">
                <a href="/events/create" class="btn btn-accent"><i class="fas fa-plus"></i> Create Event</a>
                <a href="/" class="btn">← Back to Home</a>
            </div>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME}</p></div>
    </body>
    </html>
    '''

@app.route('/events/create', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO events (title, description, date, time, location, ticket_price,
                        total_tickets, organizer, email, date_submitted, approved)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)''',
                      (request.form.get('title'), request.form.get('description'), request.form.get('date'),
                       request.form.get('time'), request.form.get('location'), request.form.get('ticket_price', 'Free'),
                       request.form.get('total_tickets'), request.form.get('organizer'), request.form.get('email'), date.today()))
        conn.commit()
        conn.close()
        return '<h1>✅ Event Created Successfully!</h1><a href="/events">View Events →</a> <a href="/">Back to Home</a>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Create Event</title><style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:10px}input,textarea{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px}button{background:#1a3d1a;color:white;padding:12px;border:none;border-radius:5px;cursor:pointer;width:100%}</style></head>
    <body><div class="container"><h1><i class="fas fa-calendar-plus"></i> Create an Event</h1><form method="POST"><input type="text" name="title" placeholder="Event Title" required><textarea name="description" rows="4" placeholder="Description" required></textarea><input type="date" name="date" required><input type="text" name="time" placeholder="Time (e.g., 7 PM)" required><input type="text" name="location" placeholder="Location" required><input type="text" name="ticket_price" placeholder="Ticket price (or 'Free')"><input type="number" name="total_tickets" placeholder="Total tickets"><input type="text" name="organizer" placeholder="Organizer"><input type="email" name="email" placeholder="Contact email"><button type="submit">Create Event →</button></form><a href="/events">← Back to Events</a></div></body></html>
    '''

@app.route('/classifieds')
def classifieds():
    category = request.args.get('category', 'all')
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()

    category_map = {'jobs': 'Jobs', 'for-sale': 'For Sale', 'housing': 'Housing', 'services': 'Services', 'garage': 'Garage Sale'}

    if category != 'all' and category in category_map:
        cursor.execute("SELECT id, title, description, price, contact, date, category FROM classifieds WHERE active = TRUE AND expiry_date >= %s AND category = %s ORDER BY date DESC", (today, category_map[category]))
    else:
        cursor.execute("SELECT id, title, description, price, contact, date, category FROM classifieds WHERE active = TRUE AND expiry_date >= %s ORDER BY date DESC", (today,))

    items = cursor.fetchall()
    conn.close()
    
    category_titles = {
        'jobs': '💼 Job Opportunities',
        'for-sale': '🏷️ Items For Sale', 
        'housing': '🏠 Housing & Real Estate',
        'services': '🔧 Local Services',
        'garage': '🏪 Garage & Yard Sales',
        'all': '📋 All Classifieds'
    }
    current_title = category_titles.get(category, '📋 All Classifieds')
    
    classifieds_html = ""
    if items:
        for item in items:
            price = f'${item["price"]}' if item["price"] and item["price"].isdigit() else (item["price"] if item["price"] else "Call for price")
            category_icon = {'Jobs':'💼','For Sale':'🏷️','Housing':'🏠','Services':'🔧','Garage Sale':'🏪'}.get(item["category"] or '', '📋')
            classifieds_html += f'''
            <div class="classified-card">
                <div class="classified-badge">{category_icon} {item["category"] or "General"}</div>
                <h3>{item["title"]}</h3>
                <div class="classified-price">{price}</div>
                <p>{item["description"][:150]}...</p>
                <div class="classified-contact"><i class="fas fa-user"></i> {item["contact"]} | <i class="fas fa-calendar"></i> {item["date"]}</div>
                <a href="/classified/{item["id"]}" class="btn-small">View Details →</a>
            </div>
            '''
    else:
        classifieds_html = '<p style="text-align:center;padding:40px">No classifieds found. <a href="/post-ad">Post an Ad →</a></p>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Classifieds - {current_title}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{{font-family:Georgia;background:#f9f9f5;margin:0}}
        .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
        .nav{{background:#2C5F2D;padding:12px;text-align:center}}
        .nav a{{color:white;margin:0 15px;text-decoration:none;font-size:14px}}
        .nav a:hover{{color:#D4A017}}
        .container{{max-width:1200px;margin:0 auto;padding:40px 20px}}
        .category-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:40px}}
        .cat-card{{background:white;border-radius:15px;padding:30px 20px;text-align:center;text-decoration:none;color:#1a3d1a;box-shadow:0 4px 12px rgba(0,0,0,0.08);transition:all 0.3s;border:2px solid transparent}}
        .cat-card:hover{{transform:translateY(-4px);border-color:#D4A017;box-shadow:0 8px 24px rgba(0,0,0,0.12)}}
        .cat-card.active{{border-color:#1a3d1a;background:#1a3d1a;color:white}}
        .cat-card.active .cat-icon{{color:#D4A017}}
        .cat-icon{{font-size:36px;margin-bottom:12px;display:block;color:#D4A017}}
        .cat-card h3{{margin:0 0 6px;font-size:16px;font-weight:bold}}
        .cat-card p{{margin:0;font-size:12px;color:#888}}
        .cat-card.active p{{color:#ccc}}
        .classifieds-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px;margin-top:30px}}
        .classified-card{{background:white;border-radius:12px;padding:22px;transition:all 0.3s;box-shadow:0 2px 10px rgba(0,0,0,0.08)}}
        .classified-card:hover{{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,0.12)}}
        .classified-badge{{display:inline-block;background:#D4A017;color:#1a3d1a;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:bold;margin-bottom:10px}}
        .classified-price{{font-size:22px;color:#D4A017;font-weight:bold;margin:10px 0}}
        .classified-contact{{color:#888;font-size:12px;margin:10px 0}}
        .btn-small{{background:#1a3d1a;color:white;padding:8px 18px;border-radius:5px;text-decoration:none;display:inline-block;margin-top:10px;font-size:13px}}
        .btn-small:hover{{background:#0d260d}}
        .btn{{background:#1a3d1a;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;font-size:15px}}
        .btn:hover{{background:#0d260d}}
        .publish-btn{{background:#D4A017;color:#1a3d1a}}
        .publish-btn:hover{{background:#c49015}}
        .section-title{{font-size:22px;font-weight:bold;color:#1a3d1a;border-left:4px solid #D4A017;padding-left:12px;margin:30px 0 20px}}
        .footer{{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}}
        @media(max-width:768px){{.classifieds-grid{{grid-template-columns:1fr}}.category-grid{{grid-template-columns:repeat(2,1fr)}}}}
    </style>
    </head>
    <body>
        <div class="header"><h1><i class="fas fa-list"></i> Classifieds</h1><p>Buy, Sell & Connect in Spruce Grove</p></div>
        <div class="nav">
            <a href="/"><i class="fas fa-home"></i> Home</a>
            <a href="/classifieds"><i class="fas fa-list"></i> All Classifieds</a>
            <a href="/post-ad"><i class="fas fa-plus-circle"></i> Post Free Ad</a>
            <a href="/news"><i class="fas fa-newspaper"></i> News</a>
            <a href="/events"><i class="fas fa-calendar-alt"></i> Events</a>
        </div>
        <div class="container">
            <div class="section-title"><i class="fas fa-th-large"></i> Browse by Category</div>
            <div class="category-grid">
                <a href="/classifieds?category=all" class="cat-card {'active' if category == 'all' else ''}">
                    <span class="cat-icon"><i class="fas fa-border-all"></i></span>
                    <h3>All Listings</h3><p>Browse everything</p>
                </a>
                <a href="/classifieds?category=jobs" class="cat-card {'active' if category == 'jobs' else ''}">
                    <span class="cat-icon"><i class="fas fa-briefcase"></i></span>
                    <h3>Jobs</h3><p>Careers & employment</p>
                </a>
                <a href="/classifieds?category=for-sale" class="cat-card {'active' if category == 'for-sale' else ''}">
                    <span class="cat-icon"><i class="fas fa-tag"></i></span>
                    <h3>For Sale</h3><p>Furniture, vehicles & more</p>
                </a>
                <a href="/classifieds?category=housing" class="cat-card {'active' if category == 'housing' else ''}">
                    <span class="cat-icon"><i class="fas fa-home"></i></span>
                    <h3>Housing</h3><p>Rentals & real estate</p>
                </a>
                <a href="/classifieds?category=services" class="cat-card {'active' if category == 'services' else ''}">
                    <span class="cat-icon"><i class="fas fa-tools"></i></span>
                    <h3>Services</h3><p>Local trades & professionals</p>
                </a>
                <a href="/classifieds?category=garage" class="cat-card {'active' if category == 'garage' else ''}">
                    <span class="cat-icon"><i class="fas fa-warehouse"></i></span>
                    <h3>Garage Sales</h3><p>Weekend sales & deals</p>
                </a>
            </div>
            <div class="section-title"><i class="fas fa-list-ul"></i> {current_title}</div>
            <div class="classifieds-grid">
                {classifieds_html}
            </div>
            <div style="text-align:center;margin-top:40px;display:flex;justify-content:center;gap:15px;flex-wrap:wrap;">
                <a href="/post-ad" class="btn publish-btn"><i class="fas fa-plus"></i> Post a Free Ad</a>
                <a href="/" class="btn"><i class="fas fa-home"></i> Back to Home</a>
            </div>
        </div>
        <div class="footer"><p>© {datetime.now().year} {NEWSPAPER_NAME} | <a href="/advertise" style="color:#D4A017;">Advertise With Us</a></p></div>
    </body>
    </html>
    '''

@app.route('/classified/<int:id>')
def classified_detail(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, price, contact, email, phone, date, category FROM classifieds WHERE id = %s AND active = TRUE", (id,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        return redirect('/classifieds')

    category_icon = {'Jobs':'💼','For Sale':'🏷️','Housing':'🏠','Services':'🔧','Garage Sale':'🏪'}.get(item["category"] or '', '📋')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>{item["title"]} - Classified Ad</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}.container{{max-width:600px;margin:40px auto;background:white;padding:30px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}}.price{{color:#D4A017;font-size:28px;font-weight:bold;margin:20px 0}}.contact{{background:#f5f5f5;padding:20px;border-radius:8px;margin:20px 0}}.btn{{background:#1a3d1a;color:white;padding:12px 24px;border-radius:5px;text-decoration:none;display:inline-block}}.badge{{display:inline-block;background:#D4A017;color:#1a3d1a;padding:5px 15px;border-radius:20px;font-size:12px;margin-bottom:15px}}</style>
    </head>
    <body>
        <div class="container">
            <div class="badge">{category_icon} {item["category"] or "General"}</div>
            <h1>{item["title"]}</h1>
            <div class="price">{item["price"] or "Price not specified"}</div>
            <p>{item["description"]}</p>
            <div class="contact">
                <h3><i class="fas fa-address-card"></i> Contact Information</h3>
                <p><i class="fas fa-phone"></i> {item["contact"]}</p>
                <p><i class="fas fa-envelope"></i> {item["email"] or "Not provided"}</p>
                <p><i class="fas fa-mobile-alt"></i> {item["phone"] or "Not provided"}</p>
            </div>
            <a href="/classifieds" class="btn"><i class="fas fa-arrow-left"></i> Back to Classifieds</a>
        </div>
    </body>
    </html>
    '''

@app.route('/post-ad', methods=['GET', 'POST'])
def post_ad():
    if request.method == 'POST':
        expiry_date = date.today() + timedelta(days=30)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO classifieds (category, title, description, price, contact, email, phone, date, expiry_date, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)''',
                      (request.form.get('category'), request.form.get('title'), request.form.get('description'),
                       request.form.get('price'), request.form.get('contact'), request.form.get('email'),
                       request.form.get('phone'), date.today(), expiry_date))
        conn.commit()
        conn.close()
        return '<h1>✅ Ad Posted! Expires in 30 days.</h1><a href="/classifieds">View Classifieds</a>'
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Post a Free Ad</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>body{font-family:Georgia;background:#f9f9f5;padding:40px}.container{max-width:600px;margin:0 auto;background:white;padding:40px;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}h1{color:#1a3d1a}input,select,textarea{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:8px;font-family:Georgia}button{background:#1a3d1a;color:white;padding:14px;border:none;border-radius:8px;cursor:pointer;font-size:16px;width:100%}.note{background:#f0f0e8;padding:15px;border-radius:8px;margin:20px 0}</style></head>
    <body><div class="container"><h1><i class="fas fa-plus-circle"></i> Post a Free Classified Ad</h1><p>Reach thousands of readers in Spruce Grove and Parkland County</p>
    <form method="POST"><select name="category" required><option value="">Select Category</option><option value="Jobs">💼 Jobs</option><option value="For Sale">🏷️ For Sale</option><option value="Housing">🏠 Housing</option><option value="Services">🔧 Services</option><option value="Garage Sale">🏪 Garage Sale</option></select>
    <input name="title" placeholder="Ad Title" required><textarea name="description" rows="5" placeholder="Description" required></textarea>
    <input name="price" placeholder="Price (e.g., $500 or OBO)"><input name="contact" placeholder="Contact info (phone or email)" required>
    <input name="email" placeholder="Email (optional)"><input name="phone" placeholder="Phone (optional)">
    <button type="submit"><i class="fas fa-paper-plane"></i> Post Ad →</button></form>
    <div class="note"><i class="fas fa-info-circle"></i> Your ad will be active for 30 days. You can renew it for free.</div>
    <a href="/classifieds"><i class="fas fa-arrow-left"></i> Back to Classifieds</a></div></body></html>
    '''

@app.route('/foodbank')
def foodbank():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Parkland Food Bank - Support Our Community</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{font-family:Georgia;background:#f9f9f5;margin:0}
        .header{background:#1a3d1a;color:white;padding:40px;text-align:center}
        .nav{background:#2C5F2D;padding:12px;text-align:center}
        .nav a{color:white;margin:0 15px;text-decoration:none}
        .stats-bar{background:#e74c3c;color:white;padding:30px;display:flex;justify-content:space-around;flex-wrap:wrap}
        .stat-number{font-size:48px;font-weight:bold}
        .container{max-width:1000px;margin:0 auto;padding:40px 20px}
        .help-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin:30px 0}
        .help-card{background:white;text-align:center;padding:40px;border-radius:15px;transition:all 0.3s;box-shadow:0 4px 15px rgba(0,0,0,0.1)}
        .help-card:hover{transform:translateY(-5px)}
        .help-card i{font-size:48px;color:#e74c3c;margin-bottom:15px}
        .info-section{background:white;border-radius:15px;padding:30px;margin:30px 0}
        .wishlist{background:#fdf0e6;border-left:4px solid #e74c3c;padding:20px;margin:20px 0}
        .btn{background:#1a3d1a;color:white;padding:12px 30px;border-radius:5px;text-decoration:none;display:inline-block;margin:10px}
        .btn-orange{background:#e74c3c}
        .footer{background:#0d260d;color:white;text-align:center;padding:30px;margin-top:40px}
        @media(max-width:768px){.help-grid{grid-template-columns:1fr}}
    </style>
    </head>
    <body>
        <div class="header"><h1><i class="fas fa-hand-holding-heart"></i> Parkland Food Bank</h1><p>Nourishing Our Community Since 1984</p></div>
        <div class="nav"><a href="/">Home</a><a href="/news">News</a><a href="/events">Events</a><a href="/support">Support</a></div>
        <div class="stats-bar">
            <div><div class="stat-number">40+</div>Years of Service</div>
            <div><div class="stat-number">5,634</div>Individuals Served</div>
            <div><div class="stat-number">31,945</div>Hampers Distributed</div>
            <div><div class="stat-number">15%</div>Increase in Need</div>
        </div>
        <div class="container">
            <div class="help-grid">
                <div class="help-card"><i class="fas fa-apple-alt"></i><h3>Donate Food</h3><p>Drop off non-perishable food items</p><p><strong>105 Madison Crescent<br>Spruce Grove, AB</strong></p><p>Mon-Fri: 9AM-4PM</p><a href="https://maps.google.com/?q=105+Madison+Crescent+Spruce+Grove" target="_blank" class="btn"><i class="fas fa-map-marker-alt"></i> Get Directions</a></div>
                <div class="help-card"><i class="fas fa-dollar-sign"></i><h3>Make a Donation</h3><p>Every dollar helps provide meals for families in need</p><p><strong>Tax receipts issued for donations over $20</strong></p><a href="https://parklandfoodbank.org/donate" target="_blank" class="btn btn-orange"><i class="fas fa-external-link-alt"></i> Donate Online</a></div>
                <div class="help-card"><i class="fas fa-hands-helping"></i><h3>Volunteer</h3><p>Help sort food, pack hampers, or deliver to those in need</p><p><strong>Call 780-962-4565</strong></p><a href="https://parklandfoodbank.org/volunteer" target="_blank" class="btn"><i class="fas fa-calendar-alt"></i> Sign Up to Volunteer</a></div>
            </div>
            <div class="info-section">
                <h2><i class="fas fa-info-circle"></i> About Parkland Food Bank</h2>
                <p>The Parkland Food Bank has been serving Spruce Grove, Stony Plain, and Parkland County for over 40 years. We provide emergency food assistance to individuals and families in need, regardless of circumstances.</p>
                <p><strong>📞 Phone:</strong> 780-962-4565<br><strong>📧 Email:</strong> info@parklandfoodbank.org<br><strong>📍 Address:</strong> 105 Madison Crescent, Spruce Grove, AB T7X 1E5</p>
                <p><strong>⏰ Hours:</strong> Monday to Friday, 9:00 AM - 4:00 PM</p>
            </div>
            <div class="wishlist">
                <h3><i class="fas fa-list"></i> Most Needed Food Items</h3>
                <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-top:15px">
                    <div>🥫 Canned vegetables</div><div>🍝 Pasta and sauce</div>
                    <div>🥫 Canned fruits</div><div>🍚 Rice and grains</div>
                    <div>🥫 Canned soup</div><div>🥜 Peanut butter</div>
                    <div>🥫 Canned beans</div><div>🍼 Baby formula</div>
                    <div>🛢️ Cooking oil</div><div>🧸 Toiletries</div>
                    <div>🥣 Cereal</div><div>🥛 Powdered milk</div>
                </div>
            </div>
            <div style="text-align:center; margin-top:30px">
                <a href="https://parklandfoodbank.org" target="_blank" class="btn btn-orange"><i class="fas fa-external-link-alt"></i> Visit Official Website</a>
                <a href="/" class="btn"><i class="fas fa-arrow-left"></i> Back to Gazette</a>
            </div>
        </div>
        <div class="footer"><p>© 2026 The Spruce Grove Gazette | Supporting Parkland Food Bank</p></div>
    </body>
    </html>
    '''

@app.route('/support')
def support():
    return _support_html().replace('__PAYPAL_CLIENT_ID__', PAYPAL_CLIENT_ID)

def _support_html():
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
            .pricing-card { background: white; border-radius: 15px; padding: 35px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s; position: relative; }
            .pricing-card:hover { transform: translateY(-5px); }
            .pricing-card.featured { border: 2px solid var(--accent); }
            .pricing-card.donation-card { border: 2px solid var(--donate); background: linear-gradient(135deg, white, #fff5f5); }
            .popular-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--accent); color: var(--primary); padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: bold; white-space: nowrap; }
            .donation-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--donate); color: white; padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: bold; white-space: nowrap; }
            .price { font-size: 48px; font-weight: bold; color: var(--primary); margin: 20px 0; }
            .price small { font-size: 16px; font-weight: normal; color: #666; }
            .features { list-style: none; padding: 0; text-align: left; margin: 25px 0; }
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
        <script src="https://www.paypal.com/sdk/js?client-id=__PAYPAL_CLIENT_ID__&currency=CAD"></script>
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
                    <a href="/subscribe" class="btn">Subscribe Free →</a>
                </div>
                <div class="pricing-card">
                    <h3>Monthly Supporter</h3>
                    <div class="price">$5<small>/month</small></div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> All free features</li>
                        <li><i class="fas fa-check"></i> Supporter badge</li>
                        <li><i class="fas fa-check"></i> Weekly exclusive content</li>
                        <li><i class="fas fa-check"></i> Behind-the-scenes updates</li>
                    </ul>
                    <a href="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-8WS19802N5406432ENHWAJVY"
                       target="_blank" class="btn" style="background:#0070ba;margin-top:15px;">
                        <img src="https://www.paypalobjects.com/webstatic/en_US/i/buttons/PP_logo_h_100x26.png" alt="PayPal" style="height:18px;vertical-align:middle;margin-right:6px;">Subscribe $5/mo
                    </a>
                </div>
                <div class="pricing-card donation-card">
                    <div class="donation-badge">❤️ MAKE A DONATION</div>
                    <h3>Support Local Journalism</h3>
                    <div class="price">$<span id="customAmountDisplay">10</span><small>/one-time</small></div>
                    <div class="custom-amount">
                        <input type="number" id="customAmount" min="5" max="1000" step="5" value="10">
                        <div style="font-size:12px;color:#666;">CAD $5 - $1000</div>
                    </div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> Choose your own amount</li>
                        <li><i class="fas fa-check"></i> One-time donation</li>
                        <li><i class="fas fa-check"></i> Supporter recognition</li>
                        <li><i class="fas fa-check"></i> Tax receipt over $20</li>
                    </ul>
                    <div id="customPaypalContainer"></div>
                </div>
                <div class="pricing-card featured">
                    <div class="popular-badge">⭐ BEST VALUE</div>
                    <h3>Yearly Supporter</h3>
                    <div class="price">$50<small>/year</small></div>
                    <div style="font-size:14px;color:#666;margin-top:-15px;">Save $10 vs monthly</div>
                    <ul class="features">
                        <li><i class="fas fa-check"></i> All monthly benefits</li>
                        <li><i class="fas fa-check"></i> Name in supporter roll</li>
                        <li><i class="fas fa-check"></i> Gazette merch discount</li>
                        <li><i class="fas fa-check"></i> Annual supporter event</li>
                        <li><i class="fas fa-check"></i> Input on coverage priorities</li>
                    </ul>
                    <a href="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-9BL3287175752125FNHWAKYY"
                       target="_blank" class="btn" style="background:#0070ba;margin-top:15px;">
                        <img src="https://www.paypalobjects.com/webstatic/en_US/i/buttons/PP_logo_h_100x26.png" alt="PayPal" style="height:18px;vertical-align:middle;margin-right:6px;">Subscribe $50/yr
                    </a>
                </div>
            </div>
            <div class="impact-section">
                <h2>Your Support Makes a Difference</h2>
                <div class="impact-grid">
                    <div class="impact-card"><i class="fas fa-newspaper"></i><h3>$10</h3><p>Funds one day of local news coverage</p></div>
                    <div class="impact-card"><i class="fas fa-camera"></i><h3>$25</h3><p>Supports community photo submissions for a week</p></div>
                    <div class="impact-card"><i class="fas fa-mobile-alt"></i><h3>$50</h3><p>Keeps the Gazette free for everyone for one month</p></div>
                </div>
            </div>
            <div style="text-align:center;margin-top:30px;padding:20px;background:#e8f5e9;border-radius:10px;">
                <i class="fas fa-lock" style="margin-right:10px;"></i>
                <strong>Secure payments by PayPal</strong> — Your payment information is encrypted and never stored on our servers.
                <br><small>You can cancel your subscription anytime from your PayPal account.</small>
                <br><br><i class="fas fa-receipt"></i> <strong>Tax receipts available for donations over $20</strong>
            </div>
        </div>
        <div class="footer">
            <p><a href="/" style="color:white;">← Back to Home</a></p>
            <p>© 2026 The Spruce Grove Gazette | Serving Spruce Grove & Parkland County</p>
        </div>
        <script>
            const customInput = document.getElementById('customAmount');
            const displaySpan = document.getElementById('customAmountDisplay');
            customInput.addEventListener('input', function() { displaySpan.innerText = customInput.value; renderCustomPaypalButton(); });
            function renderCustomPaypalButton() {
                const amount = parseFloat(customInput.value);
                const container = document.getElementById('customPaypalContainer');
                if (container) {
                    container.innerHTML = '';
                    paypal.Buttons({
                        style: { shape: 'rect', color: 'gold', layout: 'vertical', label: 'paypal', height: 40 },
                        createOrder: function(data, actions) {
                            return actions.order.create({ purchase_units: [{ amount: { value: amount.toFixed(2), currency_code: 'CAD' }, description: 'Gazette Supporter Donation' }] });
                        },
                        onApprove: function(data, actions) {
                            return actions.order.capture().then(function(details) { alert('Thank you for your $' + amount.toFixed(2) + ' donation!'); window.location.href = '/support-thank-you'; });
                        },
                        onError: function(err) { console.error(err); alert('Payment failed. Please try again.'); }
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
    <head><title>Thank You! - Spruce Grove Gazette</title></head>
    <body style="font-family:Georgia;text-align:center;padding:50px;background:#f9f9f5;">
        <h1 style="color:#1a3d1a;">🎉 Thank You for Your Support!</h1>
        <p>You are now an official Spruce Grove Gazette Supporter.</p>
        <p>Your contribution helps keep local journalism alive in Spruce Grove and Parkland County.</p>
        <p>You'll receive a confirmation email shortly.</p>
        <a href="/" style="color:#1a3d1a;font-weight:bold;">← Back to Gazette</a>
    </body>
    </html>
    '''

@app.route('/advertise')
def advertise():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Advertise With Us - Spruce Grove Gazette</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body { font-family: Georgia; background: #f9f9f5; margin: 0; }
            .header { background: #1a3d1a; color: white; padding: 40px; text-align: center; }
            .header h1 { margin: 0; font-size: 36px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
            .stats-banner { background: white; border-radius: 15px; padding: 30px; text-align: center; margin-bottom: 50px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            .stat-grid { display: flex; justify-content: center; gap: 50px; flex-wrap: wrap; }
            .stat-number { font-size: 42px; font-weight: bold; color: #D4A017; }
            .package-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin: 50px 0; }
            .package-card { background: white; border-radius: 15px; padding: 35px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.08); position: relative; }
            .package-card.featured { border: 2px solid #D4A017; }
            .popular-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #D4A017; color: #1a3d1a; padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: bold; white-space: nowrap; }
            .package-price { font-size: 36px; font-weight: bold; color: #D4A017; margin: 20px 0; }
            .btn-inquire { background: #1a3d1a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 15px; }
            .btn-inquire:hover { background: #0d260d; }
            .contact-form { background: white; border-radius: 15px; padding: 40px; margin: 50px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            .contact-form h3 { color: #1a3d1a; margin-top: 0; }
            input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-family: Georgia; }
            button[type=submit] { background: #1a3d1a; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button[type=submit]:hover { background: #0d260d; }
            .footer { background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }
            @media (max-width: 768px) { .package-grid { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <div class="header"><h1>📰 Advertise With The Gazette</h1><p>Reach thousands of local Spruce Grove readers</p></div>
        <div class="container">
            <div class="stats-banner">
                <div class="stat-grid">
                    <div><div class="stat-number">10,000+</div>Monthly Readers</div>
                    <div><div class="stat-number">500+</div>Newsletter Subscribers</div>
                    <div><div class="stat-number">100%</div>Local Audience</div>
                </div>
            </div>
            <div class="package-grid">
                <div class="package-card">
                    <h3>Digital Display</h3>
                    <div class="package-price">$100<span style="font-size:14px;color:#666;">/month</span></div>
                    <p>Banner ad prominently placed on the homepage, seen by every visitor.</p>
                    <a href="/inquire?package=Digital+Display+Ad" class="btn-inquire">Get Started →</a>
                </div>
                <div class="package-card featured">
                    <div class="popular-badge">MOST POPULAR</div>
                    <h3>Sponsored Article</h3>
                    <div class="package-price">$200<span style="font-size:14px;color:#666;">/article</span></div>
                    <p>A professionally written feature story about your business, published as editorial content.</p>
                    <a href="/inquire?package=Sponsored+Article" class="btn-inquire">Get Started →</a>
                </div>
                <div class="package-card">
                    <h3>Community Spotlight</h3>
                    <div class="package-price">$300<span style="font-size:14px;color:#666;">/month</span></div>
                    <p>Weekly featured business highlight across all Gazette channels and newsletter.</p>
                    <a href="/inquire?package=Community+Spotlight" class="btn-inquire">Get Started →</a>
                </div>
            </div>
            <div class="contact-form">
                <h3><i class="fas fa-envelope" style="color:#D4A017;margin-right:10px;"></i>Request a Media Kit</h3>
                <form action="/inquire" method="POST">
                    <input type="text" name="business_name" placeholder="Business Name" required>
                    <input type="text" name="contact_name" placeholder="Your Name" required>
                    <input type="email" name="email" placeholder="Email Address" required>
                    <input type="tel" name="phone" placeholder="Phone Number">
                    <select name="package_interest">
                        <option value="">I\'m interested in...</option>
                        <option>Digital Display Ad</option>
                        <option>Sponsored Article</option>
                        <option>Community Spotlight</option>
                        <option>Other / Not sure yet</option>
                    </select>
                    <textarea name="message" rows="4" placeholder="Tell us about your business and advertising goals..."></textarea>
                    <button type="submit">Send Inquiry →</button>
                </form>
            </div>
        </div>
        <div class="footer"><p><a href="/" style="color:white;">← Back to Home</a> | <a href="/support" style="color:#D4A017;">Support the Gazette</a></p></div>
    </body>
    </html>
    '''

@app.route('/inquire', methods=['GET', 'POST'])
def inquire():
    package = request.args.get('package', '')
    if request.method == 'POST':
        business_name = request.form.get('business_name', '')
        contact_name = request.form.get('contact_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        package_interest = request.form.get('package_interest', '')
        message = request.form.get('message', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO ad_inquiries
            (business_name, contact_name, email, phone, package_interest, message, date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (business_name, contact_name, email, phone, package_interest, message, datetime.now().date(), 'new'))
        conn.commit()
        conn.close()
        return '''<html><body style="font-family:Georgia;text-align:center;padding:50px;background:#f9f9f5;">
            <h1 style="color:#1a3d1a;">✅ Inquiry Received!</h1>
            <p>Thank you for your interest in advertising with the Spruce Grove Gazette.</p>
            <p>We'll be in touch within 1-2 business days.</p>
            <a href="/" style="color:#1a3d1a;font-weight:bold;">← Back to Home</a>
        </body></html>'''
    return redirect(f'/advertise?package={package}')

@app.route('/subscribe')
def subscribe():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Subscribe - Spruce Grove Gazette</title>
        <style>
            body { font-family: Georgia; background: #f9f9f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .container { background: white; padding: 50px 40px; border-radius: 15px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
            h1 { color: #1a3d1a; margin-top: 0; }
            p { color: #666; }
            input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-family: Georgia; font-size: 15px; }
            button { background: #1a3d1a; color: white; padding: 14px 30px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; margin-top: 10px; }
            button:hover { background: #0d260d; }
            .back { display: block; margin-top: 20px; color: #1a3d1a; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to the Gazette</h1>
            <p>Get Spruce Grove news delivered to your inbox — free, twice a week.</p>
            <form action="/do-subscribe" method="POST">
                <input type="text" name="name" placeholder="Your Name" required>
                <input type="email" name="email" placeholder="Your Email Address" required>
                <button type="submit">📩 Subscribe Now</button>
            </form>
            <a href="/" class="back">← Back to Home</a>
        </div>
    </body>
    </html>'''

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    if not name or not email:
        return redirect('/subscribe')
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO subscribers (name, email, subscribed_date) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING",
                       (name, email, datetime.now().date().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Subscribe error: {e}")
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Subscribed!</title>
    <style>body{{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}}
    .box{{background:white;padding:50px 40px;border-radius:15px;max-width:450px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);}}</style>
    </head><body><div class="box">
    <h1 style="color:#1a3d1a;">✅ You're subscribed!</h1>
    <p>Welcome, {name}! You'll receive Spruce Grove news at <strong>{email}</strong>.</p>
    <a href="/" style="color:#1a3d1a;font-weight:bold;">← Back to Home</a>
    </div></body></html>'''

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        conn = get_db()
        cursor = conn.cursor()
        try:
            # Full-text search via tsvector index; fallback to LIKE if vector not populated
            cursor.execute(
                """SELECT id, title, content, date, category, source_label,
                          ts_rank(search_vector, query) AS rank
                   FROM news_articles,
                        plainto_tsquery('english', %s) query
                   WHERE active=TRUE
                     AND (search_vector @@ query
                          OR title ILIKE %s)
                   ORDER BY rank DESC, date DESC LIMIT 20""",
                (q, f'%{q}%')
            )
            for a in cursor.fetchall():
                results.append({'type': 'News', 'id': a['id'], 'title': a['title'],
                                 'snippet': (a['content'] or '')[:150] + '...', 'url': f'/article/{a["id"]}'})
        except Exception as e:
            print(f"Search news error: {e}")
        try:
            cursor.execute(
                "SELECT id, title, description, category FROM classifieds WHERE active=TRUE AND (title ILIKE %s OR description ILIKE %s) ORDER BY date DESC LIMIT 10",
                (f'%{q}%', f'%{q}%')
            )
            for a in cursor.fetchall():
                results.append({'type': 'Classified', 'id': a['id'], 'title': a['title'],
                                 'snippet': (a['description'] or '')[:150] + '...', 'url': f'/classified/{a["id"]}'})
        except Exception as e:
            print(f"Search classifieds error: {e}")
        conn.close()
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Search - Spruce Grove Gazette</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
    body{{font-family:Georgia,'Times New Roman',serif;background:#f9f9f5;margin:0;}}
    nav{{background:#1a3d1a;padding:12px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;}}
    nav a{{color:#c8d5b9;text-decoration:none;font-size:13px;font-weight:bold;letter-spacing:.5px;}}
    nav a:hover{{color:#fff;}}
    .container{{max-width:800px;margin:40px auto;padding:0 20px;}}
    h1{{color:#1a3d1a;}} .search-box{{display:flex;gap:10px;margin-bottom:30px;}}
    .search-box input{{flex:1;padding:12px;border:2px solid #1a3d1a;border-radius:5px;font-size:16px;font-family:Georgia;}}
    .search-box button{{background:#1a3d1a;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;font-size:16px;}}
    .result{{background:white;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.07);}}
    .result a{{color:#1a3d1a;text-decoration:none;font-size:18px;font-weight:bold;}}
    .result a:hover{{text-decoration:underline;}}
    .badge{{display:inline-block;background:#e8f5e9;color:#1a3d1a;padding:2px 10px;border-radius:20px;font-size:12px;margin-bottom:8px;font-weight:bold;}}
    .snippet{{color:#555;margin-top:6px;font-size:14px;}}
    </style></head><body>
    <nav>
      <a href="/"><i class="fas fa-home"></i> HOME</a>
      <a href="/news"><i class="fas fa-newspaper"></i> NEWS</a>
      <a href="/events"><i class="fas fa-calendar-alt"></i> EVENTS</a>
      <a href="/classifieds"><i class="fas fa-list"></i> CLASSIFIEDS</a>
    </nav>
    <div class="container">
      <h1><i class="fas fa-search"></i> Search Results</h1>
      <form action="/search" method="GET" class="search-box">
        <input type="text" name="q" value="{q}" placeholder="Search news, classifieds...">
        <button type="submit"><i class="fas fa-search"></i> Search</button>
      </form>
      {"".join([f'<div class="result"><span class="badge">{r["type"]}</span><br><a href="{r["url"]}">{r["title"]}</a><p class="snippet">{r["snippet"]}</p></div>' for r in results]) if results else (f'<p style="color:#888;">No results found for "<strong>{q}</strong>".</p>' if q else '<p style="color:#888;">Enter a search term above.</p>')}
    </div></body></html>'''

@app.route('/submit-tip', methods=['GET', 'POST'])
def submit_tip():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        tip = request.form.get('tip', '').strip()
        if tip:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO news_tips (name, email, tip, date, status) VALUES (%s,%s,%s,%s,%s)",
                               (name, email, tip, datetime.now().date().isoformat(), 'pending'))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Tip error: {e}")
        return '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tip Received</title>
        <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
        .box{background:white;padding:50px 40px;border-radius:15px;max-width:450px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);}</style>
        </head><body><div class="box">
        <h1 style="color:#1a3d1a;">✅ Tip Received!</h1>
        <p>Thank you for your submission. Our journalists will review it.</p>
        <a href="/" style="color:#1a3d1a;font-weight:bold;">← Back to Home</a>
        </div></body></html>'''
    return '''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Submit a News Tip - Spruce Grove Gazette</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
    .container{background:white;padding:50px 40px;border-radius:15px;max-width:500px;width:100%;box-shadow:0 4px 20px rgba(0,0,0,.1);}
    h1{color:#1a3d1a;margin-top:0;}
    input,textarea{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box;font-family:Georgia;font-size:15px;}
    textarea{height:120px;resize:vertical;}
    button{background:#1a3d1a;color:white;padding:14px 30px;border:none;border-radius:5px;cursor:pointer;width:100%;font-size:16px;margin-top:10px;}
    button:hover{background:#0d260d;}
    .back{display:block;margin-top:20px;color:#1a3d1a;text-decoration:none;text-align:center;}
    </style></head><body>
    <div class="container">
      <h1>📰 Submit a News Tip</h1>
      <p style="color:#666;">Know something newsworthy? Let us know!</p>
      <form action="/submit-tip" method="POST">
        <input type="text" name="name" placeholder="Your Name (optional)">
        <input type="email" name="email" placeholder="Your Email (optional)">
        <textarea name="tip" placeholder="Describe your news tip..." required></textarea>
        <button type="submit">Send Tip</button>
      </form>
      <a href="/" class="back">← Back to Home</a>
    </div></body></html>'''

@app.route('/submit-photo', methods=['GET', 'POST'])
def submit_photo():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        caption = request.form.get('caption', '').strip()
        return '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Photo Received</title>
        <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
        .box{background:white;padding:50px 40px;border-radius:15px;max-width:450px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);}</style>
        </head><body><div class="box">
        <h1 style="color:#1a3d1a;">✅ Photo Submitted!</h1>
        <p>Thank you! We'll review your photo submission.</p>
        <a href="/" style="color:#1a3d1a;font-weight:bold;">← Back to Home</a>
        </div></body></html>'''
    return '''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Submit a Photo - Spruce Grove Gazette</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
    .container{background:white;padding:50px 40px;border-radius:15px;max-width:500px;width:100%;box-shadow:0 4px 20px rgba(0,0,0,.1);}
    h1{color:#1a3d1a;margin-top:0;}
    input,textarea{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box;font-family:Georgia;font-size:15px;}
    button{background:#1a3d1a;color:white;padding:14px 30px;border:none;border-radius:5px;cursor:pointer;width:100%;font-size:16px;margin-top:10px;}
    button:hover{background:#0d260d;}
    .back{display:block;margin-top:20px;color:#1a3d1a;text-decoration:none;text-align:center;}
    </style></head><body>
    <div class="container">
      <h1>📷 Submit a Community Photo</h1>
      <p style="color:#666;">Share your Spruce Grove moments with the community!</p>
      <form action="/submit-photo" method="POST" enctype="multipart/form-data">
        <input type="text" name="name" placeholder="Your Name" required>
        <input type="email" name="email" placeholder="Your Email" required>
        <input type="file" name="photo" accept="image/*" required>
        <textarea name="caption" placeholder="Caption / Description..." style="height:80px;resize:vertical;"></textarea>
        <button type="submit">Upload Photo</button>
      </form>
      <a href="/" class="back">← Back to Home</a>
    </div></body></html>'''

@app.route('/business-directory')
def business_directory():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM businesses ORDER BY name ASC")
        businesses = cursor.fetchall()
    except Exception:
        businesses = []
    conn.close()
    cards = ""
    for b in businesses:
        cards += f'''<div class="biz-card">
          <div class="biz-icon"><i class="fas fa-store"></i></div>
          <h3>{b["name"]}</h3>
          <p class="cat">{b.get("category","") or ""}</p>
          <p class="desc">{b.get("description","") or ""}</p>
          {('<p><i class="fas fa-phone"></i> ' + b["phone"] + '</p>') if b.get("phone") else ""}
          {('<p><i class="fas fa-globe"></i> <a href="' + b["website"] + '" target="_blank">' + b["website"] + '</a></p>') if b.get("website") else ""}
        </div>'''
    if not cards:
        cards = '<p style="text-align:center;color:#888;grid-column:1/-1;">No businesses listed yet. <a href="/submit-business" style="color:#1a3d1a;">Be the first!</a></p>'
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Business Directory - Spruce Grove Gazette</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
    *{{box-sizing:border-box;}}
    body{{font-family:Georgia,'Times New Roman',serif;background:#f9f9f5;margin:0;}}
    nav{{background:#1a3d1a;padding:12px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;}}
    nav a{{color:#c8d5b9;text-decoration:none;font-size:13px;font-weight:bold;letter-spacing:.5px;}}
    nav a:hover{{color:#fff;}}
    .hero{{background:linear-gradient(135deg,#1a3d1a,#2d6a2d);color:white;padding:60px 20px;text-align:center;}}
    .hero h1{{margin:0 0 10px;font-size:2.5rem;}}
    .hero p{{margin:0;opacity:.9;font-size:1.1rem;}}
    .container{{max-width:1100px;margin:40px auto;padding:0 20px;}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:24px;}}
    .biz-card{{background:white;border-radius:12px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08);text-align:center;transition:transform .2s;}}
    .biz-card:hover{{transform:translateY(-4px);box-shadow:0 6px 20px rgba(0,0,0,.12);}}
    .biz-icon{{font-size:2.5rem;color:#1a3d1a;margin-bottom:12px;}}
    .biz-card h3{{color:#1a3d1a;margin:0 0 6px;}}
    .cat{{color:#888;font-size:13px;margin:0 0 10px;}}
    .desc{{color:#555;font-size:14px;}}
    .add-btn{{display:inline-block;background:#1a3d1a;color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;margin-top:30px;}}
    .add-btn:hover{{background:#0d260d;}}
    </style></head><body>
    <nav>
      <a href="/"><i class="fas fa-home"></i> HOME</a>
      <a href="/news"><i class="fas fa-newspaper"></i> NEWS</a>
      <a href="/events"><i class="fas fa-calendar-alt"></i> EVENTS</a>
      <a href="/classifieds"><i class="fas fa-list"></i> CLASSIFIEDS</a>
      <a href="/business-directory"><i class="fas fa-store"></i> BUSINESSES</a>
      <a href="/advertise"><i class="fas fa-bullhorn"></i> ADVERTISE</a>
    </nav>
    <div class="hero">
      <h1><i class="fas fa-store"></i> Business Directory</h1>
      <p>Supporting local businesses in Spruce Grove, Alberta</p>
    </div>
    <div class="container">
      <div style="text-align:right;margin-bottom:24px;">
        <a href="/submit-business" class="add-btn"><i class="fas fa-plus"></i> List Your Business</a>
      </div>
      <div class="grid">{cards}</div>
    </div></body></html>'''

@app.route('/submit-business', methods=['GET', 'POST'])
def submit_business():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        website = request.form.get('website', '').strip()
        address = request.form.get('address', '').strip()
        if name:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO businesses (name, category, description, phone, email, website, address, date)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (name, category, description, phone, email, website, address, datetime.now().date().isoformat()))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Submit business error: {e}")
        return '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Business Listed!</title>
        <style>body{font-family:Georgia;background:#f9f9f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
        .box{background:white;padding:50px 40px;border-radius:15px;max-width:450px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);}</style>
        </head><body><div class="box">
        <h1 style="color:#1a3d1a;">✅ Business Submitted!</h1>
        <p>Thank you! Your business listing will be reviewed and added shortly.</p>
        <a href="/business-directory" style="color:#1a3d1a;font-weight:bold;">← View Directory</a>
        </div></body></html>'''
    categories = ['Retail','Restaurant & Food','Health & Wellness','Professional Services',
                  'Home & Garden','Automotive','Entertainment','Education','Other']
    cat_options = "".join([f'<option value="{c}">{c}</option>' for c in categories])
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>List Your Business - Spruce Grove Gazette</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{font-family:Georgia;background:#f9f9f5;padding:40px 20px;margin:0;}}
    .container{{background:white;padding:50px 40px;border-radius:15px;max-width:600px;margin:0 auto;box-shadow:0 4px 20px rgba(0,0,0,.1);}}
    h1{{color:#1a3d1a;margin-top:0;}}
    input,textarea,select{{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box;font-family:Georgia;font-size:15px;}}
    textarea{{height:100px;resize:vertical;}}
    button{{background:#1a3d1a;color:white;padding:14px 30px;border:none;border-radius:5px;cursor:pointer;width:100%;font-size:16px;margin-top:10px;}}
    button:hover{{background:#0d260d;}}
    .back{{display:block;margin-top:20px;color:#1a3d1a;text-decoration:none;text-align:center;}}
    label{{font-weight:bold;color:#1a3d1a;font-size:14px;}}
    </style></head><body>
    <div class="container">
      <h1><i class="fas fa-store"></i> List Your Business</h1>
      <p style="color:#666;">Get your business in front of Spruce Grove readers — free!</p>
      <form action="/submit-business" method="POST">
        <label>Business Name *</label>
        <input type="text" name="name" placeholder="e.g. Grove Coffee House" required>
        <label>Category</label>
        <select name="category"><option value="">-- Select Category --</option>{cat_options}</select>
        <label>Short Description</label>
        <textarea name="description" placeholder="What does your business do? (2-3 sentences)"></textarea>
        <label>Phone</label>
        <input type="tel" name="phone" placeholder="(780) 000-0000">
        <label>Email</label>
        <input type="email" name="email" placeholder="contact@yourbusiness.com">
        <label>Website</label>
        <input type="url" name="website" placeholder="https://yourbusiness.com">
        <label>Address</label>
        <input type="text" name="address" placeholder="123 Main St, Spruce Grove, AB">
        <button type="submit"><i class="fas fa-store"></i> Submit Listing</button>
      </form>
      <a href="/business-directory" class="back">← Back to Directory</a>
    </div></body></html>'''

# ─────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────

@app.route('/api/public-news')
def api_public_news():
    """Public aggregated news feed used by the AI crew."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT title, content, source, date FROM news_articles WHERE active=TRUE ORDER BY date DESC LIMIT 20")
        result = [{'title': a['title'], 'source': a.get('source', 'Spruce Grove Gazette'),
                   'published_at': str(a['date'])} for a in cursor.fetchall()]
    except Exception as e:
        print(f"API public-news error: {e}")
        result = []
    conn.close()
    return jsonify(result)

@app.route('/api/news')
def api_news():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, title, content, image_url, date FROM news_articles WHERE active=TRUE ORDER BY date DESC LIMIT 50")
        result = [dict(a) for a in cursor.fetchall()]
    except Exception as e:
        print(f"API news error: {e}")
        result = []
    conn.close()
    return jsonify(result)

@app.route('/api/events')
def api_events():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM events WHERE approved=TRUE ORDER BY date ASC LIMIT 30")
        result = [dict(e) for e in cursor.fetchall()]
    except Exception as e:
        print(f"API events error: {e}")
        result = []
    conn.close()
    return jsonify(result)

# ─────────────────────────────────────────
# Publish API — used by Make.com automation
# ─────────────────────────────────────────

VALID_CATEGORIES = {'News', 'Community', 'Sports', 'Business', 'Arts & Culture',
                    'Public Safety', 'Events', 'Health', 'Education', 'Opinion',
                    'Edmonton Area', 'Alberta'}

@app.route('/api/publish-article', methods=['POST'])
def api_publish_article():
    key = request.headers.get('X-Api-Key', '')
    if not GAZETTE_API_KEY or key != GAZETTE_API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON body'}), 400

    title        = (data.get('title') or '').strip()[:200]
    content      = (data.get('content') or '').strip()
    summary      = (data.get('summary') or '').strip()[:400]
    category     = (data.get('category') or 'News').strip()
    source       = (data.get('source') or '').strip()[:200]
    author       = (data.get('author') or 'Gazette Newsroom').strip()[:100]
    url          = (data.get('source_url') or '').strip()[:500]
    score        = int(data.get('score') or 50)
    urgent       = bool(data.get('urgent', False))
    story_type   = (data.get('story_type') or 'standard').strip()
    source_label = (data.get('source_label') or 'Staff').strip()
    expires_raw  = data.get('expires_from_front')

    if not title or not content or not source:
        return jsonify({'error': 'title, content, and source are required'}), 400

    if category not in VALID_CATEGORIES:
        category = 'News'

    # Set expires_from_front: caller can pass ISO date string, else default by story_type
    if expires_raw:
        try:
            from datetime import date as _date
            expires_from_front = str(expires_raw)[:10]
        except Exception:
            expires_from_front = None
    else:
        days_map = {'breaking': 1, 'developing': 2, 'standard': 7,
                    'community': 7, 'analysis': 14, 'opinion': 7, 'evergreen': None}
        days = days_map.get(story_type, 7)
        expires_from_front = (datetime.utcnow().date() + __import__('datetime').timedelta(days=days)).isoformat() if days else None

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    cursor = conn.cursor()

    # Deduplicate by title within last 48 hours
    cursor.execute(
        "SELECT id FROM news_articles WHERE title=%s AND date >= NOW() - INTERVAL '2 days'",
        (title,)
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({'status': 'duplicate', 'message': 'Article with this title already published recently'}), 200

    cursor.execute(
        '''INSERT INTO news_articles
           (title, content, summary, source, author, date, category, featured, active, url, views,
            score, urgent, story_type, source_label, expires_from_front,
            search_vector)
           VALUES (%s,%s,%s,%s,%s,%s,%s,FALSE,TRUE,%s,0,
                   %s,%s,%s,%s,%s,
                   to_tsvector('english', %s || ' ' || %s || ' ' || %s))
           RETURNING id''',
        (title, content, summary, source, author, now, category, url,
         score, urgent, story_type, source_label, expires_from_front,
         title, summary, content)
    )
    article_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()

    return jsonify({'id': article_id, 'title': title, 'category': category,
                    'score': score, 'urgent': urgent, 'status': 'published'}), 201


# ─────────────────────────────────────────
# Archive routes
# ─────────────────────────────────────────

@app.route('/archive')
def archive_index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DATE(date) AS day, COUNT(*) AS cnt
        FROM news_articles WHERE active = TRUE
        GROUP BY DATE(date) ORDER BY day DESC LIMIT 60
    """)
    days = cursor.fetchall()
    conn.close()
    rows_html = ''.join(
        f'<tr><td><a href="/archive/{str(d["day"])}">{str(d["day"])}</a></td><td>{d["cnt"]}</td></tr>'
        for d in days
    )
    return f'''<!DOCTYPE html><html><head><title>Archive – {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}
    .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
    .container{{max-width:700px;margin:40px auto;padding:0 20px}}
    table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
    th{{background:#1a3d1a;color:white;padding:12px;text-align:left}}
    td{{padding:10px 12px;border-bottom:1px solid #eee}}
    td a{{color:#1a3d1a;text-decoration:none;font-weight:bold}}td a:hover{{text-decoration:underline}}
    .nav{{background:#2C5F2D;padding:10px;text-align:center}}.nav a{{color:white;margin:0 12px;text-decoration:none}}
    .footer{{background:#0d260d;color:white;text-align:center;padding:20px;margin-top:40px}}
    </style></head><body>
    <div class="header"><h1><i class="fas fa-archive"></i> News Archive</h1></div>
    <div class="nav"><a href="/">Home</a><a href="/news">News</a><a href="/search">Search</a></div>
    <div class="container"><h2>Daily Archives</h2>
    <table><tr><th>Date</th><th>Articles</th></tr>{rows_html}</table></div>
    <div class="footer">© {datetime.now().year} {NEWSPAPER_NAME}</div></body></html>'''


@app.route('/archive/<date_str>')
def archive_day(date_str):
    try:
        from datetime import datetime as _dt
        _dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return redirect('/archive')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, title, summary, source, date, category, score, source_label
           FROM news_articles WHERE active = TRUE AND DATE(date) = %s
           ORDER BY score DESC, date DESC""",
        (date_str,)
    )
    articles = cursor.fetchall()
    conn.close()
    rows_html = ''.join(
        f'''<div style="background:white;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.08)">
            <span style="font-size:10px;background:#1a3d1a;color:white;padding:2px 8px;border-radius:10px">{a["category"]}</span>
            <span style="font-size:10px;background:#9b59b6;color:white;padding:2px 8px;border-radius:10px;margin-left:4px">{a.get("source_label") or "Staff"}</span>
            <h3 style="margin:8px 0"><a href="/article/{a["id"]}" style="color:#1a3d1a;text-decoration:none">{a["title"]}</a></h3>
            <p style="color:#555;font-size:13px;margin:0">{(a["summary"] or "")[:150]}...</p>
            <div style="color:#999;font-size:11px;margin-top:8px">{str(a["date"])[:16]} · {a["source"]} · Score: {a["score"] or 50}</div>
        </div>'''
        for a in articles
    ) or '<p>No articles archived for this date.</p>'
    return f'''<!DOCTYPE html><html><head><title>{date_str} Archive – {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}
    .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
    .container{{max-width:800px;margin:40px auto;padding:0 20px}}
    .nav{{background:#2C5F2D;padding:10px;text-align:center}}.nav a{{color:white;margin:0 12px;text-decoration:none}}
    .footer{{background:#0d260d;color:white;text-align:center;padding:20px;margin-top:40px}}
    </style></head><body>
    <div class="header"><h1><i class="fas fa-calendar-day"></i> {date_str}</h1><p>{len(articles)} articles archived</p></div>
    <div class="nav"><a href="/">Home</a><a href="/archive">Archive Index</a><a href="/news">News</a></div>
    <div class="container">{rows_html}</div>
    <div class="footer">© {datetime.now().year} {NEWSPAPER_NAME}</div></body></html>'''


@app.route('/sources')
def sources_page():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, org_type, url, region, reliability, ingestion_type, notes FROM source_registry WHERE active = TRUE ORDER BY reliability DESC, name")
    sources = cursor.fetchall()
    conn.close()
    label_map = {'staff':'🟢 Staff','government':'🏛️ Official','media':'📰 Media',
                 'NGO':'🤝 NGO','independent':'🎤 Independent','user_submitted':'📨 Submitted'}
    rows = ''.join(
        f'''<tr>
            <td><strong>{s["name"]}</strong></td>
            <td>{label_map.get(s["org_type"], s["org_type"])}</td>
            <td>{s["region"] or "—"}</td>
            <td>{"⭐" * (s["reliability"] or 0)}</td>
            <td>{s["ingestion_type"] or "manual"}</td>
            <td>{f'<a href="{s["url"]}" target="_blank">Link</a>' if s["url"] else "—"}</td>
        </tr>'''
        for s in sources
    )
    return f'''<!DOCTYPE html><html><head><title>Sources – {NEWSPAPER_NAME}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>body{{font-family:Georgia;background:#f9f9f5;margin:0}}
    .header{{background:#1a3d1a;color:white;padding:30px;text-align:center}}
    .container{{max-width:1000px;margin:40px auto;padding:0 20px}}
    table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
    th{{background:#1a3d1a;color:white;padding:12px;text-align:left;font-size:13px}}
    td{{padding:10px 12px;border-bottom:1px solid #eee;font-size:13px}}
    td a{{color:#1a3d1a}}
    .nav{{background:#2C5F2D;padding:10px;text-align:center}}.nav a{{color:white;margin:0 12px;text-decoration:none}}
    .footer{{background:#0d260d;color:white;text-align:center;padding:20px;margin-top:40px}}
    </style></head><body>
    <div class="header"><h1><i class="fas fa-list-alt"></i> Source Directory</h1><p>All news sources used by {NEWSPAPER_NAME}</p></div>
    <div class="nav"><a href="/">Home</a><a href="/news">News</a><a href="/archive">Archive</a></div>
    <div class="container">
    <table><tr><th>Source</th><th>Type</th><th>Region</th><th>Reliability</th><th>Method</th><th>URL</th></tr>
    {rows}</table></div>
    <div class="footer">© {datetime.now().year} {NEWSPAPER_NAME}</div></body></html>'''


# ─────────────────────────────────────────
# Service Worker — self-unregistering
# (old cached SW caused no-op fetch warning)
# ─────────────────────────────────────────

@app.route('/sw.js')
def service_worker():
    sw_code = (
        "self.addEventListener('install', () => self.skipWaiting());\n"
        "self.addEventListener('activate', event => {\n"
        "  event.waitUntil(\n"
        "    self.registration.unregister()\n"
        "      .then(() => self.clients.matchAll())\n"
        "      .then(clients => clients.forEach(c => c.navigate(c.url)))\n"
        "  );\n"
        "});\n"
    )
    from flask import Response
    return Response(sw_code, mimetype='application/javascript',
                    headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
