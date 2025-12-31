"""
TikTok scraper using TikTok-Api library.
TikTok actively fights scrapers, so this may break frequently.
Requires playwright for browser automation.
"""
import asyncio
from datetime import datetime

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post
)


async def scrape_tiktok_async():
    """
    Async TikTok scraping function.

    Returns:
        Number of new posts found
    """
    print("TikTok scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    total_posts = 0

    try:
        # Import here to allow graceful failure if not installed
        from TikTokApi import TikTokApi

        async with TikTokApi() as api:
            # Create sessions (required for the API to work)
            await api.create_sessions(
                num_sessions=1,
                sleep_after=3,
                headless=True
            )

            print(f"Searching for {len(keywords)} keywords/hashtags...")

            for keyword in keywords:
                try:
                    # Clean keyword for hashtag search (remove # if present)
                    search_term = keyword.lstrip('#').replace(' ', '')

                    print(f"  Searching hashtag: #{search_term}")

                    # Search by hashtag
                    hashtag = api.hashtag(name=search_term)

                    new_posts = 0
                    async for video in hashtag.videos(count=30):
                        try:
                            source_id = f"tiktok_{video.id}"

                            # Build description
                            description = video.desc if hasattr(video, 'desc') else ''

                            # Get author
                            author = None
                            if hasattr(video, 'author') and video.author:
                                author = video.author.username if hasattr(video.author, 'username') else str(video.author)

                            # Build URL
                            url = f"https://www.tiktok.com/@{author}/video/{video.id}" if author else f"https://www.tiktok.com/video/{video.id}"

                            # Get timestamp
                            created_at = datetime.now().isoformat()
                            if hasattr(video, 'create_time'):
                                created_at = datetime.fromtimestamp(video.create_time).isoformat()

                            inserted = insert_post(
                                source='tiktok',
                                source_id=source_id,
                                url=url,
                                title=None,  # TikTok doesn't have titles
                                body=description,
                                author=author,
                                subreddit=search_term,  # Store hashtag as "subreddit"
                                created_at=created_at
                            )
                            if inserted:
                                new_posts += 1

                        except Exception as e:
                            print(f"    Error processing video: {e}")
                            continue

                    print(f"    Found {new_posts} new videos")
                    total_posts += new_posts

                    # Rate limiting
                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"  Error searching '{keyword}': {e}")
                    continue

    except ImportError:
        print("TikTok-Api not installed. Run: pip install TikTok-Api")
        print("Also run: playwright install chromium")
        return 0
    except Exception as e:
        print(f"TikTok scraper error: {e}")
        return 0

    print(f"TikTok scraper completed. Found {total_posts} new posts.")
    return total_posts


def scrape_tiktok():
    """
    Synchronous wrapper for TikTok scraping.

    Returns:
        Number of new posts found
    """
    try:
        return asyncio.run(scrape_tiktok_async())
    except Exception as e:
        print(f"TikTok scraper failed: {e}")
        return 0


if __name__ == '__main__':
    scrape_tiktok()
