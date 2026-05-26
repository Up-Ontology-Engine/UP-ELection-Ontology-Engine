from __future__ import annotations
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from ..queries import (
    create_session, get_sessions, get_session,
    get_session_messages, add_message, update_session_title, delete_session
)
from ..reasoning import reasoning_query
from ..validation import InputValidationRoute

router = APIRouter(route_class=InputValidationRoute)


class ReasoningRequest(BaseModel):
    question: str = Field(..., max_length=1000)


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class AddMessageRequest(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    result: Optional[dict] = None
    ts: str


class UpdateTitleRequest(BaseModel):
    title: str


@router.post("/reasoning/query")
def reasoning_endpoint(body: ReasoningRequest):
    """
    AI-assisted political reasoning: natural language → Cypher → Neo4j results.
    Powered by Sarvam LLM when `SARVAM_API_KEY` is set, otherwise Gemini.
    """
    if not body.question.strip():
        raise HTTPException(400, "question must not be empty")
    return reasoning_query(body.question.strip())


@router.get("/chat/sessions")
def list_sessions(limit: int = Query(50, ge=1, le=200)):
    """List all reasoning sessions, newest first."""
    return {"sessions": get_sessions(limit=limit)}


@router.post("/chat/sessions")
def new_session(body: CreateSessionRequest):
    """Create a new reasoning session."""
    return create_session(title=body.title)


@router.get("/chat/sessions/{session_id}")
def get_session_detail(session_id: str):
    """Get session metadata."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return sess


@router.get("/chat/sessions/{session_id}/messages")
def list_messages(session_id: str):
    """Load all messages for a session."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"session_id": session_id, "messages": get_session_messages(session_id)}


@router.post("/chat/sessions/{session_id}/messages")
def post_message(session_id: str, body: AddMessageRequest):
    """Append a message to a session."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return add_message(session_id, body.role, body.content, body.result, body.ts)


@router.patch("/chat/sessions/{session_id}/title")
def patch_session_title(session_id: str, body: UpdateTitleRequest):
    """Rename a session."""
    ok = update_session_title(session_id, body.title)
    if not ok:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"session_id": session_id, "title": body.title}


@router.delete("/chat/sessions/{session_id}")
def remove_session(session_id: str):
    """Delete a session and all its messages."""
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"deleted": session_id}
