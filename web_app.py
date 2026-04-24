import os
from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

NEWSPAPER_NAME = "The Spruce Grove Gazette"
LAUNCH_DATE = "April 2026"

# ============================================
# REAL Parkland County News Articles
# ============================================

# FEATURED: Major Infrastructure Announcement
FEATURED_ARTICLE = {
    "title": "Province Pledges $136 Million for Parkland County Highway Upgrades",
    "date": "March 4, 2026",
    "source": "Parkland County Official News",
    "content": """
    <p>Parkland County, AB — The Government of Alberta's 2026 Budget confirms continued investment in two major transportation projects in Parkland County: improvements to Highway 60 and Highway 16, both essential to regional safety and economic growth.</p>
    
    <h3>Highway 60 Twinning and Overpass - $116 Million Investment</h3>
    <p>The Highway 60 project includes twinning the section between Highways 16 and 16A and constructing a rail overpass to reduce delays and improve safety along this key trade corridor. These upgrades will better support the heavy and highload traffic serving the Acheson Industrial Area — one of Alberta's most important economic engines.</p>
    
    <h3>Highway 16 Improvements - $20 Million Investment</h3>
    <p>The Province has reaffirmed its commitment to advancing Highway 16 improvements, with detailed design scheduled to begin in 2026 on a new interchange at Range Road 20. Planned upgrades will enhance safety and improve traffic flow along this high-speed corridor.</p>
    
    <p>"These investments are crucial for ensuring safer travel and supporting the people and industries that rely on our highways every day," said Mayor Rod Shaigec. "On behalf of the County, I express our sincere appreciation and look forward to continued collaboration as these projects move ahead."</p>
    """
}

# Article 2: Education
ARTICLE_2 = {
    "title": "Parkland School Division Receives $354,000 Annual Mental Health Grant",
    "date": "December 18, 2025",
    "source": "Parkland School Division",
    "content": """
    <p>Parkland County, AB — Parkland School Division's regular board meeting revealed major updates on mental health funding and student transportation services.</p>
    
    <h3>Mental Health Funding Secured</h3>
    <p>The division received approximately $834,000 through the Mental Health in School Pilot project over two years. Alberta Education has now added a wellbeing and mental health grant to the funding manual, with PSD receiving approximately $354,000 annually.</p>
    
    <p>"PSD will receive approximately $354,000 in the mental health grant for this school year, so the funding remains at the same level as was provided during the Mental Health in Schools Pilot," said Board Chair Lorraine Stewart.</p>
    
    <h3>Transportation Updates</h3>
    <p>PSD is now transporting over 8,000 students, a 1.4% increase from the previous year. Gail Lewis, Director of Transportation Services, noted increasing requests tied to family circumstances such as alternate addresses, child care, and joint custody.</p>
    
    <p>The division is also seeing more students requiring mobility supports and specialized equipment, as well as more complex emotional behavioral needs.</p>
    """
}

# Article 3: Environment
ARTICLE_3 = {
    "title": "Parkland County Secures $200,000 Grant for Sturgeon River Watershed Protection",
    "date": "May 27, 2025",
    "source": "Parkland County Council",
    "content": """
    <p>Parkland County, AB — Parkland County was recently successful in receiving $200,000 in grant funding through the Alberta Community Partnership Program, on behalf of the Sturgeon River Watershed Alliance.</p>
    
    <p>This opportunity supports regional collaboration and capacity building for implementation of the Sturgeon River Watershed Management Plan initiatives.</p>
    
    <h3>Grant Components</h3>
    <ul>
        <li><strong>$80,000</strong> - Watershed scale water quality evaluation</li>
        <li><strong>$120,000</strong> - Infrastructure Management Framework for Watershed Health</li>
    </ul>
    
    <p>The Sturgeon River Watershed Alliance brings together municipalities to protect water quality and watershed health across the region.</p>
    """
}

