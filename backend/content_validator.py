"""Content validation for AI-generated itineraries and quizzes.

Second-check layer that verifies coherence, consistency, hallucinations,
repetitions, and AI-phrasing patterns before serving the response.
"""

import re
from typing import Any


_VALID_CITIES = {
    "Madrid", "Barcelona", "Londres", "París", "Roma", "Ámsterdam",
    "Milán", "Venecia", "Nápoles", "Lisboa", "Oporto", "Faro",
    "Sevilla", "Bilbao", "Valencia", "Alicante", "Palma de Mallorca",
    "Málaga", "San Sebastián", "Santiago de Compostela", "Granada",
    "Zaragoza", "Almería", "Murcia", "Ciudad de México", "Buenos Aires",
    "São Paulo", "Bogotá", "Quito", "Lima", "La Paz",
}

_VALID_AIRPORTS = {
    "MAD", "BCN", "LHR", "ORY", "CDG", "AMS", "FCO", "PMI", "AGP", "SVQ",
    "BIO", "VLC", "ALC", "IBZ", "TFN", "LPA", "TFS", "EAS", "SCQ", "VGO",
    "SDR", "ZAZ", "GRX", "XRY", "LEI", "BRU", "FRA", "MUC", "BER", "MXP",
    "LIN", "VCE", "NAP", "LIS", "OPO", "FAO", "ATH", "VIE", "PRG", "BUD",
    "WAW", "CPH", "OSL", "ARN", "HEL", "IST", "DXB", "AUH", "JFK", "EWR",
    "MIA", "LAX", "MEX", "BOG", "EZE", "GRU", "NRT", "HND", "SIN", "BKK",
    "DOH",
}

_VALID_PRICES = {"€", "€€", "€€€", "€€€€"}

_AI_PHRASING_PATTERNS = [
    re.compile(r"como (agente|modelo|asistente) de (viajes|IA|inteligencia artificial)", re.I),
    re.compile(r"según (mis|nuestros) (datos|registros|conocimientos)", re.I),
    re.compile(r"(espero que|esperamos que) (disfrutes|disfruten)", re.I),
    re.compile(r"(no dudes|no duden) en (consultar|preguntar)", re.I),
    re.compile(r"¡?(buen viaje|feliz viaje|disfruta tu estancia)!?", re.I),
    re.compile(r"basado en (mi|nuestra) (experiencia|base de datos)", re.I),
    re.compile(r"ten en cuenta que (soy|somos) (un|una)", re.I),
    re.compile(r"como (agente|modelo) (de lenguaje|LLM|IA)", re.I),
    re.compile(r"(recuerda|recuerden) (siempre|llevar|traer|consultar)", re.I),
    re.compile(r"(aquí|aquí tienes|te presento) (tu|el) (itinerario|plan|guía)", re.I),
    re.compile(r"(por favor|por favor,) (ten en cuenta|recuerda|consulta)", re.I),
    re.compile(r"gracias por (confiar|elegir|usar)", re.I),
    re.compile(r"estoy aquí para (ayudarte|servirte|asistirte)", re.I),
]

_DATE_PATTERNS = [re.compile(r"^\d{4}-\d{2}-\d{2}$"), re.compile(r"^\d{2}/\d{2}(?:/\d{4})?$")]

_SUSPICIOUS_WORD_PATTERNS = [
    re.compile(p, re.I) for p in [r"\bfake\b", r"\btest\b", r"\bdemo\b", r"\bdummy\b", r"\btemp\b", r"\bsample\b"]
]

_LONG_WORD_PATTERN = re.compile(r"\b[A-Za-z]{35,}\b")
_RANDOM_CHARS_PATTERN = re.compile(r"[¢§¶•ªº][¢§¶•ªº]{2,}")
_URL_PATTERN = re.compile(r"https?://|www\.|ftp://", re.I)


def _fresh() -> dict[str, Any]:
    return {"is_valid": True, "errors": [], "warnings": []}


def _normalize(s: Any) -> str:
    return (s or "").strip()


def _capitalize(s: str) -> str:
    if not s:
        return s
    return s[0].upper() + s[1:].lower()


# ===========================================================================
# Itinerary validation
# ===========================================================================


def validate_itinerary(itinerary: dict[str, Any] | None) -> dict[str, Any]:
    r = _fresh()
    if not itinerary:
        r["is_valid"] = False
        r["errors"].append("Itinerario no puede estar vacío")
        return r
    _validate_structure(itinerary, r)
    _validate_daily_itinerary(itinerary.get("daily_itinerary", []), r)
    _validate_places(itinerary, r)
    _validate_coherence(itinerary, r)
    _detect_hallucinations(itinerary, r)
    _detect_repetitions(itinerary, r)
    _detect_ai_phrasing(itinerary, r)
    return r


