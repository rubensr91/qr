"""
Extrae codigos 2D (QR, PDF417, Aztec) de cualquier PDF.
Sin nombres hardcodeados: detecta y decodifica automaticamente
lo que haya, sea imagen embebida o vector en la pagina.

Uso:
  python extraer_qr_pdfs.py tarjeta1.pdf tarjeta2.pdf ...
  python extraer_qr_pdfs.py *.pdf

Salida en ./qr_extraidos/:
  <nombre_pdf>/
    code_pN_M.png    recortes de los codigos encontrados
    qr_data.txt      datos decodificados
    qr_base64.txt    base64 para embeber en HTML
  _all_data.txt      consolidado de todos los PDFs
  _all_base64.txt    base64 consolidado

Dependencias:
  pip install pymupdf pillow zxing-cpp
"""

import base64
import io
import os
import re
import sys

import fitz
from PIL import Image


# Resolucion del rasterizado de fallback. 300 DPI = buen balance para
# PDF417 / Aztec / QR en PDFs reales.
RENDER_DPI = 300

# Margen en pixeles alrededor del bounding box detectado al recortar.
CROP_PADDING = 20

# Formatos 2D que decodificamos. Anade o quita segun necesites.
SUPPORTED_FORMATS = (
    "QRCode",
    "PDF417",
    "Aztec",
)

# Patrones de codigos que NO nos interesan (publicidad propia del operador).
# Ejemplos: Renfe Tiempo Real (https://tiempo-real.largorecorrido.renfe.com/),
# OUIGO (https://qrco.de/...). Anade aqui mas si encuentras otros.
SKIP_PATTERNS = (
    re.compile(r"^https?://", re.IGNORECASE),
)


def _should_skip(text):
    return any(p.match(text) for p in SKIP_PATTERNS)


def _decode(pil_image):
    """Devuelve la lista de hits (zxingcpp.Barcode) que zxing-cpp encuentra
    en una imagen PIL, probando los formatos dados y rotaciones / inversiones."""
    import zxingcpp
    fmt = [getattr(zxingcpp.BarcodeFormat, name) for name in SUPPORTED_FORMATS]
    return zxingcpp.read_barcodes(
        pil_image,
        formats=fmt,
        try_rotate=True,
        try_invert=True,
    )


def _save_png(pil_image, out_dir, fname):
    """Guarda una imagen PIL como PNG y devuelve (bytes_png, base64_str)."""
    path = os.path.join(out_dir, fname)
    pil_image.save(path, "PNG")
    with open(path, "rb") as f:
        png_bytes = f.read()
    return png_bytes, base64.b64encode(png_bytes).decode()


def _crop_to_hit(page_img, hit):
    """Recorta el bounding box del codigo detectado en la imagen de pagina."""
    pos = hit.position
    xs = [pos.top_left.x, pos.top_right.x, pos.bottom_right.x, pos.bottom_left.x]
    ys = [pos.top_left.y, pos.top_right.y, pos.bottom_right.y, pos.bottom_left.y]
    return page_img.crop((
        max(int(min(xs)) - CROP_PADDING, 0),
        max(int(min(ys)) - CROP_PADDING, 0),
        min(int(max(xs)) + CROP_PADDING, page_img.width),
        min(int(max(ys)) + CROP_PADDING, page_img.height),
    ))


def extract_codes(pdf_path, out_dir):
    """Extrae todos los codigos 2D de un PDF.

    Estrategia, en orden, y si ambos paths detectan el mismo codigo
    gana el RENDERIZADO (mayor resolucion):
      1. Imagenes embebidas en cada pagina  (rapido, no rasteriza)
      2. Rasterizado de la pagina a RENDER_DPI  (cubre codigos en vector
         y ademas aporta la version en alta resolucion del mismo codigo)

    Devuelve una lista de tuplas:
        (page_num, fname, b64, texto, formato, origen)
    donde origen es "embedded" o "rendered".
    """
    doc = fitz.open(pdf_path)
    # Dict para que la version rendered pueda SUSTITUIR a la embedded
    # cuando ambas detectan el mismo codigo (mismo page/format/text).
    results = {}  # (page_num, format_name, text) -> result_tuple
    counter = {}  # (page_num) -> siguiente idx de filename

    def _next_idx(page_num):
        counter[page_num] = counter.get(page_num, 0) + 1
        return counter[page_num]

    def _save_entry(page_num, pil_img, hit, origin):
        idx = _next_idx(page_num)
        fname = f"code_p{page_num}_{idx}.png"
        _, b64 = _save_png(pil_img, out_dir, fname)
        return (page_num, fname, b64, hit.text, hit.format.name, origin)

    for page_num in range(doc.page_count):
        page_num_1based = page_num + 1
        page = doc[page_num]

        # --- 1. Imagenes embebidas ----------------------------------------
        for img_meta in page.get_images(full=True):
            try:
                info = doc.extract_image(img_meta[0])
                pil_img = Image.open(io.BytesIO(info["image"]))
            except Exception:
                continue
            for hit in _decode(pil_img):
                if not hit.text:
                    continue
                if _should_skip(hit.text):
                    print(
                        f"  P{page_num_1based} skipped  "
                        f"[{hit.format.name:<7}]  {hit.text[:60]}  "
                        f"(advertising)"
                    )
                    continue
                key = (page_num_1based, hit.format.name, hit.text)
                if key in results:
                    continue
                results[key] = _save_entry(page_num_1based, pil_img, hit, "embedded")
                print(
                    f"  P{page_num_1based} embedded  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}"
                )

        # --- 2. Rasterizado de la pagina (cubre vector + mejora resol.) ---
        pix = page.get_pixmap(dpi=RENDER_DPI)
        page_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        for hit in _decode(page_img):
            if not hit.text:
                continue
            if _should_skip(hit.text):
                # El path rendered tambien puede re-detectar codigos
                # publicitarios que ya habriamos saltado arriba; lo
                # silenciamos para no duplicar el mensaje.
                continue
            key = (page_num_1based, hit.format.name, hit.text)
            if key in results:
                # Ya tenemos una version embedded: la descartamos y
                # nos quedamos con la renderizada (mas nitida y bien recortada).
                old_fname = results[key][1]
                old_path = os.path.join(out_dir, old_fname)
                try:
                    os.remove(old_path)
                except OSError:
                    pass
                print(
                    f"  P{page_num_1based} upgrade  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}  "
                    f"(embedded -> rendered)"
                )
            else:
                print(
                    f"  P{page_num_1based} rendered  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}"
                )
            crop = _crop_to_hit(page_img, hit)
            results[key] = _save_entry(page_num_1based, crop, hit, "rendered")

    doc.close()
    return list(results.values())