# Article 4: Recreation Infrastructure
ARTICLE_4 = {
    "title": "Tri Leisure Centre Receives $235,313 Grant for Boiler Replacement",
    "date": "December 9, 2025",
    "source": "Parkland County Council",
    "content": """
    <p>Parkland County, AB — Council has approved grant funds for energy reduction projects at the Tri Leisure Centre, including a boiler replacement project partially funded by a $235,313 grant.</p>
    
    <p>Council also approved the use of the Tri Leisure Centre Restricted Reserve up to $250,000 to fund the portion of the project not covered by the grant.</p>
    
    <p>The project represents a significant step in reducing energy consumption at the regional recreation facility, which serves residents across Parkland County and surrounding communities.</p>
    """
}

# Article 5: Emergency Services
ARTICLE_5 = {
    "title": "Council Approves $250,000 for Fire Tanker Replacement",
    "date": "December 9, 2025",
    "source": "Parkland County Council",
    "content": """
    <p>Parkland County, AB — Parkland County Council has approved $250,000 in additional funding from the Lifecycle Restricted Surplus Account for the replacement of a fire water tanker truck for Fire District 1.</p>
    
    <p>The new tanker will enhance the fire department's capacity to respond to emergencies throughout the county. Fire District 1 serves a significant portion of Parkland County's population and industrial areas.</p>
    
    <p>This investment is part of ongoing efforts to ensure emergency services have modern, reliable equipment to protect residents and property.</p>
    """
}

# Article 6: Upcoming Public Hearing
ARTICLE_6 = {
    "title": "Public Hearing Set for March 24 on Proposed Road Closure",
    "date": "March 10, 2026",
    "source": "Parkland County",
    "content": """
    <p>Parkland County, AB — A public hearing has been scheduled for March 24, 2026, regarding Bylaw 2026-13, which proposes to close a portion of road for sale in Parkland County.</p>
    
    <p><strong>Hearing Details:</strong><br>
    Date: March 24, 2026<br>
    Time: 10:30 a.m.<br>
    Location: Parkland County Council Chambers, 53109A Hwy 779</p>
    
    <p>The affected road portion is located within NW 28-53-4-W5, as shown on Plan 1620765. Written submissions must be received by 4:00 p.m. on March 20, 2026.</p>
    
    <p>This is a formal Public Hearing, and Council is prepared to hear submissions from those who wish to speak to the proposed Bylaw. Verbal presentations will be limited to 10 minutes.</p>
    """
}

# Article 7: Council Proclamations
ARTICLE_7 = {
    "title": "Parkland County Recognizes November as Family Violence Prevention Month",
    "date": "September 9, 2025",
    "source": "Parkland County Council",
    "content": """
    <p>Parkland County, AB — Parkland County Council has officially proclaimed several awareness campaigns for November 2025, recognizing the importance of community health and safety.</p>
    
    <h3>November 2025 Proclamations:</h3>
    <ul>
        <li>Family Violence Prevention Month</li>
        <li>Seniors' Fall Prevention Month</li>
        <li>Restorative Justice Week</li>
        <li>GIS Day</li>
        <li>World Pancreatic Cancer Day</li>
    </ul>
    
    <p>"Parkland County supports recognized public campaigns for its community by proclamation," according to council documents. The proclamations acknowledge the work of non-profit organizations and community groups raising awareness on these important issues.</p>
    """
}

# Article 8: Senior's Tax Assistance
ARTICLE_8 = {
    "title": "County to Promote Seniors Property Tax Deferral Program",
    "date": "December 9, 2025",
    "source": "Parkland County Council",
    "content": """
    <p>Parkland County, AB — Council has directed administration to proceed with promoting the Seniors Property Tax Deferral Program available through the province.</p>
    
    <p>The program allows eligible senior homeowners to defer all or part of their annual property taxes. The deferred amount becomes a debt on the property that is repaid when the home is sold or transferred.</p>
    
    <p>Administration will work to raise awareness of this option among Parkland County seniors who may benefit from the program.</p>
    """
}

