from __future__ import annotations

import re

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import INDEX_DIR
from src.knowledge.store import corpus_documents

INDEX_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = INDEX_DIR / "lsa.joblib"


def _chunk(text: str, size: int = 700, overlap: int = 120) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        piece = " ".join(words[i : i + size])
        chunks.append(piece)
        i += max(size - overlap, 1)
    return chunks or [text]


class ScientificEmbedder:
    """Domain-tuned TF-IDF + LSA embeddings. No cloud model download required."""

    def __init__(self, vectorizer: TfidfVectorizer, svd: TruncatedSVD):
        self.vectorizer = vectorizer
        self.svd = svd

    def encode(self, texts: list[str]) -> np.ndarray:
        matrix = self.svd.transform(self.vectorizer.transform(texts))
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


def build_index() -> dict:
    docs = corpus_documents()
    records = []
    for doc in docs:
        chunks = _chunk(doc["text"])
        for idx, chunk in enumerate(chunks):
            records.append(
                {
                    "chunk_id": f"{doc['id']}::{idx}",
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "year": doc["year"],
                    "topics": doc["topics"],
                    "text": chunk,
                }
            )
    corpus = [re.sub(r"\s+", " ", rec["text"]).strip() for rec in records]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=8000,
        stop_words="english",
    )
    tfidf = vectorizer.fit_transform(corpus)
    components = max(2, min(64, min(tfidf.shape) - 1))
    svd = TruncatedSVD(n_components=components, random_state=7)
    dense = svd.fit_transform(tfidf)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    dense = dense / norms
    payload = {
        "records": records,
        "vectorizer": vectorizer,
        "svd": svd,
        "matrix": dense.astype(np.float32),
    }
    joblib.dump(payload, INDEX_PATH)
    return payload


def load_index() -> dict:
    if INDEX_PATH.exists():
        return joblib.load(INDEX_PATH)
    return build_index()
