from config import CLIENT


class EmbeddingService:
    def __init__(self, provider="google"):
        self.provider = provider

    def get_embedding(self, text: str) -> list[float]:
        if self.provider == "google":
            return self._get_google_embedding(text)
        elif self.provider == "local":
            return self._get_local_embedding(text)

    def _get_google_embedding(self, text: str):
        embedding = CLIENT.models.embed_content(
            model="gemini-embedding-2", contents=text
        )
        return embedding

    def _get_local_embedding(self, text: str):
        raise NotImplementedError("TODO: include a local model for embeddings")
