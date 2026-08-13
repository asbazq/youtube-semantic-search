from types import SimpleNamespace
from unittest.mock import patch

import torch

from utils.embedding import TextEmbedder, mean_pooling


def test_mean_pooling_ignores_padding_tokens():
    tokens = torch.tensor([[[1.0, 2.0], [3.0, 4.0], [100.0, 100.0]]])
    mask = torch.tensor([[1, 1, 0]])

    pooled = mean_pooling(tokens, mask)

    assert torch.allclose(pooled, torch.tensor([[2.0, 3.0]]))


class FakeTokenizer:
    def __call__(self, texts, **kwargs):
        del kwargs
        size = len(texts)
        return {
            "input_ids": torch.ones((size, 2), dtype=torch.long),
            "attention_mask": torch.tensor([[1, 0]] * size),
        }


class FakeModel:
    def to(self, device):
        self.device = device
        return self

    def eval(self):
        return self

    def __call__(self, **encoded):
        size = encoded["input_ids"].shape[0]
        hidden = torch.tensor([[[3.0, 4.0], [99.0, 99.0]]] * size)
        return SimpleNamespace(last_hidden_state=hidden)


@patch("utils.embedding.AutoTokenizer.from_pretrained", return_value=FakeTokenizer())
@patch("utils.embedding.AutoModel.from_pretrained", return_value=FakeModel())
def test_encode_batches_and_l2_normalizes(_model, _tokenizer):
    embedder = TextEmbedder(batch_size=2, device="cpu")

    embeddings = embedder.encode(["하나", "둘", "셋"])

    assert len(embeddings) == 3
    assert torch.allclose(torch.tensor(embeddings[0]), torch.tensor([0.6, 0.8]))
    assert all(abs(torch.linalg.vector_norm(torch.tensor(item)).item() - 1.0) < 1e-6 for item in embeddings)
