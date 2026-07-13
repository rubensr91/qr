"""
API REST que envuelve el algoritmo de extraccion de QR/barcodes.

Endpoints:
  GET  /health              -> liveness check
  POST /api/extract         -> sube un PDF, devuelve codes + campos parseados
  GET  /api/trips           -> lista viajes de la sesion
  POST /api/trips           -> guarda un viaje (con deduplicacion)
  DELETE /api/trips/{id}    -> borra un viaje
"""

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from qr_client import extract_codes, extract_codes_from_image  # noqa: E402
from itinerary import expand_section, generate_itinerary, generate_trip_name  # noqa: E402
from parser import infer_years, parse_code  # noqa: E402
from token_tracker import check_limit, get_usage  # noqa: E402
from token_tracker import _ensure_table as _ensure_token_table  # noqa: E402
from admin import router as admin_router  # noqa: E402

DB_PATH = Path(__file__).resolve().parent / "trips.db"


def _get_db() -> sqlite3.Connection:
    """Crea o abre la base de datos SQLite y devuelve una conexion.
    Si la tabla trips no existe (BD borrada), la recrea automaticamente."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("SELECT 1 FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.close()
        _init_db()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Inicializa la tabla de viajes si no existe."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            pass_data TEXT NOT NULL,
            fingerprint TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trips_session
        ON trips(session_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trips_fingerprint
        ON trips(session_id, fingerprint)
    """)
    # Migracion: si la columna fingerprint no existe en una BD vieja, añadirla
    try:
        conn.execute("SELECT fingerprint FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''")
    try:
        conn.execute("SELECT updated_at FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN updated_at TEXT")
    try:
        conn.execute("SELECT itinerary_data FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN itinerary_data TEXT")
    try:
        conn.execute("SELECT trip_name FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN trip_name TEXT NOT NULL DEFAULT ''")
    try:
        conn.execute("SELECT segments FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN segments TEXT NOT NULL DEFAULT '[]'")
    conn.commit()
    conn.close()
    # Asegurar que la tabla de tracking de tokens tambien existe
    _ensure_token_table()


# Inicializar DB al arrancar
_init_db()

app = FastAPI(title="Boarding Pass Extractor", version="0.3.0")

# CORS permisivo para que la app Ionic pueda llamar en desarrollo
# (en produccion conviene restringir al dominio de la app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router de admin (dashboard de monitoreo de tokens)
app.include_router(admin_router)


# --- Session helper ---

def _get_session_id(request: Request) -> str:
    """Obtiene el session_id del header X-Session-Id, o crea uno nuevo."""
    sid = request.headers.get("X-Session-Id", "").strip()
    if not sid:
        sid = f"ses_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    return sid


# --- Fingerprint helpers ---

