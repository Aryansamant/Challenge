from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from src.knowledge.ingest import ScientificEmbedder, load_index
from src.knowledge.store import interventions
from src.models.schemas import Evidence, LandProfile


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    source: str
    year: int | None
    text: str
    score: float

    def to_evidence(self) -> Evidence:
        snippet = self.text[:420].rsplit(" ", 1)[0] + "…"
        return Evidence(
            source=self.source,
            year=self.year if isinstance(self.year, int) else None,
            citation=f"{self.title} ({self.source})",
            snippet=snippet,
            relevance=round(self.score, 3),
            doc_id=self.doc_id,
        )


class HybridRetriever:
    """Reciprocal-rank fusion of LSA vectors and BM25, plus structured intervention filter."""

    def __init__(self):
        index = load_index()
        self.records = index["records"]
        self.matrix = index["matrix"]
        self.embedder = ScientificEmbedder(index["vectorizer"], index["svd"])
        self.bm25 = BM25Okapi([_tokens(rec["text"]) for rec in self.records])
        self.interventions = interventions()

    def search(self, query: str, k: int = 6) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        q_vec = self.embedder.encode([query])[0]
        dense_scores = self.matrix @ q_vec
        bm_scores = np.array(self.bm25.get_scores(_tokens(query)), dtype=float)

        def ranks(scores: np.ndarray) -> dict[int, int]:
            order = np.argsort(-scores)
            return {int(idx): rank + 1 for rank, idx in enumerate(order)}

        dense_rank = ranks(dense_scores)
        bm_rank = ranks(bm_scores)
        fused = []
        for i in range(len(self.records)):
            score = 1.0 / (60 + dense_rank[i]) + 1.0 / (60 + bm_rank[i])
            fused.append((score, i))
        fused.sort(reverse=True)
        out = []
        seen_docs = set()
        for score, i in fused:
            rec = self.records[i]
            if rec["doc_id"] in seen_docs:
                continue
            seen_docs.add(rec["doc_id"])
            out.append(
                RetrievedChunk(
                    chunk_id=rec["chunk_id"],
                    doc_id=rec["doc_id"],
                    title=rec["title"],
                    source=rec["source"],
                    year=rec["year"],
                    text=rec["text"],
                    score=float(score),
                )
            )
            if len(out) >= k:
                break
        return out

    def applicable_interventions(self, profile: LandProfile) -> list[dict]:
        rainfall = (profile.climate.rainfall or "").lower()
        land_type = (profile.land_use.type or "").lower()
        management = (profile.land_use.management or "").lower()
        tillage = (profile.land_use.tillage or "").lower()
        pesticides = (profile.human_impact.pesticide_intensity or "").lower()
        grazing = (profile.human_impact.grazing_pressure or "").lower()
        deforestation = (profile.human_impact.deforestation or "").lower()
        fragmentation = (profile.human_impact.fragmentation or "").lower()
        ph = profile.soil.ph
        soc = profile.soil.organic_carbon_pct
        selected = []
        for item in self.interventions:
            rules = item.get("applies_when", {})
            if rules.get("avoid_if_rainfall") and rainfall in rules["avoid_if_rainfall"]:
                # still allow with a penalty later; skip only if strictly arid and water-hungry
                if rainfall == "arid" and item["id"] == "legume_cover_crops":
                    continue
            if rules.get("land_types") and land_type and land_type not in rules["land_types"]:
                continue
            if rules.get("rainfall") and rainfall and rainfall not in rules["rainfall"]:
                continue
            if rules.get("management") and management and management not in rules["management"]:
                continue
            if rules.get("tillage") and tillage and tillage not in rules["tillage"] and tillage != "unknown":
                continue
            if rules.get("pesticide_intensity") and pesticides and pesticides not in rules["pesticide_intensity"]:
                continue
            if rules.get("grazing_pressure") and grazing and grazing not in rules["grazing_pressure"]:
                continue
            if rules.get("deforestation") and deforestation and deforestation not in rules["deforestation"]:
                continue
            if rules.get("fragmentation") and fragmentation and fragmentation not in rules["fragmentation"]:
                continue
            if rules.get("soc_low") and soc is not None and soc > 1.8:
                continue
            if item["id"] == "ph_amendment":
                if ph is None:
                    continue
                if not (ph < 5.5 or ph > 8.3):
                    continue
            selected.append(item)
        return selected or list(self.interventions)