def _validate_structure(itinerary: dict, r: dict):
    required = {"destination_overview": "string", "daily_itinerary": "list"}
    for field, expected_type in required.items():
        if field not in itinerary:
            r["is_valid"] = False
            r["errors"].append(f"Campo requerido faltante: '{field}'")
        elif expected_type == "list" and not isinstance(itinerary.get(field), list):
            r["is_valid"] = False
            r["errors"].append(f"Campo '{field}' debe ser de tipo list")
        elif expected_type == "string" and not isinstance(itinerary.get(field), str):
            r["is_valid"] = False
            r["errors"].append(f"Campo '{field}' debe ser de tipo string")


def _validate_daily_itinerary(days: list, r: dict):
    if not isinstance(days, list) or not days:
        r["is_valid"] = False
        r["errors"].append("El itinerario diario no puede estar vacío")
        return
    for i, day in enumerate(days):
        _validate_single_day(day, i, r)


def _validate_single_day(day: dict, idx: int, r: dict):
    required = [
        ("day_number", "number"),
        ("date", "string"),
        ("city", "string"),
        ("theme", "string"),
        ("morning", "object"),
        ("afternoon", "object"),
        ("evening", "object"),
        ("travel_reminders", "object"),
        ("meal_suggestions", "object"),
    ]
    for field, ftype in required:
        if field not in day:
            r["is_valid"] = False
            r["errors"].append(f"Día {idx + 1}: falta campo '{field}'")
        elif ftype == "object" and (not isinstance(day.get(field), dict) or day.get(field) is None):
            r["is_valid"] = False
            r["errors"].append(f"Día {idx + 1}: '{field}' debe ser un objeto")
        elif ftype == "number" and not isinstance(day.get(field), int):
            r["is_valid"] = False
            r["errors"].append(f"Día {idx + 1}: '{field}' debe ser tipo number")
        elif ftype == "string" and not isinstance(day.get(field), str):
            r["is_valid"] = False
            r["errors"].append(f"Día {idx + 1}: '{field}' debe ser tipo string")
    for slot_name in ("morning", "afternoon", "evening"):
        _validate_slot(day.get(slot_name), slot_name, idx, r)
    _validate_date(day.get("date", ""), f"Día {idx + 1}", r)


def _validate_slot(slot: Any, name: str, day_idx: int, r: dict):
    if not isinstance(slot, dict):
        r["is_valid"] = False
        r["errors"].append(f"Día {day_idx + 1}, {name}: debe ser un objeto")
        return
    if not isinstance(slot.get("activities"), list):
        r["warnings"].append(f"Día {day_idx + 1}, {name}: falta 'activities' (list)")
    if not isinstance(slot.get("description"), str) or not _normalize(slot.get("description")):
        r["warnings"].append(f"Día {day_idx + 1}, {name}: falta 'description'")


def _validate_places(itinerary: dict, r: dict):
    _validate_place_list(itinerary.get("hotels", []), "hotel",
                         ["name", "zone", "description", "price_range", "highlights"], r)
    _validate_place_list(itinerary.get("restaurants", []), "restaurant",
                         ["name", "type", "description", "price_range"], r)
    _validate_place_list(itinerary.get("places_of_interest", []), "place_of_interest",
                         ["name", "type", "description", "tips"], r)
    _validate_place_list(itinerary.get("historical_sites", []), "historical_site",
                         ["name", "period", "description", "curiosity"], r)


def _validate_place_list(items: list, ptype: str, required_fields: list[str], r: dict):
    for i, entry in enumerate(items):
        if not isinstance(entry, dict):
            r["is_valid"] = False
            r["errors"].append(f"{ptype}[{i}]: debe ser un objeto")
            continue
        for field in required_fields:
            if field not in entry:
                r["is_valid"] = False
                r["errors"].append(f"{ptype}[{i}]: falta '{field}'")
            elif isinstance(entry.get(field), list):
                if not entry[field]:
                    r["warnings"].append(f"{ptype}[{i}].{field}: lista vacía")
                continue
            elif not isinstance(entry.get(field), str) or not _normalize(entry.get(field)):
                r["is_valid"] = False
                r["errors"].append(f"{ptype}[{i}]: '{field}' debe ser string no vacío")
        price = entry.get("price_range")
        if isinstance(price, str) and price not in _VALID_PRICES:
            r["warnings"].append(f"{ptype}[{i}].price_range: '{price}' no es estándar (usar €/€€/€€€/€€€€)")


