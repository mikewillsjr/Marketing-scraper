#!/usr/bin/env python3
"""
Health check job.
Checks heartbeats and logs warnings for stale scrapers.
"""
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import get_db_connection


def check_health():
    """
    Check all scraper heartbeats and log warnings for stale ones.

    Returns:
        Number of healthy scrapers
    """
    print("Health check starting...")

    scrapers = ['reddit', 'twitter', 'hackernews', 'tiktok', 'instagram', 'classifier']
    cutoff = datetime.now() - timedelta(hours=24)

    conn = get_db_connection()
    cursor = conn.cursor()

    healthy = 0
    warnings = []

    for scraper in scrapers:
        cursor.execute('''
            SELECT last_success, last_error, posts_found
            FROM heartbeats
            WHERE scraper_name = ?
        ''', (scraper,))
        row = cursor.fetchone()

        if not row:
            warnings.append(f"  {scraper}: Never run")
            continue

        last_success = row['last_success']
        last_error = row['last_error']
        posts_found = row['posts_found'] or 0

        if last_success:
            success_time = datetime.fromisoformat(last_success)
            if success_time > cutoff:
                print(f"  {scraper}: OK (last success: {last_success}, posts: {posts_found})")
                healthy += 1
            else:
                hours_ago = int((datetime.now() - success_time).total_seconds() / 3600)
                warnings.append(f"  {scraper}: STALE ({hours_ago}h since last success)")
        else:
            warnings.append(f"  {scraper}: FAILED (error: {last_error})")

    conn.close()

    # Print warnings at the end
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(warning)

    print(f"\nHealth check complete. {healthy}/{len(scrapers)} scrapers healthy.")
    return healthy


if __name__ == "__main__":
    try:
        healthy = check_health()
    except Exception as e:
        print(f"Health check failed: {e}")
    # Always exit 0
    sys.exit(0)
