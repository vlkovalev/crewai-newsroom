"""
Spruce Grove Gazette v2 — Flask + SQLAlchemy + Blueprints
Run: python web_app.py
"""

import os
import json
import requests
from datetime import datetime, timedelta
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, abort)
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gazette_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ──────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────

class Article(db.Model):
    __tablename__ = 'articles'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    slug        = db.Column(db.String(200), unique=True, nullable=False)
    body        = db.Column(db.Text, nullable=False)
    summary     = db.Column(db.String(400), default='')
    category    = db.Column(db.String(60), default='News')
    image_url   = db.Column(db.String(400), default='')
    author      = db.Column(db.String(100), default='Staff')
    published   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Article {self.slug}>'


class Event(db.Model):
    __tablename__ = 'events'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    location    = db.Column(db.String(200), default='')
    start_date  = db.Column(db.DateTime, nullable=False)
    end_date    = db.Column(db.DateTime)
    category    = db.Column(db.String(60), default='Community')
    contact     = db.Column(db.String(200), default='')
    approved    = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Classified(db.Model):
    __tablename__ = 'classifieds'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    body        = db.Column(db.Text, nullable=False)
    category    = db.Column(db.String(60), default='General')
    price       = db.Column(db.String(50), default='')
    contact     = db.Column(db.String(200), default='')
    approved    = db.Column(db.Boolean, default=False)
    expires_at  = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Business(db.Model):
    __tablename__ = 'businesses'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    category    = db.Column(db.String(60), default='General')
    description = db.Column(db.Text, default='')
    address     = db.Column(db.String(300), default='')
    phone       = db.Column(db.String(30), default='')
    website     = db.Column(db.String(300), default='')
    email       = db.Column(db.String(200), default='')
    logo_url    = db.Column(db.String(400), default='')
    approved    = db.Column(db.Boolean, default=False)
    tier        = db.Column(db.String(20), default='free')  # free / supporter / featured
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Subscriber(db.Model):
    __tablename__ = 'subscribers'
    id          = db.Column(db.Integer, primary_key=True)
    email       = db.Column(db.String(200), unique=True, nullable=False)
    name        = db.Column(db.String(100), default='')
    active      = db.Column(db.Boolean, default=True)
    tier        = db.Column(db.String(20), default='free')
    paypal_sub  = db.Column(db.String(100), default='')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def get_weather():
    key = os.environ.get('OPENWEATHER_API_KEY', '')
    if not key:
        return None
    try:
        r = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'q': 'Spruce Grove,CA', 'appid': key, 'units': 'metric'},
            timeout=4
        )
        if r.status_code == 200:
            d = r.json()
            return {
                'temp': round(d['main']['temp']),
                'feels': round(d['main']['feels_like']),
                'desc': d['weather'][0]['description'].title(),
                'icon': d['weather'][0]['icon'],
            }
    except Exception:
        pass
    return None


def admin_required():
    if not session.get('admin'):
        abort(403)


def slugify(text):
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


# ──────────────────────────────────────────────
# PUBLIC ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    articles = Article.query.filter_by(published=True)\
                            .order_by(Article.created_at.desc())\
                            .limit(12).all()
    events = Event.query.filter(
        Event.approved == True,
        Event.start_date >= datetime.utcnow()
    ).order_by(Event.start_date).limit(5).all()
    weather = get_weather()
    return render_template('index.html',
                           articles=articles,
                           events=events,
                           weather=weather)


@app.route('/article/<slug>')
def article_detail(slug):
    article = Article.query.filter_by(slug=slug, published=True).first_or_404()
    related = Article.query.filter(
        Article.category == article.category,
        Article.id != article.id,
        Article.published == True
    ).order_by(Article.created_at.desc()).limit(3).all()
    return render_template('article.html', article=article, related=related)


@app.route('/category/<cat>')
def category(cat):
    articles = Article.query.filter_by(published=True, category=cat)\
                            .order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category=cat)


@app.route('/events')
def events():
    upcoming = Event.query.filter(
        Event.approved == True,
        Event.start_date >= datetime.utcnow()
    ).order_by(Event.start_date).all()
    return render_template('events.html', events=upcoming)


@app.route('/events/submit', methods=['GET', 'POST'])
def submit_event():
    if request.method == 'POST':
        ev = Event(
            title=request.form['title'],
            description=request.form.get('description', ''),
            location=request.form.get('location', ''),
            start_date=datetime.fromisoformat(request.form['start_date']),
            end_date=datetime.fromisoformat(request.form['end_date']) if request.form.get('end_date') else None,
            category=request.form.get('category', 'Community'),
            contact=request.form.get('contact', ''),
        )
        db.session.add(ev)
        db.session.commit()
        flash('Event submitted! It will appear after review.', 'success')
        return redirect(url_for('events'))
    return render_template('submit_event.html')