def _pass_fingerprint(p: dict) -> str:
    """Genera una huella unica para un pase basada en sus campos significativos.

    Vuelos:    kind + pnr + flight_date + flight + from + to
    Trenes:    kind + pnr + train + flight_date + flight_time + class
    Desconocido: kind + format + raw (truncado a 200 chars)
    Publicidad: se ignoran (no generan huella)
    """
    kind = (p.get("kind") or "").strip().lower()

    # Ignorar publicidad y URLs
    if kind == "advertising":
        return ""

    if kind == "flight":
        parts = [
            kind,
            (p.get("pnr") or "").strip().upper(),
            (p.get("flight_date") or "").strip(),
            (p.get("flight") or "").strip(),
            (p.get("from") or "").strip().upper(),
            (p.get("to") or "").strip().upper(),
        ]
    elif kind == "train":
        parts = [
            kind,
            (p.get("pnr") or "").strip().upper(),
            (p.get("train") or "").strip(),
            (p.get("flight_date") or "").strip(),
            (p.get("flight_time") or "").strip(),
            (p.get("class") or "").strip().upper(),
        ]
    else:
        raw = (p.get("raw") or "")[:200]
        parts = [
            kind or "unknown",
            (p.get("format") or "").strip(),
            raw,
        ]

    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _trip_fingerprint(passes: list[dict]) -> str:
    """Combina las huellas de todos los pases en una huella unica del viaje.

    Los pases se ordenan para que el orden de extraccion no afecte.
    Solo se consideran pases con huella no vacia (se ignoran ads).
    """
    fps = sorted(
        fp for p in passes if (fp := _pass_fingerprint(p))
    )
    if not fps:
        # Si no hay pases validos, usar hash del JSON completo
        raw = json.dumps(passes, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    return hashlib.sha256("|||".join(fps).encode()).hexdigest()[:16]


# --- Health ---

@app.get("/health")
def health():
    return {"status": "ok"}


# --- Validacion de pases ---

def _is_pass_complete(pass_data: dict) -> tuple[bool, str]:
    """Comprueba que un pase tiene todos los datos esenciales.
    Devuelve (ok, motivo) donde ok=True si es valido."""
    kind = pass_data.get("kind")
    if kind not in ("flight", "train"):
        return False, f"tipo desconocido {kind!r}"
    if not pass_data.get("flight_date"):
        return False, "falta fecha"
    if kind == "flight":
        if not pass_data.get("pnr"):
            return False, "vuelo sin localizador"
        if not pass_data.get("from") or not pass_data.get("to"):
            return False, "vuelo sin origen/destino"
        if not pass_data.get("name") or not pass_data.get("airline") or not pass_data.get("flight"):
            return False, "vuelo sin nombre/aerolinea/numero"
    if kind == "train":
        if not pass_data.get("train"):
            return False, "tren sin numero"
    return True, ""


# --- Extract ---

@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
    ALLOWED = {".pdf"} | IMG_EXTS

    if not file.filename:
        raise HTTPException(status_code=400, detail="Falta el nombre del archivo")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, PNG, JPG, WebP, BMP o TIFF")

    is_image = ext in IMG_EXTS

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = os.path.join(tmp, f"upload{ext}")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)

        try:
            if is_image:
                results, ocr_data = extract_codes_from_image(upload_path, out_dir)
                text_fields = {}
            else:
                # extract_codes ahora devuelve (codes, text_fields) para
                # evitar reabrir el PDF (fitz falla con rutas 8.3 / acentos).
                pdf_codes, text_fields = extract_codes(upload_path, out_dir)
                results = pdf_codes
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extrayendo: {e}")

    # results = [(page, fname, b64, text, format, origin), ...]
    # text_fields ya viene dentro del tuple de extract_codes para evitar
    # reabrir el PDF (fitz/PyMuPDF falla con rutas 8.3 / acentos en Windows).

    passes = []
    images = []
    descartados = 0
    for page, fname, b64, text, fmt, origin in results:
        parsed = parse_code(text)
        if parsed is None:
            descartados += 1
            print(f"[extract] p{page} descartado: {text[:60]!r}")
            continue
        # Mezclar campos del texto del PDF (solo si el barcode no los tiene)
        extras = text_fields.get(page, {})
        if extras:
            for key in ("from", "to", "seat", "name", "flight_time", "train", "coach", "pnr", "operator"):
                if key in extras and not parsed.get(key):
                    parsed[key] = extras[key]
            # Para trenes: sobreescribir train si el barcode empieza por 000 (invalido)
            if parsed.get("kind") == "train" and extras.get("train"):
                barcode_train = str(parsed.get("train", ""))
                if barcode_train.startswith("000") or barcode_train.lstrip("0") == "":
                    parsed["train"] = extras["train"]
            # Para trenes: usar el operador detectado como airline
            if parsed.get("kind") == "train" and parsed.get("operator") and not parsed.get("airline"):
                parsed["airline"] = parsed["operator"]
            # Si el código no tiene año (IATA BCBP) pero el PDF tiene fecha, usarla
            if not parsed.get("has_explicit_year") and extras.get("flight_date"):
                parsed["flight_date"] = extras["flight_date"]
                parsed["has_explicit_year"] = True
        # Mezclar hora de OCR (imagenes) si el barcode no la tiene
        if is_image and ocr_data:
            if ocr_data.get("flight_time") and not parsed.get("flight_time"):
                parsed["flight_time"] = ocr_data["flight_time"]
            if ocr_data.get("gate_close_time"):
                parsed["gate_close_time"] = ocr_data["gate_close_time"]
        # Validacion completa: descartar si faltan datos esenciales
        ok, motivo = _is_pass_complete(parsed)
        if not ok:
            descartados += 1
            raw_preview = parsed.get('raw', '')[:80] if parsed.get('raw') else text[:80]
            print(f"[extract] p{page} descartado ({motivo}): fmt={parsed.get('format','?')} raw={raw_preview!r}")
            continue
        passes.append({
            "page": page,
            "origin": origin,
            **parsed,
        })
        images.append({
            "page": page,
            "format": fmt,
            "filename": fname,
            "base64": b64,
        })
    if descartados:
        print(f"[extract] {descartados} pases descartados por datos incompletos")

    # Inferir años para vuelos sin año explícito (Ryanair, etc.)
    infer_years(passes)

    return {
        "filename": file.filename,
        "passes": passes,
        "images": images,
        "count": len(passes),
    }


