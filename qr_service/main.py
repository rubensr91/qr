"""
================================================================================
                         ⚠️  SERVICIO INTOCABLE  ⚠️
================================================================================

Este servicio extrae y recorta codigos de barras / QR de PDFs e imagenes.
ES UN SERVICIO AISLADO. Cualquier cambio en su comportamiento rompe el
contrato con todos los clientes que lo consumen.

NO MODIFICAR salvo autorizacion EXPLICITA y por escrito del dueno del
proyecto. Si necesitas un cambio, abre un issue y esperate a la revision.

API:
  POST /extract    multipart con campo "file" (PDF o imagen)
                   -> 200 JSON con {filename, items: [{page, format, text, base64}]}
                   -> 400 si formato no soportado
                   -> 500 si error interno
  GET  /health      -> 200 {"status": "ok"}

Formatos soportados: PDF, PNG, JPG, JPEG, WebP, BMP, TIFF
================================================================================
"""

import base64
import io
import os
import re
import sys
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import zxingcpp
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image


# Limites de tamano (MB)
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
RENDER_DPI = 300
CROP_PADDING = 20
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


app = FastAPI(
    title="QR Extraction Service",
    version="1.0.0",
    description="Servicio aislado de extraccion y recorte de codigos QR/barcodes",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _should_skip(text: str) -> bool:
    """Detecta URLs de publicidad que no son billetes."""
    if not text:
        return True
    return bool(URL_PATTERN.match(text.strip()))


def _decode(pil_image: Image.Image):
    """Decodifica codigos 2D con zxing-cpp (soporta QR, PDF417, Aztec, etc)."""
    return zxingcpp.read_barcodes(
        pil_image,
        formats=(
            zxingcpp.BarcodeFormat.QRCode,
            zxingcpp.BarcodeFormat.PDF417,
            zxingcpp.BarcodeFormat.Aztec,
        ),
        try_rotate=True,
        try_invert=True,
    )


def _crop_to_hit(pil_image: Image.Image, hit) -> Image.Image:
    """Recorta el bounding box del codigo detectado con padding."""
    pos = hit.position
    xs = [pos.top_left.x, pos.top_right.x, pos.bottom_right.x, pos.bottom_left.x]
    ys = [pos.top_left.y, pos.top_right.y, pos.bottom_right.y, pos.bottom_left.y]
    return pil_image.crop((
        max(int(min(xs)) - CROP_PADDING, 0),
        max(int(min(ys)) - CROP_PADDING, 0),
        min(int(max(xs)) + CROP_PADDING, pil_image.width),
        min(int(max(ys)) + CROP_PADDING, pil_image.height),
    ))


def _image_to_base64(pil_image: Image.Image) -> str:
    """Convierte una imagen PIL a PNG base64."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _extract_from_pdf(pdf_path: str, out_dir: str) -> list[dict]:
    """Extrae codigos de un PDF: imagenes embebidas + rasterizado."""
    results: dict[tuple, dict] = {}  # (page, format, text) -> item
    counter: dict[int, int] = {}

    def _next_idx(page_num: int) -> int:
        counter[page_num] = counter.get(page_num, 0) + 1
        return counter[page_num]

    def _save_entry(page_num: int, pil_img: Image.Image, hit, origin: str) -> dict:
        idx = _next_idx(page_num)
        crop = _crop_to_hit(pil_img, hit)
        return {
            "page": page_num,
            "format": hit.format.name,
            "text": hit.text or "",
            "origin": origin,
            "base64": _image_to_base64(crop),
        }

    doc = fitz.open(pdf_path)
    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_num_1based = page_num + 1

            # 1) Imagenes embebidas
            for img_meta in page.get_images(full=True):
                try:
                    info = doc.extract_image(img_meta[0])
                    pil_img = Image.open(io.BytesIO(info["image"]))
                except Exception:
                    continue
                for hit in _decode(pil_img):
                    if not hit.text or _should_skip(hit.text):
                        continue
                    key = (page_num_1based, hit.format.name, hit.text)
                    if key in results:
                        continue
                    results[key] = _save_entry(page_num_1based, pil_img, hit, "embedded")

            # 2) Rasterizado (cubre vector y mejora resolucion)
            pix = page.get_pixmap(dpi=RENDER_DPI)
            page_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            for hit in _decode(page_img):
                if not hit.text or _should_skip(hit.text):
                    continue
                key = (page_num_1based, hit.format.name, hit.text)
                if key in results:
                    # Reemplaza la version embedded por la rendered (mas nitida)
                    old_fname = results[key].get("filename", "")
                    if old_fname:
                        try:
                            os.remove(os.path.join(out_dir, old_fname))
                        except OSError:
                            pass
                results[key] = _save_entry(page_num_1based, page_img, hit, "rendered")
    finally:
        doc.close()

    return list(results.values())


def _extract_from_image(image_path: str) -> list[dict]:
    """Extrae codigos de una imagen suelta."""
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo abrir la imagen: {e}")

    results = []
    seen: set = set()
    for hit in _decode(pil_img):
        if not hit.text or _should_skip(hit.text):
            continue
        key = (hit.format.name, hit.text)
        if key in seen:
            continue
        seen.add(key)
        crop = _crop_to_hit(pil_img, hit)
        results.append({
            "page": 1,
            "format": hit.format.name,
            "text": hit.text or "",
            "origin": "screenshot",
            "base64": _image_to_base64(crop),
        })
    return results


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Falta el nombre del archivo")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {ext}. Usa PDF, PNG, JPG, WebP, BMP o TIFF",
        )

    is_image = ext in IMG_EXTS

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = os.path.join(tmp, f"upload{ext}")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande (>{MAX_FILE_SIZE_MB}MB)",
            )
        with open(upload_path, "wb") as f:
            f.write(contents)

        try:
            if is_image:
                items = _extract_from_image(upload_path)
            else:
                items = _extract_from_pdf(upload_path, out_dir)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extrayendo: {e}")

    return {
        "filename": file.filename,
        "items": items,
        "count": len(items),
    }
