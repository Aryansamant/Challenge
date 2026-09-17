from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import SESSION_DIR
from src.models.schemas import LandProfile

SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _safe_session_id(session_id: str | None) -> str:
    if session_id:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:64]
        if cleaned:
            return cleaned
    return uuid.uuid4().hex[:12]


class SessionMemory:
    def __init__(self, session_id: str | None = None):
        self.session_id = _safe_session_id(session_id)
        self.path = SESSION_DIR / f"{self.session_id}.json"
        self.profile = LandProfile()
        self.turns: list[dict] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.profile = LandProfile.model_validate(data.get("profile", {}))
        self.turns = data.get("turns", [])
        self.created_at = data.get("created_at", self.created_at)

    def remember(self, role: str, content: str) -> None:
        self.turns.append(
            {
                "role": role,
                "content": content,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.persist()

    def persist(self) -> None:
        payload = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "profile": self.profile.model_dump(),
            "turns": self.turns[-40:],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def path_for(session_id: str) -> Path:
        return SESSION_DIR / f"{session_id}.json"
