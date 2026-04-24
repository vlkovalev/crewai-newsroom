"""
Spruce Grove Gazette - Complete Newspaper Website
Generates articles on demand when needed
"""

import os
import sqlite3
import json
import requests
import subprocess
from datetime import datetime, date
from flask import Flask, jsonify, request

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
LAUNCH_YEAR = 2026
DB_PATH = 'gazette_archive.db'
GA_MEASUREMENT_ID = os.environ.get('GA_MEASUREMENT_ID', 'G-XXXXXXXXXX')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')

# ============================================
# Database Setup
# ============================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            published_date DATE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            subscribed_date DATE
        )
    ''')
    conn.commit()
    conn.close()

init_database()

# ============================================
# Article Generation
# ============================================

def generate_article():
    """Run the news generation script and save to database"""
    try:
        # Run the crew AI script
        result = subprocess.run(['python', 'news_crew_enhanced.py'], 
                               capture_output=True, 
                               text=True, 
                               timeout=120)
        
        # Look for the article in the output
        output = result.stdout
        print(f"Generation output: {output[:500]}")
        
        # Try to extract article from the output
        import re
        article_match = re.search(r'<h2.*?>.*?</h2>.*?<p>.*?</p>', output, re.DOTALL)
        
        if article_match:
            article_content = article_match.group(0)
            title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_content)
            title = title_match.group(1) if title_match else "Spruce Grove Gazette Daily Dispatch"
            
            # Save to database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO articles (title, content, published_date)
                VALUES (?, ?, ?)
            ''', (title, article_content, date.today().isoformat()))
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"Generation failed: {e}")
        return False

# ============================================
# Create Test Article
# ============================================

def create_test_article():
    """Create a sample article if none exists"""
    test_title = "Welcome to the Spruce Grove Gazette"
    test_content = """
    <h2>Welcome to the Spruce Grove Gazette!</h2>
    <p>Spruce Grove, AB — The Spruce Grove Gazette is officially launching, bringing local news to our community.</p>
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
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO articles (title, content, published_date)
        VALUES (?, ?, ?)
    ''', (test_title, test_content, date.today().isoformat()))
    conn.commit()
    conn.close()

# ============================================
# Routes
# ============================================

@app.route('/')
def home():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles")
    article_count = cursor.fetchone()[0]
    conn.close()
    
    weather = {"temp": 18, "condition": "Partly Cloudy"}
    if WEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Spruce Grove,CA&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            weather = {"temp": round(data['main']['temp']), "condition": data['weather'][0]['description'].title()}
        except:
            pass
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1a3d1a; --accent: #D4A017; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            .header {{ background: var(--primary); color: white; padding: 40px; text-align: center; }}
            .logo h1 {{ font-size: 48px; }}
            .nav {{ background: #2C5F2D; padding: 15px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .main {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 60px 20px; text-align: center; border-radius: 10px; margin-bottom: 40px; }}
            .hero h2 {{ font-size: 42px; }}
            .btn {{ display: inline-block; background: var(--accent); color: var(--primary); padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }}
            .weather {{ background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 30px; text-align: center; border-radius: 10px; }}
            .stat-number {{ font-size: 48px; font-weight: bold; color: var(--primary); }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            @media (max-width: 768px) {{
                .stats {{ grid-template-columns: 1fr; }}
                .hero h2 {{ font-size: 28px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo"><h1>📰 {NEWSPAPER_NAME}</h1><p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p></div>
        </div>
        <div class="nav">
            <a href="/">HOME</a>
            <a href="/latest">LATEST DISPATCH</a>
            <a href="/subscribe">NEWSLETTER</a>
        </div>
        <div class="main">
            <div class="hero">
                <h2>Your Hometown, Online.</h2>
                <p>Delivering trusted local news for Spruce Grove, Alberta</p>
                <a href="/latest" class="btn">Read Latest Dispatch →</a>
            </div>
            <div class="weather">
                <i class="fas fa-sun" style="font-size: 36px;"></i>
                <div style="font-size: 48px; font-weight: bold;">{weather['temp']}°C</div>
                <div>{weather['condition']}</div>
            </div>
            <div class="stats">
                <div class="stat-card"><div class="stat-number">{article_count}</div><div>Dispatches</div></div>
                <div class="stat-card"><div class="stat-number">5</div><div>Categories</div></div>
                <div class="stat-card"><div class="stat-number">5 AM</div><div>Daily Delivery</div></div>
            </div>
        </div>
        <div class="footer">
            <p>📍 Spruce Grove, Alberta</p>
            <p>© {LAUNCH_YEAR} {NEWSPAPER_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

@app.route('/latest')
def latest():
    """Get latest article or trigger generation"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, published_date FROM articles ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, content, date_pub = result
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title} - {NEWSPAPER_NAME}</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; background: #f9f9f5; }}
                h1 {{ color: #1a3d1a; border-bottom: 3px solid #D4A017; padding-bottom: 10px; }}
                h2 {{ color: #2C5F2D; }}
                h3 {{ color: #4A7C4B; }}
                .meta {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }}
                .footer {{ margin-top: 40px; text-align: center; }}
                .btn {{ display: inline-block; background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <div class="meta">📍 Spruce Grove, AB | 📅 {date_pub}</div>
            {content}
            <div class="footer">
                <a href="/" class="btn">← Back to Home</a>
            </div>
        </body>
        </html>
        '''
    
    # No article exists - create test article
    create_test_article()
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>First Dispatch Being Created</title>
        <meta http-equiv="refresh" content="3; url=/latest">
    </head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">📰 Creating First Dispatch...</h1>
        <p>Please wait. Redirecting in 3 seconds...</p>
    </body>
    </html>
    '''

@app.route('/force-generate')
def force_generate():
    """Force generate a new article using the AI crew"""
    import threading
    
    def generate():
        generate_article()
    
    thread = threading.Thread(target=generate)
    thread.start()
    
    return jsonify({"status": "started", "message": "Article generation started. Check /latest in 30 seconds."})

@app.route('/create-test-article')
def create_test_article_route():
    """Create a test article"""
    create_test_article()
    return jsonify({"status": "success", "message": "Test article created! Visit /latest"})

@app.route('/subscribe')
def subscribe():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribe</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1>📧 Subscribe to The Gazette</h1>
        <form method="POST" action="/do-subscribe">
            <input type="email" name="email" placeholder="Your email" required style="padding: 10px; width: 250px;">
            <button type="submit" style="background: #1a3d1a; color: white; padding: 10px 20px;">Subscribe</button>
        </form>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    '''

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    email = request.form.get('email')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subscribers (email, subscribed_date) VALUES (?, ?)", (email, date.today().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()
    return '<html><body style="text-align:center;padding:50px;"><h1>✅ Subscribed!</h1><a href="/">Back to Home</a></body></html>'

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/debug-files')
def debug_files():
    import glob
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles")
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({
        "articles_in_db": count,
        "files": glob.glob('*'),
        "current_directory": os.getcwd()
    })

@app.route('/sw.js')
def sw():
    return 'self.addEventListener("fetch", () => {});', 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)