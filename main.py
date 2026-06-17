import feedparser
import random
from rich.console import Console

SOURCES = {
    "Aeon": "https://aeon.co/feed.rss",
    "The Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
    "Wired": "https://www.wired.com/feed/rss",
}

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


def display_article(source, title, summary):
    import re

    clean_text = re.sub("<[^<]+?>", "", summary)
    header = Text(f"\nSource: {source}", style="italic cyan")
    title_text = Text(title, style="bold magenta")
    body = Text(f"\n{clean_text}", style="white")

    panel = Panel(
        Text.assemble(title_text, body),
        title="[bold yellow]English Passage[/bold yellow]",
        subtitle=header,
        padding=(1, 2),
        width=80,
    )

    console.print(panel)


def main():
    console.clear()
    console.print("[bold blue]Test[/bold blue]\n")
    source, title, summary = get_random_article()

    display_article(source, title, summary)


if __name__ == "__main__":
    main()
