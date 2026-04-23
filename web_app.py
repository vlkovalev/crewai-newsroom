"""
Spruce Grove Gazette - Professional Newspaper Website
Complete redesign with modern UI, enhanced features, and professional styling
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

GA_MEASUREMENT_ID = os.environ.get('GA_MEASUREMENT_ID', 'G-XXXXXXXXXX')

# ============================================
# Database Setup
# ============================================

def init_database():
    """Initialize SQLite databases"""
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
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE active = 1")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ============================================
# Main Route - Professional Newspaper Design
# ============================================

@app.route('/')
def home():
    total_articles = get_article_count()
    subscriber_count = get_subscriber_count()
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Spruce Grove Gazette - Spruce Grove's Trusted News Source</title>
    <meta name="description" content="Spruce Grove's premier AI-powered local news source. Breaking news, community events, sports, business, and weather for Spruce Grove, Alberta.">
    <meta name="keywords" content="Spruce Grove, local news, Alberta news, Spruce Grove Gazette, community news">
    <meta name="author" content="Spruce Grove Gazette">
    <meta property="og:title" content="Spruce Grove Gazette">
    <meta property="og:description" content="Your trusted source for Spruce Grove local news">
    <meta property="og:url" content="https://sprucegrovegazette.com">
    <meta property="og:type" content="website">
    <meta property="og:image" content="https://sprucegrovegazette.com/static/og-image.jpg">
    <meta name="twitter:card" content="summary_large_image">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_MEASUREMENT_ID}');
    </script>
    
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {{
            --primary: #1a3d1a;
            --primary-light: #2C5F2D;
            --primary-dark: #0d260d;
            --secondary: #8B7355;
            --accent: #D4A017;
            --text-dark: #1a1a1a;
            --text-light: #666;
            --bg-light: #f9f9f5;
            --bg-gray: #f0f0e8;
            --white: #ffffff;
            --shadow: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.1);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background: var(--bg-light);
            color: var(--text-dark);
            line-height: 1.6;
        }}
        
        /* Top Bar */
        .top-bar {{
            background: var(--primary-dark);
            color: var(--white);
            font-size: 12px;
            padding: 8px 0;
            text-align: center;
        }}
        
        /* Header */
        .header {{
            background: var(--white);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 3px solid var(--accent);
        }}
        
        .logo h1 {{
            font-size: 64px;
            font-weight: bold;
            color: var(--primary);
            letter-spacing: -1px;
            font-family: 'Times New Roman', serif;
        }}
        
        .logo p {{
            font-size: 16px;
            color: var(--text-light);
            letter-spacing: 3px;
            margin-top: 5px;
        }}
        
        .date-header {{
            background: var(--bg-gray);
            padding: 10px 20px;
            text-align: center;
            font-size: 14px;
            color: var(--text-light);
            border-bottom: 1px solid #ddd;
        }}
        
        /* Navigation */
        .nav {{
            background: var(--primary);
            padding: 15px 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: var(--shadow);
        }}
        
        .nav a {{
            color: var(--white);
            text-decoration: none;
            margin: 0 20px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 14px;
            letter-spacing: 1px;
            transition: color 0.3s;
        }}
        
        .nav a:hover {{
            color: var(--accent);
        }}
        
        /* Hero Section */
        .hero {{
            background: linear-gradient(135deg, var(--primary-dark), var(--primary));
            color: var(--white);
            padding: 60px 40px;
            text-align: center;
        }}
        
        .hero h2 {{
            font-size: 42px;
            margin-bottom: 15px;
        }}
        
        .hero p {{
            font-size: 18px;
            max-width: 600px;
            margin: 0 auto;
            opacity: 0.9;
        }}
        
        .status-badge {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 8px 20px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        
        /* Main Content */
        .main-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .stat-card {{
            background: var(--white);
            padding: 30px 20px;
            text-align: center;
            border-radius: 10px;
            box-shadow: var(--shadow);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }}
        
        .stat-card i {{
            font-size: 48px;
            color: var(--primary-light);
            margin-bottom: 15px;
        }}
        
        .stat-number {{
            font-size: 42px;
            font-weight: bold;
            color: var(--primary);
        }}
        
        .stat-label {{
            font-size: 14px;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Two Column Layout */
        .two-column {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 40px;
            margin-bottom: 50px;
        }}
        
        /* News Section */
        .section-title {{
            font-size: 28px;
            color: var(--primary);
            border-left: 4px solid var(--accent);
            padding-left: 15px;
            margin-bottom: 25px;
        }}
        
        .feature-card {{
            background: var(--white);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
            margin-bottom: 30px;
        }}
        
        .feature-card .content {{
            padding: 25px;
        }}
        
        .feature-card h3 {{
            font-size: 24px;
            color: var(--primary);
            margin-bottom: 15px;
        }}
        
        .feature-card p {{
            color: var(--text-light);
            margin-bottom: 20px;
        }}
        
        .btn {{
            display: inline-block;
            background: var(--primary);
            color: var(--white);
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background 0.3s;
        }}
        
        .btn:hover {{
            background: var(--primary-dark);
        }}
        
        .btn-outline {{
            background: transparent;
            border: 2px solid var(--primary);
            color: var(--primary);
        }}
        
        .btn-outline:hover {{
            background: var(--primary);
            color: var(--white);
        }}
        
        /* Info List */
        .info-list {{
            list-style: none;
        }}
        
        .info-list li {{
            padding: 15px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .info-list li i {{
            color: var(--primary-light);
            font-size: 20px;
            width: 30px;
        }}
        
        /* Newsletter Section */
        .newsletter-section {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: var(--white);
            padding: 50px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 50px;
        }}
        
        .newsletter-section h3 {{
            font-size: 32px;
            margin-bottom: 15px;
        }}
        
        .newsletter-form {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 25px;
            flex-wrap: wrap;
        }}
        
        .newsletter-form input {{
            padding: 15px 20px;
            width: 300px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
        }}
        
        .newsletter-form button {{
            background: var(--accent);
            color: var(--primary-dark);
            padding: 15px 30px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s;
        }}
        
        .newsletter-form button:hover {{
            transform: translateY(-2px);
        }}
        
        /* Social Section */
        .social-section {{
            background: var(--white);
            padding: 40px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 50px;
            box-shadow: var(--shadow);
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
            transition: transform 0.3s;
        }}
        
        .social-btn:hover {{
            transform: translateY(-3px);
        }}
        
        .social-btn.twitter {{ background: #1DA1F2; }}
        .social-btn.facebook {{ background: #3b5998; }}
        .social-btn.linkedin {{ background: #0077b5; }}
        .social-btn.email {{ background: #666; }}
        
        /* Footer */
        .footer {{
            background: var(--primary-dark);
            color: var(--white);
            padding: 50px 20px 30px;
        }}
        
        .footer-content {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 40px;
        }}
        
        .footer-column h4 {{
            margin-bottom: 20px;
            font-size: 18px;
        }}
        
        .footer-column a {{
            color: #ccc;
            text-decoration: none;
            display: block;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .footer-column a:hover {{
            color: var(--accent);
        }}
        
        .copyright {{
            text-align: center;
            padding-top: 40px;
            margin-top: 40px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 12px;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .logo h1 {{ font-size: 40px; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .two-column {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
            .nav a {{ margin: 0 10px; font-size: 12px; }}
        }}
        
        @media (max-width: 480px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
            .footer-content {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="top-bar">
        🌿 Spruce Grove's Trusted News Source Since 1950
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
        <a href="/latest">📰 LATEST EDITION</a>
        <a href="#">🏈 SPORTS</a>
        <a href="#">🏢 BUSINESS</a>
        <a href="#">👥 COMMUNITY</a>
        <a href="#">📅 EVENTS</a>
        <a href="/subscribe">✉️ NEWSLETTER</a>
    </div>
    
    <div class="hero">
        <div class="status-badge">
            <i class="fas fa-circle"></i> AI NEWSROOM ACTIVE
        </div>
        <h2>Your Hometown, Online.</h2>
        <p>AI-powered local news delivered fresh every morning. Covering what matters to Spruce Grove residents.</p>
    </div>
    
    <div class="main-content">
        <div class="stats-grid">
            <div class="stat-card">
                <i class="fas fa-newspaper"></i>
                <div class="stat-number">{total_articles}</div>
                <div class="stat-label">Articles Published</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-users"></i>
                <div class="stat-number">{subscriber_count}</div>
                <div class="stat-label">Newsletter Readers</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-robot"></i>
                <div class="stat-number">5</div>
                <div class="stat-label">AI Agents</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-clock"></i>
                <div class="stat-number">8:00 AM</div>
                <div class="stat-label">Daily Delivery</div>
            </div>
        </div>
        
        <div class="two-column">
            <div>
                <h2 class="section-title">📰 Today's Top Story</h2>
                <div class="feature-card">
                    <div class="content">
                        <h3>AI Newsroom Now Serving Spruce Grove</h3>
                        <p>Introducing the first AI-powered local news source for our community. The Spruce Grove Gazette uses advanced artificial intelligence to bring you timely, accurate, and engaging local news every morning.</p>
                        <a href="/latest" class="btn">Read Full Story →</a>
                    </div>
                </div>
                
                <h2 class="section-title">📌 What We Cover</h2>
                <div class="feature-card">
                    <div class="content">
                        <ul class="info-list">
                            <li><i class="fas fa-futbol"></i> <strong>Sports</strong> - High school athletics, local tournaments, and youth sports</li>
                            <li><i class="fas fa-school"></i> <strong>Education</strong> - School board news, student achievements, and programs</li>
                            <li><i class="fas fa-store"></i> <strong>Business</strong> - New openings, expansions, and local entrepreneurs</li>
                            <li><i class="fas fa-hand-sparkles"></i> <strong>Community</strong> - Events, volunteers, and local heroes</li>
                            <li><i class="fas fa-landmark"></i> <strong>City Hall</strong> - Council decisions and development projects</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div>
                <h2 class="section-title">🤖 How It Works</h2>
                <div class="feature-card">
                    <div class="content">
                        <p><strong>Five AI Agents Work Together:</strong></p>
                        <ul class="info-list">
                            <li><i class="fas fa-search"></i> <strong>Researcher</strong> - Finds local stories</li>
                            <li><i class="fas fa-check-double"></i> <strong>Fact Checker</strong> - Verifies everything</li>
                            <li><i class="fas fa-pen-fancy"></i> <strong>Writer</strong> - Crafts the story</li>
                            <li><i class="fas fa-marker"></i> <strong>Editor</strong> - Polishes the article</li>
                            <li><i class="fas fa-heading"></i> <strong>Headline Specialist</strong> - Creates engaging headlines</li>
                        </ul>
                    </div>
                </div>
                
                <h2 class="section-title">📅 Coming Up</h2>
                <div class="feature-card">
                    <div class="content">
                        <ul class="info-list">
                            <li><i class="fas fa-calendar"></i> <strong>Farmers Market</strong> - Every Saturday, Downtown</li>
                            <li><i class="fas fa-calendar"></i> <strong>City Council</strong> - Monday at 7 PM</li>
                            <li><i class="fas fa-calendar"></i> <strong>Library Story Time</strong> - Wednesday at 10:30 AM</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="newsletter-section">
            <h3>✉️ Never Miss an Edition</h3>
            <p>Get the Spruce Grove Gazette delivered to your inbox every morning at 8 AM.</p>
            <form class="newsletter-form" action="/subscribe" method="GET">
                <input type="email" name="email" placeholder="Enter your email address" required>
                <button type="submit">Subscribe Free →</button>
            </form>
            <p style="margin-top: 20px; font-size: 12px; opacity: 0.8;">No spam. Unsubscribe anytime.</p>
        </div>
        
        <div class="social-section">
            <h3>📱 Spread the Word</h3>
            <p>Help your neighbors stay informed about Spruce Grove news.</p>
            <div class="social-links">
                <a href="https://twitter.com/intent/tweet?text=Check out the Spruce Grove Gazette, your AI-powered local news source!&url=https://sprucegrovegazette.com" target="_blank" class="social-btn twitter"><i class="fab fa-twitter"></i> Share on Twitter</a>
                <a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" target="_blank" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Share on Facebook</a>
                <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://sprucegrovegazette.com" target="_blank" class="social-btn linkedin"><i class="fab fa-linkedin-in"></i> Share on LinkedIn</a>
                <a href="mailto:?subject=Spruce Grove Gazette&body=I thought you'd enjoy this local news source: https://sprucegrovegazette.com" class="social-btn email"><i class="fas fa-envelope"></i> Share via Email</a>
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
                <a href="/health">Health Check</a>
            </div>
            <div class="footer-column">
                <h4>📬 Connect</h4>
                <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                <a href="#">Submit a Letter</a>
                <a href="#">Advertising</a>
                <a href="#">Report News</a>
            </div>
            <div class="footer-column">
                <h4>🔗 Resources</h4>
                <a href="/sitemap.xml">Sitemap</a>
                <a href="/api/status">API Status</a>
                <a href="#">Privacy Policy</a>
                <a href="#">Terms of Use</a>
            </div>
            <div class="footer-column">
                <h4>📍 Location</h4>
                <a href="#">Spruce Grove, Alberta</a>
                <a href="#">Canada</a>
                <a href="#">📧 editor@sprucegrovegazette.com</a>
            </div>
        </div>
        <div class="copyright">
            <p>© {datetime.now().year} The Spruce Grove Gazette. All rights reserved.</p>
            <p>Powered by CrewAI | AI-Powered Local News | Established 1950</p>
        </div>
    </div>
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
        <p>Our AI newsroom is preparing the first edition. Check back tomorrow at 8:00 AM!</p>
        <a href="/" style="color: #1a3d1a;">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/health')
def health():
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
    return jsonify({
        "name": "Spruce Grove Gazette",
        "status": "running",
        "type": "cron-job",
        "schedule": "Daily at 8:00 AM MT",
        "last_check": datetime.now().isoformat(),
        "total_articles": get_article_count(),
        "subscribers": get_subscriber_count()
    })

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
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
            except:
                success = False
            conn.close()
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Subscribed - Spruce Grove Gazette</title>
                <style>
                    body {{ font-family: Georgia, serif; background: #f0f0e8; text-align: center; padding: 50px; }}
                    .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }}
                    h1 {{ color: #1a3d1a; }}
                    .btn {{ display: inline-block; background: #1a3d1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Welcome to the Gazette!</h1>
                    <p>You've successfully subscribed to the Spruce Grove Gazette daily newsletter.</p>
                    <p>Your first edition will arrive tomorrow at 8:00 AM.</p>
                    <a href="/" class="btn">← Back to Gazette</a>
                </div>
            </body>
            </html>
            '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subscribe - Spruce Grove Gazette</title>
        <style>
            body { font-family: Georgia, serif; background: #f0f0e8; margin: 0; padding: 50px; }
            .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #1a3d1a; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2C5F2D; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to The Gazette</h1>
            <p>Get local news delivered to your inbox every morning.</p>
            <form method="POST">
                <input type="text" name="name" placeholder="Your name (optional)">
                <input type="email" name="email" placeholder="Your email address" required>
                <button type="submit">Subscribe →</button>
            </form>
            <p style="margin-top: 20px; font-size: 12px; color: #666;">No spam. Unsubscribe anytime.</p>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/sitemap.xml')
def sitemap():
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://sprucegrovegazette.com/</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>
    <url><loc>https://sprucegrovegazette.com/latest</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>
    <url><loc>https://sprucegrovegazette.com/subscribe</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
</urlset>'''
    return app.response_class(sitemap_content, mimetype='application/xml')

# ============================================
# Run the App
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)