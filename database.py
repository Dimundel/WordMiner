import sqlite3


def get_connection():
    return sqlite3.connect("words.db")


def init_db(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            definition TEXT,
            context TEXT,
            simple_synonym TEXT,
            source_url TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ease_factor REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 1,
            next_review TIMESTAMP
        )
    """)

    conn.commit()
    return conn


def save_words(conn, words, source_url):
    cursor = conn.cursor()
    for row in words:
        cursor.execute(
            """
            INSERT OR IGNORE INTO words (word, definition, context, simple_synonym, source_url)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                row["word"],
                row["definition"],
                row["context"],
                row["simple_synonym"],
                source_url,
            ),
        )
    conn.commit()