# ===========================================================================
# Coherence
# ===========================================================================


def _validate_coherence(itinerary: dict, r: dict):
    days = itinerary.get("daily_itinerary", [])
    _validate_day_sequence(days, r)
    _validate_city_coherence(days, r)
    _validate_slot_coherence(days, r)


def _validate_day_sequence(days: list, r: dict):
    for i, day in enumerate(days):
        if day.get("day_number") != i + 1:
            r["is_valid"] = False
            r["errors"].append(f"Día {i + 1}: day_number={day.get('day_number')}, esperado {i + 1}")


def _validate_city_coherence(days: list, r: dict):
    seen: set[str] = set()
    for day in days:
        raw = _normalize(day.get("city", ""))
        if not raw:
            continue
        city = _capitalize(raw)
        if city and city not in _VALID_CITIES:
            r["warnings"].append(f"Ciudad '{city}' no está en la lista de ciudades conocidas — ¿posible alucinación?")
        if city in seen:
            r["warnings"].append(f"Ciudad '{city}' repetida en varios días")
        else:
            seen.add(city)


def _validate_slot_coherence(days: list, r: dict):
    for day in days:
        m = (day.get("morning") or {}).get("description", "")
        a = (day.get("afternoon") or {}).get("description", "")
        e = (day.get("evening") or {}).get("description", "")
        if m and a and m == a:
            r["warnings"].append(f"Día {day.get('day_number')}: descripción mañana === tarde")
        if a and e and a == e:
            r["warnings"].append(f"Día {day.get('day_number')}: descripción tarde === noche")
        if m and e and m == e:
            r["warnings"].append(f"Día {day.get('day_number')}: descripción mañana === noche")


# ===========================================================================
# Hallucinations
# ===========================================================================


def _detect_hallucinations(itinerary: dict, r: dict):
    _detect_suspicious_places(itinerary, r)
    _detect_url_in_content(itinerary, "root", r)
    _detect_suspicious_text(itinerary, r)
    _validate_price_format(itinerary, r)
    _validate_text_lengths(itinerary, r)


def _detect_suspicious_places(itinerary: dict, r: dict):
    fields = ["name", "zone", "description", "theme", "period", "curiosity"]

    def check(entry: Any, label_type: str, i: int):
        if not isinstance(entry, dict):
            return
        for f in fields:
            val = entry.get(f)
            if not isinstance(val, str):
                continue
            for pat in _SUSPICIOUS_WORD_PATTERNS:
                if pat.search(val):
                    r["warnings"].append(f"{label_type}[{i}].{f}: texto sospechoso ('{val[:40]}')")
                    break

    for i, h in enumerate(itinerary.get("hotels", [])):
        check(h, "hotel", i)
    for i, rest in enumerate(itinerary.get("restaurants", [])):
        check(rest, "restaurant", i)
    for i, poi in enumerate(itinerary.get("places_of_interest", [])):
        check(poi, "place_of_interest", i)
    for i, hs in enumerate(itinerary.get("historical_sites", [])):
        check(hs, "historical_site", i)
    for i, d in enumerate(itinerary.get("daily_itinerary", [])):
        check(d, "daily_itinerary", i)


def _detect_url_in_content(obj: Any, path: str, r: dict):
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _detect_url_in_content(item, f"{path}[{i}]", r)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _detect_url_in_content(v, f"{path}.{k}", r)
    elif isinstance(obj, str):
        if _URL_PATTERN.search(obj):
            r["warnings"].append(f"{path}: contiene URL ('{obj[:60]}')")


def _detect_suspicious_text(itinerary: dict, r: dict):
    def check(text: str, label: str):
        if _LONG_WORD_PATTERN.search(text):
            r["warnings"].append(f"{label}: palabra excesivamente larga — posible alucinación")
        if _RANDOM_CHARS_PATTERN.search(text):
            r["warnings"].append(f"{label}: caracteres aleatorios — posible alucinación")

    for d in itinerary.get("daily_itinerary", []):
        check(d.get("theme", ""), f"Día {d.get('day_number')} theme")
    for i, h in enumerate(itinerary.get("hotels", [])):
        check(h.get("description", ""), f"hotel[{i}] description")
    for i, rest in enumerate(itinerary.get("restaurants", [])):
        check(rest.get("description", ""), f"restaurant[{i}] description")