def get_weather():
    return {
        "current": {
            "temp": 18,
            "feels_like": 17,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind": 15,
            "uv": 5,
            "visibility": 16,
            "icon": "🌤️"
        },
        "forecast": [
            {"day": "Mon", "high": 20, "low": 8, "condition": "Sunny", "icon": "☀️"},
            {"day": "Tue", "high": 22, "low": 10, "condition": "Partly Cloudy", "icon": "⛅"},
            {"day": "Wed", "high": 19, "low": 9, "condition": "Light Rain", "icon": "🌧️"},
            {"day": "Thu", "high": 21, "low": 11, "condition": "Sunny", "icon": "☀️"},
            {"day": "Fri", "high": 23, "low": 12, "condition": "Sunny", "icon": "☀️"}
        ]
    }

def get_events():
    return [
        {"name": "Public Hearing - Bylaw 2026-13", "date": "March 24, 2026", "location": "Council Chambers", "time": "10:30 AM"},
        {"name": "Parkland County Council Meeting", "date": "Regular Schedule", "location": "County Centre", "time": "9:00 AM"},
        {"name": "Toddler Storytime", "date": "Weekly", "location": "Parkland Community Library", "time": "10:00 AM"}
    ]

def get_gallery():
    return [
        {"title": "Highway 60 Twinning Project", "caption": "$116 million investment for safer travel"},
        {"title": "PSD Mental Health Program", "caption": "$354,000 annual grant for student wellbeing"},
        {"title": "Sturgeon River Watershed", "caption": "$200,000 for water quality protection"},
        {"title": "Tri Leisure Centre", "caption": "$235,313 grant for boiler replacement"}
    ]

classifieds = []
subscribers = []

