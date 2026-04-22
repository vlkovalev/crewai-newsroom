"""
Spruce Grove Gazette - AI Newsroom with Ghost Auto-Post
This script generates news articles using CrewAI and automatically publishes them to Ghost CMS.
"""

import os
import requests
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from langchain_community.tools import DuckDuckGoSearchRun
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

# ============================================
# Ghost CMS Configuration
# ============================================

# Get Ghost credentials from environment variables or set them here
GHOST_URL = os.environ.get('GHOST_URL', 'https://sprucegrovegazette-com.ghost.io')
GHOST_ADMIN_API_KEY = os.environ.get('GHOST_ADMIN_API_KEY', 'your-admin-api-key-here')

# ============================================
# Ghost API Functions
# ============================================

def publish_to_ghost(title, html_content, tags=None, feature_image=None):
    """
    Publish an article to Ghost CMS using the Admin API
    
    Args:
        title (str): Article title
        html_content (str): Article content in HTML format
        tags (list): List of tag names
        feature_image (str): URL of feature image
    """
    if not GHOST_ADMIN_API_KEY or GHOST_ADMIN_API_KEY == 'your-admin-api-key-here':
        print("⚠️ Ghost Admin API key not configured. Skipping auto-publish.")
        print("   Set GHOST_ADMIN_API_KEY environment variable to enable auto-publish.")
        return None
    
    # Ghost Admin API endpoint for posts
    url = f"{GHOST_URL}/ghost/api/admin/posts/"
    
    # Prepare the post data
    post_data = {
        "posts": [{
            "title": title,
            "html": html_content,
            "status": "published",  # Change to "draft" if you want to review first
            "published_at": datetime.now().isoformat(),
            "tags": [{"name": tag} for tag in (tags or ["AI-Generated", "Local News"])],
            "feature_image": feature_image,
            "meta_title": title[:60],  # Ghost recommended length
            "meta_description": html_content[:150].strip() if html_content else title,
            "codeinjection_head": None,
            "codeinjection_foot": None
        }]
    }
    
    # Make the API request
    headers = {
        "Authorization": f"Ghost {GHOST_ADMIN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=post_data, headers=headers)
        
        if response.status_code == 201:
            post = response.json()
            post_url = f"{GHOST_URL}/{post['posts'][0]['slug']}"
            print(f"\n✅ Article published successfully!")
            print(f"   📝 Title: {title}")
            print(f"   🔗 URL: {post_url}")
            return post
        else:
            print(f"\n❌ Failed to publish article: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"\n❌ Error publishing to Ghost: {str(e)}")
        return None

# ============================================
# Search Tool Setup
# ============================================

# Initialize the search tool
search = DuckDuckGoSearchRun()

class SpruceGroveSearchInput(BaseModel):
    """Input for Spruce Grove search"""
    query: str = Field(description="The search query for Spruce Grove news")

class SpruceGroveSearchTool(BaseTool):
    name: str = "Spruce Grove News Search"
    description: str = "Search for local news, events, and information about Spruce Grove, Alberta"
    args_schema: Type[BaseModel] = SpruceGroveSearchInput
    
    def _run(self, query: str) -> str:
        """Execute the search"""
        enhanced_query = f"Spruce Grove Alberta {query} local news community"
        try:
            result = search.invoke(enhanced_query)
            return result if result else "No results found."
        except Exception as e:
            return f"Search error: {str(e)}"

# Create the tool instance
search_tool = SpruceGroveSearchTool()
print("✅ Search tool created successfully")

# ============================================
# Create the AI Agents
# ============================================

researcher = Agent(
    role="Local News Researcher",
    goal=f"Find current local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}",
    backstory="""You are an experienced journalist who knows Spruce Grove, Alberta.
    You find real, factual information about local events, government decisions, and community news.""",
    tools=[search_tool],
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role="News Writer",
    goal="Write engaging news articles for the Spruce Grove Gazette",
    backstory="""You are an award-winning journalist who writes clear, engaging, 
    and community-focused news articles. You write in a warm, professional voice.
    Always include a catchy headline and structure your article with proper HTML tags.""",
    verbose=True,
    allow_delegation=False
)

print("✅ Agents created: Researcher, Writer")

# ============================================
# Define the Tasks
# ============================================

research_task = Task(
    description=f"""Research current local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}.

    Use the search tool to find 2-3 local news stories about:
    - Community events happening soon
    - Local government news
    - Business openings or achievements
    - School or sports news
    
    For each story, note the key facts, date, and why it matters to residents.
    
    Write your findings in a clear, organized way.
    """,
    agent=researcher,
    expected_output="A research report with 2-3 local news stories, including key facts and relevance."
)

writing_task = Task(
    description="""Write a complete news article based on the research.

    The article must:
    - Have an engaging headline using <h2> tags
    - Include a dateline (Spruce Grove, AB)
    - Be 200-300 words
    - Use <p> tags for paragraphs
    - Be written in a friendly, community newspaper style
    - Focus on Spruce Grove, Alberta
    
    Format the article as clean HTML that can be directly published to a website.
    
    Example structure:
    <h2>Your Catchy Headline Here</h2>
    <p><em>Spruce Grove, AB</em> - Your first paragraph...</p>
    <p>Second paragraph...</p>
    <p>Third paragraph with conclusion.</p>
    """,
    agent=writer,
    expected_output="A complete HTML news article ready for publication."
)

print("✅ Tasks created")

# ============================================
# Create and Run the Crew
# ============================================

news_crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,
    verbose=True
)

print("\n" + "="*60)
print("🤖 Spruce Grove Gazette AI Newsroom")
print("="*60)
print(f"📅 Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"📍 Location: Spruce Grove, Alberta")
print("="*60)
print("\n🚀 Generating article...\n")

# Run the crew
result = news_crew.kickoff()

print("\n" + "="*60)
print("📰 Generated Article:")
print("="*60)
print(result)
print("="*60)

# Save to local file as backup
output_file = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"<html><head><title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>")
    f.write("<meta charset='UTF-8'>")
    f.write("<style>body{font-family:Georgia,serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.6;}</style>")
    f.write("</head><body>")
    f.write(str(result))
    f.write("</body></html>")

print(f"\n💾 Article saved locally to: {output_file}")

# ============================================
# Auto-Publish to Ghost
# ============================================

print("\n" + "="*60)
print("📤 Publishing to Ghost CMS...")
print("="*60)

# Extract title from the article (look for <h2> tag)
title = "Spruce Grove Gazette Daily Dispatch"
if hasattr(result, 'raw') and result.raw:
    import re
    h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', str(result))
    if h2_match:
        title = h2_match.group(1).strip()
    elif hasattr(result, 'title'):
        title = result.title

# Publish to Ghost
publish_result = publish_to_ghost(
    title=title,
    html_content=str(result),
    tags=["local-news", "ai-generated", "daily-digest"],
    feature_image="https://images.unsplash.com/photo-1585829365293-ab7cd400c167?w=1200&h=600&fit=crop"
)

if publish_result:
    print("\n🎉 Success! Article is live on your website!")
else:
    print("\n⚠️ Article was saved locally but not published to Ghost.")
    print("   To enable auto-publish, set your GHOST_ADMIN_API_KEY.")

print("\n" + "="*60)
print("🏁 AI Newsroom session complete!")
print("="*60)