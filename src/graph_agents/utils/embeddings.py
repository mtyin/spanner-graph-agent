from typing import Any, List, Optional

from google import genai
from google.genai.types import EmbedContentConfig


class Embeddings(object):

    def __init__(self, model: str, *args: Any, **kwargs: Any):
        self.model = model
        client = genai.Client(*args, **kwargs)
        self.embeddings = client.models

    def get_embeddings(
        self, texts: List[str], *args: Any, **kwargs: Any
    ) -> Optional[List[Optional[List[float]]]]:
        embeddings = self.embeddings.embed_content(
            model=self.model, contents=texts, *args, **kwargs
        ).embeddings
        if embeddings is None:
            return None
        return [embedding.values for embedding in embeddings]
