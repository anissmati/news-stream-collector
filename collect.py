from datetime import datetime, timezone
import hashlib
import os
import re
import sqlite3
import feedparser
from gnews import GNews
import requests

DB_NAME = "news_dataset.db"

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "NEWSAPI_KEY_HERE")

CATEGORIES = [
    "Technology",
    "Sports",
    "Politics",
    "Science",
    "Business",
    "World",
]

RSS_FEEDS = {
    "Technology": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
    ],
    "Sports": [
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "Politics": [
        "https://rss.politico.com/politics-news.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
    ],
    "Science": [
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://phys.org/rss-feed/",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://fortune.com/feed/",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    ],
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
}

GNEWS_TOPIC_MAP = {
    "Technology": "TECHNOLOGY",
    "Sports": "SPORTS",
    "Politics": "POLITICS",
    "Science": "SCIENCE",
    "Business": "BUSINESS",
    "World": "WORLD",
}


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_hash TEXT UNIQUE,
                title TEXT NOT NULL,
                summary TEXT,
                source_name TEXT,
                category TEXT NOT NULL,
                url TEXT,
                fetch_channel TEXT,
                published_at TEXT,
                collected_at TEXT,
                label_score REAL DEFAULT NULL
            )
        """
        )
        conn.commit()


def generate_hash(title: str, url: str = "") -> str:
    seed = url.strip().lower() if url else re.sub(r"[^a-zA-Z0-9]", "", title.lower())
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    return " ".join(clean.split())


# ---------------- FETCH LOGIC ----------------


def fetch_newsapi(category: str):
    """Fetches articles from NewsAPI."""
    if not NEWSAPI_KEY or NEWSAPI_KEY.startswith("YOUR_"):
        return []

    articles = []
    if category.lower() in [
        "technology",
        "sports",
        "science",
        "business",
    ]:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": NEWSAPI_KEY,
            "category": category.lower(),
            "language": "en",
            "pageSize": 25,
        }
    else:
        url = "https://newsapi.org/v2/everything"
        query = "politics" if category == "Politics" else "world news"
        params = {
            "apiKey": NEWSAPI_KEY,
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 25,
        }

    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") == "ok":
            for item in data.get("articles", []):
                title = item.get("title") or ""
                # Filter out generic removed notices
                if "[Removed]" in title or not title.strip():
                    continue

                articles.append(
                    {
                        "title": title.strip(),
                        "summary": item.get("description") or "",
                        "source_name": (item.get("source") or {}).get(
                            "name", "NewsAPI"
                        ),
                        "category": category,
                        "url": item.get("url", ""),
                        "fetch_channel": "newsapi",
                        "published_at": item.get("publishedAt", ""),
                    }
                )
    except Exception as e:
        print(f"  [!] NewsAPI failed for '{category}': {e}")

    return articles


def fetch_gnews(category: str):
    """Fetches articles using the gnews python library."""
    articles = []
    topic = GNEWS_TOPIC_MAP.get(category, category.upper())

    try:
        google_news = GNews(language="en", period="1d", max_results=20)
        raw_items = google_news.get_news_by_topic(topic)

        if not raw_items:
            raw_items = google_news.get_news(category.lower())

        for item in raw_items:
            title = item.get("title", "").strip()
            if not title:
                continue

            articles.append(
                {
                    "title": title,
                    "summary": item.get("description") or "",
                    "source_name": (item.get("publisher") or {}).get(
                        "title", "Google News"
                    ),
                    "category": category,
                    "url": item.get("url", ""),
                    "fetch_channel": "gnews",
                    "published_at": item.get("published date", ""),
                }
            )
    except Exception as e:
        print(f"  [!] GNews failed for '{category}': {e}")

    return articles


def fetch_rss(category: str):
    """Fetches direct headlines from curated RSS feeds."""
    articles = []
    feed_urls = RSS_FEEDS.get(category, [])

    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            feed_source = feed.feed.get("title", "RSS Feed")

            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                raw_summary = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or ""
                )
                summary = clean_html(raw_summary)

                pub_date = entry.get("published", "") or entry.get(
                    "updated", ""
                )

                articles.append(
                    {
                        "title": title,
                        "summary": summary,
                        "source_name": feed_source,
                        "category": category,
                        "url": entry.get("link", ""),
                        "fetch_channel": "rss",
                        "published_at": pub_date,
                    }
                )
        except Exception as e:
            print(f"  [!] RSS failed for '{feed_url}': {e}")

    return articles


# ---------------- PIPELINE RUNNER ----------------


def run_collection():
    init_db()
    total_fetched = 0
    new_inserts = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    print(
        f"=== Starting News Scraping Run ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ==="
    )

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        for category in CATEGORIES:
            print(f"\nProcessing [{category}]...")

            cat_articles = []
            cat_articles.extend(fetch_newsapi(category))
            cat_articles.extend(fetch_gnews(category))
            cat_articles.extend(fetch_rss(category))

            total_fetched += len(cat_articles)
            cat_new = 0

            for art in cat_articles:
                title = art["title"]
                if len(title) < 10:
                    continue

                art_hash = generate_hash(title, art.get("url", ""))

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO raw_articles 
                    (article_hash, title, summary, source_name, category, url, fetch_channel, published_at, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        art_hash,
                        title,
                        art["summary"],
                        art["source_name"],
                        art["category"],
                        art["url"],
                        art["fetch_channel"],
                        art["published_at"] or now_iso,
                        now_iso,
                    ),
                )
                if cursor.rowcount > 0:
                    cat_new += 1
                    new_inserts += 1

            conn.commit()
            print(
                f"  -> Fetched {len(cat_articles)} items | Added {cat_new} new unique rows"
            )

        cursor.execute("SELECT COUNT(*) FROM raw_articles")
        total_in_db = cursor.fetchone()[0]

    print("\n" + "=" * 45)
    print(f"Fetch completed successfully.")
    print(f"Total processed:   {total_fetched}")
    print(f"New rows added:    {new_inserts}")
    print(f"Total DB rows:     {total_in_db}")
    print("=" * 45)


if __name__ == "__main__":
    run_collection()