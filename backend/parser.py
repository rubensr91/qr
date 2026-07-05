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
        "class": clas,
        "seat": seat,
        "check_in_seq": chkseq,
        "raw": text,
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

    # 2) Si no habia fecha con slashes, buscar formato compacto MMDDHHMM (QR).
    #    Cojemos el ULTIMO match valido: en tickets reales el bloque MMDDHHMM
    #    viene al final, los anteriores suelen ser ruido dentro del bloque
    #    de digitos del ticket.
    if flight_date is None or flight_time is None:
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

    # 3) Tren + clase + localizador. Cogemos el ULTIMO match (los registros
    #    Aztecs concatenan padding "CNO0000000000..." que no es el localizador
    #    real; el real viene al final).
    train_matches = list(_RENFE_TRAIN_RE.finditer(text))
    if not train_matches:
        return None
    train_match = train_matches[-1]

    # Limpiar ceros de padding al final del localizador
    pnr = train_match["loc"].rstrip("0").rstrip(".")

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
    }


# --- Dispatcher -------------------------------------------------------------

def parse_code(text, year=None):
    """Detecta el formato y devuelve dict con campos normalizados.
    Si no reconoce nada, devuelve un dict minimo con solo `raw`."""
    if not text or not text.strip():
        return {"format": "EMPTY", "raw": text or ""}

    text = text.strip()

    # URLs de publicidad -> "ad" para que el cliente las pueda ocultar.
    if text.lower().startswith(("http://", "https://")):
        return {"format": "URL", "kind": "advertising", "raw": text}

    # IATA BCBP
    if text.startswith("M1") or text.startswith("M2"):
        result = _parse_iata_bcbp(text, year=year)
        if result:
            return result

    # Renfe / OUIGO / Iryo etc. -> si tiene un tren de 5-6 digitos + clase
    # + localizador, es muy probablemente un ticket de tren. No exigimos
    # fecha porque el formato QR no la lleva con slashes.
    if len(text) > 30 and _RENFE_TRAIN_RE.search(text):
        result = _parse_renfe(text)
        if result:
            return result

    return {"format": "UNKNOWN", "raw": text}
