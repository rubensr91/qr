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


def _ocr_flight_time(image_path: str) -> dict[str, str | None]:
    """Extrae hora de salida y cierre de puertas de una imagen via Tesseract OCR.

    Busca patrones como:
      Salida   La puerta cierra a las   Fecha
      07:00    06:30                    02 ene.

    Returns dict con 'flight_time' y 'gate_close_time'.
    """
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    except Exception as e:
        print(f"[ocr] Error importando pytesseract: {e}", file=sys.stderr, flush=True)
        return {"flight_time": None, "gate_close_time": None}

    try:
        img = Image.open(image_path)
        w, h = img.size
        if max(w, h) < 1200:
            img = img.resize((w * 2, h * 2), Image.LANCZOS)
        text = pytesseract.image_to_string(
            img, lang='spa+eng', config='--psm 6 --oem 1',
        )
    except Exception as e:
        print(f"[ocr] Error en OCR: {e}", file=sys.stderr, flush=True)
        return {"flight_time": None, "gate_close_time": None}

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    flight_time: str | None = None
    gate_close_time: str | None = None

    time_re = re.compile(r"(\d{1,2})[:.](\d{2})")

    for i, line in enumerate(lines):
        has_salida = 'salida' in line.lower()
        has_puerta = 'puerta' in line.lower()

        if not (has_salida or has_puerta):
            continue

        data_line = ''
        for j in range(i + 1, min(i + 3, len(lines))):
            if lines[j] and time_re.search(lines[j]):
                data_line = lines[j]
                break

        if not data_line:
            continue

        times = []
        for m in time_re.finditer(data_line):
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                times.append(f"{hh:02d}:{mm:02d}")

        if has_salida and len(times) > 0 and flight_time is None:
            flight_time = times[0]
        if has_puerta and len(times) > 1 and gate_close_time is None:
            gate_close_time = times[1]
        elif has_puerta and len(times) == 1 and gate_close_time is None:
            gate_close_time = times[0]

    if flight_time is None or gate_close_time is None:
        all_times = []
        for m in time_re.finditer(text):
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                all_times.append(f"{hh:02d}:{mm:02d}")

        seen = set()
        unique_times = []
        for t in all_times:
            if t not in seen:
                seen.add(t)
                unique_times.append(t)

        if flight_time is None and len(unique_times) > 0:
            flight_time = unique_times[0]
        if gate_close_time is None and len(unique_times) > 1:
            gate_close_time = unique_times[1]

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
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"qr_service devolvio {r.status_code}: {detail}")

    return r.json()


def _items_to_tuples(items: list[dict], out_dir: str) -> list[tuple]:
    """Convierte la respuesta JSON del servicio al formato de tuplas
    que espera app.py: (page, fname, b64, text, fmt, origin).
    """
    tuples = []
    for i, it in enumerate(items):
        page = it.get("page", 1)
        fmt = it.get("format", "Unknown")
        text = it.get("text", "")
        b64 = it.get("base64", "")
        origin = it.get("origin", "service")
        fname = f"qr_p{page}_{i+1}_{fmt}.png"
        tuples.append((page, fname, b64, text, fmt, origin))
    return tuples


def extract_codes(pdf_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de un PDF via qr_service."""
    data = _service_extract(pdf_path, is_image=False)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    text_fields = {}
    try:
        import extraer_qr_pdfs  # noqa: E402
        text_fields = extraer_qr_pdfs.extract_text_fields(pdf_path)
    except Exception:
        pass

    return codes, text_fields


def extract_codes_from_image(image_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de una imagen via qr_service + OCR de hora de salida."""
    data = _service_extract(image_path, is_image=True)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    ocr_data = _ocr_flight_time(image_path)

    return codes, ocr_data
