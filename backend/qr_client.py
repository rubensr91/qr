"""
Cliente HTTP para el servicio de extraccion de QR (qr_service/).

Este modulo reemplaza el import directo de extraer_qr_pdfs.py. Mantiene
la misma API que el script legacy (mismas funciones, mismos returns)
para que app.py no note la diferencia.

El servicio qr_service es INTOCABLE (ver qr_service/README.md). Si
necesitas cambiar la extraccion de QR, modifica este cliente, no el
servicio.
"""

import base64
import os
import re
import sys
import time

import requests

# URL del servicio qr_service. Configurable por env var.
QR_SERVICE_URL = os.getenv("QR_SERVICE_URL", "http://127.0.0.1:8766")
TIMEOUT = 120  # segundos para PDFs grandes

# Lazy load de easyocr (pesado, ~2GB de modelos)
_easyocr_reader = None


def _get_ocr_reader():
    """Inicializa easyocr una sola vez (lazy, carga ~2GB de modelos)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(['es', 'en'], gpu=False)
    return _easyocr_reader


def _ocr_flight_time(image_path: str) -> dict[str, str | None]:
    """Extrae hora de salida y cierre de puertas de una imagen via OCR.

    Busca patrones de tabla como:
      Salida          La puerta cierra    Fecha
      09:15           08:45               30 dic

    Usa matching por posicion X para asociar cada hora con su etiqueta.

    Returns dict con 'flight_time' y 'gate_close_time' (None si no se encuentra).
    """
    try:
        reader = _get_ocr_reader()
        results = reader.readtext(image_path)
    except Exception as e:
        print(f"[ocr] Error: {e}", file=sys.stderr, flush=True)
        return {"flight_time": None, "gate_close_time": None}

    # Extraer items con posicion
    items = []
    for bbox, text, conf in results:
        x = int(bbox[0][0])
        y = int(bbox[0][1])
        items.append({"text": text.strip(), "x": x, "y": y, "conf": conf})

    flight_time = None
    gate_close_time = None

    # Buscar etiquetas y asociar con horas por proximidad en X
    labels = [
        ("flight_time", re.compile(r"^(?:Salida|Departs|Departure)$", re.IGNORECASE)),
        ("gate_close", re.compile(r"^(?:La puerta cierra|Gate closes|Cierre puertas|Puerta cierra|Gate closing|Embarking)(?:\s+a\s+las)?$", re.IGNORECASE)),
    ]

    time_re = re.compile(r"^(\d{1,2})[.:](\d{2})$")

    for field_name, label_pattern in labels:
        # Encontrar la etiqueta
        label_items = [it for it in items if label_pattern.match(it["text"])]
        if not label_items:
            continue

        # Encontrar horas (HH:MM o HH.MM)
        time_items = [it for it in items if time_re.match(it["text"])]

        # Buscar la hora mas cercana en X a cada etiqueta (debajo, misma columna)
        for label in label_items:
            candidates = [
                t for t in time_items
                if abs(t["x"] - label["x"]) < 80 and t["y"] > label["y"]
            ]
            if candidates:
                # La mas cercana en Y (justo debajo)
                best = min(candidates, key=lambda t: t["y"] - label["y"])
                m = time_re.match(best["text"])
                hh, mm = int(m.group(1)), int(m.group(2))
                if 0 <= hh <= 23 and 0 <= mm <= 59:
                    time_str = f"{hh:02d}:{mm:02d}"
                    if field_name == "flight_time":
                        flight_time = time_str
                    elif field_name == "gate_close":
                        gate_close_time = time_str

    return {"flight_time": flight_time, "gate_close_time": gate_close_time}


def _service_extract(file_path: str, is_image: bool) -> dict:
    """Llama al endpoint /extract del qr_service. Devuelve el JSON."""
    endpoint = "extract"
    url = f"{QR_SERVICE_URL.rstrip('/')}/{endpoint}"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        try:
            r = requests.post(url, files=files, timeout=TIMEOUT)
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"No se puede conectar al qr_service en {url}. "
                f"¿Esta arrancado? Error: {e}"
            ) from e

    if r.status_code != 200:
        # Reenviamos el detalle del servicio tal cual
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"qr_service devolvio {r.status_code}: {detail}")

    return r.json()


def _items_to_tuples(items: list[dict], out_dir: str) -> list[tuple]:
    """Convierte la respuesta JSON del servicio al formato de tuplas
    que espera app.py: (page, fname, b64, text, fmt, origin).

    Los PNGs NO se guardan en disco porque el servicio ya devuelve
    el crop en base64. El campo fname es solo un identificador.
    """
    tuples = []
    for i, it in enumerate(items):
        # El servicio devuelve items sin filename; generamos uno
        page = it.get("page", 1)
        fmt = it.get("format", "Unknown")
        text = it.get("text", "")
        b64 = it.get("base64", "")
        origin = it.get("origin", "service")
        # Identificador unico, sin extension (app.py no usa el archivo)
        fname = f"qr_p{page}_{i+1}_{fmt}.png"
        tuples.append((page, fname, b64, text, fmt, origin))
    return tuples


def extract_codes(pdf_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de un PDF via qr_service.

    Devuelve (codes, text_fields) con el mismo formato que
    extraer_qr_pdfs.extract_codes() para que app.py no note la diferencia.
    Los text_fields vienen vacios porque el servicio no extrae texto;
    app.py los necesita para origen/destino de Renfe. Para mantener
    esa funcionalidad, importamos extraer_qr_pdfs solo para el text.
    """
    data = _service_extract(pdf_path, is_image=False)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    # El servicio no extrae texto del PDF (solo recorta codigos).
    # Para mantener la extraccion de origen/destino/etc de Renfe,
    # seguimos usando extraer_qr_pdfs.extract_text_fields() en local.
    # Esta es la UNICA llamada al script legacy: solo para el texto.
    text_fields = {}
    try:
        import extraer_qr_pdfs  # noqa: E402  - import solo para text fields
        text_fields = extraer_qr_pdfs.extract_text_fields(pdf_path)
    except Exception:
        pass

    return codes, text_fields


def extract_codes_from_image(image_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de una imagen via qr_service + OCR de hora de salida.

    Returns (codes, ocr_data) donde ocr_data = {flight_time, gate_close_time}.
    Para imagenes no hay text_fields (Renfe no tiene imagenes sueltas).
    """
    data = _service_extract(image_path, is_image=True)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    # OCR para extraer hora de salida y cierre de puertas
    ocr_data = _ocr_flight_time(image_path)

    return codes, ocr_data