@app.route('/')
def home():
    weather = get_weather()
    events = get_events()
    gallery = get_gallery()
    
    gallery_html = ''.join([f'<div class="gallery-item"><div class="gallery-placeholder">{p["title"]}</div><p><strong>{p["title"]}</strong><br>{p["caption"]}</p></div>' for p in gallery])
    events_html = ''.join([f'<li><strong>{e["name"]}</strong><br>{e["date"]} at {e["time"]}<br>📍 {e["location"]}</li>' for e in events])
    
    forecast_html = ''.join([f'''
        <div class="forecast-day">
            <div class="forecast-day-name">{f["day"]}</div>
            <div class="forecast-icon">{f["icon"]}</div>
            <div class="forecast-temp">{f["high"]}° / {f["low"]}°</div>
        </div>
    ''' for f in weather['forecast']])
    
    # Build the "More News" grid with real articles
    more_news_grid = f'''
        <div class="news-card">
            <h3>{ARTICLE_2['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_2['date']}</div>
            <p>{ARTICLE_2['content'][:200]}...</p>
        </div>
        <div class="news-card">
            <h3>{ARTICLE_3['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_3['date']}</div>
            <p>{ARTICLE_3['content'][:200]}...</p>
        </div>
        <div class="news-card">
            <h3>{ARTICLE_4['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_4['date']}</div>
            <p>{ARTICLE_4['content'][:200]}...</p>
        </div>
        <div class="news-card">
            <h3>{ARTICLE_5['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_5['date']}</div>
            <p>{ARTICLE_5['content'][:200]}...</p>
        </div>
        <div class="news-card">
            <h3>{ARTICLE_6['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_6['date']}</div>
            <p>{ARTICLE_6['content'][:200]}...</p>
        </div>
        <div class="news-card">
            <h3>{ARTICLE_7['title']}</h3>
            <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_7['date']}</div>
            <p>{ARTICLE_7['content'][:200]}...</p>
        </div>
    '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{NEWSPAPER_NAME} - Parkland County's Trusted News Source</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1a3d1a; --primary-light: #2C5F2D; --accent: #D4A017; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Georgia', serif; background: #f9f9f5; }}
            
            .top-bar {{ background: var(--primary); color: white; font-size: 12px; padding: 8px 0; text-align: center; }}
            .header {{ background: white; padding: 30px 20px; text-align: center; border-bottom: 3px solid var(--accent); }}
            .logo h1 {{ font-size: 48px; color: var(--primary); }}
            .logo p {{ font-size: 14px; color: #666; letter-spacing: 2px; }}
            .date-header {{ background: #f0f0e8; padding: 10px; text-align: center; font-size: 14px; }}
            
            .nav {{ background: var(--primary); padding: 15px; text-align: center; position: sticky; top: 0; z-index: 100; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; text-transform: uppercase; font-size: 13px; }}
            .nav a:hover {{ color: var(--accent); }}
            
            .hero {{ background: linear-gradient(135deg, #1a3d1a, #2C5F2D); color: white; padding: 40px 20px; text-align: center; }}
            .hero h2 {{ font-size: 36px; }}
            .hero p {{ font-size: 16px; margin-top: 10px; }}
            .search-bar {{ max-width: 500px; margin: 20px auto 0; display: flex; gap: 10px; }}
            .search-bar input {{ flex: 1; padding: 12px; border: none; border-radius: 5px; }}
            .search-bar button {{ background: var(--accent); color: var(--primary); padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            
            .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            
            .featured-article {{ background: white; border-radius: 10px; padding: 30px; margin-bottom: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .featured-article h2 {{ color: var(--primary); margin-bottom: 15px; font-size: 28px; }}
            .featured-article h3 {{ color: var(--primary-light); margin: 20px 0 10px; }}
            .featured-article p {{ line-height: 1.8; margin-bottom: 15px; }}
            .article-meta {{ color: #666; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 15px; font-size: 14px; }}
            .article-source {{ color: var(--accent); font-size: 12px; margin-bottom: 15px; }}
            
            .more-news {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 30px; margin-bottom: 40px; }}
            .news-card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.3s; }}
            .news-card:hover {{ transform: translateY(-3px); }}
            .news-card h3 {{ color: var(--primary); margin-bottom: 10px; font-size: 18px; }}
            .news-card-date {{ color: #999; font-size: 11px; margin-bottom: 15px; }}
            .news-card p {{ color: #555; line-height: 1.5; font-size: 14px; }}
            
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
            .stat-card {{ background: white; padding: 30px; text-align: center; border-radius: 10px; transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-number {{ font-size: 36px; font-weight: bold; color: var(--primary); }}
            
            .two-column {{ display: grid; grid-template-columns: 2fr 1fr; gap: 40px; margin-bottom: 40px; }}
            .section-title {{ font-size: 24px; color: var(--primary); border-left: 4px solid var(--accent); padding-left: 15px; margin-bottom: 20px; }}
            .feature-card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .btn {{ display: inline-block; background: var(--primary); color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-top: 15px; transition: background 0.3s; }}
            .btn:hover {{ background: #0d260d; }}
            
            .weather-widget {{ background: linear-gradient(135deg, #1e3c72, #2a5298); border-radius: 15px; padding: 20px; color: white; margin-bottom: 30px; }}
            .weather-header {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            .weather-main {{ text-align: center; }}
            .weather-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .weather-temp {{ font-size: 48px; font-weight: bold; }}
            .weather-temp small {{ font-size: 18px; }}
            .weather-details {{ display: flex; justify-content: space-around; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); }}
            .forecast-day {{ text-align: center; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 8px; }}
            
            .gallery {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
            .gallery-item {{ background: white; border-radius: 10px; padding: 15px; text-align: center; }}
            .gallery-placeholder {{ background: var(--primary-light); color: white; padding: 40px; border-radius: 8px; margin-bottom: 10px; }}
            
            .newsletter {{ background: linear-gradient(135deg, var(--primary), #0d260d); color: white; padding: 40px; border-radius: 15px; text-align: center; margin: 40px 0; }}
            .newsletter input {{ padding: 12px; width: 250px; border: none; border-radius: 5px; margin: 10px; }}
            .newsletter button {{ background: var(--accent); color: var(--primary); padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }}
            
            .social-section {{ background: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 40px; }}
            .social-links {{ display: flex; justify-content: center; gap: 15px; margin-top: 20px; flex-wrap: wrap; }}
            .social-btn {{ padding: 10px 20px; border-radius: 25px; text-decoration: none; color: white; }}
            .social-btn.twitter {{ background: #1DA1F2; }}
            .social-btn.facebook {{ background: #3b5998; }}
            .social-btn.email {{ background: #666; }}
            
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 40px; margin-top: 40px; }}
            .footer-content {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 1200px; margin: 0 auto; }}
            .footer-column a {{ color: #ccc; text-decoration: none; display: block; margin-bottom: 8px; font-size: 14px; }}
            .footer-column a:hover {{ color: var(--accent); }}
            .copyright {{ text-align: center; padding-top: 30px; margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; }}
            
            @media (max-width: 768px) {{
                .more-news {{ grid-template-columns: 1fr; }}
                .stats {{ grid-template-columns: repeat(2, 1fr); }}
                .two-column {{ grid-template-columns: 1fr; }}
                .footer-content {{ grid-template-columns: repeat(2, 1fr); }}
                .hero h2 {{ font-size: 24px; }}
                .gallery {{ grid-template-columns: 1fr; }}
                .featured-article h2 {{ font-size: 22px; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">🌿 Serving Spruce Grove & Parkland County | "Your Hometown, Online."</div>
        
        <div class="header">
            <div class="logo">
                <h1>📰 {NEWSPAPER_NAME}</h1>
                <p>ESTABLISHED {LAUNCH_DATE} | INDEPENDENT & LOCAL</p>
                <div style="font-size: 12px; color: #D4A017; margin-top: 5px;">Serving Spruce Grove, Parkland County, Stony Plain & surrounding areas</div>
            </div>
        </div>
        
        <div class="date-header">📍 Spruce Grove, Alberta | {datetime.now().strftime('%A, %B %d, %Y')}</div>
        
        <div class="nav">
            <a href="/">🏠 HOME</a>
            <a href="/classifieds">📋 CLASSIFIEDS</a>
            <a href="/post-ad">📝 POST AN AD</a>
            <a href="/subscribe">✉️ NEWSLETTER</a>
        </div>
        
        <div class="hero">
            <h2>Your Hometown, Online.</h2>
            <p>Serving Spruce Grove, Parkland County, Stony Plain and surrounding areas</p>
            <form class="search-bar" action="/search" method="GET">
                <input type="text" name="q" placeholder="Search Gazette dispatches, events, and archives...">
                <button type="submit"><i class="fas fa-search"></i> Search</button>
            </form>
        </div>
        
        <div class="main-content">
            <!-- Featured Article -->
            <div class="featured-article">
                <div class="article-meta">📍 Parkland County | 📅 {FEATURED_ARTICLE['date']}</div>
                <div class="article-source">Source: {FEATURED_ARTICLE['source']}</div>
                <h2>{FEATURED_ARTICLE['title']}</h2>
                {FEATURED_ARTICLE['content']}
            </div>
            
            <!-- More News Grid -->
            <h2 class="section-title">📰 More Parkland County News</h2>
            <div class="more-news">
                {more_news_grid}
                <div class="news-card">
                    <h3>{ARTICLE_8['title']}</h3>
                    <div class="news-card-date">📍 Parkland County | 📅 {ARTICLE_8['date']}</div>
                    <p>{ARTICLE_8['content'][:200]}...</p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card"><i class="fas fa-newspaper"></i><div class="stat-number">8</div><div>Dispatches</div></div>
                <div class="stat-card"><i class="fas fa-tags"></i><div class="stat-number">6</div><div>Categories</div></div>
                <div class="stat-card"><i class="fas fa-users"></i><div class="stat-number">{len(subscribers)}</div><div>Subscribers</div></div>
                <div class="stat-card"><i class="fas fa-clock"></i><div class="stat-number">5 AM</div><div>Daily Delivery</div></div>
            </div>
            
            <div class="two-column">
                <div>
                    <h2 class="section-title">📸 Parkland County in Photos</h2>
                    <div class="gallery">{gallery_html}</div>
                </div>
                
                <div>
                    <div class="weather-widget">
                        <div class="weather-header">
                            <span><i class="fas fa-map-marker-alt"></i> Spruce Grove, AB</span>
                            <span>{datetime.now().strftime('%A')}</span>
                        </div>
                        <div class="weather-main">
                            <div class="weather-icon">{weather['current']['icon']}</div>
                            <div class="weather-temp">{weather['current']['temp']}<small>°C</small></div>
                            <div>{weather['current']['condition']}</div>
                            <div style="font-size: 14px; opacity: 0.8;">Feels like {weather['current']['feels_like']}°C</div>
                        </div>
                        <div class="weather-details">
                            <div class="weather-detail"><i class="fas fa-tint"></i><br>{weather['current']['humidity']}%<br><small>Humidity</small></div>
                            <div class="weather-detail"><i class="fas fa-wind"></i><br>{weather['current']['wind']}<br><small>km/h</small></div>
                            <div class="weather-detail"><i class="fas fa-sun"></i><br>{weather['current']['uv']}<br><small>UV Index</small></div>
                            <div class="weather-detail"><i class="fas fa-eye"></i><br>{weather['current']['visibility']}<br><small>km</small></div>
                        </div>
                        <div class="forecast">
                            {forecast_html}
                        </div>
                    </div>
                    
                    <h2 class="section-title">📅 Upcoming Public Hearings & Events</h2>
                    <div class="feature-card">
                        <ul style="list-style: none;">{events_html}</ul>
                    </div>
                    
                    <h2 class="section-title">📱 Install Our App</h2>
                    <div class="feature-card" style="text-align: center;">
                        <i class="fas fa-mobile-alt" style="font-size: 48px; color: var(--primary);"></i>
                        <p>Add the Gazette to your home screen for quick access.</p>
                        <button class="btn" onclick="alert('To install: Tap Share then Add to Home Screen')">📲 Install App</button>
                    </div>
                </div>
            </div>
            
            <div class="newsletter">
                <h3>✉️ Never Miss an Edition</h3>
                <p>Get the Spruce Grove Gazette delivered to your inbox every morning.</p>
                <form action="/do-subscribe" method="POST">
                    <input type="email" name="email" placeholder="Enter your email address" required>
                    <button type="submit">Subscribe Free →</button>
                </form>
            </div>
            
            <div class="social-section">
                <h3>📱 Follow The Gazette</h3>
                <div class="social-links">
                    <a href="https://twitter.com/intent/tweet?text=Spruce Grove Gazette&url=https://sprucegrovegazette.com" target="_blank" class="social-btn twitter"><i class="fab fa-twitter"></i> Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=https://sprucegrovegazette.com" target="_blank" class="social-btn facebook"><i class="fab fa-facebook-f"></i> Facebook</a>
                    <a href="mailto:?subject=Spruce Grove Gazette&body=Check out this local news source: https://sprucegrovegazette.com" class="social-btn email"><i class="fas fa-envelope"></i> Email</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <div class="footer-column">
                    <h4>📰 The Gazette</h4>
                    <a href="/">Home</a>
                    <a href="/classifieds">Classifieds</a>
                    <a href="/subscribe">Newsletter</a>
                </div>
                <div class="footer-column">
                    <h4>📬 Connect</h4>
                    <a href="/post-ad">Post an Ad</a>
                    <a href="mailto:editor@sprucegrovegazette.com">editor@sprucegrovegazette.com</a>
                </div>
                <div class="footer-column">
                    <h4>🔗 Resources</h4>
                    <a href="https://www.parklandcounty.com" target="_blank">Parkland County</a>
                    <a href="https://www.psd.ca" target="_blank">Parkland School Division</a>
                </div>
                <div class="footer-column">
                    <h4>📍 Our Region</h4>
                    <a href="#">Spruce Grove</a>
                    <a href="#">Parkland County</a>
                    <a href="#">Stony Plain</a>
                </div>
            </div>
            <div class="copyright">
                <p>© {datetime.now().year} {NEWSPAPER_NAME}. All rights reserved.</p>
                <p>Serving Spruce Grove, Parkland County, and surrounding areas since {LAUNCH_DATE}</p>
            </div>
        </div>
    </body>
    </html>
    '''

