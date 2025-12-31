# Mike's Scraper

Private market intelligence tool that monitors social media for business opportunities.

## What This Tool Does

1. Add businesses through the dashboard
2. AI suggests keywords using 4 different models (GPT-4o, Claude Opus, DeepSeek, Gemini)
3. Scrapes Reddit, Twitter/X, Hacker News, TikTok, and Instagram for those keywords
4. AI classifies posts to find business opportunities
5. Dashboard to review everything

## Quick Start (Local)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

Get your API key at: https://openrouter.ai/keys

### 3. Initialize Database

```bash
python init_db.py
```

### 4. Start Dashboard

```bash
streamlit run dashboard.py
```

Opens at: http://localhost:8501

### 5. Add Your First Business

1. Go to the **Businesses** tab
2. Enter business name and description
3. Click "Generate Keyword Suggestions"
4. Review AI suggestions (4 models work in parallel)
5. Select keywords and save

## Deploy to Render

1. Push this repo to GitHub
2. Go to https://render.com
3. Create new "Blueprint" and connect your repo
4. Add environment variable: `OPENROUTER_API_KEY`
5. Deploy

The `render.yaml` configures:
- Web service (Streamlit dashboard)
- Persistent disk for SQLite database
- 7 cron jobs for scrapers and classification

## Directory Structure

```
mikes-scraper/
├── dashboard.py              # Main Streamlit UI
├── init_db.py               # Database initialization
├── requirements.txt         # Python dependencies
├── render.yaml             # Render deployment config
├── .env.example            # Environment template
├── database/
│   └── models.py           # DB helpers
├── scrapers/
│   ├── base_scraper.py     # Shared utilities
│   ├── reddit_scraper.py
│   ├── twitter_scraper.py
│   ├── hackernews_scraper.py
│   ├── tiktok_scraper.py
│   └── instagram_scraper.py
├── processing/
│   ├── keyword_suggester.py  # 4-model keyword AI
│   └── classifier.py         # Post classification AI
└── jobs/
    ├── scrape_reddit.py
    ├── scrape_twitter.py
    ├── scrape_hackernews.py
    ├── scrape_tiktok.py
    ├── scrape_instagram.py
    ├── classify_posts.py
    └── health_check.py
```

## Dashboard Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Stats and charts |
| Opportunities | High-relevance posts (7+) with status management |
| All Posts | Searchable list of all scraped posts |
| Businesses | Add/manage businesses and keywords |
| Health | Scraper status monitoring |

## Scraper Schedule (Render Cron)

| Scraper | Schedule |
|---------|----------|
| Reddit | Every 2 hours |
| Twitter | Every 4 hours |
| Hacker News | Every 3 hours |
| TikTok | Every 6 hours |
| Instagram | Every 6 hours |
| Classifier | Every hour (at :30) |
| Health Check | Every 6 hours |

## Test Scrapers Locally

```bash
# Test individual scrapers
python jobs/scrape_reddit.py
python jobs/scrape_hackernews.py
python jobs/classify_posts.py
```

## Notes

- **Twitter** requires authentication - see `scrapers/twitter_scraper.py` for details
- **TikTok** and **Instagram** may require additional setup due to anti-scraping measures
- All scrapers exit gracefully - one failure won't crash the app
- Database auto-detects path: `/data/scraper.db` (Render) or `./data/scraper.db` (local)