@app.route('/classifieds')
def classifieds():
    cat = request.args.get('cat', '')
    q = Classified.query.filter(
        Classified.approved == True,
        Classified.expires_at >= datetime.utcnow()
    )
    if cat:
        q = q.filter_by(category=cat)
    ads = q.order_by(Classified.created_at.desc()).all()
    cats = db.session.query(Classified.category).distinct().all()
    return render_template('classifieds.html', ads=ads, cats=[c[0] for c in cats], selected=cat)


@app.route('/classifieds/post', methods=['GET', 'POST'])
def post_classified():
    if request.method == 'POST':
        ad = Classified(
            title=request.form['title'],
            body=request.form['body'],
            category=request.form.get('category', 'General'),
            price=request.form.get('price', ''),
            contact=request.form.get('contact', ''),
        )
        db.session.add(ad)
        db.session.commit()
        flash('Classified posted! It will appear after review.', 'success')
        return redirect(url_for('classifieds'))
    return render_template('post_classified.html')


@app.route('/directory')
def directory():
    cat = request.args.get('cat', '')
    q = Business.query.filter_by(approved=True)
    if cat:
        q = q.filter_by(category=cat)
    businesses = q.order_by(Business.tier.desc(), Business.name).all()
    cats = db.session.query(Business.category).distinct().all()
    return render_template('directory.html', businesses=businesses,
                           cats=[c[0] for c in cats], selected=cat)


@app.route('/directory/list', methods=['GET', 'POST'])
def list_business():
    if request.method == 'POST':
        biz = Business(
            name=request.form['name'],
            category=request.form.get('category', 'General'),
            description=request.form.get('description', ''),
            address=request.form.get('address', ''),
            phone=request.form.get('phone', ''),
            website=request.form.get('website', ''),
            email=request.form.get('email', ''),
        )
        db.session.add(biz)
        db.session.commit()
        flash('Business listed! It will appear after review.', 'success')
        return redirect(url_for('directory'))
    return render_template('list_business.html')


@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    paypal_id = os.environ.get('PAYPAL_CLIENT_ID', '')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        if not email:
            flash('Email is required.', 'danger')
            return redirect(url_for('subscribe'))
        existing = Subscriber.query.filter_by(email=email).first()
        if existing:
            flash('You are already subscribed!', 'info')
        else:
            sub = Subscriber(email=email, name=name)
            db.session.add(sub)
            db.session.commit()
            flash('Subscribed! Thank you for supporting the Gazette.', 'success')
        return redirect(url_for('index'))
    return render_template('subscribe.html', paypal_id=paypal_id)


# PayPal webhook
@app.route('/paypal/webhook', methods=['POST'])
def paypal_webhook():
    data = request.get_json(silent=True) or {}
    event_type = data.get('event_type', '')
    if event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
        sub_id = data.get('resource', {}).get('id', '')
        payer = data.get('resource', {}).get('subscriber', {})
        email = payer.get('email_address', '')
        if email:
            existing = Subscriber.query.filter_by(email=email).first()
            if existing:
                existing.tier = 'supporter'
                existing.paypal_sub = sub_id
            else:
                db.session.add(Subscriber(email=email, tier='supporter', paypal_sub=sub_id))
            db.session.commit()
    return '', 200


# ──────────────────────────────────────────────
# ADMIN ROUTES
# ──────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pw = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if request.form.get('password') == pw:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Wrong password.', 'danger')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
def admin_dashboard():
    admin_required()
    stats = {
        'articles': Article.query.count(),
        'events': Event.query.filter_by(approved=False).count(),
        'classifieds': Classified.query.filter_by(approved=False).count(),
        'businesses': Business.query.filter_by(approved=False).count(),
        'subscribers': Subscriber.query.filter_by(active=True).count(),
    }
    recent = Article.query.order_by(Article.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)


@app.route('/admin/articles')
def admin_articles():
    admin_required()
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('admin/articles.html', articles=articles)


@app.route('/admin/articles/new', methods=['GET', 'POST'])
def admin_new_article():
    admin_required()
    if request.method == 'POST':
        title = request.form['title']
        slug = slugify(title)
        # ensure unique slug
        base, n = slug, 1
        while Article.query.filter_by(slug=slug).first():
            slug = f'{base}-{n}'; n += 1
        art = Article(
            title=title, slug=slug,
            body=request.form['body'],
            summary=request.form.get('summary', ''),
            category=request.form.get('category', 'News'),
            image_url=request.form.get('image_url', ''),
            author=request.form.get('author', 'Staff'),
            published=bool(request.form.get('published')),
        )
        db.session.add(art)
        db.session.commit()
        flash('Article created.', 'success')
        return redirect(url_for('admin_articles'))
    categories = ['News', 'Sports', 'Arts & Culture', 'Business', 'Community', 'Opinion']
    return render_template('admin/edit_article.html', article=None, categories=categories)


