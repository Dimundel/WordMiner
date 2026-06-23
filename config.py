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
Analyze the text below. Find advanced English vocabulary words (C1-C2 level).
For each word, extract the following information strictly according to the JSON schema:
1. "word": the advanced word found in the text (base form or as it appears).
2. "definition": a clear dictionary definition of the word.
3. "context": the EXACT full sentence from the text where this word appears. Do not change a single letter.
4. "simple_synonym": a very simple, common synonym (A2-B1 level) that fits the context. It should be easily understood by a beginner.

TEXT:
"""
