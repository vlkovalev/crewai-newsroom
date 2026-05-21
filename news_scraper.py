#!/usr/bin/env python3
"""
RSS news scraper for Spruce Grove Gazette.
Fetches items from regional/national RSS feeds, filters for local relevance,
summarizes with OpenAI, and writes directly to the Gazette Postgres database.

Can be run standalone (via Render cron) or imported and called by APScheduler.
Requires: OPENAI_API_KEY, DATABASE_URL
"""

import os
import sys
import json
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

RSS_SOURCES = [
    # ── Google News targeted searches — guaranteed local content ──
    {
        'name': 'Google News – Spruce Grove',
        'url': 'https://news.google.com/rss/search?q=%22Spruce+Grove%22+Alberta&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Media', 'category': None, 'always_local': True,
    },
    {
        'name': 'Google News – Parkland County',
        'url': 'https://news.google.com/rss/search?q=%22Parkland+County%22+Alberta&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Media', 'category': None, 'always_local': True,
    },
    {
        'name': 'Google News – Stony Plain',
        'url': 'https://news.google.com/rss/search?q=%22Stony+Plain%22+Alberta&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Media', 'category': None, 'always_local': True,
    },
    {
        'name': 'Google News – Spruce Grove RCMP',
        'url': 'https://news.google.com/rss/search?q=%22Spruce+Grove%22+RCMP&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 5, 'label': 'Official', 'category': 'Public Safety', 'always_local': True,
    },
    # ── Official government & public sources ──
    {
        'name': 'City of Spruce Grove',
        'url': 'https://www.sprucegrove.org/city-services/newsroom/rss/',
        'reliability': 5, 'label': 'Official', 'category': 'News', 'always_local': True,
    },
    {
        'name': 'Parkland County News',
        'url': 'https://www.parklandcounty.com/en/news/rss.aspx',
        'reliability': 5, 'label': 'Official', 'category': 'News', 'always_local': True,
    },
    {
        'name': 'Government of Alberta',
        'url': 'https://www.alberta.ca/rss/news.xml',
        'reliability': 5, 'label': 'Official', 'category': 'News', 'always_local': False,
    },
    {
        'name': 'RCMP Alberta',
        'url': 'https://news.google.com/rss/search?q=RCMP+Alberta+%22Spruce+Grove%22+OR+%22Parkland%22&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 5, 'label': 'Official', 'category': 'Public Safety', 'always_local': True,
    },
    {
        'name': 'Sturgeon School Division',
        'url': 'https://news.google.com/rss/search?q=%22Sturgeon+School+Division%22&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Official', 'category': 'Education', 'always_local': True,
    },
    {
        'name': 'Parkland School Division',
        'url': 'https://news.google.com/rss/search?q=%22Parkland+School+Division%22&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Official', 'category': 'Education', 'always_local': True,
    },
    # ── Edmonton & Alberta regional news (separate section on front page) ──
    {
        'name': 'CBC Edmonton',
        'url': 'https://www.cbc.ca/cmlink/rss-canada-edmonton',
        'reliability': 5, 'label': 'Media', 'category': None,
        'always_local': False, 'region_scope': 'edmonton',
    },
    {
        'name': 'Edmonton Journal',
        'url': 'https://edmontonjournal.com/feed/',
        'reliability': 4, 'label': 'Media', 'category': None,
        'always_local': False, 'region_scope': 'edmonton',
    },
    {
        'name': 'CTV Edmonton',
        'url': 'https://edmonton.ctvnews.ca/rss/ctvnews-ca-edmonton-1.822430',
        'reliability': 4, 'label': 'Media', 'category': None,
        'always_local': False, 'region_scope': 'edmonton',
    },
    {
        'name': 'Google News – Edmonton',
        'url': 'https://news.google.com/rss/search?q=Edmonton+Alberta&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Media', 'category': None,
        'always_local': True, 'region_scope': 'edmonton',
    },
    {
        'name': 'Google News – Alberta',
        'url': 'https://news.google.com/rss/search?q=Alberta+news&hl=en-CA&gl=CA&ceid=CA:en',
        'reliability': 4, 'label': 'Media', 'category': None,
        'always_local': True, 'region_scope': 'alberta',
    },
    {
        'name': 'Government of Alberta – All News',
        'url': 'https://www.alberta.ca/rss/news.xml',
        'reliability': 5, 'label': 'Official', 'category': 'News',
        'always_local': True, 'region_scope': 'alberta',
    },
]

# Edmonton/Alberta sources publish to category 'Edmonton Area' or 'Alberta'
# when region_scope is set and the story is not Spruce Grove specific
EDMONTON_KEYWORDS = ['edmonton', 'alberta', 'yeg']

LOCAL_KEYWORDS = [
    'spruce grove', 'parkland county', 'stony plain',
    'parkland region', 'grove transit', 'spruce grove rcmp',
    'calahoo', 'pioneer road', 'century road', 'grove',
    'spruce grove saints', 'spruce grove regals',
]

IMPACT_KEYWORDS = [
    'fire', 'crash', 'emergency', 'arrest', 'death', 'flood',
    'closure', 'council', 'budget', 'school', 'election', 'bylaw',
    'hospital', 'missing', 'evacuation', 'alert',
]


def get_db():
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def is_local(title, desc):
    text = (title + ' ' + (desc or '')).lower()
    return any(kw in text for kw in LOCAL_KEYWORDS)


