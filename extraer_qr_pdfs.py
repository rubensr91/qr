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
    # Extraer campos de texto del PDF (origen, destino, plaza, etc.)
    # Se hace aqui mismo para evitar abrir el PDF dos veces (fitz falla
    # con rutas 8.3 / caracteres especiales en Windows al reabrir).
    text_fields = _extract_text_fields_from_doc(doc)

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
                # publicitarios que ya habiamos saltado arriba; lo
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

    # --- 3. Dedup post-extraccion: Renfe y otros tienen el mismo ticket
    # en QR (compacto, mal decodificado) y en Aztec (completo). Aqui
    # parseamos cada resultado y eliminamos los duplicados quedandonos
    # con el que tenga mas datos. Solo si la extraccion devolvio
    # algo que se pueda parsear.
    try:
        # El parser esta en backend/; anyadimos al path si no esta
        import sys as _sys
        _HERE = os.path.dirname(os.path.abspath(__file__))
        _BACKEND = os.path.join(_HERE, "backend")
        if os.path.isdir(_BACKEND) and _BACKEND not in _sys.path:
            _sys.path.insert(0, _BACKEND)
        from parser import parse_code
        # Agrupar por (pagina, identificador-de-ticket)
        groups: dict[tuple, list[tuple]] = {}
        for tup in results.values():
            page, fname, b64, text, fmt, origin = tup
            parsed = parse_code(text)
            if not parsed:
                continue
            # Identificador unico del ticket segun el formato
            # NO usamos la fecha porque en QR compacto sale mal; usamos
            # solo (page, tipo, codigo) y descartamos por texto mas largo.
            if parsed.get("kind") == "train":
                tid = ("train", parsed.get("train"), parsed.get("pnr"))
            elif parsed.get("airline"):
                tid = ("flight", parsed.get("airline"), parsed.get("flight"))
            else:
                continue
            groups.setdefault((page,) + tid, []).append(tup)
        print(f"  [dedup] {len(groups)} grupos unicos")

        # Para cada grupo, conservar el que tenga el texto mas largo
        # (mas datos = barcode completo vs compacto) y borrar el resto
        total_dropped = 0
        for key, tups in groups.items():
            if len(tups) <= 1:
                continue
            # Ordenar por longitud de texto descendente
            tups.sort(key=lambda t: len(t[3]), reverse=True)
            keep = tups[0]
            for drop in tups[1:]:
                # Encontrar y borrar la entrada con este filename
                for k in list(results.keys()):
                    if results[k] is drop:
                        del results[k]
                        # Borrar el archivo PNG
                        drop_path = os.path.join(out_dir, drop[1])
                        try:
                            os.remove(drop_path)
                        except OSError:
                            pass
                        total_dropped += 1
                        break
            print(f"  [dedup] p{keep[0]} {key}: kept {keep[1]} (len={len(keep[3])}), dropped {len(tups)-1}")
        if total_dropped:
            print(f"  [dedup] total dropped: {total_dropped}")
    except ImportError as e:
        print(f"  [dedup] Error import: {e}")
    except Exception as e:
        import traceback
        print(f"  [dedup] Error: {e}")
        traceback.print_exc()

    doc.close()
    # Devolvemos (codes, text_fields). codes mantiene la forma antigua
    # para no romper compatibilidad.
    return list(results.values()), text_fields


