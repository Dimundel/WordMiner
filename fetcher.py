import feedparser
import requests
import random
from bs4 import BeautifulSoup
from config import SOURCES


def get_full_text(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException as e:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

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
        return None, None, None

    article = random.choice(feed.entries[:10])

    full_text = get_full_text(article.link)
    return source_name, article.title, full_text