# --- Trips CRUD ---

@app.get("/api/trips")
def list_trips(request: Request, x_session_id: str = Header(default="")):
    """Lista todos los viajes guardados para la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)
    print(f"[list_trips] session_id={sid} header={x_session_id!r}")
    if not sid:
        return {"trips": [], "session_id": ""}

    conn = _get_db()
    rows = conn.execute(
        "SELECT id, session_id, filename, pass_data, created_at, updated_at, trip_name, segments "
        "FROM trips WHERE session_id = ? ORDER BY created_at DESC",
        (sid,),
    ).fetchall()
    conn.close()

    print(f"[list_trips] found {len(rows)} trips for session {sid}")

    trips = []
    for r in rows:
        trips.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "filename": r["filename"],
            "trip_name": r["trip_name"] or "",
            "pass_data": json.loads(r["pass_data"]),
            "segments": json.loads(r["segments"] or "[]"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return {"trips": trips, "session_id": sid}


@app.post("/api/trips")
async def create_trip(request: Request, x_session_id: str = Header(default="")):
    """Guarda un viaje con deduplicacion.

    - Si el viaje no existe (misma huella) -> INSERT (status: created)
    - Si existe con mismos datos -> no hace nada (status: duplicate)
    - Si existe con datos distintos -> UPDATE (status: updated)

    Body: {filename, passes, images}
    """
    sid = _get_session_id_via_header(request, x_session_id)

    body = await request.json()
    filename = body.get("filename", "unknown.pdf")
    trip_name = body.get("trip_name", "").strip()
    passes = body.get("passes", body.get("pass_data", []))
    images = body.get("images", [])
    segments = body.get("segments", [])

    # Validar que todos los pases tengan datos completos
    for p in passes:
        ok, motivo = _is_pass_complete(p)
        if not ok:
            raise HTTPException(
                status_code=400,
                detail=f"Pase incompleto rechazado: {motivo}. Re-subir el archivo desde la home.",
            )

    # Auto-generar nombre si no se proporciono
    if not trip_name:
        try:
            trip_name = generate_trip_name(passes, segments)
        except Exception as e:
            print(f"[create_trip] Error generando nombre: {e}")
            trip_name = filename

    new_data = json.dumps({"passes": passes, "images": images}, ensure_ascii=False, sort_keys=True)
    fingerprint = _trip_fingerprint(passes)

    print(f"[create_trip] session_id={sid} fingerprint={fingerprint} passes={len(passes)} file={filename}")

    conn = _get_db()

    # Buscar viaje existente con la misma huella en esta sesion
    existing = conn.execute(
        "SELECT id, pass_data FROM trips "
        "WHERE session_id = ? AND fingerprint = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (sid, fingerprint),
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        existing_data = existing["pass_data"]

        # Comparar datos normalizados (ignorando whitespace en JSON)
        if json.loads(existing_data) == json.loads(new_data):
            conn.close()
            return {
                "status": "duplicate",
                "id": existing["id"],
                "session_id": sid,
                "filename": filename,
                "trip_name": trip_name,
                "message": "Este viaje ya estaba guardado, sin cambios",
            }

        # Datos distintos -> actualizar
        conn.execute(
            "UPDATE trips SET filename = ?, pass_data = ?, updated_at = ? WHERE id = ?",
            (filename, new_data, now, existing["id"]),
        )
        conn.commit()
        conn.close()
        return {
            "status": "updated",
            "id": existing["id"],
            "session_id": sid,
            "filename": filename,
            "message": "Viaje actualizado con nuevos datos",
        }

    # No existe -> insertar
    segments_json = json.dumps(segments, ensure_ascii=False)
    cursor = conn.execute(
        "INSERT INTO trips (session_id, filename, pass_data, fingerprint, trip_name, segments) VALUES (?, ?, ?, ?, ?, ?)",
        (sid, filename, new_data, fingerprint, trip_name, segments_json),
    )
    trip_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "created",
        "id": trip_id,
        "session_id": sid,
        "filename": filename,
        "trip_name": trip_name,
        "message": "Viaje guardado",
    }


@app.delete("/api/trips/{trip_id}")
def delete_trip(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Borra un viaje por ID, solo si pertenece a la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()

    return {"ok": True, "deleted": trip_id}


# --- Segments ---

@app.put("/api/trips/{trip_id}/segments")
async def update_segments(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Actualiza los segmentos manuales de un viaje.

    Body: { segments: [{type, ...}, ...] }
    Tipos soportados: flight, train, hotel, car, restaurant, activity
    """
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    body = await request.json()
    segments = body.get("segments", [])
    conn.execute(
        "UPDATE trips SET segments = ?, updated_at = ? WHERE id = ?",
        (json.dumps(segments, ensure_ascii=False), datetime.now(timezone.utc).isoformat(), trip_id),
    )
    conn.commit()
    conn.close()

    return {"ok": True, "trip_id": trip_id, "segments_count": len(segments)}


