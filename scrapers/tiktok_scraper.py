"""
TikTok scraper using direct HTTP requests.
Scrapes TikTok's web API without external dependencies.
TikTok actively fights scrapers, so this may break frequently.
"""
import json
import re
import time
from datetime import datetime
from urllib.parse import quote

import requests

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post,
    retry_with_backoff
)


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 3


def get_tiktok_session():
    """Create a session with TikTok-appropriate headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    return session


def parse_sigi_state(html):
    """
    Extract video data from TikTok's SIGI_STATE script tag.
    TikTok embeds JSON data in the page for SSR hydration.
    """
    videos = []

    try:
        # Look for SIGI_STATE which contains the page data
        pattern = r'<script id="SIGI_STATE" type="application/json">(.+?)</script>'
        match = re.search(pattern, html, re.DOTALL)

        if match:
            data = json.loads(match.group(1))

            # Extract items from ItemModule
            item_module = data.get('ItemModule', {})
            for video_id, video_data in item_module.items():
                try:
                    author = video_data.get('author', '')
                    desc = video_data.get('desc', '')
                    create_time = video_data.get('createTime', 0)

                    videos.append({
                        'id': video_id,
                        'author': author,
                        'description': desc,
                        'created_at': datetime.fromtimestamp(int(create_time)).isoformat() if create_time else datetime.now().isoformat(),
                        'url': f"https://www.tiktok.com/@{author}/video/{video_id}"
                    })
                except Exception as e:
                    print(f"    Error parsing video {video_id}: {e}")
                    continue

    except json.JSONDecodeError as e:
        print(f"    JSON decode error: {e}")
    except Exception as e:
        print(f"    Error parsing SIGI_STATE: {e}")

    # Fallback: try __UNIVERSAL_DATA_FOR_REHYDRATION__
    if not videos:
        try:
            pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.+?)</script>'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                data = json.loads(match.group(1))
                default_scope = data.get('__DEFAULT_SCOPE__', {})

                # Try to find video list in various locations
                for key in ['webapp.video-detail', 'webapp.hashtag-detail']:
                    if key in default_scope:
                        item_list = default_scope[key].get('itemList', [])
                        for item in item_list:
                            try:
                                video_id = item.get('id', '')
                                author = item.get('author', {}).get('uniqueId', '')
                                desc = item.get('desc', '')
                                create_time = item.get('createTime', 0)

                                if video_id:
                                    videos.append({
                                        'id': video_id,
                                        'author': author,
                                        'description': desc,
                                        'created_at': datetime.fromtimestamp(int(create_time)).isoformat() if create_time else datetime.now().isoformat(),
                                        'url': f"https://www.tiktok.com/@{author}/video/{video_id}"
                                    })
                            except Exception as e:
                                continue
        except Exception as e:
            print(f"    Error parsing UNIVERSAL_DATA: {e}")

    return videos


@retry_with_backoff(max_retries=2, base_delay=5)
def search_tiktok_hashtag(hashtag, session):
    """
    Search TikTok by hashtag via web scraping.
    Returns list of video dicts.
    """
    # Clean hashtag
    hashtag = hashtag.lstrip('#').replace(' ', '').lower()

    url = f"https://www.tiktok.com/tag/{quote(hashtag)}"

    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return parse_sigi_state(response.text)


@retry_with_backoff(max_retries=2, base_delay=5)
def search_tiktok_keyword(keyword, session):
    """
    Search TikTok by keyword via web scraping.
    Returns list of video dicts.
    """
    # TikTok search URL
    url = f"https://www.tiktok.com/search?q={quote(keyword)}"

    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return parse_sigi_state(response.text)


def scrape_tiktok():
    """
    Main TikTok scraping function.
    Searches by hashtag and keyword.

    Returns:
        Number of new posts found
    """
    print("TikTok scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    print(f"Searching for {len(keywords)} keywords/hashtags...")
    session = get_tiktok_session()
    total_posts = 0

    for keyword in keywords:
        try:
            # Clean keyword
            search_term = keyword.strip()

            # Determine if it's a hashtag or keyword search
            if search_term.startswith('#') or (len(search_term) <= 30 and ' ' not in search_term):
                # Hashtag search
                hashtag = search_term.lstrip('#')
                print(f"  Searching hashtag: #{hashtag}")
                videos = search_tiktok_hashtag(hashtag, session)
            else:
                # Keyword search
                print(f"  Searching keyword: {search_term}")
                videos = search_tiktok_keyword(search_term, session)

            new_posts = 0
            for video in videos[:30]:  # Limit to 30 per search
                try:
                    source_id = f"tiktok_{video['id']}"

                    inserted = insert_post(
                        source='tiktok',
                        source_id=source_id,
                        url=video['url'],
                        title=None,
                        body=video.get('description', ''),
                        author=video.get('author'),
                        subreddit=search_term.lstrip('#'),  # Store hashtag/keyword
                        created_at=video.get('created_at', datetime.now().isoformat())
                    )
                    if inserted:
                        new_posts += 1

                except Exception as e:
                    print(f"    Error processing video: {e}")
                    continue

            print(f"    Found {len(videos)} videos, {new_posts} new")
            total_posts += new_posts

            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"  Access denied for '{keyword}' - TikTok may be blocking requests")
            else:
                print(f"  HTTP error searching '{keyword}': {e}")
            continue
        except Exception as e:
            print(f"  Error searching '{keyword}': {e}")
            continue

    print(f"TikTok scraper completed. Found {total_posts} new posts.")
    return total_posts


if __name__ == '__main__':
    scrape_tiktok()