# ============================================
# Classifieds Routes (same as before)
# ============================================

@app.route('/classifieds')
def classifieds_page():
    category = request.args.get('category', 'all')
    
    filtered = classifieds
    if category != 'all':
        filtered = [c for c in classifieds if c['category'] == category]
    
    categories = [
        {"id": "all", "name": "All Categories", "icon": "📋"},
        {"id": "jobs", "name": "Jobs", "icon": "💼"},
        {"id": "sale", "name": "For Sale", "icon": "🏷️"},
        {"id": "housing", "name": "Housing", "icon": "🏠"},
        {"id": "services", "name": "Services", "icon": "🔧"},
        {"id": "garage", "name": "Garage Sales", "icon": "🏪"}
    ]
    
    categories_html = ''.join([f'<a href="/classifieds?category={c["id"]}" class="filter-btn {"active" if category == c["id"] else ""}">{c["icon"]} {c["name"]}</a>' for c in categories])
    
    if filtered:
        classifieds_html = ''.join([f'''
            <div class="classified-card">
                <span class="classified-category">{c["category"].upper()}</span>
                <h3>{c["title"]}</h3>
                <p>{c["description"]}</p>
                <div class="classified-price">{c["price"]}</div>
                <small>Contact: {c["contact"]} | Posted: {c["date"]}</small>
            </div>
        ''' for c in filtered])
    else:
        classifieds_html = '<p style="text-align: center; color: #666;">No classifieds yet. Be the first to <a href="/post-ad">post an ad</a>!</p>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Classifieds - {NEWSPAPER_NAME}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: Georgia, serif; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .nav {{ background: #2C5F2D; padding: 12px; text-align: center; }}
            .nav a {{ color: white; margin: 0 15px; text-decoration: none; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
            .category-filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; }}
            .filter-btn {{ background: white; padding: 10px 20px; border: 1px solid #ddd; border-radius: 25px; text-decoration: none; color: #333; }}
            .filter-btn.active {{ background: #1a3d1a; color: white; border-color: #1a3d1a; }}
            .classified-card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .classified-category {{ display: inline-block; background: #D4A017; color: #1a3d1a; padding: 3px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; }}
            .classified-price {{ color: #D4A017; font-size: 20px; font-weight: bold; margin: 10px 0; }}
            .post-ad-btn {{ background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
            @media (max-width: 768px) {{
                .container {{ padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <p>Classifieds • Trade • Employment</p>
        </div>
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/classifieds">📋 Classifieds</a>
            <a href="/post-ad">📝 Post an Ad</a>
        </div>
        <div class="container">
            <h2>📋 Classifieds</h2>
            <div class="category-filters">{categories_html}</div>
            {classifieds_html}
            <div style="text-align: center; margin-top: 30px;">
                <a href="/post-ad" class="post-ad-btn">📝 Post an Ad →</a>
            </div>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} {NEWSPAPER_NAME} | "Your Hometown, Online."</p>
        </div>
    </body>
    </html>
    '''

@app.route('/post-ad', methods=['GET', 'POST'])
def post_ad():
    if request.method == 'POST':
        new_ad = {
            "id": len(classifieds) + 1,
            "category": request.form.get('category'),
            "title": request.form.get('title'),
            "description": request.form.get('description'),
            "price": request.form.get('price'),
            "contact": request.form.get('contact'),
            "date": datetime.now().strftime('%b %d, %Y')
        }
        classifieds.insert(0, new_ad)
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Ad Posted</title></head>
        <body style="font-family: Georgia; text-align: center; padding: 50px;">
            <h1 style="color: #1a3d1a;">✅ Ad Posted Successfully!</h1>
            <p>Your classified ad has been submitted.</p>
            <a href="/classifieds" style="color: #1a3d1a;">← View Classifieds</a>
        </body>
        </html>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Post an Ad - {NEWSPAPER_NAME}</title>
        <style>
            body {{ font-family: Georgia, serif; background: #f9f9f5; margin: 0; }}
            .header {{ background: #1a3d1a; color: white; padding: 20px; text-align: center; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .form-card {{ background: white; padding: 30px; border-radius: 10px; }}
            input, select, textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; font-family: inherit; }}
            button {{ background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .footer {{ background: #0d260d; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📰 {NEWSPAPER_NAME}</h1>
            <p>Post a Classified Ad</p>
        </div>
        <div class="container">
            <div class="form-card">
                <h2>📝 Post an Ad</h2>
                <p>Reach the Spruce Grove and Parkland County community.</p>
                <form method="POST">
                    <select name="category" required>
                        <option value="">Select Category</option>
                        <option value="jobs">💼 Jobs / Employment</option>
                        <option value="sale">🏷️ For Sale</option>
                        <option value="housing">🏠 Housing / Rentals</option>
                        <option value="services">🔧 Services</option>
                        <option value="garage">🏪 Garage Sale</option>
                    </select>
                    <input type="text" name="title" placeholder="Ad Title" required>
                    <textarea name="description" rows="5" placeholder="Describe what you are offering..." required></textarea>
                    <input type="text" name="price" placeholder="Price (e.g., $250 or Best Offer)">
                    <input type="text" name="contact" placeholder="Contact info (phone, email)" required>
                    <button type="submit">📢 Post Ad →</button>
                </form>
                <a href="/classifieds">← Back to Classifieds</a>
            </div>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} {NEWSPAPER_NAME} | "Your Hometown, Online."</p>
        </div>
    </body>
    </html>
    '''

@app.route('/subscribe')
def subscribe():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subscribe - Spruce Grove Gazette</title>
        <style>
            body { font-family: Georgia, serif; background: #f9f9f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .container { background: white; padding: 40px; border-radius: 10px; max-width: 400px; text-align: center; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #1a3d1a; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Subscribe to The Gazette</h1>
            <p>Get local news delivered to your inbox every morning.</p>
            <form action="/do-subscribe" method="POST">
                <input type="email" name="email" placeholder="Your email address" required>
                <button type="submit">Subscribe →</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/do-subscribe', methods=['POST'])
def do_subscribe():
    email = request.form.get('email')
    if email:
        subscribers.append({"email": email, "date": datetime.now().strftime('%Y-%m-%d')})
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Subscribed</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1 style="color: #1a3d1a;">✅ Subscribed!</h1>
        <p>Thank you for subscribing to the Spruce Grove Gazette.</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/search')
def search():
    query = request.args.get('q', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Search Results</title></head>
    <body style="font-family: Georgia; text-align: center; padding: 50px;">
        <h1>🔍 Search Results for: "{query}"</h1>
        <p>Search functionality coming soon. Check back later!</p>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)