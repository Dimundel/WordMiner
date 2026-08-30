import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise EnvironmentError("GOOGLE_API_KEY is not set. Add it to your .env file.")

CLIENT = genai.Client()
MODEL = "gemini-flash-lite-latest"
EMBEDDING_MODEL = "gemini-embedding-2"
# Full size is 3072; 768 keeps the JSON in SQLite small and ranks the same.
EMBEDDING_DIMENSIONS = 768
ACTIVE_LIMIT = 20

# Podcast and video pages carry only a blurb (500-1300 chars) where real
# articles run 2600 and up, and yield almost no vocabulary. Skip them.
MIN_ARTICLE_LENGTH = 2000
ARTICLE_ATTEMPTS = 5

SOURCES = {
    "Aeon": "https://aeon.co/feed.rss",
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "The Conversation": "https://theconversation.com/us/articles.atom",
    "Nautilus": "https://nautil.us/feed/",
    "The Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
}

EXTRACT_PROMPT = """
Analyze the text below. Find advanced English vocabulary words (C1-C2 level).
For each word, extract the following information strictly according to the JSON schema:
1. "word": the advanced word found in the text (base form or as it appears).
2. "definition": a clear dictionary definition of the word.
3. "context": the EXACT full sentence from the text where this word appears. Do not change a single letter.
4. "simple_synonym": a very simple, common synonym (A2-B1 level) that fits the context. It should be easily understood by a beginner.

TEXT:
"""
