"""
Spruce Grove Gazette - Enhanced AI Newsroom
Multi-agent crew for generating local news articles
"""

import os
import re
from datetime import datetime
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
    print("❌ ERROR: OPENAI_API_KEY environment variable is not set!")
    exit(1)

print("✅ OpenAI API key found")

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
- Use "we" and "our" when referring to the community

Article Structure:
1. Headline: Bold, engaging, 8-12 words
2. Dateline: "Spruce Grove, AB —" at start of first paragraph
3. Lead paragraph: Answers who, what, when, where, why
4. Body: 2-3 short paragraphs with key details
5. Local impact: Explain how this matters to residents
6. Closing: Forward-looking statement

Style Rules:
- Use active voice
- Keep sentences under 25 words
- Use local examples
- End with "— The Spruce Grove Gazette"
"""

# ============================================
# Create AI Agents
# ============================================

print("🤖 Creating AI agents...")

# Agent 1: Researcher (Enhanced for multiple topics)
researcher = Agent(
    role="Local News Researcher",
    goal=f"Find current, factual local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')} across multiple categories",
    backstory="""You are an experienced journalist who knows Spruce Grove, Alberta inside and out.
    You specialize in covering:
    - Sports news (high school teams, local leagues, tournaments)
    - School board updates (decisions, events, achievements)
    - Business profiles (new openings, expansions, success stories)
    - Community spotlight (local heroes, volunteers, organizations)
    - City council decisions
    - Development projects
    - Cultural events
    
    You focus on stories that matter to residents and highlight the best of Spruce Grove.""",
    verbose=True,
    allow_delegation=False
)

# Agent 2: Fact Checker
fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts, dates, names, and locations in the research",
    backstory="""You are a meticulous fact-checker who verifies every claim, double-checks names and dates, 
    and ensures accuracy before publication. You never let a factual error slip through.
    You pay special attention to sports statistics, school board decisions, and business information.""",
    verbose=True,
    allow_delegation=False
)

# Agent 3: Writer
writer = Agent(
    role="News Writer",
    goal="Write engaging, well-structured news articles in the Spruce Grove Gazette voice",
    backstory=f"""You are an award-winning journalist who writes in a warm, professional voice that residents trust.
    You excel at making all topics engaging - from sports highlights to school board meetings to business features.
    
    Follow this style guide:
    {GAZETTE_STYLE_GUIDE}""",
    verbose=True,
    allow_delegation=False
)

# Agent 4: Editor
editor = Agent(
    role="Senior Editor",
    goal="Review, polish, and ensure the article meets Gazette standards",
    backstory="""You are the Senior Editor with 30 years of experience. You have an eagle eye for errors, 
    style inconsistencies, and tone issues. You ensure every article is worthy of the Gazette's reputation.
    You maintain consistency across all topic areas.""",
    verbose=True,
    allow_delegation=True
)

# Agent 5: Headline Specialist
headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling, clickable headlines that capture the essence of the article",
    backstory="""You are a master of the headline. You know how to grab attention while staying truthful.
    Your headlines are clear, clever, and community-focused. You can write great headlines for sports,
    business, education, and community news alike.""",
    verbose=True,
    allow_delegation=False
)

print("✅ 5 Agents created")

# ============================================
# Define Enhanced Tasks with More Topics
# ============================================

print("📋 Creating tasks with expanded local coverage...")

# Task 1: Research (Expanded with 5 categories)
research_task = Task(
    description=f"""Research current local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}.

    Find 5-7 local news stories covering these categories:

    1. SPORTS NEWS:
       - High school sports (Panthers, Lakers, etc.)
       - Local tournaments or championships
       - Youth sports achievements
       - Recreational league highlights
       - Individual athlete accomplishments

    2. SCHOOL BOARD UPDATES:
       - Parkland School Division decisions
       - New programs or initiatives
       - Student achievements and awards
       - School events and fundraisers
       - Teacher or staff recognition

    3. BUSINESS PROFILES:
       - New business openings
       - Business expansions or relocations
       - Local entrepreneur success stories
       - Business anniversaries (5, 10, 25 years)
       - Unique local shops or services

    4. COMMUNITY SPOTLIGHT:
       - Local heroes or volunteers
       - Community organizations making an impact
       - Fundraising efforts
       - Neighborhood initiatives
       - Senior or youth recognition

    5. GENERAL LOCAL NEWS:
       - City council decisions
       - Development projects
       - Infrastructure updates
       - Community events and festivals
       - Public safety information

    For each story, provide:
    - Clear, factual headline
    - What happened (key details)
    - When it happened or will happen
    - Where in Spruce Grove
    - Who is involved (names, roles)
    - Why it matters to residents
    - Sources (where you found the info)

    Prioritize recent and upcoming events.
    """,
    agent=researcher,
    expected_output="A comprehensive research report with 5-7 local news stories covering sports, schools, business, community, and general news with all key facts, dates, locations, and sources."
)

# Task 2: Fact Check (Enhanced)
fact_check_task = Task(
    description="""Review the research and verify every fact across all categories:
    
    For SPORTS:
    - Verify team names and leagues are correct
    - Check scores and statistics
    - Confirm athlete names and positions
    - Validate tournament dates and locations
    
    For SCHOOL BOARD:
    - Confirm school names and divisions
    - Verify trustee or administrator names
    - Check program details and dates
    - Validate student names and achievements
    
    For BUSINESS:
    - Verify business names and owners
    - Check opening dates and locations
    - Confirm business history for anniversaries
    - Validate economic impact claims
    
    For COMMUNITY:
    - Verify organization names
    - Check volunteer names and roles
    - Confirm event dates and locations
    - Validate fundraising amounts
    
    Make corrections where needed and flag any unverified claims.
    """,
    agent=fact_checker,
    expected_output="A verified research report with all facts confirmed, corrections made, and any unverified claims flagged."
)

# Task 3: Write Article (Multi-topic)
writing_task = Task(
    description="""Write a complete, engaging news article that covers the verified research.

    IMPORTANT: Create a ROUNDUP article that covers multiple topics:
    - Start with the most newsworthy story
    - Include 2-3 sentences on each major topic
    - Use subheadings to separate categories (Sports, Schools, Business, Community)
    - Keep readers engaged throughout

    Follow the Spruce Grove Gazette Style Guide exactly.
    
    The article must include:
    - A strong main headline (use <h2> tags)
    - Lead paragraph with dateline "Spruce Grove, AB —"
    - Subheadings for each category: <h3>Sports</h3>, <h3>Schools</h3>, <h3>Business</h3>, <h3>Community</h3>
    - 2-3 paragraphs per category with key details
    - Local impact section explaining why this matters
    - Forward-looking closing statement about community pride
    
    Format as clean HTML with:
    - <h2> for main headline
    - <h3> for category subheadings
    - <p> for paragraphs
    - <em> for emphasis when appropriate
    - <blockquote> for any quotes
    
    Make it feel like a real community newspaper - warm, informative, and engaging.
    """,
    agent=writer,
    expected_output="A complete HTML news article covering sports, schools, business, and community news, following Gazette style guidelines, ready for editing."
)

# Task 4: Edit (Enhanced)
editing_task = Task(
    description="""Review and polish the multi-topic article:
    
    - Fix grammar, spelling, and punctuation
    - Ensure consistent style and tone across all sections
    - Verify proper HTML formatting
    - Add transitions between different topics
    - Ensure each category gets balanced coverage
    - Remove any weak or redundant phrases
    - Check that all facts from research are included
    - Verify local impact is clear for each story
    
    Make the article as strong and engaging as possible.
    """,
    agent=editor,
    expected_output="A polished, publication-ready HTML article covering all local news categories with balanced, engaging content."
)

# Task 5: Headline
headline_task = Task(
    description="""Create 3 compelling headline options for this multi-topic community news article.
    
    Each headline should:
    - Be 8-12 words maximum
    - Capture the most newsworthy element
    - Use active voice
    - Be clear and accurate
    - Appeal to community readers
    - Hint at the variety of topics covered
    
    Options could focus on:
    - The most exciting single story
    - The variety of community news
    - Community pride and achievement
    - Upcoming events or changes
    
    Select the best one as the final <h2> headline.
    """,
    agent=headline_writer,
    expected_output="3 headline options with the best one selected as the final <h2> headline."
)

print("✅ 5 Tasks created with expanded coverage")

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
print("🤖 Spruce Grove Gazette - AI Newsroom")
print("="*60)
print(f"📅 Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"📍 Location: Spruce Grove, Alberta")
print(f"📰 Categories: Sports | Schools | Business | Community")
print("="*60)
print("\n🚀 Generating comprehensive news roundup...\n")

# Run the crew
result = news_crew.kickoff()

# Get the final article
article_html = str(result)

# Extract headline for title
title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette Weekly Roundup"

print("\n" + "="*60)
print("📰 Final Article:")
print("="*60)
print(article_html)
print("="*60)

# Save locally
output_file = f"spruce_grove_roundup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2C5F2D; border-bottom: 3px solid #2C5F2D; padding-bottom: 10px; }}
        h2 {{ color: #2C5F2D; margin-top: 30px; }}
        h3 {{ color: #4A7C4B; margin-top: 25px; font-style: italic; }}
        .meta {{ color: #666; font-size: 0.9em; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }}
        .category-badge {{ display: inline-block; background: #2C5F2D; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; margin-right: 10px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.8em; color: #999; text-align: center; }}
        blockquote {{ border-left: 4px solid #2C5F2D; margin: 20px 0; padding-left: 20px; font-style: italic; }}
    </style>
</head>
<body>
    <h1>📰 Spruce Grove Gazette</h1>
    <div class="meta">📍 Spruce Grove, AB | 📅 {datetime.now().strftime('%B %d, %Y')} | 🤖 Weekly Community Roundup</div>
    {article_html}
    <div class="footer">
        <p>— The Spruce Grove Gazette</p>
        <p>Your Hometown, Online | Established 1950</p>
        <p><em>Covering what matters to Spruce Grove residents</em></p>
    </div>
</body>
</html>""")

print(f"\n💾 Article saved to: {output_file}")
print(f"📊 Coverage: Sports | Schools | Business | Community")

# Publish to Ghost if API key is set
if GHOST_ADMIN_API_KEY:
    print("\n📤 Attempting to publish to Ghost CMS...")
    print("⚠️ Ghost publishing configured but not implemented in this version")

print("\n" + "="*60)
print("✅ AI Newsroom session complete!")
print("📰 Spruce Grove is better informed!")
print("="*60)