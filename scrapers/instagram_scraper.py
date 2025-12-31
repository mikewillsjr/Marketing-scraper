"""
Instagram scraper using instaloader library.
Instagram rate limits aggressively, so be careful with usage.
"""
from datetime import datetime

from scrapers.base_scraper import (
    get_all_keywords,
    insert_post
)


def scrape_instagram():
    """
    Main Instagram scraping function.
    Searches by hashtag.

    Returns:
        Number of new posts found
    """
    print("Instagram scraper starting...")

    keywords = get_all_keywords()
    if not keywords:
        print("No keywords configured, skipping")
        return 0

    total_posts = 0

    try:
        import instaloader

        # Initialize Instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False
        )

        # Note: For better results, login is recommended
        # L.login("username", "password")
        # Or load session: L.load_session_from_file("username")

        print(f"Searching for {len(keywords)} hashtags...")

        for keyword in keywords:
            try:
                # Clean keyword for hashtag search
                hashtag_name = keyword.lstrip('#').replace(' ', '').lower()

                # Skip if it looks like a phrase rather than hashtag
                if len(hashtag_name) > 50 or ' ' in keyword.strip():
                    print(f"  Skipping phrase (not a hashtag): {keyword}")
                    continue

                print(f"  Searching hashtag: #{hashtag_name}")

                # Get hashtag posts
                hashtag = instaloader.Hashtag.from_name(L.context, hashtag_name)

                new_posts = 0
                post_count = 0

                for post in hashtag.get_posts():
                    try:
                        # Limit posts per hashtag
                        post_count += 1
                        if post_count > 20:
                            break

                        source_id = f"instagram_{post.shortcode}"

                        # Get caption
                        caption = post.caption if post.caption else ""

                        # Get author
                        author = post.owner_username

                        # Build URL
                        url = f"https://www.instagram.com/p/{post.shortcode}/"

                        # Get timestamp
                        created_at = post.date_utc.isoformat() if post.date_utc else datetime.now().isoformat()

                        inserted = insert_post(
                            source='instagram',
                            source_id=source_id,
                            url=url,
                            title=None,  # Instagram doesn't have titles
                            body=caption[:5000],  # Truncate long captions
                            author=author,
                            subreddit=hashtag_name,  # Store hashtag as "subreddit"
                            created_at=created_at
                        )
                        if inserted:
                            new_posts += 1

                    except Exception as e:
                        print(f"    Error processing post: {e}")
                        continue

                print(f"    Found {new_posts} new posts")
                total_posts += new_posts

            except instaloader.exceptions.QueryReturnedNotFoundException:
                print(f"  Hashtag not found: {hashtag_name}")
                continue
            except instaloader.exceptions.TooManyRequestsException:
                print("  Rate limited by Instagram. Stopping.")
                break
            except instaloader.exceptions.ConnectionException as e:
                print(f"  Connection error: {e}")
                continue
            except Exception as e:
                print(f"  Error searching '{keyword}': {e}")
                continue

    except ImportError:
        print("instaloader not installed. Run: pip install instaloader")
        return 0
    except Exception as e:
        print(f"Instagram scraper error: {e}")
        return 0

    print(f"Instagram scraper completed. Found {total_posts} new posts.")
    return total_posts


if __name__ == '__main__':
    scrape_instagram()