@app.route('/admin/articles/<int:id>/edit', methods=['GET', 'POST'])
def admin_edit_article(id):
    admin_required()
    art = Article.query.get_or_404(id)
    if request.method == 'POST':
        art.title = request.form['title']
        art.body = request.form['body']
        art.summary = request.form.get('summary', '')
        art.category = request.form.get('category', 'News')
        art.image_url = request.form.get('image_url', '')
        art.author = request.form.get('author', 'Staff')
        art.published = bool(request.form.get('published'))
        db.session.commit()
        flash('Article updated.', 'success')
        return redirect(url_for('admin_articles'))
    categories = ['News', 'Sports', 'Arts & Culture', 'Business', 'Community', 'Opinion']
    return render_template('admin/edit_article.html', article=art, categories=categories)


@app.route('/admin/articles/<int:id>/delete', methods=['POST'])
def admin_delete_article(id):
    admin_required()
    art = Article.query.get_or_404(id)
    db.session.delete(art)
    db.session.commit()
    flash('Article deleted.', 'success')
    return redirect(url_for('admin_articles'))


@app.route('/admin/moderate/<model>/<int:id>/<action>', methods=['POST'])
def admin_moderate(model, id, action):
    admin_required()
    models = {'event': Event, 'classified': Classified, 'business': Business}
    cls = models.get(model)
    if not cls:
        abort(404)
    obj = cls.query.get_or_404(id)
    if action == 'approve':
        obj.approved = True
        db.session.commit()
        flash(f'{model.title()} approved.', 'success')
    elif action == 'reject':
        db.session.delete(obj)
        db.session.commit()
        flash(f'{model.title()} rejected.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/events')
def admin_events():
    admin_required()
    items = Event.query.order_by(Event.approved, Event.created_at.desc()).all()
    return render_template('admin/moderate.html', items=items, model='event', title='Events')


@app.route('/admin/classifieds')
def admin_classifieds():
    admin_required()
    items = Classified.query.order_by(Classified.approved, Classified.created_at.desc()).all()
    return render_template('admin/moderate.html', items=items, model='classified', title='Classifieds')


@app.route('/admin/businesses')
def admin_businesses():
    admin_required()
    items = Business.query.order_by(Business.approved, Business.created_at.desc()).all()
    return render_template('admin/moderate.html', items=items, model='business', title='Businesses')


@app.route('/admin/generate', methods=['POST'])
def admin_generate():
    admin_required()
    import threading
    t = threading.Thread(target=generate_daily_articles, daemon=True)
    t.start()
    flash('AI article generation started — refresh in 30 seconds.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/subscribers')
def admin_subscribers():
    admin_required()
    subs = Subscriber.query.order_by(Subscriber.created_at.desc()).all()
    return render_template('admin/subscribers.html', subscribers=subs)


# ──────────────────────────────────────────────
# API ENDPOINTS (JSON)
# ──────────────────────────────────────────────

@app.route('/api/weather')
def api_weather():
    return jsonify(get_weather() or {})


@app.route('/api/articles')
def api_articles():
    limit = min(int(request.args.get('limit', 20)), 100)
    cat = request.args.get('category', '')
    q = Article.query.filter_by(published=True)
    if cat:
        q = q.filter_by(category=cat)
    arts = q.order_by(Article.created_at.desc()).limit(limit).all()
    return jsonify([{
        'id': a.id, 'title': a.title, 'slug': a.slug,
        'summary': a.summary, 'category': a.category,
        'author': a.author, 'created_at': a.created_at.isoformat()
    } for a in arts])


# ──────────────────────────────────────────────
# SCHEDULED TASKS
# ──────────────────────────────────────────────

def cleanup_expired():
    """Remove expired classifieds"""
    with app.app_context():
        expired = Classified.query.filter(
            Classified.expires_at < datetime.utcnow()
        ).all()
        for ad in expired:
            db.session.delete(ad)
        if expired:
            db.session.commit()
            print(f'Cleaned up {len(expired)} expired classifieds')


