"""
Spruce Grove Gazette - Complete Working Version
"""

import os
import json
import subprocess
import re
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
LAUNCH_YEAR = 2026
ARTICLE_FILE = 'latest_article.json'

def save_article(title, html_content, date):
    """Save article to JSON file"""
    article_data = {
        'title': title,
        'html': html_content,
        'date': date
    }
    with open(ARTICLE_FILE, 'w', encoding='utf-8') as f:
        json.dump(article_data, f)
    print(f"Article saved: {title}")

def load_article():
    """Load article from JSON file"""
    if os.path.exists(ARTICLE_FILE):
        with open(ARTICLE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_weather():
    return {"temp": 18, "condition": "Partly Cloudy"}

@app.route('/')
def home():
    weather = get_weather()
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
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo"><h1>📰 {NEWSPAPER_NAME}</h1><p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p></div>
        </div>
        <div class="nav">
            <a href="/">HOME</a>
            <a href="/latest">LATEST DISPATCH</a>
            <a href="/run-bot">🤖 GENERATE NEWS</a>
            <a href="/create-test">📝 CREATE TEST</a>
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
    """Display the latest article"""
    article = load_article()
    
    if article:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{article['title']} - {NEWSPAPER_NAME}</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; background: #f9f9f5; }}
                h1 {{ color: #1a3d1a; border-bottom: 3px solid #D4A017; padding-bottom: 10px; }}
                h2 {{ color: #2C5F2D; }}
                h3 {{ color: #4A7C4B; }}
                .meta {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }}
                .footer {{ margin-top: 40px; text-align: center; }}
                .btn {{ display: inline-block; background: #1a3d1a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <div class="meta">📍 Spruce Grove, AB | 📅 {article['date']}</div>
            {article['html']}
            <div class="footer">
                <a href="/" class="btn">← Back to Home</a>
                <a href="/run-bot" class="btn" style="background: #D4A017; color: #1a3d1a;">↻ Generate Fresh News</a>
            </div>
        </body>
        </html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>No Article Yet</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1>📰 No Article Generated Yet</h1>
        <p>Click the button below to generate the first dispatch.</p>
        <a href="/run-bot" style="background: #1a3d1a; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">🤖 Generate First Dispatch →</a>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    '''

@app.route('/run-bot')
def run_bot():
    """Run the news generation bot"""
    try:
        # Run the news generation script
        result = subprocess.run(['python', 'news_crew_enhanced.py'], 
                               capture_output=True, 
                               text=True, 
                               timeout=120)
        
        output = result.stdout
        
        # Try to extract article HTML from the output
        # Look for the article content between the === Final Article: === lines
        article_match = re.search(r'Final Article:\n=+\n(.*?)\n=+', output, re.DOTALL)
        
        if article_match:
            article_html = article_match.group(1)
            
            # Extract title from h2 tag
            title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
            title = title_match.group(1) if title_match else "Spruce Grove Gazette Dispatch"
            
            # Save the article
            save_article(title, article_html, datetime.now().strftime('%B %d, %Y'))
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Article Generated</title></head>
            <body style="font-family: Georgia; text-align: center; padding: 50px;">
                <h1 style="color: #1a3d1a;">✅ Article Generated Successfully!</h1>
                <p>The latest dispatch has been created.</p>
                <p><strong>Title:</strong> {title}</p>
                <a href="/latest" style="background: #1a3d1a; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">📰 Read Latest Dispatch →</a>
                <p><a href="/">← Back to Home</a></p>
            </body>
            </html>
            '''
        
        # If no article found, show the output for debugging
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Generation Output</title></head>
        <body style="font-family: Georgia; padding: 20px;">
            <h1>Bot Output</h1>
            <pre style="background: #f0f0f0; padding: 20px; overflow: auto;">{output[:2000]}</pre>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1>❌ Error Running Bot</h1>
            <p>{str(e)}</p>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        '''

@app.route('/create-test')
def create_test():
    """Create a test article"""
    test_title = "Spruce Grove Gazette - Test Edition"
    test_html = """
    <h2>Welcome to the Spruce Grove Gazette!</h2>
    <p>Spruce Grove, AB — The Spruce Grove Gazette is officially launching today, bringing AI-powered local news to our community.</p>
    <h3>What We Cover</h3>
    <p>Our newsroom will deliver daily articles on:</p>
    <ul>
        <li>Local sports and recreation highlights</li>
        <li>School board decisions and student achievements</li>
        <li>New business openings and local entrepreneurs</li>
        <li>Community events and volunteer spotlights</li>
        <li>City council updates and development projects</li>
    </ul>
    <h3>Stay Connected</h3>
    <p>Subscribe to our newsletter to receive the Gazette directly in your inbox every morning at 5:00 AM.</p>
    <p>— The Spruce Grove Gazette</p>
    """
    
    save_article(test_title, test_html, datetime.now().strftime('%B %d, %Y'))
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test Article Created</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Test Article Created!</h1>
        <p>Visit <a href="/latest">/latest</a> to view it.</p>
        <a href="/latest">View Latest Dispatch →</a>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/debug')
def debug():
    article = load_article()
    return jsonify({
        "article_exists": article is not None,
        "article_title": article['title'] if article else None,
        "file_exists": os.path.exists(ARTICLE_FILE)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)