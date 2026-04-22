"""
Spruce Grove Gazette - Enhanced AI Newsroom
Features:
- Multi-agent crew (Researcher, Writer, Fact-Checker, Editor, Headline Specialist)
- Custom Gazette voice and style
- AI image generation (DALL-E)
- Auto-publish to Ghost CMS
"""

import os
import re
import requests
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool, tool
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv
from typing import Type
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# ============================================
# Ghost CMS Configuration
# ============================================

GHOST_URL = os.environ.get('GHOST_URL', 'https://sprucegrovegazette-com.ghost.io')
GHOST_ADMIN_API_KEY = os.environ.get('GHOST_ADMIN_API_KEY', '')

# OpenAI API key for images (same as your OpenAI key)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# ============================================
# AI Image Generation (DALL-E)
# ============================================

def generate_article_image(topic, title):
    """Generate a feature image using DALL-E"""
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        # Create a prompt for the image
        image_prompt = f"A professional, warm photograph for a small-town newspaper article about {topic} in Spruce Grove, Alberta. The image should be suitable for a community news website, with natural lighting and authentic local feel. Title: {title}"
        
        response = openai.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        image_url = response.data[0].url
        print(f"   🖼️ Generated image: {image_url[:50]}...")
        return image_url
    except Exception as e:
        print(f"   ⚠️ Image generation failed: {e}")
        return "https://images.unsplash.com/photo-1585829365293-ab7cd400c167?w=1200&h=600&fit=crop"

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
- Avoid jargon and overly complex sentences

Article Structure:
1. Headline: Bold, engaging, 8-12 words
2. Dateline: "Spruce Grove, AB —" at start of first paragraph
3. Lead paragraph: Answers who, what, when, where, why
4. Body: 2-3 short paragraphs with key details
5. Local impact: Explain how this matters to residents
6. Closing: Forward-looking statement or call to action

Style Rules:
- Use active voice
- Keep sentences under 25 words
- Use local examples and references
- Include quotes when possible (marked with " ")
- End with "— The Spruce Grove Gazette"

Prohibited:
- Negative or sensational language
- Unverified claims
- National politics (unless directly relevant to Spruce Grove)
"""

# ============================================
# Search Tool Setup
# ============================================

search = DuckDuckGoSearchRun()

class SpruceGroveSearchInput(BaseModel):
    """Input for Spruce Grove search"""
    query: str = Field(description="The search query for Spruce Grove news")

class SpruceGroveSearchTool(BaseTool):
    name: str = "Spruce Grove News Search"
    description: str = "Search for local news, events, and information about Spruce Grove, Alberta"
    args_schema: Type[BaseModel] = SpruceGroveSearchInput
    
    def _run(self, query: str) -> str:
        enhanced_query = f"Spruce Grove Alberta {query} local news community event"
        try:
            result = search.invoke(enhanced_query)
            return result if result else "No results found."
        except Exception as e:
            return f"Search error: {str(e)}"

search_tool = SpruceGroveSearchTool()
print("✅ Search tool created")

# ============================================
# Create Enhanced AI Agents
# ============================================

# Agent 1: Researcher
researcher = Agent(
    role="Local News Researcher",
    goal=f"Find current, factual local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}",
    backstory="""You are an experienced journalist who knows Spruce Grove, Alberta inside and out.
    You have deep connections in the community and know where to find reliable local information.
    You focus on stories that matter to residents: city council, schools, business, events, and development.""",
    tools=[search_tool],
    verbose=True,
    allow_delegation=False
)

# Agent 2: Fact Checker
fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts, dates, names, and locations in the research",
    backstory="""You are a meticulous fact-checker with 15 years of experience at major newspapers.
    You verify every claim, double-check names and dates, and ensure accuracy before publication.
    You never let a factual error slip through.""",
    verbose=True,
    allow_delegation=False
)

# Agent 3: Writer (with Gazette style)
writer = Agent(
    role="News Writer",
    goal="Write engaging, well-structured news articles in the Spruce Grove Gazette voice",
    backstory=f"""You are an award-winning journalist who has written for the Spruce Grove Gazette for 20 years.
    You know the community inside out and write in a warm, professional voice that residents trust.
    
    Follow this style guide:
    {GAZETTE_STYLE_GUIDE}
    
    You write with pride about Spruce Grove and always put the reader first.""",
    verbose=True,
    allow_delegation=False
)

# Agent 4: Editor
editor = Agent(
    role="Senior Editor",
    goal="Review, polish, and ensure the article meets Gazette standards",
    backstory="""You are the Senior Editor of the Spruce Grove Gazette with 30 years of experience.
    You have an eagle eye for errors, style inconsistencies, and tone issues.
    You ensure every article that leaves your desk is worthy of the Gazette's reputation.""",
    verbose=True,
    allow_delegation=True
)