# Topic rotation — cycles through categories so articles stay varied
_TOPIC_ROTATION = [
    ('Community', 'a community event, neighbourhood initiative, or local volunteer story in Spruce Grove, Alberta'),
    ('News',      'a local government update, city council decision, or infrastructure project in Spruce Grove, Alberta'),
    ('Sports',    'a youth or amateur sports story, local team result, or recreation program in Spruce Grove, Alberta'),
    ('Arts & Culture', 'a local arts event, cultural festival, library program, or creative community story in Spruce Grove, Alberta'),
    ('Business',  'a new business opening, local entrepreneur story, or economic development update in Spruce Grove, Alberta'),
    ('Opinion',   'an editorial opinion piece about life, growth, or community values in Spruce Grove, Alberta'),
]
_topic_index = 0


def generate_daily_articles():
    """Call Gemini to write 3 fresh Spruce Grove articles and save to DB."""
    global _topic_index
    key = os.environ.get('GEMINI_API_KEY', '')
    if not key:
        print('[AI] No GEMINI_API_KEY — skipping article generation')
        return

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}'
    today = datetime.utcnow().strftime('%B %d, %Y')

    with app.app_context():
        generated = 0
        for _ in range(3):
            cat, topic_desc = _TOPIC_ROTATION[_topic_index % len(_TOPIC_ROTATION)]
            _topic_index += 1

            prompt = (
                f'You are a staff writer for the Spruce Grove Gazette, a community newspaper in Spruce Grove, Alberta, Canada. '
                f'Today is {today}. Write a realistic, engaging local news article about {topic_desc}. '
                f'Use specific Spruce Grove locations, street names, parks, or venues to make it feel authentic. '
                f'Respond ONLY with valid JSON in this exact format:\n'
                f'{{"title": "...", "summary": "One sentence, max 150 chars.", '
                f'"body": "Full HTML article body using <p> tags, 3-5 paragraphs.", '
                f'"author": "First Last (staff writer name)"}}'
            )

            try:
                resp = requests.post(url, json={
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {'temperature': 0.85, 'maxOutputTokens': 1024}
                }, timeout=20)

                if resp.status_code != 200:
                    print(f'[AI] Gemini error {resp.status_code}: {resp.text[:200]}')
                    continue

                raw = resp.json()
                text = raw['candidates'][0]['content']['parts'][0]['text'].strip()
                # Strip markdown code fences if present
                if text.startswith('```'):
                    text = text.split('```')[1]
                    if text.startswith('json'):
                        text = text[4:]
                text = text.strip()

                data = json.loads(text)
                title   = data.get('title', '').strip()
                summary = data.get('summary', '').strip()[:400]
                body    = data.get('body', '').strip()
                author  = data.get('author', 'Staff Writer').strip()

                if not title or not body:
                    print('[AI] Empty title or body — skipping')
                    continue

                # Build a unique slug
                base_slug = slugify(title)
                slug = base_slug
                n = 1
                while Article.query.filter_by(slug=slug).first():
                    slug = f'{base_slug}-{n}'; n += 1

                art = Article(
                    title=title, slug=slug, body=body,
                    summary=summary, category=cat,
                    author=author, published=True,
                )
                db.session.add(art)
                db.session.commit()
                generated += 1
                print(f'[AI] Generated: {title}')

            except json.JSONDecodeError as e:
                print(f'[AI] JSON parse error: {e}')
            except Exception as e:
                print(f'[AI] Unexpected error: {e}')

        print(f'[AI] Daily generation complete — {generated}/3 articles saved')


# ──────────────────────────────────────────────
# APP STARTUP
# ──────────────────────────────────────────────

def create_app():
    with app.app_context():
        db.create_all()
        # Seed sample data if empty
        if Article.query.count() == 0:
            sample = Article(
                title='Welcome to the Spruce Grove Gazette v2',
                slug='welcome-to-gazette-v2',
                body='<p>The Gazette v2 is live! This improved version features a proper database, '
                     'blueprint architecture, better admin tools, and a mobile-friendly design.</p>'
                     '<p>Stay tuned for more Spruce Grove news, events, and community updates.</p>',
                summary='Spruce Grove Gazette v2 is now live with improvements.',
                category='News',
                author='Editorial Staff',
                published=True,
            )
            db.session.add(sample)
            db.session.commit()

    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired, 'interval', hours=24)
    scheduler.add_job(generate_daily_articles, 'cron', hour=6, minute=0)  # 6 AM UTC daily
    scheduler.start()

    # Generate articles immediately if the DB is nearly empty (must be inside app context)
    with app.app_context():
        if Article.query.count() <= 1:
            import threading
            t = threading.Thread(target=generate_daily_articles, daemon=True)
            t.start()

    return app


if __name__ == '__main__':
    create_app()
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port)
