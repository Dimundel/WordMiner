import feedparser
import random
import json
import re
import requests
import sqlite3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from google import genai

load_dotenv()
client = genai.Client()

SOURCES = {
    "Aeon": "https://aeon.co/feed.rss",
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "The Conversation": "https://theconversation.com/us/articles.atom",
    "Nautilus": "https://nautil.us/feed/",
    "The Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
}

PROMPT = """
Find in the text below words from advanced vocabulary (C1-C2 level).
Return ONLY a JSON array, no markdown, no explanation.
Example: [{"word": "ephemeral", "definition": "lasting for a very short time"}]
"""

console = Console()


def init_db():
    conn = sqlite3.connect("words.db")
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


def get_full_text(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    article = soup.find("article")
    if article:
        paragraphs = article.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    return " ".join(p.get_text() for p in paragraphs)


def get_random_article():
    source_name = random.choice(list(SOURCES.keys()))
    url = SOURCES[source_name]

    with console.status(f"[bold green]Fetching from {source_name}..."):
        feed = feedparser.parse(url)

    if not feed.entries:
        return None, None, None

    article = random.choice(feed.entries[:10])

    with console.status("[bould green]Fetching full article..."):
        full_text = get_full_text(article.link)
    return source_name, article.title, full_text


def display_article(source, title, summary, highlight_words):
    clean_text = re.sub("<[^<]+?>", "", summary)
    header = Text(f"\nSource: {source}", style="italic cyan")
    title_text = Text(title, style="bold magenta")
    body = Text(f"\n{clean_text}", style="white")

    if highlight_words:
        for row in highlight_words:
            word = row["word"]
            word = word.strip().strip(".,!?:;")
            if not word:
                continue
            pattern = rf"\b{re.escape(word)}\b"
            body.highlight_regex(pattern, style="bold yellow underline")

    panel = Panel(
        Text.assemble(title_text, body),
        title="[bold yellow]English Passage[/bold yellow]",
        subtitle=header,
        padding=(1, 2),
        width=80,
    )

    console.print(panel)


def get_words_from_llm_response(response):
    data = json.loads(response)
    return data


def display_words(words):
    if not words:
        return

    content = Text()

    for i, row in enumerate(words, 1):
        content.append(f"{i}. ", style="bold cyan")
        content.append(f"{row['word']}", style="bold yellow")
        content.append(f": {row['definition']}\n")

    panel = Panel(
        content,
        title="[bold green]Vocabulary List[/bold green]",
        border_style="green",
        padding=(1, 2),
        width=80,
    )

    console.print(panel)


def main(conn):
    console.clear()
    console.print("[bold blue]Test[/bold blue]\n")
    source, title, summary = get_random_article()

    if source:
        prompt = PROMPT + "\n" + summary

        with console.status("[bold green]Analzying text..."):
            response = client.models.generate_content(
                model="gemini-flash-lite-latest", contents=prompt
            )

        highlight_words = get_words_from_llm_response(response.text)

        display_article(source, title, summary, highlight_words)
        print()
        display_words(highlight_words)

        save_words(conn, highlight_words, source)

        console.print(
            "\n[dim]Press Enter to get another one or Ctrl+C to exit...[/dim]"
        )
        input()
    else:
        console.print("\n[red]Failed to fetch articles. Check your internet.[/red]")


if __name__ == "__main__":
    conn = init_db()
    try:
        while True:
            main(conn)
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
