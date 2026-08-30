from google.genai import types

from config import CLIENT, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


class EmbeddingService:
    def __init__(self, provider="google"):
        self.provider = provider

    def get_embedding(self, text: str) -> list[float]:
        if self.provider == "google":
            return self._get_google_embedding(text)
        elif self.provider == "local":
            return self._get_local_embedding(text)

        raise ValueError(f"Unknown embedding provider: {self.provider}")

    def _get_google_embedding(self, text: str) -> list[float]:
        # A list of contents is embedded into one vector, not one per item,
        # so words have to be sent individually.
        response = CLIENT.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        return list(response.embeddings[0].values)

    def _get_local_embedding(self, text: str) -> list[float]:
        raise NotImplementedError("TODO: include a local model for embeddings")


def embedding_text(word):
    """A bare word gives a noisy vector, so pair it with its definition."""
    definition = word.get("definition") or ""
    return f"{word['word']}: {definition}".strip(": ")
