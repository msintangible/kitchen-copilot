"""
routes/session.py
HTTP endpoints — health check and session token creation.
"""

import logging
from fastapi import APIRouter
from Backend.security import generate_session_token

logger = logging.getLogger("kitchen_copilot.routes.session")
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check — Cloud Run uses this to verify the service is alive.
    Test it: curl http://localhost:8000/health
    """
    return {"status": "ok", "service": "kitchen-copilot"}


@router.post("/session/token")
async def create_session_token():
    """
    Frontend calls this BEFORE opening the WebSocket.
    Returns a one-time token used to authenticate the WS connection.

    Frontend usage:
      const { token, session_id } = await fetch('/session/token', {
        method: 'POST'
      }).then(r => r.json())

      const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`)
    """
    token, session_id = generate_session_token()
    return {
        "token": token,
        "session_id": session_id
    }