# Agent 5: Headline Specialist
headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling, clickable headlines that capture the essence of the article",
    backstory="""You are a master of the headline. You know how to grab attention while staying truthful and engaging.
    You've written thousands of headlines that make readers want to learn more.
    Your headlines are clear, clever, and community-focused.""",
    verbose=True,
    allow_delegation=False
)

print("✅ 5 Agents created: Researcher, Fact-Checker, Writer, Editor, Headline Specialist")

# ============================================
# Define Enhanced Tasks
# ============================================

# Task 1: Research
research_task = Task(
    description=f"""Research current local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}.

    Find 3-5 local news stories about:
    - Community events happening in the next 2 weeks
    - Local government decisions from recent council meetings
    - Business openings, expansions, or achievements
    - School news, sports, or student achievements
    - Development projects or infrastructure updates
    
    For each story, collect:
    - What happened (key facts)
    - When it happened or will happen (dates)
    - Where (location within Spruce Grove)
    - Who is involved (people, organizations)
    - Why it matters to residents
    - Sources (where you found the information)
    """,
    agent=researcher,
    expected_output="A detailed research report with 3-5 local news stories including all key facts, dates, locations, and sources."
)

# Task 2: Fact Check
fact_check_task = Task(
    description="""Review the research and verify every fact:
    
    - Check all dates are correct and in the proper format
    - Verify all names are spelled correctly
    - Confirm all locations exist in Spruce Grove
    - Ensure sources are credible
    - Flag any unverified claims
    
    Make corrections where needed and note any unresolved questions.
    """,
    agent=fact_checker,
    expected_output="A verified research report with all facts confirmed and any issues flagged."
)

# Task 3: Write Article
writing_task = Task(
    description="""Write a complete news article based on the verified research.

    Follow the Spruce Grove Gazette Style Guide exactly.
    
    The article must include:
    - A strong lead paragraph (who, what, when, where, why)
    - 3-5 short paragraphs with key details
    - Local impact section
    - Forward-looking closing statement
    
    Format as clean HTML with:
    - <h2> for headline
    - <p> for paragraphs
    - <em> for emphasis when appropriate
    - <blockquote> for any quotes
    
    Keep the tone warm, professional, and community-focused.
    """,
    agent=writer,
    expected_output="A complete HTML news article following Gazette style guidelines, ready for editing."
)

# Task 4: Edit
editing_task = Task(
    description="""Review and polish the article:
    
    - Check for grammar, spelling, and punctuation
    - Ensure consistent style and tone
    - Verify proper HTML formatting
    - Add transitions between paragraphs
    - Ensure the article flows well
    - Remove any redundant or weak phrases
    
    Make the article as strong as possible before final review.
    """,
    agent=editor,
    expected_output="A polished, publication-ready HTML article."
)

# Task 5: Headline
headline_task = Task(
    description="""Create 3 compelling headline options for the article.
    
    Each headline should:
    - Be 8-12 words maximum
    - Capture the most newsworthy element
    - Use active voice
    - Be clear and accurate
    - Make readers want to learn more
    
    Select the best one as the final headline.
    """,
    agent=headline_writer,
    expected_output="3 headline options with the best one selected as the final <h2> headline."
)

