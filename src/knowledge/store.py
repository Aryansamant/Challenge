from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.config import CORPUS_DIR, KNOWLEDGE_DIR


def _load_json(name: str):
    path = KNOWLEDGE_DIR / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def interventions() -> list[dict]:
    return _load_json("interventions.json")


@lru_cache(maxsize=1)
def thresholds() -> dict:
    return _load_json("thresholds.json")


@lru_cache(maxsize=1)
def causal_graph() -> dict:
    return _load_json("causal_links.json")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        raw = value.strip()
        if raw.startswith("[") and raw.endswith("]"):
            items = [item.strip() for item in raw[1:-1].split(",") if item.strip()]
            meta[key.strip()] = items
        elif raw.isdigit():
            meta[key.strip()] = int(raw)
        else:
            meta[key.strip()] = raw
    return meta, parts[2].strip()


@lru_cache(maxsize=1)
def corpus_documents() -> list[dict]:
    docs = []
    for path in sorted(Path(CORPUS_DIR).glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        docs.append(
            {
                "id": meta.get("id", path.stem),
                "title": meta.get("title", path.stem),
                "source": meta.get("source", "internal corpus"),
                "year": meta.get("year"),
                "topics": meta.get("topics", []),
                "path": str(path),
                "text": body,
            }
        )
    return docs
