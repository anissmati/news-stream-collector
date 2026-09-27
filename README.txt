# News Stream Collector & Dataset Engine

A lightweight, automated news collection pipeline designed to aggregate, deduplicate, and store multi-category articles from RSS feeds, Google News, and NewsAPI. Built to create structured datasets for downstream NLP classification, relevance scoring, and news bot recommendation systems.

## Features

- **Multi-Source Fetching:** Aggregates articles concurrently from NewsAPI, GNews, and curated direct RSS feeds.
- **Strict Deduplication:** Uses deterministic MD5 content and URL hashing to drop duplicate stories at the database level.
- **6 Category Coverage:** Technology, Sports, Politics, Science, Business, and World.
- **Fail-Safe & Resilient:** Backed by an ACID-compliant SQLite storage engine that handles intermittent runs, laptop sleeps, and crashes without data corruption.
- **Export-Ready:** Structured schema pre-configured for direct loading into Pandas DataFrames and batch labeling via LLMs.

---

## Supported Categories

| Category | Primary Sources |
| :--- | :--- |
| **Technology** | Ars Technica, The Verge, TechCrunch, NewsAPI, GNews |
| **Sports** | ESPN, BBC Sport, NewsAPI, GNews |
| **Politics** | Politico, BBC Politics, NewsAPI Everything |
| **Science** | ScienceDaily, Phys.org, BBC Science, NewsAPI, GNews |
| **Business** | BBC Business, Fortune, CNBC, NewsAPI, GNews |
| **World** | BBC World, Al Jazeera, NYT World, NewsAPI Everything |

---

## Getting Started

### 1. Prerequisites

Ensure you have Python 3.9+ installed:

```bash
git clone [https://github.com/](https://github.com/)<your-username>/news-stream-collector.git
cd news-stream-collector
pip install -r requirements.txt