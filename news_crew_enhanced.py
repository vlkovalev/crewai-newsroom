"""Render cron wrapper for one-off daily article generation."""

from web_app import create_app, generate_daily_articles

if __name__ == '__main__':
    app = create_app(start_scheduler=False)
    with app.app_context():
        generate_daily_articles()
    print('news_crew_enhanced.py completed successfully')
