"""
Spruce Grove Gazette - AI Newsroom (Simplified)
No external dependencies - runs reliably on Render
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

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Check if OpenAI API key is set
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    exit(1)

print("OpenAI API key found")

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

print("Creating AI agents...")

# Agent 1: Researcher
researcher = Agent(
    role="Local News Researcher",
    goal=f"Find current, factual local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}",
    backstory="""You are an experienced journalist who knows Spruce Grove, Alberta inside and out.
    You focus on stories that matter to residents: city council, schools, business, events, and development.
    Cover sports, school board updates, business profiles, and community spotlights.""",
    verbose=True,
    allow_delegation=False
)

# Agent 2: Fact Checker
fact_checker = Agent(
    role="Fact Checker",
    goal="Verify all facts, dates, names, and locations in the research",
    backstory="""You are a meticulous fact-checker who verifies every claim, double-checks names and dates, 
    and ensures accuracy before publication. You never let a factual error slip through.""",
    verbose=True,
    allow_delegation=False
)

# Agent 3: Writer (with Gazette style)
writer = Agent(
    role="News Writer",
    goal="Write engaging, well-structured news articles in the Spruce Grove Gazette voice",
    backstory=f"""You are an award-winning journalist who writes in a warm, professional voice that residents trust.
    
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
    backstory="""You are the Senior Editor with 30 years of experience. You have an eagle eye for errors, 
    style inconsistencies, and tone issues. You ensure every article is worthy of the Gazette's reputation.""",
    verbose=True,
    allow_delegation=True
)

# Agent 5: Headline Specialist
headline_writer = Agent(
    role="Headline Specialist",
    goal="Create compelling, clickable headlines that capture the essence of the article",
    backstory="""You are a master of the headline. You know how to grab attention while staying truthful.
    Your headlines are clear, clever, and community-focused.""",
    verbose=True,
    allow_delegation=False
)

print("5 Agents created: Researcher, Fact-Checker, Writer, Editor, Headline Specialist")

# ============================================
# Define Enhanced Tasks
# ============================================

print("Creating tasks...")

# Task 1: Research
research_task = Task(
    description=f"""Research current local news about Spruce Grove, Alberta for {datetime.now().strftime('%B %d, %Y')}.

    Find 3-5 local news stories covering:
    - Sports news (high school teams, local leagues, tournaments)
    - School board updates (decisions, events, achievements)
    - Business profiles (new openings, expansions, success stories)
    - Community spotlight (local heroes, volunteers, organizations)
    - City council decisions and development projects
    
    For each story, collect:
    - What happened (key facts)
    - When it happened or will happen (dates)
    - Where (location within Spruce Grove)
    - Who is involved (people, organizations)
    - Why it matters to residents
    """,
    agent=researcher,
    expected_output="A detailed research report with 3-5 local news stories including all key facts, dates, locations, and why they matter to residents."
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
    - A strong headline (use <h2> tags)
    - A lead paragraph with dateline "Spruce Grove, AB —"
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
    
    - Fix grammar, spelling, and punctuation
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
    
    Select the best one as the final <h2> headline.
    """,
    agent=headline_writer,
    expected_output="3 headline options with the best one selected as the final <h2> headline."
)

print("5 Tasks created")

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
print("Spruce Grove Gazette - AI Newsroom")
print("="*60)
print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
print(f"Location: Spruce Grove, Alberta")
print(f"Agents: Researcher → Fact-Checker → Writer → Editor → Headline")
print("="*60)
print("\nGenerating article with AI newsroom...\n")

# Run the crew
result = news_crew.kickoff()

# Extract the final article
article_html = str(result)

# Extract headline for title
title_match = re.search(r'<h2[^>]*>(.*?)</h2>', article_html)
title = title_match.group(1) if title_match else "Spruce Grove Gazette Daily Dispatch"

print("\n" + "="*60)
print("Final Article:")
print("="*60)
print(article_html)
print("="*60)

# Save the article
output_file = f"spruce_grove_gazette_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Spruce Grove Gazette - {datetime.now().strftime('%B %d, %Y')}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1, h2 {{ color: #2C5F2D; }}
        .meta {{ color: #666; font-size: 0.9em; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.8em; color: #999; text-align: center; }}
        blockquote {{ border-left: 4px solid #2C5F2D; margin: 20px 0; padding-left: 20px; font-style: italic; }}
    </style>
</head>
<body>
    <h1>Spruce Grove Gazette</h1>
    <div class="meta">Spruce Grove, AB | {datetime.now().strftime('%B %d, %Y')}</div>
    {article_html}
    <div class="footer">
        <p>— The Spruce Grove Gazette</p>
        <p>Your Hometown, Online | Established April 2026</p>
    </div>
</body>
</html>""")

print(f"\nArticle saved to: {output_file}")
print("\n" + "="*60)
print("AI Newsroom session complete!")
print("Spruce Grove Gazette is ready to publish!")
print("="*60)