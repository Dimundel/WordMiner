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
            source_url TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ease_factor REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 1,
            next_review TIMESTAMP
        )
    """)

    conn.commit()
    return conn


def save_word(conn, word, definition, source_url):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO words (word, definition, source_url)
        VALUES (?, ?, ?)
    """,
        (word, definition, source_url),
    )
    conn.commit()


def save_words(conn, words, source_url):
    for row in words:
        word = row["word"]
        definition = row["definition"]
        save_word(conn, word, definition, source_url)