def _validate_price_format(itinerary: dict, r: dict):
    for i, h in enumerate(itinerary.get("hotels", [])):
        pr = h.get("price_range")
        if pr and pr not in _VALID_PRICES:
            r["warnings"].append(f"hotel[{i}].price_range: '{pr}' inválido")
    for i, rest in enumerate(itinerary.get("restaurants", [])):
        pr = rest.get("price_range")
        if pr and pr not in _VALID_PRICES:
            r["warnings"].append(f"restaurant[{i}].price_range: '{pr}' inválido")


def _validate_text_lengths(itinerary: dict, r: dict):
    MAX_DESC = 200
    MAX_THEME = 50
    for i, h in enumerate(itinerary.get("hotels", [])):
        desc = h.get("description", "") or ""
        if len(desc) > MAX_DESC:
            r["warnings"].append(f"hotel[{i}].description muy largo ({len(desc)} chars)")
    for i, rest in enumerate(itinerary.get("restaurants", [])):
        desc = rest.get("description", "") or ""
        if len(desc) > MAX_DESC:
            r["warnings"].append(f"restaurant[{i}].description muy largo ({len(desc)} chars)")
    for i, d in enumerate(itinerary.get("daily_itinerary", [])):
        theme = d.get("theme", "") or ""
        if len(theme) > MAX_THEME:
            r["warnings"].append(f"daily_itinerary[{i}].theme muy largo ({len(theme)} chars)")


# ===========================================================================
# Repetitions
# ===========================================================================


def _detect_repetitions(itinerary: dict, r: dict):
    _detect_duplicate_names(itinerary, r)
    _detect_duplicate_descriptions(itinerary, r)
    _detect_similar_days(itinerary, r)


def _detect_duplicate_names(itinerary: dict, r: dict):
    def extract(items: list, ptype: str):
        seen: dict[str, int] = {}
        for i, item in enumerate(items):
            name = _normalize(item.get("name", ""))
            if not name:
                continue
            key = name.lower()
            if key in seen:
                r["warnings"].append(f"{ptype}: nombre duplicado '{name}' (índices {seen[key]} y {i})")
            else:
                seen[key] = i

    extract(itinerary.get("hotels", []), "hotel")
    extract(itinerary.get("restaurants", []), "restaurant")
    extract(itinerary.get("places_of_interest", []), "place_of_interest")
    extract(itinerary.get("historical_sites", []), "historical_site")


def _detect_duplicate_descriptions(itinerary: dict, r: dict):
    def extract(items: list, ptype: str):
        seen: dict[str, int] = {}
        for i, item in enumerate(items):
            desc = _normalize(item.get("description", ""))
            if not desc:
                continue
            key = desc.lower()
            if key in seen:
                r["warnings"].append(f"{ptype}: descripción duplicada (índices {seen[key]} y {i})")
            else:
                seen[key] = i

    extract(itinerary.get("hotels", []), "hotel")
    extract(itinerary.get("restaurants", []), "restaurant")
    extract(itinerary.get("places_of_interest", []), "place_of_interest")
    extract(itinerary.get("historical_sites", []), "historical_site")


def _detect_similar_days(itinerary: dict, r: dict):
    days = itinerary.get("daily_itinerary", [])
    for i in range(len(days)):
        for j in range(i + 1, len(days)):
            a = days[i]
            b = days[j]
            if (
                (a.get("morning") or {}).get("description") == (b.get("morning") or {}).get("description")
                and (a.get("afternoon") or {}).get("description") == (b.get("afternoon") or {}).get("description")
                and (a.get("evening") or {}).get("description") == (b.get("evening") or {}).get("description")
            ):
                r["warnings"].append(
                    f"Día {a.get('day_number')} y {b.get('day_number')}: "
                    "patrones idénticos — ¿contenido generado automáticamente?"
                )

    theme_count: dict[str, int] = {}
    for d in days:
        t = _normalize(d.get("theme", "")).lower()
        if t:
            theme_count[t] = theme_count.get(t, 0) + 1
    for theme, count in theme_count.items():
        if count >= 3:
            r["warnings"].append(f"Tema '{theme}' repetido {count} veces en el itinerario")


# ===========================================================================
# AI phrasing detection
# ===========================================================================


