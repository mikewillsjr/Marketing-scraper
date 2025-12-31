"""
Reddit scraper using old.reddit.com/search.
Easier to parse than new Reddit.
"""
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post,
    retry_with_backoff
)


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 2  # seconds between requests


def parse_reddit_timestamp(time_str):
    """Parse Reddit's relative time string to datetime."""
    # Reddit shows things like "1 hour ago", "2 days ago", etc.
    # For simplicity, we'll just use current time as approximation
    return datetime.now().isoformat()


def parse_search_results(html):
    """Parse Reddit search results HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    posts = []

    # Find all search result items
    for thing in soup.find_all('div', class_='thing'):
        try:
            # Extract data attributes
            data_fullname = thing.get('data-fullname', '')
            data_subreddit = thing.get('data-subreddit', '')
            data_author = thing.get('data-author', '')
            data_url = thing.get('data-url', '')

            # Get title
            title_elem = thing.find('a', class_='title')
            title = title_elem.get_text(strip=True) if title_elem else ''

            # Get selftext/body (if it's a self post)
            body = ''
            expando = thing.find('div', class_='expando')
            if expando:
                usertext = expando.find('div', class_='usertext-body')
                if usertext:
                    body = usertext.get_text(strip=True)

            # Get permalink
            comments_link = thing.find('a', class_='comments')
            permalink = comments_link.get('href', '') if comments_link else ''
            if permalink and not permalink.startswith('http'):
                permalink = f"https://reddit.com{permalink}"

            # Generate unique source_id
            source_id = data_fullname or f"reddit_{hash(title + data_author)}"

            if title:  # Only add if we have a title
                posts.append({
                    'source_id': source_id,
                    'title': title,
                    'body': body[:5000],  # Truncate long bodies
                    'author': data_author,
                    'subreddit': data_subreddit,
                    'url': permalink or data_url,
                    'created_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error parsing post: {e}")
            continue

    return posts


@retry_with_backoff(max_retries=3, base_delay=5)
def search_reddit(keyword, session):
    """Search Reddit for a keyword."""
    encoded_keyword = quote_plus(keyword)
    url = f"https://old.reddit.com/search?q={encoded_keyword}&sort=new&t=week"

    response = session.get(
        url,
        headers={'User-Agent': USER_AGENT},
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return parse_search_results(response.text)


def scrape_reddit():
    """
    Main scraping function.
    Gets keywords from database and searches Reddit for each.

    Returns:
        Number of new posts found
    """
    print("Reddit scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    print(f"Searching for {len(keywords)} keywords...")
    session = requests.Session()
    total_posts = 0

    for keyword in keywords:
        try:
            print(f"  Searching: {keyword}")
            posts = search_reddit(keyword, session)

            new_posts = 0
            for post in posts:
                inserted = insert_post(
                    source='reddit',
                    source_id=post['source_id'],
                    url=post['url'],
                    title=post['title'],
                    body=post['body'],
                    author=post['author'],
                    subreddit=post['subreddit'],
                    created_at=post['created_at']
                )
                if inserted:
                    new_posts += 1

            print(f"    Found {len(posts)} posts, {new_posts} new")
            total_posts += new_posts

            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"  Error searching '{keyword}': {e}")
            continue

    print(f"Reddit scraper completed. Found {total_posts} new posts.")
    return total_posts


if __name__ == '__main__':
    scrape_reddit()
