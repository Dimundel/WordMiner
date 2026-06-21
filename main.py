import feedparser
import random
import json
import re
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from google import genai

load_dotenv()
client = genai.Client()

SOURCES = {
    "Aeon": "https://aeon.co/feed.rss",
    "The Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
    "Wired": "https://www.wired.com/feed/rss",
}

PROMPT = """
Find in the text below at least 2 words from advanced vocabulary (C1-C2 level).
Return ONLY a JSON array, no markdown, no explanation.
Example: [{"word": "ephemeral", "definition": "lasting for a very short time"}]
"""

console = Console()


def get_random_article():
    source_name = random.choice(list(SOURCES.keys()))
    url = SOURCES[source_name]

    with console.status(f"[bold green]Fetching from {source_name}..."):
        feed = feedparser.parse(url)

    if not feed.entries:
        return None, None, None

    article = random.choice(feed.entries[:10])
    return source_name, article.title, article.summary


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


def main():
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

        console.print(
            "\n[dim]Press Enter to get another one or Ctrl+C to exit...[/dim]"
        )
        input()
    else:
        console.print("\n[red]Failed to fetch articles. Check your internet.[/red]")


if __name__ == "__main__":
    try:
        while True:
            main()
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