def _detect_ai_phrasing(itinerary: dict, r: dict):
    def check_text(text: str, label: str):
        if not text:
            return
        for pat in _AI_PHRASING_PATTERNS:
            if pat.search(text):
                r["warnings"].append(f"{label}: posible frase de IA ('{text[:50]}…')")
                break

    check_text(itinerary.get("destination_overview", ""), "destination_overview")
    check_text(itinerary.get("weather_summary", ""), "weather_summary")
    for d in itinerary.get("daily_itinerary", []):
        check_text(d.get("theme", ""), f"Día {d.get('day_number')} theme")
    for i, h in enumerate(itinerary.get("hotels", [])):
        check_text(h.get("description", ""), f"hotel[{i}]")
    for i, rest in enumerate(itinerary.get("restaurants", [])):
        check_text(rest.get("description", ""), f"restaurant[{i}]")
    for i, poi in enumerate(itinerary.get("places_of_interest", [])):
        check_text(poi.get("description", ""), f"place_of_interest[{i}]")
    for i, hs in enumerate(itinerary.get("historical_sites", [])):
        check_text(hs.get("description", ""), f"historical_site[{i}]")
    for i, tip in enumerate(itinerary.get("transport_tips", [])):
        check_text(tip, f"transport_tip[{i}]")
    for i, tip in enumerate(itinerary.get("general_tips", [])):
        check_text(tip, f"general_tip[{i}]")
    for i, note in enumerate(itinerary.get("cultural_notes", [])):
        check_text(note, f"cultural_note[{i}]")


# ===========================================================================
# Date validation
# ===========================================================================


def _validate_date(date_str: str, ctx: str, r: dict):
    if not date_str:
        return
    valid = any(p.search(date_str) for p in _DATE_PATTERNS)
    if not valid:
        r["warnings"].append(f"{ctx}: formato de fecha no estándar ('{date_str}')")
    if valid and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        from datetime import date as dt  # noqa: PLC0415
        try:
            dt.fromisoformat(date_str)
        except (ValueError, TypeError):
            r["is_valid"] = False
            r["errors"].append(f"{ctx}: fecha inválida '{date_str}'")


# ===========================================================================
# Quiz validation
# ===========================================================================


def validate_quiz(questions: list[dict] | None) -> dict[str, Any]:
    r = _fresh()
    if not questions:
        r["is_valid"] = False
        r["errors"].append("Las preguntas del cuestionario no pueden estar vacías")
        return r
    if len(questions) < 8:
        r["warnings"].append(f"El cuestionario tiene {len(questions)} preguntas (recomendado mínimo 8)")
    for i, q in enumerate(questions):
        _validate_quiz_question(q, i, r)
    _detect_quiz_repetitions(questions, r)
    _detect_quiz_ai_phrasing(questions, r)
    return r


def _validate_quiz_question(q: dict, idx: int, r: dict):
    if not q:
        r["is_valid"] = False
        r["errors"].append(f"Pregunta {idx}: no puede estar vacía")
        return
    if not isinstance(q.get("question"), str) or not _normalize(q.get("question")):
        r["is_valid"] = False
        r["errors"].append(f"Pregunta {idx}: texto inválido")
    opts = q.get("options")
    if not isinstance(opts, list) or len(opts) != 3:
        r["is_valid"] = False
        r["errors"].append(f"Pregunta {idx}: debe tener exactamente 3 opciones")
    else:
        for oi, opt in enumerate(opts):
            if not isinstance(opt, str) or not _normalize(opt):
                r["is_valid"] = False
                r["errors"].append(f"Pregunta {idx}, opción {oi}: vacía o inválida")
        ci = q.get("correct_index")
        if not isinstance(ci, int) or ci < 0 or ci > 2:
            r["is_valid"] = False
            r["errors"].append(f"Pregunta {idx}: correct_index={ci} fuera de rango [0,2]")


def _detect_quiz_repetitions(questions: list[dict], r: dict):
    seen_questions: dict[str, int] = {}
    for i, q in enumerate(questions):
        key = _normalize(q.get("question", "")).lower()
        if not key:
            continue
        if key in seen_questions:
            r["warnings"].append(
                f"Quiz: pregunta duplicada (índices {seen_questions[key]} y {i}): "
                f"'{q.get('question', '')[:60]}'"
            )
        else:
            seen_questions[key] = i

    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            opts_i = set(o.lower().strip() for o in questions[i].get("options", []))
            opts_j = set(o.lower().strip() for o in questions[j].get("options", []))
            common = len(opts_i & opts_j)
            if common >= 3:
                r["warnings"].append(f"Quiz: pregunta {i} y {j} comparten todas las opciones")
            elif common >= 2:
                r["warnings"].append(f"Quiz: pregunta {i} y {j} comparten {common}/3 opciones")


def _detect_quiz_ai_phrasing(questions: list[dict], r: dict):
    for i, q in enumerate(questions):
        options_text = " ".join(q.get("options", []))
        text = f"{q.get('question', '')} {options_text}"
        for pat in _AI_PHRASING_PATTERNS:
            if pat.search(text):
                r["warnings"].append(f"Quiz pregunta {i}: posible frase de IA")
                break