def _extract_text_fields_from_doc(doc):
    """Extrae campos de texto de un fitz.Document ya abierto.

    Devuelve dict {page_num_1based: {from, to, seat, coach, name}}.
    Funcion auxiliar: separada para poder llamarla con un doc compartido.
    """
    fields_by_page = {}
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text()
        page_fields = {}

        # Origen (ciudad o estacion, texto corto)
        m = re.search(r"(?:Origen|Desde|Salida\s+de)\s*:?\s*\n?\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if not m:
            m = re.search(r"Origen\s*\n\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Filtrar falsos positivos: texto demasiado generico
            if not any(w in val.lower() for w in ('minutos','antes','salida','llegada','añadir','puedes','información','billete','tarjeta')):
                page_fields["from"] = val

        # Destino (ciudad o estacion, texto corto)
        m = re.search(r"(?:Destino|Hasta|Llegada\s+a)\s*:?\s*\n?\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if not m:
            m = re.search(r"Destino\s*\n\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not any(w in val.lower() for w in ('minutos','antes','salida','llegada','añadir','puedes','información','billete','tarjeta')):
                page_fields["to"] = val

        # Plaza / Asiento: patron de asiento real (digitos+letra, ej: "14A", "23B")
        m = re.search(r"(?:Plaza|Asiento|Coche)\s*:?\s*\n?\s*(\d{1,2}\s*[A-Z])", text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?:Plaza|Asiento)\s*:?\s*\n?\s*(\S+)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if len(val) <= 6 and not val.lower() in ('información','importante','billete'):
                page_fields["seat"] = val

        # Coche
        m = re.search(r"Coche:\s*\n?\s*(\S+)", text, re.IGNORECASE)
        if m:
            page_fields["coach"] = m.group(1).strip()

        # Fecha con año (formato DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD,
        # o DD MES YYYY como "06 DIC 2026" / "06 December 2026")
        date_match = re.search(
            r"(\d{2})[\s/-](\d{2}|[A-Za-z]{3,})[\s/-](\d{4})",
            text,
        )
        if date_match:
            d, m, y = date_match.group(1), date_match.group(2), date_match.group(3)
            # Si el mes es texto, convertir a número
            month_map = {
                "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05",
                "jun": "06", "jul": "07", "ago": "08", "sep": "09", "oct": "10",
                "nov": "11", "dic": "12",
                "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05",
                "jun": "06", "jul": "07", "aug": "08", "sep": "09", "oct": "10",
                "nov": "11", "dec": "12",
            }
            if m.lower()[:3] in month_map:
                m = month_map[m.lower()[:3]]
            try:
                from datetime import date as dt_date
                dt_date(int(y), int(m), int(d))
                page_fields["flight_date"] = f"{y}-{int(m):02d}-{int(d):02d}"
            except (ValueError, TypeError):
                pass

        # Nombre del pasajero (varios formatos segun operador)
        m = None
        # 1) Etiqueta + formato APELLIDO/NOMBRE o Nombre Apellido
        for pat in [
            r"(?:Pasajero|Titular|Nombre|Viajero|Viajero\s+General)\s*:?\s*\n?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s/]{3,40})",
            r"DNI\s*[óo]?\s*DOC\.?ID:?\s*\n\s*\*+\S+\s*\n\s*(\S+)",
            r"S(?:r|ra)\.\s+(\S[\S ]+)",
            # OUIGO: nombre en formato "Nombre Apellido" en linea propia
            r"\n([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\n",
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                break
        if m:
            val = m.group(1).strip()
            if '/' in val or (' ' in val and len(val) >= 6) or len(val) >= 4:
                # Evitar falsos positivos
                if not any(w in val.lower() for w in ('minutos','antes','salida','mascotas','olvides','equipaje','billete','ouigo')):
                    page_fields["name"] = val

        # OUIGO: origen/destino en formato "Ciudad - Estacion" (lineas propias)
        if not page_fields.get("from") or not page_fields.get("to"):
            ouigo_cities = re.findall(
                r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ - .+)$",
                text, re.MULTILINE,
            )
            real = [c.strip() for c in ouigo_cities if len(c.strip()) > 8]
            if len(real) >= 2:
                page_fields["from"] = real[0]
                page_fields["to"] = real[-1]

        # OUIGO: nombre (antes de "Viajero General")
        if not page_fields.get("name"):
            m = re.search(
                r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\s*\n\s*Viajero General",
                text,
            )
            if m:
                page_fields["name"] = m.group(1).strip()

        # OUIGO: tren (5 digitos tras la fecha)
        m = re.search(r"\d{2}\.\d{2}\.\d{4}\s*\n\s*(\d{5})", text)
        if m:
            page_fields["train"] = m.group(1)

        # OUIGO: coche (digito tras la hora)
        m = re.search(r"\d{2}:\d{2}\s*\n\s*(\d)\s*\n", text)
        if m:
            page_fields["coach"] = m.group(1)

        # OUIGO: fecha en formato DD.MM.YYYY
        if not page_fields.get("flight_date"):
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
            if m:
                d, mo, y = m.group(1), m.group(2), m.group(3)
                page_fields["flight_date"] = f"{y}-{mo}-{d}"

        # OUIGO: localizador (6 caracteres alfanumericos en linea propia)
        if not page_fields.get("pnr"):
            m = re.search(r"\n([A-Z0-9]{6})\n", text)
            if m and m.group(1) not in ('ALTURA','OUIGO','VENTA'):
                page_fields["pnr"] = m.group(1)

        # Hora de salida (varios formatos segun aerolinea)
        # Ryanair: "Departs", "Departure", "Salida"
        # Vueling: "Salida", "Hora", "Departure"
        # Iberia: "Salida", "Hora"
        time_patterns = [
            r"(?:Hora de salida|Hora salida|Salida|Departs|Departure|Hora)[:\s]*\n?\s*(\d{1,2}[:.]\d{2})",
            r"(?:Salida|Hora)[:\s]*\n?\s*(\d{1,2}[:.]\d{2})",
            r"(\d{1,2}[:.]\d{2})\s*(?:Hora de salida|Salida|Departs)",
        ]
        for pat in time_patterns:
            tm = re.search(pat, text, re.IGNORECASE)
            if tm:
                raw_time = tm.group(1).replace(".", ":")
                h, mn = raw_time.split(":")
                page_fields["flight_time"] = f"{int(h):02d}:{int(mn):02d}"
                break

        if page_fields:
            fields_by_page[page_num + 1] = page_fields

    return fields_by_page


def extract_text_fields(pdf_path):
    """Extrae campos de texto del PDF: origen, destino, plaza, coche, nombre.

    Util para Renfe/OUIGO que no llevan esos datos en el codigo de barras.
    Acepta una ruta de archivo o un objeto fitz.Document ya abierto.
    Devuelve un dict {page_num_1based: {from, to, seat, coach, name}}.
    """
    if isinstance(pdf_path, fitz.Document):
        return _extract_text_fields_from_doc(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        import sys as _sys
        print(f"[extract_text_fields] Error abriendo PDF: {e}", file=_sys.stderr, flush=True)
        return {}
    result = _extract_text_fields_from_doc(doc)
    doc.close()
    return result


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
