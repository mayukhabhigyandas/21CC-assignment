import hashlib
import math
import os
import threading

_model = None
_lock = threading.Lock()

def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    if os.getenv("EMBEDDING_PROVIDER", "fastembed").lower() != "off":
                        from fastembed import TextEmbedding
                        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
                except Exception:
                    _model = False
    return _model

def _fallback(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector

def embed_text(text: str) -> list[float]:
    model = _get_model()
    if model:
        vector = list(model.embed([text]))[0]
        return [float(value) for value in vector]
    return _fallback(text)

def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
