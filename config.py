from dotenv import load_dotenv
from google import genai

load_dotenv()

CLIENT = genai.Client()

SOURCES = {
    "Aeon": "https://aeon.co/feed.rss",
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "The Conversation": "https://theconversation.com/us/articles.atom",
    "Nautilus": "https://nautil.us/feed/",
    "The Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
}

EXTRACT_PROMPT = """
Find in the text below words from advanced vocabulary (C1-C2 level).
Return ONLY a JSON array, no markdown, no explanation.
Example: [{"word": "ephemeral", "definition": "lasting for a very short time"}]
"""
