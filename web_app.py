"""
Spruce Grove Gazette - Web Status Page
This shows your bot's status and connects to your domain
"""

from flask import Flask, jsonify, send_file
import os
import glob
from datetime import datetime

app = Flask(__name__)

# Get the latest article file
def get_latest_article():
    html_files = glob.glob('spruce_grove_gazette_*.html')
    if html_files:
        latest = max(html_files, key=os.path.getctime)
        return latest
    return None

@app.route('/')
def home():
    """Main status page"""
    latest_article = get_latest_article()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Spruce Grove Gazette</title>
        <style>
            body {{
                font-family: Georgia, 'Times New Roman', serif;
                background: #f5f5f0;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 50px auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: #2C5F2D;
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 48px;
            }}
            .header p {{
                margin: 10px 0 0;
                opacity: 0.9;
            }}
            .content {{
                padding: 40px;
            }}
            .status {{
                background: #e8f5e9;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 30px;
            }}
            .status-badge {{
                display: inline-block;
                background: #27ae60;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            .info-box {{
                background: #f9f9f5;
                padding: 20px;
                border-left: 4px solid #2C5F2D;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background: #2C5F2D;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px;
            }}
            .button:hover {{
                background: #1a3d1a;
            }}
            .footer {{
                background: #1a3d1a;
                color: white;
                text-align: center;
                padding: 20px;
                font-size: 12px;
            }}
            .latest-article {{
                background: #f0f0f0;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📰 Spruce Grove Gazette</h1>
                <p>Your Hometown, Online | Established 1950</p>
            </div>
            
            <div class="content">
                <div class="status">
                    <span class="status-badge">● AI BOT RUNNING</span>
                    <p style="margin-top: 15px;">Automated news generation active</p>
                </div>
                
                <h2>About This Bot</h2>
                <p>This AI-powered newsroom automatically generates local news articles for Spruce Grove, Alberta using CrewAI agents.</p>
                
                <div class="info-box">
                    <strong>🤖 What it does:</strong><br>
                    • Researches local news, sports, and events<br>
                    • Fact-checks all information<br>
                    • Writes professional articles<br>
                    • Publishes in Gazette style<br>
                    • Runs daily on schedule
                </div>
                
                <h2>Latest Edition</h2>
                <div class="latest-article">
                    <strong>📅 Last generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
                    <strong>📊 Status:</strong> Active and running<br>
                    <a href="/latest" class="button">Read Latest Edition →</a>
                    <a href="/health" class="button" style="background: #666;">Health Check →</a>
                </div>
                
                <h2>Schedule</h2>
                <p>The bot runs daily at 8:00 AM Mountain Time, generating fresh local news for Spruce Grove residents.</p>
            </div>
            
            <div class="footer">
                <p>Spruce Grove, Alberta | Email: editor@sprucegrovegazette.com</p>
                <p>Powered by CrewAI | Automated Newsroom</p>
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
    return "No articles generated yet. The bot will create one soon!"

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    latest = get_latest_article()
    return jsonify({
        "status": "healthy",
        "bot": "spruce-grove-news-bot",
        "last_article": latest,
        "time": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/status')
def api_status():
    """JSON API for bot status"""
    return jsonify({
        "name": "Spruce Grove Gazette Bot",
        "status": "running",
        "type": "cron-job",
        "schedule": "Daily at 8:00 AM MT",
        "last_check": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)