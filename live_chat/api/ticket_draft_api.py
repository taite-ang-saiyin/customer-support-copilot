"""FastAPI router for ticket draft generation."""

from __future__ import annotations

from fastapi import APIRouter, Body

from live_chat.generation.ticket_generator import generate_ticket_draft


router = APIRouter(prefix="/tickets", tags=["live_chat-tickets"])


@router.post("/{ticket_id}/draft")
def create_ticket_draft(ticket_id: str, payload: dict = Body(...)) -> dict:
    request = dict(payload)
    request["ticket_id"] = ticket_id
    return generate_ticket_draft(request)