def auto_category(title, desc):
    t = (title + ' ' + (desc or '')).lower()
    if any(k in t for k in ['sport', 'hockey', 'soccer', 'regals', 'saints', 'football', 'baseball', 'basketball']):
        return 'Sports'
    if any(k in t for k in ['fire', 'crash', 'emergency', 'arrest', 'flood', 'evacuation', 'alert', 'missing']):
        return 'Public Safety'
    if any(k in t for k in ['council', 'mayor', 'bylaw', 'rcmp', 'police', 'election', 'government']):
        return 'News'
    if any(k in t for k in ['business', 'store', 'restaurant', 'company', 'economy', 'jobs', 'hiring']):
        return 'Business'
    if any(k in t for k in ['arts', 'culture', 'festival', 'music', 'theatre', 'gallery', 'library']):
        return 'Arts & Culture'
    if any(k in t for k in ['school', 'education', 'university', 'college', 'student', 'teacher']):
        return 'Education'
    if any(k in t for k in ['health', 'hospital', 'clinic', 'vaccine', 'medical', 'doctor']):
        return 'Health'
    return 'Community'


def score_article(title, desc, reliability):
    score = 25
    score += {5: 15, 4: 12, 3: 8}.get(reliability, 4)
    if is_local(title, desc):
        score += 25
    text = (title + ' ' + (desc or '')).lower()
    # Safety/emergency stories score higher
    if any(k in text for k in ['fire', 'crash', 'emergency', 'arrest', 'death', 'flood', 'evacuation']):
        score += 20
    elif any(k in text for k in IMPACT_KEYWORDS):
        score += 12
    else:
        score += 5
    return min(score, 95)


def fetch_rss(url):
    try:
        resp = requests.get(
            url, timeout=15,
            headers={'User-Agent': 'SpraceGroveGazette-NewsBot/1.0'}
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        return [
            {
                'title': (item.findtext('title') or '').strip(),
                'desc':  (item.findtext('description') or '').strip()[:800],
                'link':  (item.findtext('link') or '').strip(),
            }
            for item in root.iter('item')
        ]
    except Exception as e:
        print(f'[WARN] RSS fetch failed {url}: {e}')
        return []


def summarize_with_openai(title, desc, source_name, openai_key):
    prompt = (
        f'You write for the Spruce Grove Gazette, a community newspaper in Spruce Grove, Alberta, Canada. '
        f'Summarize this news item from {source_name} for local Spruce Grove readers. '
        f'Explain the local relevance. '
        f'Return ONLY valid JSON: '
        f'{{"summary":"one sentence max 150 chars","body":"2-3 plain text paragraphs"}}\n\n'
        f'Headline: {title}\nDetails: {desc}'
    )
    try:
        resp = requests.post(
            OPENAI_URL,
            headers={'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 450,
                'response_format': {'type': 'json_object'},
            },
            timeout=30,
        )
        data = json.loads(resp.json()['choices'][0]['message']['content'])
        return data.get('summary', '').strip()[:400], data.get('body', '').strip()
    except Exception as e:
        print(f'[WARN] OpenAI summarize error: {e}')
        return '', ''


def run_scraper():
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    if not openai_key:
        print('[ERROR] OPENAI_API_KEY not set')
        return 0

    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    published = 0

    for src in RSS_SOURCES:
        print(f'[SCRAPER] Checking {src["name"]}...')
        items = fetch_rss(src['url'])

        for item in items[:30]:
            title = item['title']
            desc  = item['desc']

            if not title:
                continue
            if not src.get('always_local') and not is_local(title, desc):
                continue

            # Deduplicate: skip if same title published in last 48h
            cursor.execute(
                "SELECT id FROM news_articles WHERE title=%s AND date >= NOW() - INTERVAL '2 days'",
                (title,)
            )
            if cursor.fetchone():
                continue

            score    = score_article(title, desc, src['reliability'])
            # Route Edmonton/Alberta regional stories to their own category
            region_scope = src.get('region_scope', 'local')
            if region_scope == 'edmonton' and not is_local(title, desc):
                category = 'Edmonton Area'
                score = max(score - 10, 20)  # slightly lower priority than hyper-local
            elif region_scope == 'alberta' and not is_local(title, desc):
                category = 'Alberta'
                score = max(score - 15, 15)
            else:
                category = src.get('category') or auto_category(title, desc)
            summary, body = summarize_with_openai(title, desc, src['name'], openai_key)

            if not summary or not body:
                continue

            text_lc = (title + ' ' + desc).lower()
            urgent  = any(k in text_lc for k in [
                'emergency alert', 'mandatory evacuation', 'evacuation order',
                'wildfire emergency', 'missing person', 'amber alert',
                'flood warning', 'active shooter', 'shelter in place',
                'boil water advisory',
            ])
            expires = (datetime.utcnow().date() + timedelta(days=3)).isoformat()

            cursor.execute(
                '''INSERT INTO news_articles
                   (title, content, summary, source, author, date, category,
                    featured, active, url, views,
                    score, urgent, story_type, source_label, expires_from_front,
                    search_vector)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,
                           FALSE,TRUE,%s,0,
                           %s,%s,'standard',%s,%s,
                           to_tsvector('english', %s||' '||%s||' '||%s))''',
                (title, body, summary,
                 src['name'], f'{src["name"]} / Gazette Desk',
                 now_str, category,
                 item['link'],
                 score, urgent, src['label'], expires,
                 title, summary, body)
            )
            published += 1
            print(f'[OK] {src["name"]}: {title[:70]} (score={score})')

    conn.commit()
    conn.close()
    print(f'[SCRAPER DONE] {published} new articles from RSS feeds')
    return published


if __name__ == '__main__':
    count = run_scraper()
    sys.exit(0 if count >= 0 else 1)