# --- Itinerary ---

@app.get("/api/itinerary/{trip_id}")
def get_trip_itinerary(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Obtiene el itinerario guardado de un viaje, si existe."""
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id, itinerary_data FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    itinerary_data = row["itinerary_data"]
    if not itinerary_data:
        raise HTTPException(status_code=404, detail="Itinerario no generado aun")

    return {
        "trip_id": trip_id,
        "cached": True,
        "itinerary": json.loads(itinerary_data),
    }


@app.post("/api/itinerary/{trip_id}")
async def generate_trip_itinerary(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Genera (o devuelve cache) un itinerario para un viaje.

    Si el viaje ya tiene itinerario guardado, lo devuelve directamente.
    Si no, consulta clima y genera con DeepSeek, guardando el resultado.
    """
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id, pass_data, itinerary_data, segments FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    # Devolver cache si ya existe (pero no si tiene error de parseo)
    cached = row["itinerary_data"]
    if cached:
        cached_it = json.loads(cached)
        if not cached_it.get("parse_error") and not cached_it.get("error"):
            conn.close()
            return {
                "trip_id": trip_id,
                "cached": True,
                "itinerary": cached_it,
            }

    pass_data = json.loads(row["pass_data"])
    passes = pass_data.get("passes", [])
    segments = json.loads(row["segments"] or "[]")
    conn.close()

    if not passes and not segments:
        raise HTTPException(status_code=400, detail="El viaje no tiene pases ni segmentos")

    # Verificar limite de tokens antes de llamar a DeepSeek
    allowed, usage_stats = check_limit(sid)
    if not allowed:
        if usage_stats.get("blocked"):
            error_msg = "Sesion bloqueada por el administrador"
        else:
            error_msg = "Limite de tokens excedido para esta sesion"
        raise HTTPException(
            status_code=429,
            detail={
                "error": error_msg,
                "blocked": usage_stats.get("blocked", False),
                "total_tokens_used": usage_stats["total_tokens_used"],
                "max_tokens": usage_stats["max_tokens"],
                "remaining": usage_stats["remaining"],
                "request_count": usage_stats["request_count"],
            },
        )

    # Generar nuevo itinerario
    try:
        itinerary = await generate_itinerary(passes, segments, session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando itinerario: {e}")

    # Guardar en BD (solo si no tiene errores)
    if not itinerary.get("parse_error") and not itinerary.get("error"):
        conn = _get_db()
        conn.execute(
            "UPDATE trips SET itinerary_data = ? WHERE id = ?",
            (json.dumps(itinerary, ensure_ascii=False), trip_id),
        )
        conn.commit()
        conn.close()

    # Incluir estadisticas de tokens en la respuesta
    token_info = itinerary.pop("_token_usage", None)
    response = {
        "trip_id": trip_id,
        "cached": False,
        "itinerary": itinerary,
    }
    if token_info:
        response["token_usage"] = token_info

    return response


# --- Expand section ---


@app.post("/api/itinerary/{trip_id}/expand")
async def expand_trip_section(
    trip_id: int,
    request: Request,
    x_session_id: str = Header(default=""),
):
    """Genera mas recomendaciones de una seccion concreta del itinerario.

    Body: { "section": "restaurants" | "hotels" | "visit" | "tips" }
    """
    sid = _get_session_id_via_header(request, x_session_id)
    body = await request.json()
    section = (body.get("section") or "").strip()

    if section not in ("restaurants", "hotels", "visit", "tips"):
        raise HTTPException(status_code=400, detail="Seccion no valida")

    conn = _get_db()
    row = conn.execute(
        "SELECT id, pass_data, itinerary_data, segments FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    pass_data = json.loads(row["pass_data"])
    passes = pass_data.get("passes", [])
    segments = json.loads(row["segments"] or "[]")
    itinerary_data = row["itinerary_data"]
    existing_itinerary = json.loads(itinerary_data) if itinerary_data else {}

    # Verificar limite de tokens
    allowed, usage_stats = check_limit(sid)
    if not allowed:
        if usage_stats.get("blocked"):
            error_msg = "Sesion bloqueada por el administrador"
        else:
            error_msg = "Limite de tokens excedido para esta sesion"
        raise HTTPException(
            status_code=429,
            detail={
                "error": error_msg,
                "blocked": usage_stats.get("blocked", False),
                "total_tokens_used": usage_stats["total_tokens_used"],
                "max_tokens": usage_stats["max_tokens"],
                "remaining": usage_stats["remaining"],
                "request_count": usage_stats["request_count"],
            },
        )

    try:
        result = expand_section(passes, segments, existing_itinerary, section, session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error expandiendo {section}: {e}")

    return result


# --- Token Usage ---


@app.get("/api/token-usage")
def token_usage(request: Request, x_session_id: str = Header(default="")):
    """Devuelve las estadisticas de consumo de tokens de la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)
    return get_usage(sid)


def _get_session_id_via_header(request: Request, header_value: str) -> str:
    """Combina header X-Session-Id con fallback a generacion automatica."""
    sid = (header_value or "").strip()
    if not sid:
        sid = request.headers.get("X-Session-Id", "").strip()
    if not sid:
        sid = f"ses_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    return sid
