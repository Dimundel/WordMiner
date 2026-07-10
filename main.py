import re
import argparse
from database import (
    get_connection,
    init_db,
    save_words,
    get_words_for_practice,
    get_learning_status,
    update_word_progress,
)
from fetcher import get_random_article
from llm import extract_words_from_text
from ui import (
    console,
    display_article,
    display_words,
    display_word_bank,
    display_practice_sentences,
)
from config import ACTIVE_LIMIT


def mode_fetch(conn):
    learning_words, mastered_words = get_learning_status(conn)

    if learning_words >= ACTIVE_LIMIT:
        console.print(
            f"Limit of {ACTIVE_LIMIT} words has reached. Practice them first to fetch new articles."
        )
        return False

    with console.status("[bold green]Searching for new article...[/bold green]"):
        source, title, text = get_random_article()
    if source:
        with console.status("[bold green]Analyzing text...[/bold green]"):
            words = extract_words_from_text(text)
        display_article(source, title, text, words)
        print()
        display_words(words)

        save_words(conn, words, source)
        console.print(
            "\n[dim]Press Enter to get another one or Ctrl+C to exit...[/dim]"
        )
        input()

    return True


def mode_practice(conn):
    words_data = get_words_for_practice(conn, limit=10, strict=True)

    if not words_data:
        console.print(
            "[yellow]Everything is learned for now! Showing some active words for extra practice...[/yellow]\n"
        )
        words_data = get_words_for_practice(conn, limit=10, strict=False)

    if not words_data:
        console.print(
            "[bold red]No words to practice. Go fetch some articles first![/bold red]"
        )
        return

    if len(words_data) < 5:
        console.print(
            "[bold red]Not enough words in database (need at least 5). Fetch some articles![/bold red]"
        )
        return

    word_bank = []
    questions = []

    for row in words_data:
        target_word = row["word"]
        context = row["context"]
        synonym = row["simple_synonym"]

        pattern = rf"(?i)\b{re.escape(target_word)}\b"
        hidden_context, count = re.subn(pattern, f"[___] ({synonym})", context)

        if count == 0:
            continue

        word_bank.append(target_word)
        questions.append(
            {
                "id": len(questions) + 1,
                "target_word": target_word,
                "hidden_context": hidden_context,
                "definition": row["definition"],
            }
        )

        if len(questions) == 5:
            break

    display_word_bank(word_bank)
    display_practice_sentences(questions)

    score = 0
    console.print("[dim]Type correct word for this sentence:[/dim]")

    for q in questions:
        answer = input(f"Sentence {q['id']}: ").strip()

        if answer.lower() == q["target_word"].lower():
            console.print("[bold green]Correct![/bold green]\n")
            score += 1
            update_word_progress(conn, q["target_word"], True)
        else:
            console.print("[bold red]Incorrect.[/bold red]")
            console.print(
                f"Correct answer: [bold green]{q['target_word']}[/bold green]"
            )
            console.print(f"[dim]Definition: {q['definition']}[/dim]\n")
            update_word_progress(conn, q["target_word"], False)

    console.print(f"[bold cyan]Your result: {score}/{len(questions)}[/bold cyan]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--practice", action="store_true")
    args = parser.parse_args()

    conn = get_connection()
    init_db(conn)

    if args.practice:
        mode_practice(conn)
    else:
        try:
            while mode_fetch(conn):
                pass
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
    conn.close()


if __name__ == "__main__":
    main()
