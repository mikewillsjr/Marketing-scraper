#!/usr/bin/env python3
"""
Cron job wrapper for Twitter scraper.
Exits cleanly (code 0) even on failure to prevent Render from marking as crashed.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.twitter_scraper import scrape_twitter
from scrapers.base_scraper import update_heartbeat

if __name__ == "__main__":
    try:
        posts_found = scrape_twitter()
        update_heartbeat('twitter', success=True, posts_found=posts_found)
        print(f"Twitter scraper completed. Found {posts_found} posts.")
    except Exception as e:
        update_heartbeat('twitter', success=False, error=str(e))
        print(f"Twitter scraper failed: {e}")
    # Always exit 0 to prevent Render from marking as crashed
    sys.exit(0)
