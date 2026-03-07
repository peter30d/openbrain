from functools import cached_property
from sentence_transformers import SentenceTransformer


class EmbeddingProvider:
    def __init__(self, model_name: str):
        self.model_name = model_name

    @cached_property
    def model(self) -> SentenceTransformer:
        return SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in vec]

