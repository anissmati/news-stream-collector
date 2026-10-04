import os
import sqlite3
import pandas as pd

DB_NAME = "news_dataset.db"
CSV_FILE = "news_dataset.csv"


def export_new_rows():
    if not os.path.exists(DB_NAME):
        print(f"Database file '{DB_NAME}' not found. Run collect.py first.")
        return

    # Check for existing records in CSV
    existing_hashes = set()
    file_exists = os.path.isfile(CSV_FILE)

    if file_exists and os.path.getsize(CSV_FILE) > 0:
        try:
            # Read only the article_hash column to keep memory usage minimal
            existing_df = pd.read_csv(CSV_FILE, usecols=["article_hash"])
            existing_hashes = set(existing_df["article_hash"].dropna().astype(str))
            print(f"Found existing CSV with {len(existing_hashes)} records.")
        except Exception as e:
            print(f"Warning: Could not read existing hashes ({e}). Proceeding carefully.")

    # Pull data from SQLite
    conn = sqlite3.connect(DB_NAME)
    query = """
        SELECT 
            id,
            article_hash,
            title,
            summary,
            source_name,
            category,
            url,
            fetch_channel,
            published_at,
            collected_at,
            label_score
        FROM raw_articles
    """
    db_df = pd.read_sql_query(query, conn)
    conn.close()

    if db_df.empty:
        print("Database is currently empty. Nothing to export.")
        return

    # Filter out rows that are already inside the CSV
    if existing_hashes:
        new_df = db_df[~db_df["article_hash"].isin(existing_hashes)]
    else:
        new_df = db_df

    if new_df.empty:
        print("CSV is already up to date. No new rows to export.")
        return

    # Append new rows (write header only if creating a fresh file)
    new_df.to_csv(
        CSV_FILE,
        mode="a" if file_exists else "w",
        header=not file_exists,
        index=False,
        encoding="utf-8"
    )

    total_count = len(existing_hashes) + len(new_df)
    print(f"Exported {len(new_df)} new rows to '{CSV_FILE}'.")
    print(f"Total rows now in CSV: {total_count}")


if __name__ == "__main__":
    export_new_rows()