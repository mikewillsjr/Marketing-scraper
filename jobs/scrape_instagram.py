#!/usr/bin/env python3
"""
Cron job wrapper for Instagram scraper.
Exits cleanly (code 0) even on failure to prevent Render from marking as crashed.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.instagram_scraper import scrape_instagram
from scrapers.base_scraper import update_heartbeat

if __name__ == "__main__":
    try:
        posts_found = scrape_instagram()
        update_heartbeat('instagram', success=True, posts_found=posts_found)
        print(f"Instagram scraper completed. Found {posts_found} posts.")
    except Exception as e:
        update_heartbeat('instagram', success=False, error=str(e))
        print(f"Instagram scraper failed: {e}")
    # Always exit 0 to prevent Render from marking as crashed
    sys.exit(0)
