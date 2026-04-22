"""
Spruce Grove Gazette - AI Newsroom
"""

import os
import re
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    exit(1)

print("✅ OpenAI API key found")

GAZETTE_STYLE_GUIDE = """
Spruce Grove Gazette Style Guide:
- Warm and community-focused tone
- Professional but not stuffy
- Use active voice
- Keep sentences under 25 words
- End with "— The Spruce Grove Gazette"
"""

print("🤖 Creating AI agents...")

researcher = Agent(
    role="Local News Researcher",
    goal=f"Find local news about Spruce Grove for {datetime.now().strftime('%B %d, %Y')}",
    backstory="You are an experienced journalist who knows Spruce Grove, Alberta well.",
    verbose=True,
    allow_delegation=False
)

fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts and details",
    backstory="You are a meticulous fact-checker who ensures accuracy.",
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role="News Writer",
    goal="Write engaging articles in the Spruce Grove Gazette voice",
    backstory=f"You are an award-winning journalist. Follow this style: {GAZETTE_STYLE_GUIDE}",
    verbose=True,
    allow_delegation=False
)

editor = Agent(
    role="Senior Editor",
    goal="Polish and perfect the article",
    backstory="You are a Senior Editor with 30 years of experience.",
    verbose=True,
    allow_delegation=True
)

headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling headlines",
    backstory="You are a master of writing engaging headlines.",
    verbose=True,
    allow_delegation=False
)

print("✅ 5 Agents created")

research_task = Task(
    description=f"""Create 3-5 local news stories about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}.

    Topics to cover:
    - Community events
    - Local government
    - Business news
    - School updates
    - Development projects
    
    Provide key facts, dates, locations, and why each matters to residents.
    """,
    agent=researcher,
    expected_output="Research report with 3-5 local news stories including all key details."
)

fact_check_task = Task(
    description="Verify all facts, dates, names, and locations. Correct any errors.",
    agent=fact_checker,
    expected_output="Verified research report with all facts confirmed."
)

writing_task = Task(
    description="""Write a complete news article in HTML format.

    Requirements:
    - <h2> for headline
    - Start with "Spruce Grove, AB —"
    - 3-5 short paragraphs
    - Local impact section
    - Closing statement
    
    Follow the Gazette style guide.
    """,
    agent=writer,
    expected_output="Complete HTML news article ready for editing."
)

editing_task = Task(
    description="Polish the article: fix grammar, improve flow, ensure proper HTML formatting.",
    agent=editor,
    expected_output="Polished, publication-ready HTML article."
)

headline_task = Task(
    description="Create 3 headline options and select the best one as the final <h2> headline.",
    agent=headline_writer,
    expected_output="3 headline options with the best one selected as final <h2> headline."
)

print("✅ 5 Tasks created")

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
print("="*60)
print("\n🚀 Generating article...\n")

result = news_crew.kickoff()
article_html = str(result)

title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette Daily Dispatch"

print("\n" + "="*60)
print("📰 Final Article:")
print("="*60)
print(article_html)
print("="*60)

output_file = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Spruce Grove Gazette</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2 {{ color: #2C5F2D; }}
        .footer {{ margin-top: 40px; text-align: center; color: #999; }}
    </style>
</head>
<body>
    <h1>📰 Spruce Grove Gazette</h1>
    <div>📍 Spruce Grove, AB | 📅 {datetime.now().strftime('%B %d, %Y')}</div>
    {article_html}
    <div class="footer">— The Spruce Grove Gazette</div>
</body>
</html>""")

print(f"\n💾 Article saved to: {output_file}")
print("\n✅ AI Newsroom session complete!")
