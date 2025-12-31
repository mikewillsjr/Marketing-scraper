# Mike's Scraper - Resume Point

## Status: PAUSED
Last updated: 2025-12-31

## What's Working
- Dashboard deployed at siteonaplatter.com
- Database with 5 tables (businesses, keywords, posts, analysis, heartbeats)
- 4-model AI keyword suggestions (GPT-5.2, Claude Opus 4.5, Gemini 3 Pro, DeepSeek V3.2)
- Manual scraper buttons on Overview tab (Reddit, HN, TikTok, Classify)
- All Posts tab with filters (source, date range, search) and Clear All button
- Clickable links to original posts

## What's Disabled
- All cron jobs (auto scraping) - commented out in render.yaml

## Known Issues to Fix
1. **Reddit returning irrelevant results** - Added keyword filtering but needs more testing
2. **Hacker News 0 matches** - Keywords may be too specific for HN content
3. **TikTok scraper** - Returns 0 results, likely blocked by TikTok
4. **Twitter/Instagram scrapers** - Not implemented (placeholders only)
5. **All Posts links** - Code is deployed but user may need hard refresh to see

## Files Changed in This Session
- `scrapers/reddit_scraper.py` - Added JSON API + keyword filtering
- `scrapers/hackernews_scraper.py` - Smarter keyword matching (all words appear)
- `dashboard.py` - Added filters, Clear All button, clickable post links
- `render.yaml` - Cron jobs commented out

## To Re-enable Auto Scraping
Uncomment the `crons:` section in `render.yaml` and push to GitHub.

---

## Claude Code Prompt
Copy this to continue where we left off:

```
I'm resuming work on Mike's Scraper. Here's where we left off:

1. Dashboard is live at siteonaplatter.com
2. Cron jobs are DISABLED (paused auto-scraping)
3. Main issues:
   - Reddit scraper returns some irrelevant results despite filtering
   - HN scraper gets 0 matches (keywords too specific?)
   - TikTok blocked, Twitter/Instagram not implemented
4. Recent changes: Added source/date filters to All Posts tab, clickable links to posts, Clear All button

The user (Mike) is not a developer - give exact instructions, no options.

What would you like to work on?
```
