"""
Parser de los datos decodificados de las tarjetas de embarque / billetes.

Formatos soportados:
  - IATA BCBP (M1 = 1 trayecto, M2 = multiples). Usado por Vueling, Iberia,
    Ryanair, AA, Lufthansa, etc.
  - Renfe / OUIGO (formato propietario Renfe). Extrae fecha, hora, tren,
    clase y localizador.

Devuelve un dict con campos normalizados. Si no reconoce el formato, devuelve
el texto crudo en `raw` para mostrar tal cual.
"""

import re
from datetime import date, timedelta


def _doy_to_date(year, doy):
    try:
        return date(year, 1, 1) + timedelta(days=int(doy) - 1)
    except (ValueError, TypeError):
        return None


# --- IATA BCBP ---------------------------------------------------------------
#
# Layout fijo (IATA Resolution 792) tras M1/M2:
#   0-1     : "M1" / "M2"
#   2-21    : nombre pasajero (20 chars, right-padded)
#   22      : electronic ticket indicator (E o espacio)
#   23-29   : PNR (7 chars, right-padded)
#   30-32   : aeropuerto origen
#   33-35   : aeropuerto destino
#   36-38   : aerolinea (3 chars, right-padded, p.ej. "VY " para VY)
#   39-43   : vuelo (5 chars, right-padded, p.ej. " 2225")
#   44-46   : dia del ano (3 chars)
#   47      : clase
#   48-51   : asiento (4 chars, p.ej. "024C")
#   52-55   : secuencia check-in (4 chars)
#   56+     : datos variables
#
# No hay separadores entre los campos: es un layout empaquetado.
# Por eso mejor parsear por posicion fija que por regex.

def _parse_iata_bcbp(text, year=None):
    if len(text) < 56:
        return None
    if text[0] != "M" or text[1] not in "12":
        return None
    name = text[2:22].strip()
    if not name or "/" not in name:
        # Un BCBP valido siempre tiene nombre con formato APELLIDO/NOMBRE
        return None
    pnr = text[23:30].strip()
    from_ = text[30:33]
    to = text[33:36]
    airline = text[36:39].strip()
    flight = text[39:44].strip().lstrip("0") or text[39:44].strip()
    doy_str = text[44:47]
    clas = text[47]
    seat = text[48:52].strip()
    chkseq = text[52:56].strip()

    if not doy_str.isdigit():
        return None
    flight_date = _doy_to_date(year or date.today().year, int(doy_str))

    # Intentar extraer hora de salida de la seccion de datos variables (pos 56+)
    # Algunas aerolineas incluyen el campo condicional "14" (Departure Time).
    # Formatos posibles en variable data:
    #   - "14HHMM"        (6 chars: campo 14 + 4 digitos HHMM)
    #   - "1404HHMM"      (8 chars: campo 14 + len 04 + 4 digitos)
    #   - "+HHMM" o " HH:MM" en Ryanair (no incluido, pero otras lo hacen)
    flight_time = None
    var_data = text[56:]
    # Buscar campo IATA "14" seguido de HHMM
    m = re.search(r"14\d{2}(\d{2})(\d{2})", var_data)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            flight_time = f"{hh:02d}:{mm:02d}"
    # Fallback: buscar cualquier HH:MM o HHMM en datos variables
    if not flight_time:
        m = re.search(r"(\d{2}):(\d{2})", var_data)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                flight_time = f"{hh:02d}:{mm:02d}"
    if not flight_time:
        m = re.search(r"\b([01]\d|2[0-3])([0-5]\d)\b", var_data)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            flight_time = f"{hh:02d}:{mm:02d}"

    return {
        "format": "IATA_BCBP",
        "kind": "flight",
        "name": name,
        "pnr": pnr,
        "from": from_,
        "to": to,
        "airline": airline,
        "flight": flight,
        "flight_date": flight_date.isoformat() if flight_date else None,
        "flight_time": flight_time,
        "class": clas,
        "seat": seat,
        "check_in_seq": chkseq,
        "raw": text,
        "has_explicit_year": False,
        "doy": doy_str,
    }


