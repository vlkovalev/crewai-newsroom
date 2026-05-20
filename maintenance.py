#!/usr/bin/env python3
"""
Nightly maintenance for Spruce Grove Gazette.
- Decays article scores (older articles score lower over time)
- Populates missing FTS search vectors
- Sets missing expires_from_front dates
- Logs DB health stats

Can be run standalone (via Render cron) or imported by APScheduler.
Requires: DATABASE_URL
"""

import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime


def get_db():
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def run_maintenance():
    print(f'[MAINTENANCE] Starting at {datetime.utcnow().isoformat()}')
    conn = get_db()
    cursor = conn.cursor()

    # 1. Populate missing FTS vectors (new articles not yet indexed)
    cursor.execute("""
        UPDATE news_articles
        SET search_vector = to_tsvector('english',
            coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(content,''))
        WHERE search_vector IS NULL AND active = TRUE
    """)
    fts_updated = cursor.rowcount
    print(f'  FTS vectors populated: {fts_updated}')

    # 2. Set expires_from_front for any articles missing it
    cursor.execute("""
        UPDATE news_articles
        SET expires_from_front = date + INTERVAL '7 days'
        WHERE expires_from_front IS NULL AND date IS NOT NULL AND active = TRUE
    """)
    expires_set = cursor.rowcount
    print(f'  Expiry dates set: {expires_set}')

    # 3. Score decay — reduce stored score by 3 for articles older than 24h.
    #    Stored score floor is 5 (never fully disappears from archive/search).
    #    Pinned and urgent articles are exempt from decay.
    cursor.execute("""
        UPDATE news_articles
        SET score = GREATEST(coalesce(score, 50) - 3, 5)
        WHERE active = TRUE
          AND pinned = FALSE
          AND urgent = FALSE
          AND date < NOW() - INTERVAL '24 hours'
          AND coalesce(score, 50) > 5
    """)
    decayed = cursor.rowcount
    print(f'  Articles score-decayed: {decayed}')

    # 4. Auto-demote expired urgent flags (urgent older than 12h loses flag)
    cursor.execute("""
        UPDATE news_articles
        SET urgent = FALSE
        WHERE urgent = TRUE AND date < NOW() - INTERVAL '12 hours'
    """)
    urgent_cleared = cursor.rowcount
    print(f'  Urgent flags cleared: {urgent_cleared}')

    # 5. Stats
    cursor.execute("SELECT COUNT(*) FROM news_articles WHERE active = TRUE")
    total = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) FROM news_articles WHERE active = TRUE AND date >= NOW() - INTERVAL '24 hours'")
    today = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) FROM news_articles WHERE active = TRUE AND date >= NOW() - INTERVAL '7 days'")
    week = cursor.fetchone()['count']

    cursor.execute("SELECT category, COUNT(*) FROM news_articles WHERE active = TRUE GROUP BY category ORDER BY count DESC")
    by_cat = {r['category']: r['count'] for r in cursor.fetchall()}

    conn.commit()
    conn.close()

    print(f'  Total active articles: {total}')
    print(f'  Published today: {today}')
    print(f'  Published this week: {week}')
    print(f'  By category: {by_cat}')
    print(f'[MAINTENANCE] Complete')
    return True


if __name__ == '__main__':
    success = run_maintenance()
    sys.exit(0 if success else 1)