print("✅ 5 Tasks created")

# ============================================
# Ghost Publishing Function
# ============================================

def publish_to_ghost(title, html_content, topic, feature_image=None):
    """Publish article to Ghost CMS"""
    if not GHOST_ADMIN_API_KEY:
        print("⚠️ Ghost Admin API key not configured. Skipping auto-publish.")
        return None
    
    url = f"{GHOST_URL}/ghost/api/admin/posts/"
    
    post_data = {
        "posts": [{
            "title": title,
            "html": html_content,
            "status": "published",
            "published_at": datetime.now().isoformat(),
            "tags": [{"name": "Local News"}, {"name": "AI-Generated"}, {"name": "Daily Digest"}],
            "feature_image": feature_image,
            "meta_title": title[:60],
            "meta_description": re.sub(r'<[^>]+>', '', html_content)[:150] if html_content else title
        }]
    }
    
    headers = {
        "Authorization": f"Ghost {GHOST_ADMIN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=post_data, headers=headers)
        if response.status_code == 201:
            post = response.json()
            post_url = f"{GHOST_URL}/{post['posts'][0]['slug']}"
            print(f"\n✅ Article published to Ghost!")
            print(f"   🔗 URL: {post_url}")
            return post
        else:
            print(f"\n❌ Failed to publish: {response.status_code}")
            return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

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
print("🤖 Spruce Grove Gazette - Enhanced AI Newsroom")
print("="*60)
print(f"📅 Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"📍 Location: Spruce Grove, Alberta")
print(f"👥 Agents: Researcher → Fact-Checker → Writer → Editor → Headline")
print("="*60)
print("\n🚀 Generating article with AI newsroom...\n")

# Run the crew
result = news_crew.kickoff()

# Extract the final article
article_html = str(result)

# Extract headline for title
title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette Daily Dispatch"

# Extract topic for image generation
topic_match = re.search(r'community|event|council|school|business', article_html, re.IGNORECASE)
topic = topic_match.group(0) if topic_match else "local news"

print("\n" + "="*60)
print("🎨 Generating feature image...")
print("="*60)

# Generate image
feature_image = generate_article_image(topic, title)

print("\n" + "="*60)
print("📰 Final Article:")
print("="*60)
print(article_html)
print("="*60)

# Save locally
output_file = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #1a1a1a; }}
        h1, h2 {{ font-family: Georgia, serif; color: #2C5F2D; }}
        .meta {{ color: #666; font-size: 0.9em; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 20px 0; }}
        blockquote {{ border-left: 4px solid #2C5F2D; margin: 20px 0; padding-left: 20px; font-style: italic; color: #555; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.8em; color: #999; text-align: center; }}
    </style>
</head>
<body>
    <h1>📰 Spruce Grove Gazette</h1>
    <div class="meta">📍 Spruce Grove, AB | 📅 {datetime.now().strftime('%B %d, %Y')} | 🤖 AI-Generated</div>
    {f'<img src="{feature_image}" alt="Article feature image">' if feature_image else ''}
    {article_html}
    <div class="footer">
        <p>— The Spruce Grove Gazette</p>
        <p>Your Hometown, Online. | Established 1950</p>
        <p><small>This article was generated by the Gazette AI Newsroom and reviewed by editorial staff.</small></p>
    </div>
</body>
</html>""")

print(f"\n💾 Article saved to: {output_file}")

# Publish to Ghost
print("\n" + "="*60)
print("📤 Publishing to Ghost CMS...")
print("="*60)

publish_to_ghost(
    title=title,
    html_content=article_html,
    topic=topic,
    feature_image=feature_image
)

print("\n" + "="*60)
print("🏁 AI Newsroom session complete!")
print("="*60)