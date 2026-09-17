from __future__ import annotations

from src.conversation.dialogue import needed_questions, ready_to_recommend
from src.conversation.extractor import extract_from_text, merge_profiles
from src.conversation.memory import SessionMemory
from src.geo.climate import enrich_from_coordinates
from src.knowledge.retriever import HybridRetriever
from src.llm.synthesizer import maybe_llm_polish, render_pack
from src.models.schemas import ChatRequest, ChatResponse, LandProfile, RecommendationPack


class BioIntelEngine:
    def __init__(self):
        self.retriever = HybridRetriever()

    def ingest_request(self, memory: SessionMemory, request: ChatRequest) -> LandProfile:
        profile = memory.profile
        if request.profile:
            profile = merge_profiles(profile, request.profile)
        if request.coordinates and len(request.coordinates) == 2:
            profile.geo.lat = request.coordinates[0]
            profile.geo.lon = request.coordinates[1]
        if request.message:
            profile = extract_from_text(request.message, profile)
        if profile.geo.lat is not None and profile.geo.lon is not None:
            profile = enrich_from_coordinates(profile)
        memory.profile = profile
        memory.persist()
        return profile

    def respond(self, request: ChatRequest) -> ChatResponse:
        memory = SessionMemory(request.session_id)
        if request.message:
            memory.remember("user", request.message)
        profile = self.ingest_request(memory, request)
        follow_ups = needed_questions(profile)
        can_run = ready_to_recommend(profile)

        pack: RecommendationPack | None = None
        if can_run:
            pack = self._recommend(profile, request.message or "")
            pack.follow_ups = follow_ups if follow_ups and profile.filled_variable_count() < 6 else []
            questions_only = False
        else:
            pack = RecommendationPack(
                diagnosis_summary=(
                    "The site record is still incomplete. An environmental-science answer needs at least "
                    "soil, climate/water, and land-use variables together — single-variable advice would be misleading."
                ),
                limiting_factors=["incomplete multi-metric profile"],
                metric_status=[],
                causal_chains=[],
                recommendations=[],
                follow_ups=follow_ups,
                confidence_overall="low",
                variables_used=[
                    key
                    for group, payload in profile.as_context_dict().items()
                    if isinstance(payload, dict)
                    for key in payload
                ],
                retrieval_notes="Recommendation engine paused until three environmental axes are populated.",
            )
            questions_only = True

        message = maybe_llm_polish(render_pack(pack, profile, questions_only=questions_only), pack)
        memory.remember("assistant", message)
        return ChatResponse(
            session_id=memory.session_id,
            assistant_message=message,
            pack=pack,
            profile=profile,
            needs_more_input=questions_only,
            retrieved_doc_ids=[ev.doc_id for ev in (pack.retrieved_evidence if pack else [])],
        )

    def _recommend(self, profile: LandProfile, message: str) -> RecommendationPack:
        from src.reasoning.recommender import recommend

        return recommend(profile, self.retriever, message)
