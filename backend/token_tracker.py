"""
Control de gasto de tokens por sesion.

Limita las llamadas a DeepSeek por session_id para evitar abuso.
Usa SQLite para persistir el consumo acumulado.

Soporta:
- Limite global por env var DEEPSEEK_MAX_TOKENS_PER_SESSION
- Limite personalizado por sesion (grant manual)
- Bloqueo/desbloqueo manual de sesiones
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# --- Configuracion ---

DB_PATH = Path(__file__).resolve().parent / "trips.db"
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS_PER_SESSION", "200000"))


def _get_db() -> sqlite3.Connection:
    """Abre conexion a la BD con row_factory para acceso por nombre."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table():
    """Crea la tabla token_usage y aplica migraciones si es necesario."""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            session_id TEXT PRIMARY KEY,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            request_count INTEGER NOT NULL DEFAULT 0,
            blocked INTEGER NOT NULL DEFAULT 0,
            token_limit INTEGER,
            last_updated TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Migraciones para BDs existentes
    for col, col_type in [
        ("blocked", "INTEGER NOT NULL DEFAULT 0"),
        ("token_limit", "INTEGER"),
    ]:
        try:
            conn.execute(f"SELECT {col} FROM token_usage LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE token_usage ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def _effective_limit(row: sqlite3.Row | None) -> int:
    """Devuelve el limite efectivo de tokens para una fila (o el global)."""
    if row and row["token_limit"] is not None:
        return row["token_limit"]
    return MAX_TOKENS


def _build_stats(row: sqlite3.Row | None, session_id: str) -> dict:
    """Construye el diccionario de estadisticas a partir de una fila."""
    limit = _effective_limit(row)
    used = row["total_tokens"] if row else 0
    blocked = bool(row["blocked"]) if row else False
    return {
        "session_id": session_id,
        "input_tokens": row["input_tokens"] if row else 0,
        "output_tokens": row["output_tokens"] if row else 0,
        "total_tokens_used": used,
        "max_tokens": limit,
        "remaining": max(0, limit - used),
        "request_count": row["request_count"] if row else 0,
        "blocked": blocked,
        "has_custom_limit": bool(row and row["token_limit"] is not None),
        "last_updated": row["last_updated"] if row else None,
    }


# --- Funciones publicas ---

def check_limit(session_id: str) -> tuple[bool, dict]:
    """Verifica si la sesion aun tiene tokens disponibles.

    Returns:
        (allowed, stats) donde allowed=True si la sesion puede seguir
        haciendo llamadas a DeepSeek (no bloqueada y bajo el limite).
    """
    _ensure_table()
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return (True, _build_stats(None, session_id))

    stats = _build_stats(row, session_id)
    if stats["blocked"]:
        return (False, stats)

    limit = _effective_limit(row)
    return (row["total_tokens"] < limit, stats)


def record_usage(session_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Registra el consumo de tokens de una llamada a DeepSeek.

    Si la sesion esta bloqueada, igual registra el consumo (para auditoria)
    aunque la llamada no deberia haberse producido.
    """
    _ensure_table()
    total = input_tokens + output_tokens
    now = datetime.now(timezone.utc).isoformat()

    conn = _get_db()
    conn.execute("""
        INSERT INTO token_usage
            (session_id, input_tokens, output_tokens, total_tokens,
             request_count, last_updated)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            input_tokens = input_tokens + excluded.input_tokens,
            output_tokens = output_tokens + excluded.output_tokens,
            total_tokens = total_tokens + excluded.total_tokens,
            request_count = request_count + 1,
            last_updated = excluded.last_updated
    """, (session_id, input_tokens, output_tokens, total, now))

    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def get_usage(session_id: str) -> dict:
    """Obtiene las estadisticas de uso de tokens de una sesion."""
    _ensure_table()
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return _build_stats(None, session_id)
    return _build_stats(row, session_id)


def grant_tokens(session_id: str, additional_tokens: int) -> dict:
    """Concede tokens extra a una sesion (aumenta su limite personalizado).

    Si la sesion no tenia limite personalizado, se crea uno basado en
    el limite global + el extra.
    Si ya tenia limite personalizado, se incrementa.
    """
    _ensure_table()
    conn = _get_db()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    if row and row["token_limit"] is not None:
        new_limit = row["token_limit"] + additional_tokens
    else:
        new_limit = MAX_TOKENS + additional_tokens

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO token_usage (session_id, token_limit, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            token_limit = excluded.token_limit,
            last_updated = excluded.last_updated
    """, (session_id, new_limit, now))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def block_session(session_id: str, blocked: bool = True) -> dict:
    """Bloquea o desbloquea una sesion manualmente.

    Cuando blocked=True, la sesion no puede hacer mas llamadas a DeepSeek
    independientemente de los tokens que le queden.
    """
    _ensure_table()
    conn = _get_db()

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO token_usage (session_id, blocked, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            blocked = excluded.blocked,
            last_updated = excluded.last_updated
    """, (session_id, 1 if blocked else 0, now))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def list_all_sessions() -> list[dict]:
    """Lista todas las sesiones con uso de tokens, incluyendo
    sesiones que tienen viajes pero aun no han consumido tokens.

    Hace un LEFT JOIN con trips para enriquecer con contexto:
    numero de viajes y ultimo viaje creado.
    """
    _ensure_table()
    conn = _get_db()

    rows = conn.execute("""
        SELECT
            tu.session_id,
            tu.input_tokens,
            tu.output_tokens,
            tu.total_tokens,
            tu.request_count,
            tu.blocked,
            tu.token_limit,
            tu.last_updated,
            COUNT(t.id) as trip_count,
            MAX(t.created_at) as last_trip_at,
            GROUP_CONCAT(DISTINCT t.trip_name) as trip_names
        FROM token_usage tu
        LEFT JOIN trips t ON t.session_id = tu.session_id
        GROUP BY tu.session_id
        ORDER BY tu.total_tokens DESC
    """).fetchall()

    sessions = []
    for row in rows:
        stats = _build_stats(row, row["session_id"])
        stats["trip_count"] = row["trip_count"] or 0
        stats["last_trip_at"] = row["last_trip_at"]
        # Reconstruir trip_names como lista
        names_raw = row["trip_names"] or ""
        stats["trip_names"] = [n.strip() for n in names_raw.split(",") if n.strip()] if names_raw else []
        sessions.append(stats)

    conn.close()
    return sessions