# --- Renfe / OUIGO (formato propietario) ------------------------------------
#
# No esta estandarizado. Lo que SI hemos confirmado en los PDFs:
#   - Aztec: "DD/MM/YYYY" + "HH:MM" + tren + clase + localizador
#   - QR:    "MMDD" + "HHMM" pegados + tren + clase + localizador
#   - Localizador: 6-10 chars alfanum (puede acabar en ".." o padding de 0s)
#
# Renfe: 6 digitos tren + 1 letra clase + 6-10 alnum localizador
# OUIGO: 6 digitos tren + 1 letra clase + el localizador esta a veces
#         cifrado en base64 dentro del mismo bloque.

_RENFE_DATE_SLASH_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")  # DD/MM/YYYY
_RENFE_TIME_RE = re.compile(r"(\d{2}):(\d{2})")                  # HH:MM
# MMDD + HHMM pegados (formato QR Renfe, p.ej. "07260831" = 26-jul 08:31).
# Sin lookbehind/lookahead porque los digitos van pegados a otros en el bloque.
_RENFE_DATE_COMPACT_RE = re.compile(r"([01]\d)([0-3]\d)(\d{2})(\d{2})")
_RENFE_TRAIN_RE = re.compile(
    r"(?P<train>\d{5,6})"
    r"(?P<clas>[A-Z])"
    r"(?P<loc>[A-Z0-9.=]{6,12})"
)


