#!/usr/bin/env python3
"""
Render Cron Job — generates 3 Spruce Grove articles via OpenAI and publishes
them to the web service via HTTP (POST /api/publish-article).

Required env vars:
  OPENAI_API_KEY    — OpenAI API key
  GAZETTE_BASE_URL  — base URL of the web service, e.g. https://your-app.onrender.com
  GAZETTE_API_KEY   — shared secret matching X-Api-Key on the web service
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

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
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    gazette_url = os.environ.get('GAZETTE_BASE_URL', '').rstrip('/')
    gazette_api_key = os.environ.get('GAZETTE_API_KEY', '')

    if not openai_key:
        print('[ERROR] OPENAI_API_KEY not set')
        return False
    if not gazette_url:
        print('[ERROR] GAZETTE_BASE_URL not set')
        return False
    if not gazette_api_key:
        print('[ERROR] GAZETTE_API_KEY not set')
        return False

    publish_url = f'{gazette_url}/api/publish-article'
    today = datetime.utcnow().strftime('%B %d, %Y')
    openai_headers = {
        'Authorization': f'Bearer {openai_key}',
        'Content-Type': 'application/json',
    }
    publish_headers = {
        'X-Api-Key': gazette_api_key,
        'Content-Type': 'application/json',
    }

    topic_index = load_topic_index()
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
                headers=openai_headers,
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

            pub_resp = requests.post(
                publish_url,
                headers=publish_headers,
                json={
                    'title': title,
                    'content': content,
                    'summary': summary,
                    'category': cat,
                    'source': 'Gazette AI',
                    'author': author,
                },
                timeout=15
            )

            if pub_resp.status_code in (200, 201):
                result = pub_resp.json()
                status = result.get('status', 'published')
                print(f'[OK] {cat}: {title} ({status})')
                if status != 'duplicate':
                    generated += 1
            else:
                print(f'[ERROR] Publish failed {pub_resp.status_code}: {pub_resp.text[:200]}')

        except json.JSONDecodeError as e:
            print(f'[ERROR] JSON parse error: {e}')
        except requests.exceptions.Timeout:
            print('[ERROR] Request timed out')
        except requests.exceptions.RequestException as e:
            print(f'[ERROR] Request error: {e}')
        except Exception as e:
            print(f'[ERROR] Unexpected: {e}')

    save_topic_index(topic_index)
    print(f'[DONE] {generated}/3 articles saved')
    return generated > 0


if __name__ == '__main__':
    success = generate_daily_articles()
    sys.exit(0 if success else 1)
