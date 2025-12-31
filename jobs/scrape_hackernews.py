#!/usr/bin/env python3
"""
Cron job wrapper for Hacker News scraper.
Exits cleanly (code 0) even on failure to prevent Render from marking as crashed.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.hackernews_scraper import scrape_hackernews
from scrapers.base_scraper import update_heartbeat

if __name__ == "__main__":
    try:
        posts_found = scrape_hackernews()
        update_heartbeat('hackernews', success=True, posts_found=posts_found)
        print(f"Hacker News scraper completed. Found {posts_found} posts.")
    except Exception as e:
        update_heartbeat('hackernews', success=False, error=str(e))
        print(f"Hacker News scraper failed: {e}")
    # Always exit 0 to prevent Render from marking as crashed
    sys.exit(0)