def _parse_renfe(text):
    flight_date = None
    flight_time = None

    # 1) Intentar formato con slashes (Aztec, ticket completo)
    date_match = _RENFE_DATE_SLASH_RE.search(text)
    if date_match:
        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        try:
            flight_date = date(y, m, d).isoformat()
        except ValueError:
            pass

    time_match = _RENFE_TIME_RE.search(text)
    if time_match:
        h, mn = int(time_match.group(1)), int(time_match.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            flight_time = f"{h:02d}:{mn:02d}"

    # 2) Si no habia fecha con slashes, buscar formato MMDD y HHMM.
    #    En el QR compacto de Renfe la fecha puede estar embebida en una
    #    cadena de digitos mas larga (ej: "00004 0726 0831 200111").
    #    Tomamos el ULTIMO candidato valido cerca del localizador.
    if flight_date is None or flight_time is None:
        # Primero intentamos MMDDHHMM seguido (8 digitos exactos)
        for compact in reversed(list(_RENFE_DATE_COMPACT_RE.finditer(text))):
            mm, dd, hh, mn = (
                int(compact.group(1)),
                int(compact.group(2)),
                int(compact.group(3)),
                int(compact.group(4)),
            )
            if 1 <= mm <= 12 and 1 <= dd <= 31 and 0 <= hh <= 23 and 0 <= mn <= 59:
                if flight_date is None:
                    try:
                        flight_date = date(date.today().year, mm, dd).isoformat()
                    except ValueError:
                        pass
                if flight_time is None:
                    flight_time = f"{hh:02d}:{mn:02d}"
                break

        # Si no se encontro, buscar MMDD y HHMM por separado (sin lookbehind)
        if flight_date is None or flight_time is None:
            mmdd_candidates = []
            for m in re.finditer(r"([01]\d)([0-3]\d)", text):
                mm, dd = int(m.group(1)), int(m.group(2))
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    mmdd_candidates.append((m.start(), mm, dd))

            for _, mm, dd in reversed(mmdd_candidates):
                if flight_date is None:
                    try:
                        flight_date = date(date.today().year, mm, dd).isoformat()
                    except ValueError:
                        pass
                    break

            if flight_time is None:
                # Buscar HHMM cerca del MMDD encontrado
                for pos, mm, dd in mmdd_candidates:
                    # Buscar HHMM en los siguientes 8 digitos
                    window = text[pos+4:pos+20] if pos+4 < len(text) else ""
                    hmm_match = re.search(r"(\d{2})(\d{2})", window)
                    if hmm_match:
                        hh, mn = int(hmm_match.group(1)), int(hmm_match.group(2))
                        if 0 <= hh <= 23 and 0 <= mn <= 59:
                            flight_time = f"{hh:02d}:{mn:02d}"
                            break

    # 3) Tren + clase + localizador. Cogemos el ULTIMO match (los registros
    #    Aztecs concatenan padding "CNO0000000000..." que no es el localizador
    #    real; el real viene al final).
    train_matches = list(_RENFE_TRAIN_RE.finditer(text))
    if not train_matches:
        return None
    train_match = train_matches[-1]

    # Limpiar ceros de padding al final del localizador
    pnr = train_match["loc"].rstrip("0").rstrip(".")

    # Rechazar PNRs claramente invalidos
    if len(pnr) < 4 or pnr.upper() in ("NO", "SI", "CNO", "ANO", "BNO", "DNO"):
        pnr = ""

    # Validacion: sin fecha ni localizador util, el pase es inutil -> descartar
    if not pnr or not flight_date:
        return None

    return {
        "format": "RENFE",
        "kind": "train",
        "name": None,
        "pnr": pnr,
        "train": train_match["train"],
        "flight_date": flight_date,
        "flight_time": flight_time,
        "class": train_match["clas"],
        "seat": None,
        "raw": text,
        "has_explicit_year": True,
    }


# --- Year inference ---------------------------------------------------------
# Para billetes sin año explicito (IATA BCBP: solo dia del año),
# inferimos el año minimizando el lapso entre vuelos consecutivos.
# Ej: 31-Dic (DOY=365) + 3-Ene (DOY=3) → 2026 y 2027 (gap de 3 días).

def infer_years(passes: list[dict]) -> None:
    """Infiere años para vuelos sin año explícito minimizando el lapso.

    Agrupa por (pnr, kind), mantiene orden original de páginas,
    detecta cruce de año cuando DOY decrece (ej: DOY=365 → DOY=3).
    Modifica los pases in-place.
    """
    groups: dict[tuple, list[dict]] = {}
    for p in passes:
        if p.get("has_explicit_year", True):
            continue
        key = (p.get("pnr"), p.get("kind"))
        groups.setdefault(key, []).append(p)

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        base_year = date.today().year
        prev_doy = int(group[0].get("doy", 0))

        for p in group:
            doy = int(p.get("doy", 0))
            if prev_doy > 180 and doy < prev_doy and doy < 180:
                base_year += 1
            try:
                corrected = date(base_year, 1, 1) + timedelta(days=doy - 1)
                p["flight_date"] = corrected.isoformat()
            except (ValueError, TypeError):
                pass
            prev_doy = doy


# --- Dispatcher -------------------------------------------------------------

def _has_essential_data(parsed):
    """Comprueba que un pase tiene los datos minimos para ser util.
    Descarta pases sin fecha o sin localizador/codigo de vuelo."""
    fmt = parsed.get("format")
    if fmt in ("URL", "EMPTY", "UNKNOWN"):
        return False
    if not parsed.get("flight_date"):
        return False
    if fmt == "IATA_BCBP":
        if not parsed.get("airline") or not parsed.get("flight"):
            return False
    if fmt == "RENFE":
        if not parsed.get("pnr") or not parsed.get("train"):
            return False
    return True


def parse_code(text, year=None):
    """Detecta el formato y devuelve dict con campos normalizados.
    Devuelve None si el pase no tiene los datos esenciales (fecha, codigo, etc.)
    para que sea descartado por el caller."""
    if not text or not text.strip():
        return None

    text = text.strip()

    # URLs de publicidad -> descartar (no son billetes)
    if text.lower().startswith(("http://", "https://")):
        return None

    result = None

    # IATA BCBP
    if text.startswith("M1") or text.startswith("M2"):
        result = _parse_iata_bcbp(text, year=year)

    # Renfe / OUIGO / Iryo etc.
    if result is None and len(text) > 30 and _RENFE_TRAIN_RE.search(text):
        result = _parse_renfe(text)

    if result is None:
        return None

    # Validacion final: descartar si faltan datos esenciales
    if not _has_essential_data(result):
        return None

    return result
