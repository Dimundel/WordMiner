import math
import sqlite3


def get_connection():
    conn = sqlite3.connect("words.db")
    conn.row_factory = sqlite3.Row
    return conn


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
                row["word"].strip(),
                row["definition"],
                row["context"],
                row["simple_synonym"].strip(),
                source_url,
            ),
        )
    conn.commit()


def get_words_for_practice(conn, limit=5, strict=True):
    cursor = conn.cursor()

    if strict:
        query = """
            SELECT word, definition, context, simple_synonym FROM words 
            WHERE (next_review <= datetime('now') OR next_review IS NULL)
              AND context IS NOT NULL
            ORDER BY next_review ASC, RANDOM() LIMIT ?
        """
    else:
        query = """
            SELECT word, definition, context, simple_synonym FROM words 
            WHERE interval < 14 AND context IS NOT NULL
            ORDER BY RANDOM() LIMIT ?
        """
    cursor.execute(
        query,
        (limit,),
    )

    return [dict(row) for row in cursor.fetchall()]


def get_learning_status(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM words WHERE interval < 14")
    learning_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM words WHERE interval >= 14")
    mastered_count = cursor.fetchone()[0]

    return learning_count, mastered_count


def update_word_progress(conn, word, is_correct):
    cursor = conn.cursor()

    cursor.execute("SELECT interval, ease_factor FROM words WHERE word = ?", (word,))
    row = cursor.fetchone()

    if not row:
        return

    current_interval, ease_factor = row["interval"], row["ease_factor"]

    if is_correct:
        new_ease = max(1.3, ease_factor + 0.1)
        new_interval = max(1, math.ceil(current_interval * new_ease))

    else:
        new_ease = max(1.3, ease_factor - 0.2)
        new_interval = 1

    time_diff = f"+{new_interval} days"

    cursor.execute(
        """
            UPDATE words
            SET interval = ?, ease_factor = ?, next_review = datetime('now', ?)
            WHERE word = ?
                   """,
        (new_interval, new_ease, time_diff, word),
    )
    conn.commit()
