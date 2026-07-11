"""
Router de administracion para el dashboard de monitoreo de tokens.

Endpoints:
  GET  /api/admin/sessions   -> lista todas las sesiones con uso
  POST /api/admin/grant      -> concede tokens extra a una sesion
  POST /api/admin/block      -> bloquea/desbloquea una sesion
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .token_tracker import block_session, grant_tokens, list_all_sessions

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas ---

class GrantRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="ID de sesion")
    amount: int = Field(..., gt=0, description="Cantidad de tokens a conceder")


class BlockRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="ID de sesion")
    blocked: bool = Field(..., description="True para bloquear, False para desbloquear")


# --- Endpoints ---

@router.get("/sessions")
def admin_list_sessions():
    """Lista todas las sesiones con sus estadisticas de tokens y viajes."""
    return {"sessions": list_all_sessions()}


@router.post("/grant")
def admin_grant_tokens(body: GrantRequest):
    """Concede tokens extra al limite de una sesion."""
    try:
        stats = grant_tokens(body.session_id, body.amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conceder tokens: {e}")

    return {
        "ok": True,
        "message": f"Concedidos {body.amount:,} tokens a {body.session_id}",
        "session": stats,
    }


@router.post("/block")
def admin_block_session(body: BlockRequest):
    """Bloquea o desbloquea una sesion."""
    try:
        stats = block_session(body.session_id, body.blocked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al {'bloquear' if body.blocked else 'desbloquear'} sesion: {e}")

    action = "Bloqueada" if body.blocked else "Desbloqueada"
    return {
        "ok": True,
        "message": f"{action} sesion {body.session_id}",
        "session": stats,
    }
