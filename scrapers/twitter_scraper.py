"""
Twitter/X scraper using twikit library.
Twitter actively fights scrapers, so this may break frequently.
"""
import asyncio
import os
import time
from datetime import datetime

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post,
    retry_with_backoff
)


async def scrape_twitter_async():
    """
    Async Twitter scraping function using twikit.

    Returns:
        Number of new posts found
    """
    print("Twitter scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    total_posts = 0

    try:
        # Import twikit here to allow graceful failure
        from twikit import Client

        # Initialize client
        client = Client('en-US')

        # Note: twikit requires authentication
        # You would need to login with cookies or credentials
        # For now, we'll document the expected flow

        # Check for auth cookies file
        cookies_file = os.path.join(os.path.dirname(__file__), '..', 'twitter_cookies.json')

        if not os.path.exists(cookies_file):
            print("Twitter requires authentication. Please create twitter_cookies.json")
            print("See twikit documentation for cookie-based authentication")
            return 0

        # Load cookies
        client.load_cookies(cookies_file)

        print(f"Searching for {len(keywords)} keywords...")

        for keyword in keywords:
            try:
                print(f"  Searching: {keyword}")

                # Search tweets
                tweets = await client.search_tweet(keyword, 'Latest')

                new_posts = 0
                for tweet in tweets:
                    try:
                        source_id = f"twitter_{tweet.id}"

                        inserted = insert_post(
                            source='twitter',
                            source_id=source_id,
                            url=f"https://twitter.com/i/web/status/{tweet.id}",
                            title=None,  # Twitter doesn't have titles
                            body=tweet.text,
                            author=tweet.user.screen_name if tweet.user else None,
                            subreddit=None,
                            created_at=tweet.created_at.isoformat() if tweet.created_at else datetime.now().isoformat()
                        )
                        if inserted:
                            new_posts += 1
                    except Exception as e:
                        print(f"    Error processing tweet: {e}")
                        continue

                print(f"    Found {len(tweets) if tweets else 0} tweets, {new_posts} new")
                total_posts += new_posts

                # Rate limiting - Twitter is aggressive
                await asyncio.sleep(3)

            except Exception as e:
                print(f"  Error searching '{keyword}': {e}")
                continue

    except ImportError:
        print("twikit not installed. Run: pip install twikit")
        return 0
    except Exception as e:
        print(f"Twitter scraper error: {e}")
        return 0

    print(f"Twitter scraper completed. Found {total_posts} new posts.")
    return total_posts


def scrape_twitter():
    """
    Synchronous wrapper for Twitter scraping.

    Returns:
        Number of new posts found
    """
    try:
        return asyncio.run(scrape_twitter_async())
    except Exception as e:
        print(f"Twitter scraper failed: {e}")
        return 0


if __name__ == '__main__':
    scrape_twitter()
