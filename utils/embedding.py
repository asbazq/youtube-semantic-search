"""Shared PyTorch/Hugging Face text embedding utilities."""

from typing import List, Sequence

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_LENGTH = 128


def mean_pooling(token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Mean-pool token embeddings while excluding padding tokens."""
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).to(token_embeddings.dtype)
    summed = torch.sum(token_embeddings * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


class TextEmbedder:
    """Encode text with AutoTokenizer/AutoModel and normalized mean pooling."""

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_length: int = DEFAULT_MAX_LENGTH,
        device: str | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.max_length = max_length
        self.device = torch.device(device or self._default_device())
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    @staticmethod
    def _default_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        """Return one L2-normalized embedding per input text."""
        if not texts:
            return []

        embeddings: List[List[float]] = []
        with torch.inference_mode():
            for start in range(0, len(texts), self.batch_size):
                batch = list(texts[start : start + self.batch_size])
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                encoded = {key: value.to(self.device) for key, value in encoded.items()}
                output = self.model(**encoded)
                pooled = mean_pooling(output.last_hidden_state, encoded["attention_mask"])
                normalized = F.normalize(pooled, p=2, dim=1)
                embeddings.extend(normalized.cpu().tolist())
        return embeddings
