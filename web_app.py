from flask import Flask
from datetime import datetime

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"

# Hardcoded test article - this WILL work
TEST_ARTICLE = """
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
"""

@app.route('/')
def home():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{NEWSPAPER_NAME}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            .header {{ background: #1a3d1a; color: white; padding: 40px; text-align: center; }}
            .logo h1 {{ font-size: 48px; }}
            .nav {{ background: #2C5F2D; padding: 15px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .main {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 60px 20px; text-align: center; border-radius: 10px; margin-bottom: 40px; }}
            .hero h2 {{ font-size: 42px; }}
            .btn {{ display: inline-block; background: #D4A017; color: #1a3d1a; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }}
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
        </div>
        <div class="main">
            <div class="hero">
                <h2>Your Hometown, Online.</h2>
                <p>Delivering trusted local news for Spruce Grove, Alberta</p>
                <a href="/latest" class="btn">Read Latest Dispatch →</a>
            </div>
        </div>
        <div class="footer">
            <p>📍 Spruce Grove, Alberta</p>
            <p>© 2026 {NEWSPAPER_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

@app.route('/latest')
def latest():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Latest Dispatch - {NEWSPAPER_NAME}</title>
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
        <div class="meta">📍 Spruce Grove, AB | 📅 {datetime.now().strftime('%B %d, %Y')}</div>
        {TEST_ARTICLE}
        <div class="footer">
            <a href="/" class="btn">← Back to Home</a>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)