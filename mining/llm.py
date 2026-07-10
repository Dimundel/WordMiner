import json
from pydantic import BaseModel
from config import CLIENT, EXTRACT_PROMPT, MODEL


class VocabularyWord(BaseModel):
    word: str
    definition: str
    context: str
    simple_synonym: str


def extract_words_from_text(text: str) -> list[dict]:
    prompt = EXTRACT_PROMPT + "\n" + text
    response = CLIENT.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[VocabularyWord],
        },
    )
    return json.loads(response.text)
