from database import get_connection, init_db, save_words
from fetcher import get_random_article
from llm import extract_words_from_text
from ui import console, display_article, display_words


def mode_fetch(conn):
    with console.status("[bold green]Searching for new article...[/bold green]"):
        source, title, text = get_random_article()
    if source:
        with console.status("[bold green]Analazying text...[/bold green]"):
            words = extract_words_from_text(text)
        display_article(source, title, text, words)
        print()
        display_words(words)

        save_words(conn, words, source)
        console.print(
            "\n[dim]Press Enter to get another one or Ctrl+C to exit...[/dim]"
        )
        input()


def main():

    conn = get_connection()
    init_db(conn)

    try:
        while True:
            mode_fetch(conn)
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    conn.close()


if __name__ == "__main__":
    main()
