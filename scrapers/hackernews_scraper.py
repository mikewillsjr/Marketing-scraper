"""
Hacker News scraper using the official Firebase API.
No rate limiting needed since it's the official API.
"""
import requests
from datetime import datetime

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post,
    retry_with_backoff
)


HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
REQUEST_TIMEOUT = 30


@retry_with_backoff(max_retries=3, base_delay=2)
def fetch_item(item_id):
    """Fetch a single HN item by ID."""
    response = requests.get(
        f"{HN_API_BASE}/item/{item_id}.json",
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


@retry_with_backoff(max_retries=3, base_delay=2)
def fetch_new_stories(limit=500):
    """Fetch the latest story IDs."""
    response = requests.get(
        f"{HN_API_BASE}/newstories.json",
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    story_ids = response.json()
    return story_ids[:limit] if story_ids else []


def matches_keywords(item, keywords):
    """Check if an HN item matches any of our keywords."""
    if not item:
        return False

    # Build searchable text
    title = (item.get('title') or '').lower()
    text = (item.get('text') or '').lower()
    searchable = f"{title} {text}"

    # Check each keyword
    for keyword in keywords:
        if keyword.lower() in searchable:
            return True

    return False


def scrape_hackernews():
    """
    Main scraping function.
    Fetches recent stories and filters by keywords.

    Returns:
        Number of new posts found
    """
    print("Hacker News scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    print(f"Matching against {len(keywords)} keywords...")

    # Fetch recent story IDs
    try:
        story_ids = fetch_new_stories(limit=500)
        print(f"Fetched {len(story_ids)} recent stories")
    except Exception as e:
        print(f"Failed to fetch story IDs: {e}")
        return 0

    total_posts = 0
    checked = 0
    matches = 0

    for story_id in story_ids:
        try:
            item = fetch_item(story_id)
            checked += 1

            if not item:
                continue

            # Skip deleted/dead items
            if item.get('deleted') or item.get('dead'):
                continue

            # Only process stories (not comments/jobs/polls)
            if item.get('type') != 'story':
                continue

            # Check if matches any keywords
            if not matches_keywords(item, keywords):
                continue

            matches += 1

            # Generate source_id
            source_id = f"hn_{item['id']}"

            # Build URL
            url = item.get('url')
            if not url:
                url = f"https://news.ycombinator.com/item?id={item['id']}"

            # Parse timestamp
            timestamp = item.get('time')
            created_at = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()

            # Insert post
            inserted = insert_post(
                source='hackernews',
                source_id=source_id,
                url=url,
                title=item.get('title'),
                body=item.get('text'),  # Only self-posts have text
                author=item.get('by'),
                subreddit=None,
                created_at=created_at
            )

            if inserted:
                total_posts += 1
                print(f"  New: {item.get('title', '')[:60]}...")

        except Exception as e:
            print(f"  Error fetching story {story_id}: {e}")
            continue

        # Progress update every 100 stories
        if checked % 100 == 0:
            print(f"  Checked {checked} stories, found {matches} matches, {total_posts} new")

    print(f"Hacker News scraper completed.")
    print(f"  Checked: {checked} stories")
    print(f"  Matched: {matches} stories")
    print(f"  New posts: {total_posts}")

    return total_posts


if __name__ == '__main__':
    scrape_hackernews()
