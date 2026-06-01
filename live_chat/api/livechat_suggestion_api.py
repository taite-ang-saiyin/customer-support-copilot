"""FastAPI router for live chat suggestion generation."""

from __future__ import annotations

from fastapi import APIRouter, Body

from live_chat.generation.livechat_generator import generate_livechat_suggestion


router = APIRouter(prefix="/chat/conversations", tags=["live_chat-livechat"])


@router.post("/{conversation_id}/suggest")
def create_livechat_suggestion(conversation_id: str, payload: dict = Body(...)) -> dict:
    request = dict(payload)
    request["conversation_id"] = conversation_id
    return generate_livechat_suggestion(request)
