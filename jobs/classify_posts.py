#!/usr/bin/env python3
"""
Cron job wrapper for post classification.
Exits cleanly (code 0) even on failure to prevent Render from marking as crashed.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from processing.classifier import classify_posts
from scrapers.base_scraper import update_heartbeat

if __name__ == "__main__":
    try:
        posts_classified = classify_posts(batch_size=10)
        update_heartbeat('classifier', success=True, posts_found=posts_classified)
        print(f"Classification completed. Processed {posts_classified} posts.")
    except Exception as e:
        update_heartbeat('classifier', success=False, error=str(e))
        print(f"Classification failed: {e}")
    # Always exit 0 to prevent Render from marking as crashed
    sys.exit(0)
