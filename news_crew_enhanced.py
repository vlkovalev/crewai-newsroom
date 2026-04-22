"""
Spruce Grove Gazette - Complete AI Newsroom
Features: Weather, Events, Letters, Photo Gallery, Social Sharing
"""

import os
import re
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================

GHOST_URL = os.environ.get('GHOST_URL', 'https://sprucegrovegazette-com.ghost.io')
GHOST_ADMIN_API_KEY = os.environ.get('GHOST_ADMIN_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Check if OpenAI API key is set
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    exit(1)

print("OpenAI API key found")

# ============================================
# Weather Data (Simulated - Replace with API)
# ============================================

def get_spruce_grove_weather():
    """Get weather forecast for Spruce Grove"""
    today = datetime.now()
    
    # In production, replace with actual API call to:
    # - Environment Canada API
    # - OpenWeatherMap
    # - WeatherAPI.com
    
    # Sample weather data (replace with real API)
    weather_data = {
        "current": {
            "temperature": 18,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind": "15 km/h SW"
        },
        "forecast": [
            {"day": "Today", "high": 20, "low": 8, "condition": "Sunny"},
            {"day": "Tomorrow", "high": 22, "low": 10, "condition": "Partly Cloudy"},
            {"day": "Wednesday", "high": 19, "low": 9, "condition": "Light Rain"},
            {"day": "Thursday", "high": 21, "low": 11, "condition": "Sunny"},
            {"day": "Friday", "high": 23, "low": 12, "condition": "Sunny"}
        ]
    }
    return weather_data

# ============================================
# Upcoming Events Calendar
# ============================================

def get_upcoming_events():
    """Get upcoming events in Spruce Grove"""
    # In production, replace with API calls to:
    # - City of Spruce Grove events calendar
    # - Local community boards
    # - Facebook Events API
    
    events = [
        {"name": "Spruce Grove Farmers Market", "date": datetime.now().strftime("%B %d, %Y"), "time": "10:00 AM - 3:00 PM", "location": "Downtown Spruce Grove", "description": "Local produce, crafts, and goods"},
        {"name": "City Council Meeting", "date": (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y"), "time": "7:00 PM", "location": "City Hall", "description": "Public welcome to attend"},
        {"name": "Youth Sports Registration", "date": (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y"), "time": "All day", "location": "Online", "description": "Spring soccer and baseball registration opens"},
        {"name": "Community Clean-Up Day", "date": (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y"), "time": "9:00 AM - 2:00 PM", "location": "Various locations", "description": "Help keep Spruce Grove beautiful"},
        {"name": "Public Library Story Time", "date": (datetime.now() + timedelta(days=2)).strftime("%B %d, %Y"), "time": "10:30 AM", "location": "Spruce Grove Public Library", "description": "Free children's program"}
    ]
    return events

# ============================================
# Letter to the Editor
# ============================================

def get_letter_to_editor():
    """Generate a sample letter to the editor"""
    # In production, this would come from user submissions
    letters = [
        {
            "author": "Margaret Thompson, Spruce Grove",
            "subject": "Thank you to our volunteers",
            "content": "I want to extend a heartfelt thank you to all the volunteers who made the Spring Festival a huge success. Your dedication makes Spruce Grove special.",
            "date": datetime.now().strftime("%B %d, %Y")
        },
        {
            "author": "James Wilson, Brookwood",
            "subject": "Crosswalk safety concerns",
            "content": "I'm writing to raise awareness about crosswalk safety on McLeod Avenue. Let's all work together to keep our pedestrians safe.",
            "date": datetime.now().strftime("%B %d, %Y")
        }
    ]
    return letters[0]  # Return most recent letter

# ============================================
# Photo Gallery Placeholders
# ============================================

def get_photo_gallery():
    """Get photo gallery placeholders"""
    # In production, these would be actual image URLs from:
    # - Cloud storage (AWS S3, Cloudinary)
    # - Local uploads
    # - Community submissions
    
    gallery = [
        {"title": "Spring Festival Celebration", "caption": "Residents enjoy the annual Spring Festival", "placeholder": "Community Event", "image_url": "https://via.placeholder.com/800x400/2C5F2D/ffffff?text=Spring+Festival"},
        {"title": "New Business Opening", "caption": "Main Street's newest local shop", "placeholder": "Local Business", "image_url": "https://via.placeholder.com/800x400/4A7C4B/ffffff?text=New+Business"},
        {"title": "Youth Sports Action", "caption": "Local soccer team in tournament play", "placeholder": "Youth Sports", "image_url": "https://via.placeholder.com/800x400/2C5F2D/ffffff?text=Youth+Sports"},
        {"title": "Community Volunteers", "caption": "Volunteers cleaning up the park", "placeholder": "Community Spirit", "image_url": "https://via.placeholder.com/800x400/4A7C4B/ffffff?text=Volunteers"}
    ]
    return gallery

# ============================================
# Gazette Style Guide
# ============================================

GAZETTE_STYLE_GUIDE = """
Spruce Grove Gazette Style Guide:

Voice & Tone:
- Warm and community-focused
- Professional but not stuffy
- Proud of Spruce Grove
- Informative and engaging

Article Structure:
1. Headline: Bold, engaging, 8-12 words
2. Lead paragraph with dateline
3. Body paragraphs with key details
4. Local impact section
5. Closing statement

Style Rules:
- Use active voice
- Keep sentences under 25 words
- Use local examples
"""

# ============================================
# Create AI Agents
# ============================================

print("Creating AI agents...")

researcher = Agent(
    role="Local News Researcher",
    goal=f"Research comprehensive news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}",
    backstory="""You are an experienced journalist covering:
    - Sports news (high school teams, local leagues)
    - School board updates
    - Business profiles and openings
    - Community spotlight and events
    - City council decisions
    - Development projects""",
    verbose=True,
    allow_delegation=False
)

fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts, dates, names, and locations",
    backstory="""You ensure accuracy across all content types.""",
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role="News Writer",
    goal="Write engaging articles in the Spruce Grove Gazette voice",
    backstory=f"""You create warm, professional content. Follow: {GAZETTE_STYLE_GUIDE}""",
    verbose=True,
    allow_delegation=False
)

editor = Agent(
    role="Senior Editor",
    goal="Polish and perfect the complete newspaper",
    backstory="""You ensure everything meets Gazette standards.""",
    verbose=True,
    allow_delegation=True
)

headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling headlines",
    backstory="""You master engaging, clickable headlines.""",
    verbose=True,
    allow_delegation=False
)

print("5 Agents created")

# ============================================
# Define Tasks
# ============================================

print("Creating tasks...")

research_task = Task(
    description=f"""Research local news for {datetime.now().strftime('%B %d, %Y')}.

    Find 5-7 stories covering:
    - Sports news (high school, youth, recreational)
    - School board updates and achievements
    - Business profiles and openings
    - Community spotlight and volunteers
    - City council and development
    
    For each: provide key facts, dates, locations, people involved, and local impact.
    """,
    agent=researcher,
    expected_output="Comprehensive research report with 5-7 local news stories."
)

fact_check_task = Task(
    description="Verify all facts across all stories. Check names, dates, locations.",
    agent=fact_checker,
    expected_output="Verified research report with all facts confirmed."
)

writing_task = Task(
    description="""Write a complete newspaper-style article.

    Include sections for:
    - Top news stories (3-4 paragraphs)
    - Sports roundup (2-3 paragraphs)
    - Schools and education (2-3 paragraphs)
    - Business news (2-3 paragraphs)
    - Community spotlight (2-3 paragraphs)
    
    Format with HTML: <h2> for headline, <h3> for sections, <p> for paragraphs.
    """,
    agent=writer,
    expected_output="Complete HTML article covering all local news sections."
)

editing_task = Task(
    description="Polish the article: fix grammar, ensure flow, verify HTML formatting.",
    agent=editor,
    expected_output="Polished, publication-ready HTML article."
)

headline_task = Task(
    description="Create 3 compelling headline options and select the best as final <h2>.",
    agent=headline_writer,
    expected_output="3 headline options with best one selected."
)

print("5 Tasks created")

# ============================================
# HTML Template Builder
# ============================================

def build_complete_html(news_content, weather, events, letter, gallery):
    """Build complete HTML page with all sections"""
    
    # Social sharing links
    current_url = "https://sprucegrovegazette.com"
    encoded_title = "Spruce Grove Gazette - Local News"
    encoded_url = current_url
    
    social_links = f"""
    <div class="social-share">
        <h4>Share this edition:</h4>
        <a href="https://www.facebook.com/sharer/sharer.php?u={encoded_url}" target="_blank" class="social-btn facebook">Facebook</a>
        <a href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}" target="_blank" class="social-btn twitter">Twitter</a>
        <a href="mailto:?subject={encoded_title}&body=Check out this week's Spruce Grove Gazette: {encoded_url}" class="social-btn email">Email</a>
    </div>
    """
    
    # Weather section
    weather_html = f"""
    <div class="weather-section">
        <h3>Spruce Grove Weather</h3>
        <div class="current-weather">
            <span class="temp">{weather['current']['temperature']}°C</span>
            <span class="condition">{weather['current']['condition']}</span>
            <span class="details">Humidity: {weather['current']['humidity']}% | Wind: {weather['current']['wind']}</span>
        </div>
        <div class="forecast">
            {"".join([f'<div class="forecast-day"><strong>{day["day"]}</strong><br>{day["high"]}°/{day["low"]}°<br>{day["condition"]}</div>' for day in weather['forecast']])}
        </div>
    </div>
    """
    
    # Events calendar
    events_html = f"""
    <div class="events-section">
        <h3>Upcoming Events</h3>
        <div class="events-list">
            {"".join([f'''
            <div class="event-item">
                <div class="event-date">{event["date"]}</div>
                <div class="event-details">
                    <strong>{event["name"]}</strong><br>
                    Time: {event["time"]} | Location: {event["location"]}<br>
                    <em>{event["description"]}</em>
                </div>
            </div>
            ''' for event in events])}
        </div>
    </div>
    """
    
    # Letter to editor
    letter_html = f"""
    <div class="letter-section">
        <h3>Letter to the Editor</h3>
        <div class="letter">
            <div class="letter-subject"><strong>Subject:</strong> {letter['subject']}</div>
            <div class="letter-content">"{letter['content']}"</div>
            <div class="letter-author">— {letter['author']}</div>
            <div class="letter-date">Date: {letter['date']}</div>
        </div>
        <p class="submit-letter"><a href="#">Submit your letter to the editor →</a></p>
    </div>
    """
    
    # Photo gallery
    gallery_html = f"""
    <div class="gallery-section">
        <h3>Spruce Grove in Photos</h3>
        <div class="photo-gallery">
            {"".join([f'''
            <div class="gallery-item">
                <img src="{photo['image_url']}" alt="{photo['title']}" loading="lazy">
                <div class="gallery-caption">
                    <strong>{photo['title']}</strong><br>
                    {photo['caption']}
                </div>
            </div>
            ''' for photo in gallery])}
        </div>
        <p class="photo-credit">Share your photos: photos@sprucegrovegazette.com</p>
    </div>
    """
    
    # Complete HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>
    <meta property="og:title" content="Spruce Grove Gazette">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{current_url}">
    <meta name="twitter:card" content="summary_large_image">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Georgia, 'Times New Roman', serif; background: #f5f5f0; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        
        /* Header */
        .header {{ background: #2C5F2D; color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 48px; margin-bottom: 10px; }}
        .header p {{ font-size: 18px; opacity: 0.9; }}
        .date {{ margin-top: 10px; font-style: italic; }}
        
        /* Navigation */
        .nav {{ background: #1a3d1a; padding: 15px; text-align: center; }}
        .nav a {{ color: white; margin: 0 15px; text-decoration: none; font-weight: bold; }}
        .nav a:hover {{ text-decoration: underline; }}
        
        /* Main content */
        .main-content {{ padding: 40px; }}
        
        /* Weather */
        .weather-section {{ background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
        .current-weather {{ text-align: center; margin-bottom: 20px; }}
        .temp {{ font-size: 48px; font-weight: bold; display: block; }}
        .forecast {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; text-align: center; }}
        .forecast-day {{ background: white; padding: 10px; border-radius: 5px; }}
        
        /* Events */
        .events-section {{ margin-bottom: 30px; }}
        .event-item {{ display: flex; gap: 20px; padding: 15px; border-bottom: 1px solid #ddd; }}
        .event-date {{ min-width: 120px; font-weight: bold; color: #2C5F2D; }}
        
        /* Letter */
        .letter-section {{ background: #f9f9f5; padding: 20px; border-left: 4px solid #2C5F2D; margin-bottom: 30px; }}
        .letter-content {{ font-style: italic; margin: 15px 0; font-size: 18px; }}
        .letter-author {{ font-weight: bold; margin-top: 10px; }}
        .submit-letter {{ margin-top: 15px; }}
        .submit-letter a {{ color: #2C5F2D; text-decoration: none; font-weight: bold; }}
        
        /* Gallery */
        .photo-gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .gallery-item {{ background: #f5f5f0; border-radius: 10px; overflow: hidden; }}
        .gallery-item img {{ width: 100%; height: 250px; object-fit: cover; }}
        .gallery-caption {{ padding: 15px; }}
        .photo-credit {{ text-align: center; font-size: 12px; color: #666; margin-top: 10px; }}
        
        /* Social sharing */
        .social-share {{ text-align: center; margin: 40px 0; padding: 20px; background: #f0f0f0; border-radius: 10px; }}
        .social-btn {{ display: inline-block; margin: 0 10px; padding: 10px 20px; text-decoration: none; border-radius: 5px; color: white; }}
        .social-btn.facebook {{ background: #3b5998; }}
        .social-btn.twitter {{ background: #1da1f2; }}
        .social-btn.email {{ background: #666; }}
        
        /* News article */
        .news-article {{ margin-bottom: 40px; }}
        .news-article h2 {{ color: #2C5F2D; margin: 20px 0 15px 0; }}
        .news-article h3 {{ color: #4A7C4B; margin: 20px 0 10px 0; }}
        .news-article p {{ margin-bottom: 15px; line-height: 1.8; }}
        
        /* Footer */
        .footer {{ background: #1a3d1a; color: white; text-align: center; padding: 30px; margin-top: 40px; }}
        .footer a {{ color: white; text-decoration: none; margin: 0 10px; }}
        
        @media (max-width: 768px) {{
            .main-content {{ padding: 20px; }}
            .event-item {{ flex-direction: column; gap: 5px; }}
            .forecast {{ grid-template-columns: repeat(2, 1fr); }}
            .photo-gallery {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Spruce Grove Gazette</h1>
            <p>Your Hometown, Online | Established 1950</p>
            <div class="date">Spruce Grove, AB | {datetime.now().strftime('%B %d, %Y')}</div>
        </div>
        
        <div class="nav">
            <a href="#">Home</a>
            <a href="#">News</a>
            <a href="#">Sports</a>
            <a href="#">Business</a>
            <a href="#">Community</a>
            <a href="#">Events</a>
            <a href="#">Opinion</a>
        </div>
        
        <div class="main-content">
            {weather_html}
            
            <div class="news-article">
                {news_content}
            </div>
            
            {events_html}
            
            {letter_html}
            
            {gallery_html}
            
            {social_links}
        </div>
        
        <div class="footer">
            <p>Email: editor@sprucegrovegazette.com</p>
            <p>Phone: (780) 123-4567</p>
            <p>123 Main Street, Spruce Grove, AB</p>
            <div style="margin-top: 20px;">
                <a href="#">About Us</a> | 
                <a href="#">Advertise</a> | 
                <a href="#">Subscribe</a> | 
                <a href="#">Contact</a>
            </div>
            <p style="margin-top: 20px;">Copyright {datetime.now().year} Spruce Grove Gazette. All rights reserved.</p>
            <p><small>Portions of this content generated by AI and reviewed by editorial staff</small></p>
        </div>
    </div>
</body>
</html>"""

# ============================================
# Create and Run the Crew
# ============================================

news_crew = Crew(
    agents=[researcher, fact_checker, writer, editor, headline_writer],
    tasks=[research_task, fact_check_task, writing_task, editing_task, headline_task],
    process=Process.sequential,
    verbose=True
)

print("\n" + "="*60)
print("Spruce Grove Gazette - Complete AI Newsroom")
print("="*60)
print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"Location: Spruce Grove, Alberta")
print(f"Sections: News | Sports | Business | Community")
print(f"Weather | Events | Letters | Gallery | Social")
print("="*60)
print("\nGenerating complete newspaper edition...\n")

# Get real-time data
print("Gathering real-time data...")
weather_data = get_spruce_grove_weather()
events_data = get_upcoming_events()
letter_data = get_letter_to_editor()
gallery_data = get_photo_gallery()
print(f"Weather: {weather_data['current']['temperature']}°C, {weather_data['current']['condition']}")
print(f"Events: {len(events_data)} upcoming")
print(f"Gallery: {len(gallery_data)} photos")

# Run the crew for news content
print("\nAI agents writing news content...\n")
result = news_crew.kickoff()
article_html = str(result)

# Build complete HTML page
print("\nBuilding complete newspaper page...")
complete_html = build_complete_html(article_html, weather_data, events_data, letter_data, gallery_data)

# Extract headline for title
title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette"

# Save the complete newspaper
output_file = f"spruce_grove_gazette_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(complete_html)

print("\n" + "="*60)
print("Complete Newspaper Edition Generated!")
print("="*60)
print(f"Saved to: {output_file}")
print(f"File size: {len(complete_html):,} characters")
print(f"Includes: Weather | Events | Letters | Gallery | Social Sharing")
print("="*60)

# Show preview of sections
print("\nEdition Contents:")
print(f"   Weather: {weather_data['current']['temperature']}°C, {weather_data['current']['condition']}")
print(f"   Events: {len(events_data)} local events")
print(f"   Letter from: {letter_data['author']}")
print(f"   Photos: {len(gallery_data)} community photos")
print(f"   Social: Facebook | Twitter | Email sharing")
print(f"   News: AI-generated local coverage")

print("\n" + "="*60)
print("Complete AI Newsroom session finished!")
print("Spruce Grove Gazette is ready to publish!")
print("="*60)