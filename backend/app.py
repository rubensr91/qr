"""
API REST que envuelve el algoritmo de extraccion de QR/barcodes.

Endpoints:
  GET  /health              -> liveness check
  POST /api/extract         -> sube un PDF, devuelve codes + campos parseados
"""

import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Path al script existente (en la raiz del proyecto, no en backend/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from extraer_qr_pdfs import extract_codes  # noqa: E402
from .parser import parse_code  # noqa: E402

app = FastAPI(title="Boarding Pass Extractor", version="0.1.0")

# CORS permisivo para que la app Ionic pueda llamar en desarrollo
# (en produccion conviene restringir al dominio de la app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se esperaba un PDF")

    # Guardamos el PDF a un tmp porque extraer_qr_pdfs espera una ruta
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "upload.pdf")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(contents)

        try:
            results = extract_codes(pdf_path, out_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extrayendo: {e}")

    # results = [(page, fname, b64, text, format, origin), ...]
    passes = []
    images = []
    for page, fname, b64, text, fmt, origin in results:
        parsed = parse_code(text)
        passes.append({
            "page": page,
            "origin": origin,  # "embedded" o "rendered"
            **parsed,
        })
        # Solo devolvemos la imagen si la queremos mostrar en la app
        # (incluimos todas por defecto; el cliente puede filtrar)
        images.append({
            "page": page,
            "format": fmt,
            "filename": fname,
            "base64": b64,
        })

    return {
        "filename": file.filename,
        "passes": passes,
        "images": images,
        "count": len(passes),
    }
