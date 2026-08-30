import feedparser
import requests
import random
from bs4 import BeautifulSoup
from config import ARTICLE_ATTEMPTS, MIN_ARTICLE_LENGTH, SOURCES


def get_full_text(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    article = soup.find("article")
    if article:
        paragraphs = article.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    return "\n\n".join(p.get_text() for p in paragraphs)


def get_random_article():
    source_name = random.choice(list(SOURCES.keys()))
    url = SOURCES[source_name]

    feed = feedparser.parse(url)

    if not feed.entries:
        return None, None, None, None

    entries = feed.entries[:10]
    for article in random.sample(entries, min(ARTICLE_ATTEMPTS, len(entries))):
        full_text = get_full_text(article.link)

        if full_text and len(full_text) >= MIN_ARTICLE_LENGTH:
            return source_name, article.title, article.link, full_text

    return None, None, None, None
