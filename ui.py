import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def display_article(source, title, full_text, highlight_words):
    header = Text(f"\nSource: {source}", style="italic cyan")
    title_text = Text(title, style="bold magenta")
    body = Text(f"\n{full_text}", style="white")

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
    )

    console.print(panel)


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
    )
    console.print(panel)
