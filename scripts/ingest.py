"""Rebuild the local vector index from data/knowledge/corpus."""

from src.knowledge.ingest import build_index


if __name__ == "__main__":
    payload = build_index()
    print(f"Indexed {len(payload['records'])} chunks → data/index/lsa.joblib")
