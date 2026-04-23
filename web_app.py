"""
Spruce Grove Gazette - Complete Web Application
Features: Status page, Google Analytics, Newsletter, Social Sharing, Stats Dashboard
"""

import os
import sqlite3
import glob
from datetime import datetime, date
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

# ============================================
# Configuration
# ============================================

# Google Analytics Measurement ID (replace with your own)
GA_MEASUREMENT_ID = os.environ.get('GA_MEASUREMENT_ID', 'G-XXXXXXXXXX')

# Email configuration (optional - for newsletter)
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# ============================================
# Database Setup
# ============================================

def init_database():
    """Initialize SQLite databases"""
    # Articles archive database
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
    conn.commit()
    conn.close()
    
    # Subscribers database
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            subscribed_date DATE,
            active BOOLEAN DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()
    print("Databases initialized")

# Call database initialization
init_database()

# ============================================
# Helper Functions
# ============================================

def get_latest_article():
    """Get the latest generated article file"""
    html_files = glob.glob('spruce_grove_gazette_*.html')
    if html_files:
        latest = max(html_files, key=os.path.getctime)
        return latest
    return None

def get_article_count():
    """Get total number of generated articles"""
    conn = sqlite3.connect('gazette_archive.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_subscriber_count():
    """Get total number of active subscribers"""
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE active = 1")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ============================================
# Routes
# ============================================

@app.route('/')
def home():
    """Main status page with all features"""
    
    # Get statistics
    total_articles = get_article_count()
    subscriber_count = get_subscriber_count()
    latest_article = get_latest_article()
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Spruce Grove Gazette - AI-Powered Local News</title>
        <meta name="description" content="AI-powered local news for Spruce Grove, Alberta. Daily news, weather, events, and community updates delivered every morning.">
        <meta name="keywords" content="Spruce Grove, local news, Alberta news, community news, AI newsroom">
        <meta name="author" content="Spruce Grove Gazette">
        <meta property="og:title" content="Spruce Grove Gazette">
        <meta property="og:description" content="Your AI-powered local news source for Spruce Grove, Alberta">
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
        
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Georgia, 'Times New Roman', serif; background: #f5f5f0; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
            
            /* Header */
            .header {{ background: #2C5F2D; color: white; padding: 40px; text-align: center; }}
            .header h1 {{ font-size: 48px; margin-bottom: 10px; }}
            .header p {{ font-size: 18px; opacity: 0.9; }}
            .date {{ margin-top: 10px; font-style: italic; }}
            
            /* Navigation */
            .nav {{ background: #1a3d1a; padding: 15px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; font-weight: bold; }}
            .nav a:hover {{ text-decoration: underline; }}
            
            /* Main content */
            .main-content {{ padding: 40px; }}
            
            /* Status badge */
            .status {{ background: #e8f5e9; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
            .status-badge {{ display: inline-block; background: #27ae60; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
            
            /* Stats cards */
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: #f9f9f5; padding: 20px; border-radius: 10px; text-align: center; }}
            .stat-number {{ font-size: 36px; font-weight: bold; color: #2C5F2D; }}
            
            /* Info boxes */
            .info-box {{ background: #f9f9f5; padding: 20px; border-left: 4px solid #2C5F2D; margin: 20px 0; }}
            
            /* Buttons */
            .button {{ display: inline-block; background: #2C5F2D; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 5px; transition: transform 0.2s; }}
            .button:hover {{ background: #1a3d1a; transform: translateY(-2px); }}
            
            /* Newsletter box */
            .newsletter {{ background: linear-gradient(135deg, #2C5F2D, #1a3d1a); color: white; padding: 40px; border-radius: 10px; text-align: center; margin: 30px 0; }}
            .newsletter input {{ padding: 12px; width: 250px; border: none; border-radius: 5px; margin: 10px; }}
            .newsletter button {{ background: #f5f5f0; color: #2C5F2D; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
            
            /* Social section */
            .social-section {{ text-align: center; margin: 40px 0; padding: 30px; background: #f9f9f5; border-radius: 10px; }}
            .social-links {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin: 20px 0; }}
            .social-btn {{ display: inline-block; padding: 12px 24px; border-radius: 5px; text-decoration: none; color: white; font-weight: bold; transition: transform 0.2s; }}
            .social-btn:hover {{ transform: translateY(-2px); }}
            .social-btn.twitter {{ background: #1DA1F2; }}
            .social-btn.facebook {{ background: #3b5998; }}
            .social-btn.linkedin {{ background: #0077b5; }}
            .social-btn.email {{ background: #666; }}
            
            /* Footer */
            .footer {{ background: #1a3d1a; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            .footer a {{ color: white; text-decoration: none; margin: 0 10px; }}
            
            /* Responsive */
            @media (max-width: 768px) {{
                .main-content {{ padding: 20px; }}
                .social-links {{ flex-direction: column; }}
                .newsletter input {{ width: 90%; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📰 Spruce Grove Gazette</h1>
                <p>Your Hometown, Online | Established 1950</p>
                <div class="date">📍 Spruce Grove, AB | AI-Powered Local News</div>
            </div>
            
            <div class="nav">
                <a href="/">Home</a>
                <a href="/latest">Latest Edition</a>
                <a href="/subscribe">Newsletter</a>
                <a href="/health">Health Check</a>
                <a href="/api/status">API Status</a>
            </div>
            
            <div class="main-content">
                <div class="status">
                    <span class="status-badge">● AI BOT RUNNING</span>
                    <p style="margin-top: 15px;">Automated news generation active | Daily at 8:00 AM MT</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_articles}</div>
                        <div>Articles Generated</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{subscriber_count}</div>
                        <div>Newsletter Subscribers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">24/7</div>
                        <div>Bot Availability</div>
                    </div>
                </div>
                
                <div class="info-box">
                    <h3>🤖 About This AI Newsroom</h3>
                    <p>This website is powered by <strong>CrewAI</strong>, a multi-agent AI system that automatically researches, writes, and publishes local news for Spruce Grove, Alberta.</p>
                    <p><strong>What it covers:</strong> Sports, schools, business, community events, city council, and development projects.</p>
                    <p><strong>How it works:</strong> Five AI agents work together: Researcher → Fact-Checker → Writer → Editor → Headline Specialist.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/latest" class="button">📖 Read Latest Edition →</a>
                    <a href="/health" class="button" style="background: #666;">💚 Health Check →</a>
                </div>
                
                <div class="newsletter">
                    <h3>📧 Get the Gazette in Your Inbox</h3>
                    <p>Subscribe to receive our daily news digest every morning at 8:00 AM.</p>
                    <form action="/subscribe" method="GET">
                        <input type="email" name="email" placeholder="Enter your email" required>
                        <button type="submit">Subscribe Free →</button>
                    </form>
                    <p style="margin-top: 15px; font-size: 12px; opacity: 0.8;">No spam. Unsubscribe anytime.</p>
                </div>
                
                <div class="social-section">
                    <h3>📱 Share the Gazette</h3>
                    <div class="social-links">
                        <a href="https://twitter.com/intent/tweet?text=Spruce Grove Gazette - Your Local AI Newsroom&url=https://sprucegrovegazette.com" target="_blank" class="social-btn twitter">🐦 Share on Twitter</a>
                        <a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" target="_blank" class="social-btn facebook">📘 Share on Facebook</a>
                        <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://sprucegrovegazette.com" target="_blank" class="social-btn linkedin">🔗 Share on LinkedIn</a>
                        <a href="mailto:?subject=Check out the Spruce Grove Gazette&body=I thought you'd enjoy this AI-powered local news source: https://sprucegrovegazette.com" class="social-btn email">📧 Share via Email</a>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>📧 editor@sprucegrovegazette.com</p>
                <p>📍 Spruce Grove, Alberta</p>
                <div style="margin-top: 20px;">
                    <a href="/">Home</a> | 
                    <a href="/subscribe">Subscribe</a> | 
                    <a href="/latest">Latest Edition</a> |
                    <a href="/sitemap.xml">Sitemap</a>
                </div>
                <p style="margin-top: 20px;">© 2026 Spruce Grove Gazette. AI-Powered Local News.</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/latest')
def latest_article():
    """Serve the latest generated article"""
    latest = get_latest_article()
    if latest:
        return send_file(latest)
    return "<h1>No articles generated yet</h1><p>The bot will create the first edition soon. Check back later!</p>"

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    latest = get_latest_article()
    return jsonify({
        "status": "healthy",
        "bot": "spruce-grove-news-bot",
        "last_article": latest,
        "time": datetime.now().isoformat(),
        "version": "2.0.0"
    })

@app.route('/api/status')
def api_status():
    """JSON API for bot status"""
    return jsonify({
        "name": "Spruce Grove Gazette Bot",
        "status": "running",
        "type": "cron-job",
        "schedule": "Daily at 8:00 AM MT",
        "last_check": datetime.now().isoformat(),
        "total_articles": get_article_count(),
        "subscribers": get_subscriber_count()
    })

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    """Subscribe to daily newspaper email"""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name', '')
        
        if email:
            conn = sqlite3.connect('subscribers.db')
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO subscribers (email, name, subscribed_date, active) VALUES (?, ?, ?, 1)",
                    (email, name, date.today())
                )
                conn.commit()
                success = True
            except sqlite3.IntegrityError:
                success = False
            conn.close()
            
            if success:
                return '''
                <!DOCTYPE html>
                <html>
                <head><title>Subscribed - Spruce Grove Gazette</title></head>
                <body style="font-family: Georgia, serif; text-align: center; padding: 50px;">
                    <h1 style="color: #2C5F2D;">✅ Subscribed!</h1>
                    <p>Thank you for subscribing to the Spruce Grove Gazette daily newsletter.</p>
                    <p>You'll receive our daily news digest every morning at 8:00 AM.</p>
                    <a href="/" style="color: #2C5F2D;">← Back to Gazette</a>
                </body>
                </html>
                '''
            else:
                return '''
                <!DOCTYPE html>
                <html>
                <head><title>Already Subscribed</title></head>
                <body style="font-family: Georgia, serif; text-align: center; padding: 50px;">
                    <h1 style="color: #e74c3c;">⚠️ Already Subscribed</h1>
                    <p>This email is already on our mailing list.</p>
                    <a href="/" style="color: #2C5F2D;">← Back to Gazette</a>
                </body>
                </html>
                '''
    
    # Show subscription form
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subscribe - Spruce Grove Gazette</title>
        <style>
            body { font-family: Georgia, serif; background: #f5f5f0; margin: 0; padding: 50px; }
            .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            h1 { color: #2C5F2D; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            button { background: #2C5F2D; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }
            button:hover { background: #1a3d1a; }
            .note { font-size: 12px; color: #666; margin-top: 20px; }
            a { color: #2C5F2D; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to Daily News</h1>
            <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
            <form method="POST">
                <input type="text" name="name" placeholder="Your name (optional)">
                <input type="email" name="email" placeholder="Your email address" required>
                <button type="submit">Subscribe →</button>
            </form>
            <p class="note">🔒 No spam. Unsubscribe anytime. Your email is safe with us.</p>
            <p class="note"><a href="/">← Back to Gazette</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/sitemap.xml')
def sitemap():
    """Generate sitemap for search engines"""
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://sprucegrovegazette.com/</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://sprucegrovegazette.com/health</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>hourly</changefreq>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>https://sprucegrovegazette.com/api/status</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>hourly</changefreq>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>https://sprucegrovegazette.com/subscribe</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>'''
    return app.response_class(sitemap_content, mimetype='application/xml')

# ============================================
# Run the App
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)