def extract_codes_from_image(image_path, out_dir):
    """Extrae todos los codigos 2D de una imagen (screenshot, foto, etc.).

    Soporta PNG, JPG, WebP, BMP, TIFF y cualquier formato que PIL pueda abrir.

    Devuelve el mismo formato que extract_codes():
        [(page_num, fname, b64, texto, formato, origen)]
    donde page_num es siempre 1 y origen es "screenshot".
    """
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  Error abriendo imagen: {e}")
        return []

    results = []
    seen = set()
    counter = 0

    for hit in _decode(pil_img):
        if not hit.text:
            continue
        if _should_skip(hit.text):
            print(
                f"  skipped  [{hit.format.name:<7}]  {hit.text[:60]}  "
                f"(advertising)"
            )
            continue
        key = (hit.format.name, hit.text)
        if key in seen:
            continue
        seen.add(key)

        counter += 1
        fname = f"code_p1_{counter}.png"
        crop = _crop_to_hit(pil_img, hit)
        _, b64 = _save_png(crop, out_dir, fname)

        print(
            f"  [{hit.format.name:<7}]  {hit.text[:90]}"
        )
        results.append((1, fname, b64, hit.text, hit.format.name, "screenshot"))

    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdfs = sys.argv[1:]
    # Carpeta de salida junto al primer PDF. Cada PDF va a su propia
    # subcarpeta para que los nombres de archivo no se pisen entre PDFs.
    base_dir = os.path.join(os.path.dirname(os.path.abspath(pdfs[0])), "qr_extraidos")
    os.makedirs(base_dir, exist_ok=True)

    consolidated_data = []
    consolidated_b64 = []

    for pdf in pdfs:
        print(f"\n{'=' * 64}")
        print(f"Procesando: {os.path.basename(pdf)}")
        print(f"{'=' * 64}")

        # Subcarpeta = nombre del PDF sin extension, saneado.
        stem = os.path.splitext(os.path.basename(pdf))[0]
        sub = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
        out_dir = os.path.join(base_dir, sub)
        os.makedirs(out_dir, exist_ok=True)

        res = extract_codes(pdf, out_dir)
        if not res:
            print(f"  (sin codigos)")
            continue

        # Ficheros por PDF (facil de navegar).
        with open(os.path.join(out_dir, "qr_data.txt"), "w", encoding="utf-8") as f:
            f.write(
                "\n".join(f"  P{page} [{fmt}]: {text}" for page, _, _, text, fmt, _ in res)
            )
        with open(os.path.join(out_dir, "qr_base64.txt"), "w", encoding="utf-8") as f:
            for page, fname, b64, _text, _fmt, _origin in res:
                stem_png = os.path.splitext(fname)[0]
                f.write(f"  {stem_png} = data:image/png;base64,{b64}\n")

        # Y ademas un consolidado a nivel raiz para vision global.
        consolidated_data.append(f"\n=== {os.path.basename(pdf)} ===")
        for page, _fn, _b64, text, fmt, _origin in res:
            consolidated_data.append(f"  P{page} [{fmt}]: {text}")
        consolidated_b64.append(f"\n=== {os.path.basename(pdf)} ===")
        for page, fname, b64, _text, _fmt, _origin in res:
            stem_png = f"{sub}/{os.path.splitext(fname)[0]}"
            consolidated_b64.append(f"  {stem_png} = data:image/png;base64,{b64}\n")

    with open(os.path.join(base_dir, "_all_data.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(consolidated_data))
    with open(os.path.join(base_dir, "_all_base64.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(consolidated_b64))

    print(f"\nListo. {len(pdfs)} PDF(s) -> {base_dir}/")


if __name__ == "__main__":
    main()
