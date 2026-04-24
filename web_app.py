"""
Spruce Grove Gazette - Simple Working Version
"""

import os
import requests
import subprocess
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"
LAUNCH_YEAR = 2026

# Store the latest article in memory
latest_article_html = None
latest_article_title = "Welcome to the Spruce Grove Gazette"
latest_article_date = datetime.now().strftime('%B %d, %Y')

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
            <a href="/run-bot">RUN BOT NOW</a>
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
    global latest_article_html, latest_article_title, latest_article_date
    
    if latest_article_html:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{latest_article_title} - {NEWSPAPER_NAME}</title>
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
            <div class="meta">📍 Spruce Grove, AB | 📅 {latest_article_date}</div>
            {latest_article_html}
            <div class="footer">
                <a href="/" class="btn">← Back to Home</a>
                <a href="/run-bot" class="btn" style="background: #D4A017; color: #1a3d1a;">↻ Generate New Article</a>
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
    import subprocess
    import re
    
    try:
        # Run the news generation script
        result = subprocess.run(['python', 'news_crew_enhanced.py'], 
                               capture_output=True, 
                               text=True, 
                               timeout=120)
        
        output = result.stdout
        
        # Extract the article HTML from the output
        article_match = re.search(r'<h2[^>]*>.*?</h2>.*?<p>.*?</p>.*?<p>.*?</p>', output, re.DOTALL)
        
        if article_match:
            global latest_article_html, latest_article_title, latest_article_date
            latest_article_html = article_match.group(0)
            
            # Extract title
            title_match = re.search(r'<h2[^>]*>(.*?)</h2>', latest_article_html)
            if title_match:
                latest_article_title = title_match.group(1)
            
            latest_article_date = datetime.now().strftime('%B %d, %Y')
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Article Generated</title></head>
            <body style="font-family: Georgia; text-align: center; padding: 50px;">
                <h1 style="color: #1a3d1a;">✅ Article Generated Successfully!</h1>
                <p>The latest dispatch has been created.</p>
                <a href="/latest" style="background: #1a3d1a; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">📰 Read Latest Dispatch →</a>
                <p><a href="/">← Back to Home</a></p>
            </body>
            </html>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Generation Issue</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1>⚠️ Issue Generating Article</h1>
            <p>The bot ran but didn't produce expected output. Check logs.</p>
            <pre style="text-align: left; background: #f0f0f0; padding: 20px; overflow: auto;">{output[:500]}</pre>
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

@app.route('/create-test-article')
def create_test_article():
    """Create a simple test article without running the full bot"""
    global latest_article_html, latest_article_title, latest_article_date
    
    latest_article_title = "Spruce Grove Gazette - Test Edition"
    latest_article_date = datetime.now().strftime('%B %d, %Y')
    latest_article_html = """
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
    <h3>Coming Soon</h3>
    <p>The first full AI-generated dispatch will appear here shortly. Our team is working to bring you the best local coverage.</p>
    <p>— The Spruce Grove Gazette</p>
    """
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test Article Created</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Test Article Created!</h1>
        <p>A test article has been created. Visit <a href="/latest">/latest</a> to see it.</p>
        <a href="/latest">View Latest Dispatch →</a>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/debug-files')
def debug_files():
    import glob
    return jsonify({
        "files": glob.glob('*'),
        "current_directory": os.getcwd()
    })

@app.route('/sw.js')
def sw():
    return 'self.addEventListener("fetch", () => {});', 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)