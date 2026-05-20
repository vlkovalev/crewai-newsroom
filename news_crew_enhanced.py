#!/usr/bin/env python3
"""
Standalone cron script — generates 3 Spruce Grove articles via OpenAI API
and inserts them into gazette.db. Run by Render Cron Job daily.

Usage: python news_crew_enhanced.py
Requires: OPENAI_API_KEY env var
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / 'gazette.db'
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

TOPIC_ROTATION = [
    ('Community',     'a community event, neighbourhood initiative, or local volunteer story in Spruce Grove, Alberta'),
    ('News',          'a local government update, city council decision, or infrastructure project in Spruce Grove, Alberta'),
    ('Sports',        'a youth or amateur sports story, local team result, or recreation program in Spruce Grove, Alberta'),
    ('Arts & Culture','a local arts event, cultural festival, library program, or creative community story in Spruce Grove, Alberta'),
    ('Business',      'a new business opening, local entrepreneur story, or economic development update in Spruce Grove, Alberta'),
    ('Opinion',       'an editorial opinion piece about life, growth, or community values in Spruce Grove, Alberta'),
]

INDEX_FILE = Path(__file__).parent / '.topic_index'


def load_topic_index():
    try:
        return int(INDEX_FILE.read_text().strip())
    except (ValueError, IOError, FileNotFoundError):
        return 0


def save_topic_index(n):
    try:
        INDEX_FILE.write_text(str(n))
    except IOError as e:
        print(f'[WARN] Could not save topic index: {e}')


def generate_daily_articles():
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        print('[ERROR] OPENAI_API_KEY not set')
        return False

    today = datetime.utcnow().strftime('%B %d, %Y')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    topic_index = load_topic_index()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    generated = 0
    for _ in range(3):
        cat, topic_desc = TOPIC_ROTATION[topic_index % len(TOPIC_ROTATION)]
        topic_index += 1

        prompt = (
            f'You are a staff writer for the Spruce Grove Gazette, a community newspaper '
            f'in Spruce Grove, Alberta, Canada. Today is {today}. '
            f'Write a realistic, engaging local news article about {topic_desc}. '
            f'Use specific Spruce Grove locations, street names, parks, or venues to make it feel authentic. '
            f'Respond ONLY with valid JSON in this exact format:\n'
            f'{{"title": "...", "summary": "One sentence, max 150 chars.", '
            f'"content": "Full article body, 3-5 paragraphs separated by blank lines.", '
            f'"author": "First Last (staff writer name)"}}'
        )

        try:
            resp = requests.post(
                OPENAI_URL,
                headers=headers,
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.85,
                    'max_tokens': 1024,
                    'response_format': {'type': 'json_object'},
                },
                timeout=30
            )

            if resp.status_code != 200:
                print(f'[ERROR] OpenAI {resp.status_code}: {resp.text[:200]}')
                continue

            text = resp.json()['choices'][0]['message']['content'].strip()
            data = json.loads(text)

            title   = data.get('title', '').strip()
            summary = data.get('summary', '').strip()[:400]
            content = data.get('content', '').strip()
            author  = data.get('author', 'Staff Writer').strip()

            if not title or not content:
                print('[WARN] Empty title or content — skipping')
                continue

            cursor.execute(
                '''INSERT INTO news_articles
                   (title, content, summary, source, author, date, category, featured, active, views)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, 0)''',
                (title, content, summary, 'Gazette AI', author, now, cat)
            )
            conn.commit()
            generated += 1
            print(f'[OK] {cat}: {title}')

        except json.JSONDecodeError as e:
            print(f'[ERROR] JSON parse error: {e}')
        except requests.exceptions.Timeout:
            print('[ERROR] OpenAI API timed out')
        except requests.exceptions.RequestException as e:
            print(f'[ERROR] Request error: {e}')
        except Exception as e:
            print(f'[ERROR] Unexpected: {e}')

    conn.close()
    save_topic_index(topic_index)
    print(f'[DONE] {generated}/3 articles saved')
    return generated > 0


if __name__ == '__main__':
    success = generate_daily_articles()
    sys.exit(0 if success else 1)
