"""
Modulo de generacion de itinerarios de viaje usando DeepSeek LLM y Open-Meteo.

DeepSeek: recomendaciones personalizadas (restaurantes, hoteles, lugares, historia, tips).
Open-Meteo: prediccion meteorologica gratuita sin API key.
"""

import json
from datetime import datetime, date

import httpx
from openai import OpenAI

# --- Configuracion ---

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _format_short_date(date_str: str) -> str:
    """Convierte '2026-12-06' -> '06/12' para nombres de viaje compactos."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m")
    except (ValueError, TypeError):
        return date_str

# Coordenadas de aeropuertos/ciudades comunes para el clima
CITY_COORDS: dict[str, tuple[float, float]] = {
    "MAD": (40.4168, -3.7038), "BCN": (41.3874, 2.1686),
    "LHR": (51.4700, -0.4543), "ORY": (48.7239, 2.3795),
    "CDG": (49.0097, 2.5479), "AMS": (52.3105, 4.7683),
    "FCO": (41.8003, 12.2389), "PMI": (39.5517, 2.7382),
    "AGP": (36.6749, -4.4991), "SVQ": (37.3891, -5.9845),
    "BIO": (43.3011, -2.9103), "VLC": (39.4893, -0.4816),
    "ALC": (38.2824, -0.5582), "IBZ": (38.9067, 1.4206),
    "TFN": (28.4826, -16.3197), "LPA": (27.9388, -15.3866),
    "TFS": (28.0444, -16.5725), "EAS": (43.3566, -1.7906),
    "SCQ": (42.8984, -8.4153), "VGO": (42.2346, -8.6262),
    "SDR": (43.4271, -3.8206), "ZAZ": (41.6662, -1.0419),
    "GRX": (37.1887, -3.7767), "XRY": (36.7441, -6.0605),
    "LEI": (36.8438, -2.3671), "BRU": (50.9018, 4.4836),
    "FRA": (50.0392, 8.5592), "MUC": (48.3537, 11.7750),
    "BER": (52.5588, 13.2884), "MXP": (45.63, 8.7231),
    "LIN": (45.4495, 9.2774), "VCE": (45.5047, 12.3395),
    "NAP": (40.8845, 14.2907), "LIS": (38.7746, -9.1353),
    "OPO": (41.2372, -8.6708), "FAO": (37.0204, -7.9719),
    "ATH": (37.9363, 23.9474), "VIE": (48.1192, 16.5667),
    "PRG": (50.1061, 14.2667), "BUD": (47.4365, 19.2553),
    "WAW": (52.1699, 20.9728), "DUB": (53.4264, -6.2499),
    "CPH": (55.6176, 12.6498), "OSL": (60.1975, 11.1008),
    "ARN": (59.6491, 17.9306), "HEL": (60.3183, 24.9524),
    "IST": (41.2611, 28.7427), "DXB": (25.2487, 55.3653),
    "JFK": (40.6413, -73.7781), "EWR": (40.6895, -74.1745),
    "MIA": (25.7959, -80.2870), "LAX": (33.9416, -118.4085),
    "MEX": (19.4357, -99.0718), "BOG": (4.6996, -74.1466),
    "EZE": (-34.8124, -58.5396), "GRU": (-23.4254, -46.4819),
    "NRT": (35.7738, 140.3874), "HND": (35.5533, 139.7811),
    "SIN": (1.3592, 103.9900), "BKK": (13.6930, 100.7523),
    "DOH": (25.2686, 51.6100), "AUH": (24.4335, 54.6481),
}

AIRPORT_CITY_NAMES: dict[str, str] = {
    "MAD": "Madrid", "BCN": "Barcelona", "LHR": "Londres",
    "ORY": "París", "CDG": "París", "AMS": "Ámsterdam",
    "FCO": "Roma", "PMI": "Palma de Mallorca", "AGP": "Málaga",
    "SVQ": "Sevilla", "BIO": "Bilbao", "VLC": "Valencia",
    "ALC": "Alicante", "IBZ": "Ibiza", "TFN": "Tenerife",
    "LPA": "Gran Canaria", "TFS": "Tenerife Sur", "EAS": "San Sebastián",
    "SCQ": "Santiago", "VGO": "Vigo", "SDR": "Santander",
    "ZAZ": "Zaragoza", "GRX": "Granada", "XRY": "Jerez",
    "LEI": "Almería", "BRU": "Bruselas", "FRA": "Fráncfort",
    "MUC": "Múnich", "BER": "Berlín", "MXP": "Milán",
    "LIN": "Milán", "VCE": "Venecia", "NAP": "Nápoles",
    "LIS": "Lisboa", "OPO": "Oporto", "FAO": "Faro",
    "ATH": "Atenas", "VIE": "Viena", "PRG": "Praga",
    "BUD": "Budapest", "WAW": "Varsovia", "DUB": "Dublín",
    "CPH": "Copenhague", "OSL": "Oslo", "ARN": "Estocolmo",
    "HEL": "Helsinki", "IST": "Estambul", "DXB": "Dubái",
    "JFK": "Nueva York", "EWR": "Nueva York", "MIA": "Miami",
    "LAX": "Los Ángeles", "MEX": "Ciudad de México",
    "BOG": "Bogotá", "EZE": "Buenos Aires", "GRU": "São Paulo",
    "NRT": "Tokio", "HND": "Tokio", "SIN": "Singapur",
    "BKK": "Bangkok", "DOH": "Doha", "AUH": "Abu Dabi",
}

# Normalizacion de ciudades que aparecen escritas enteras en el billete
# (no como codigo IATA) en PDFs de Renfe/OUIGO
SPANISH_CITY_ALIASES: dict[str, str] = {
    "MADRID P.ATOCHA": "Madrid",
    "MADRID ATOCHA": "Madrid",
    "MADRID CHAMARTIN": "Madrid",
    "MADRID PUERTA DE ATOCHA": "Madrid",
    "BARCELONA SANTS": "Barcelona",
    "TOLEDO": "Toledo",
    "SEVILLA SANTA JUSTA": "Sevilla",
    "VALENCIA JOAQUIN SOROLLA": "Valencia",
    "MADRID": "Madrid",
    "BARCELONA": "Barcelona",
    "SEVILLA": "Sevilla",
    "VALENCIA": "Valencia",
    "MALAGA": "Málaga",
    "BILBAO": "Bilbao",
    "ZARAGOZA": "Zaragoza",
    "SANTIAGO": "Santiago de Compostela",
    "A CORUÑA": "A Coruña",
    "VIGO": "Vigo",
    "ALICANTE": "Alicante",
    "MURCIA": "Murcia",
}


def _sort_by_date(items: list[dict], date_key: str = "flight_date", time_key: str = "flight_time") -> list[dict]:
    """Ordena items por fecha y hora usando objetos date para orden correcto."""
    def sort_key(item):
        d_str = item.get(date_key, "")
        t_str = item.get(time_key, "") or ""
        try:
            d = date.fromisoformat(d_str) if d_str else date.min
            return (d, t_str)
        except (ValueError, TypeError):
            return (date.min, t_str)
    return sorted(items, key=sort_key)


def _get_city_name(code: str) -> str:
    """Convierte codigo de aeropuerto a nombre de ciudad."""
    if not code:
        return ""
    code_upper = code.upper().strip()
    if code_upper in AIRPORT_CITY_NAMES:
        return AIRPORT_CITY_NAMES[code_upper]
    if code_upper in SPANISH_CITY_ALIASES:
        return SPANISH_CITY_ALIASES[code_upper]
    return code


def _get_coords(code: str) -> tuple[float, float] | None:
    """Obtiene coordenadas para un codigo de aeropuerto."""
    return CITY_COORDS.get(code.upper())


# --- Clima (Open-Meteo, gratuito, sin API key) ---

async def fetch_weather(city_code: str, start_date: str, end_date: str) -> list[dict]:
    """Obtiene prediccion meteorologica para una ciudad en un rango de fechas.

    Devuelve lista de {date, temp_max, temp_min, precipitation, condition, wind_speed}.
    """
    coords = _get_coords(city_code)
    if not coords:
        return []

    lat, lon = coords
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[weather] Error: {e}")
        return []

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    weather_codes = daily.get("weather_code", [])
    wind = daily.get("wind_speed_10m_max", [])

    weather = []
    for i, d in enumerate(dates):
        weather.append({
            "date": d,
            "temp_max": temps_max[i] if i < len(temps_max) else None,
            "temp_min": temps_min[i] if i < len(temps_min) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "condition": _weather_emoji(weather_codes[i] if i < len(weather_codes) else 0),
            "wind_kmh": wind[i] if i < len(wind) else None,
        })
    return weather


def _weather_emoji(code: int) -> str:
    """Convierte codigo WMO a descripcion con emoji."""
    if code == 0:
        return "☀️ Despejado"
    if code in (1, 2, 3):
        return "🌤️ Parcialmente nublado"
    if code in (45, 48):
        return "🌫️ Niebla"
    if code in (51, 53, 55):
        return "🌧️ Llovizna"
    if code in (61, 63, 65, 80, 81, 82):
        return "🌧️ Lluvia"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄️ Nieve"
    if code in (95, 96, 99):
        return "⛈️ Tormenta"
    return "🌥️ Nublado"


# --- Calendario diario (extrae itinerario base de pases + segmentos) ---

_SPANISH_WEEKDAYS = [
    "Lunes", "Martes", "Miércoles", "Jueves",
    "Viernes", "Sábado", "Domingo",
]

def _spanish_weekday(date_str: str) -> str:
    """Convierte '2025-12-01' -> 'Lunes'."""
    try:
        d = date.fromisoformat(date_str)
        return _SPANISH_WEEKDAYS[d.weekday()]
    except (ValueError, TypeError):
        return ""


def _infer_city_per_day(
    passes: list[dict],
    segments: list[dict],
    all_dates: list[str],
) -> dict[str, str | None]:
    """Determina en qué ciudad está el viajero cada día del viaje.

    Algoritmo:
    1. Ciudad inicial = origen del primer vuelo.
    2. Hoteles: Si hay check-in en fecha D, la ciudad del hotel pisa la actual
       y se mantiene hasta el check-out (inclusive).
    3. Vuelos/trenes: al llegar a destino, se actualiza la ciudad actual
       para esa fecha y las siguientes.
    4. Actividades y restaurantes: refuerzan la ciudad para su fecha.

    Returns dict {fecha: ciudad | None}.
    """
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)

    # Ciudad inicial: origen del primer vuelo, o None
    current_city: str | None = None
    if flights_sorted:
        current_city = _get_city_name(flights_sorted[0].get("from", ""))

    # Hoteles: rango de fechas -> ciudad (prioridad máxima)
    hotel_map: dict[str, str] = {}
    for s in segments:
        if s.get("type") != "hotel":
            continue
        city = _get_city_name(s.get("city", ""))
        if not city:
            continue
        ci = s.get("check_in", "")
        co = s.get("check_out", "")
        if not ci:
            continue
        # Aplicar a todas las fechas entre check_in y check_out (inclusive)
        for d in all_dates:
            if ci <= d <= (co or ci):
                hotel_map[d] = city

    # Vuelos y trenes: eventos que cambian la ciudad
    transport_events: list[dict] = []
    for f in flights_sorted:
        fd = f.get("flight_date", "")
        if not fd:
            continue
        transport_events.append({
            "date": fd,
            "time": f.get("flight_time", "") or "12:00",
            "to_city": _get_city_name(f.get("to", "")),
        })
    for s in segments:
        if s.get("type") == "train":
            transport_events.append({
                "date": s.get("date", ""),
                "time": s.get("time", "") or "12:00",
                "to_city": _get_city_name(s.get("to", "")),
            })
        elif s.get("type") == "flight":
            transport_events.append({
                "date": s.get("date", ""),
                "time": s.get("time", "") or "12:00",
                "to_city": _get_city_name(s.get("to_city", s.get("to", ""))),
            })
    transport_events.sort(key=lambda e: (e["date"], e["time"]))

    city_per_day: dict[str, str | None] = {}
    for date in all_dates:
        # 1. ¿Hay hotel que cubra esta fecha?
        if date in hotel_map:
            current_city = hotel_map[date]
            city_per_day[date] = current_city
            continue

        # 2. ¿Hay llegada de vuelo/tren en esta fecha?
        arrivals_today = [e for e in transport_events if e["date"] == date]
        if arrivals_today:
            # La última llegada del día fija la ciudad
            last = arrivals_today[-1]
            if last["to_city"]:
                current_city = last["to_city"]

        city_per_day[date] = current_city

    # 3. Refuerzo: actividades y restaurantes confirman ciudad para su fecha
    for s in segments:
        if s.get("type") in ("activity", "restaurant"):
            city = _get_city_name(s.get("city", ""))
            date = s.get("date", "")
            if city and date in city_per_day:
                if city_per_day[date] is None:
                    city_per_day[date] = city

    return city_per_day


def _build_daily_calendar(
    passes: list[dict],
    segments: list[dict],
    all_dates: list[str],
    *,
    origin_city: str | None = None,
) -> list[dict]:
    """Construye un calendario diario del viaje a partir de pases y segmentos.

    Cada día incluye:
    - date, day_number, weekday (español), city
    - events: lista de eventos fijos
    - free_blocks: franjas horarias libres para sugerir actividades
    - is_origin_day: True si la ciudad = ciudad de origen (sin sugerencias)

    Args:
        origin_city: ciudad de origen del viajero. Días en esta ciudad
                     se marcan como is_origin_day sin bloques libres.
    """
    flights = [p for p in passes if p.get("kind") == "flight"]
    trains = [p for p in passes if p.get("kind") == "train"]

    flights_sorted = _sort_by_date(flights)

    city_per_day = _infer_city_per_day(passes, segments, all_dates)

    # Construir eventos diarios
    days: dict[str, dict] = {
        d: {
            "date": d,
            "day_number": i + 1,
            "weekday": _spanish_weekday(d),
            "city": city_per_day.get(d),
            "is_origin_day": bool(origin_city and city_per_day.get(d) == origin_city),
            "events": [],
        }
        for i, d in enumerate(all_dates)
    }

    # --- Vuelos (PDF) ---
    for f in flights_sorted:
        fd = f.get("flight_date", "")
        if fd not in days:
            continue
        time_str = f.get("flight_time", "") or ""
        airline = f.get("airline", "")
        flight_no = f.get("flight", "")
        from_city = _get_city_name(f.get("from", ""))
        to_city = _get_city_name(f.get("to", ""))
        days[fd]["events"].append({
            "type": "flight_arrival",
            "time": time_str,
            "description": f"Llegada {airline}{flight_no} desde {from_city}",
            "city": to_city,
        })

    # --- Trenes (PDF) ---
    for t in trains:
        fd = t.get("flight_date", "")
        if fd not in days:
            continue
        time_str = t.get("flight_time", "") or ""
        train_no = t.get("train", "")
        from_raw = t.get("from", "")
        to_raw = t.get("to", "")
        from_city = _get_city_name(from_raw) or from_raw
        to_city = _get_city_name(to_raw) or to_raw
        days[fd]["events"].append({
            "type": "train_arrival",
            "time": time_str,
            "description": f"Llegada tren {train_no} desde {from_city}",
            "city": to_city,
        })

    # --- Vuelos manuales ---
    for s in segments:
        if s.get("type") != "flight":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        airline = s.get("airline", "")
        flight_no = s.get("flight_number", "")
        from_city = _get_city_name(s.get("from", "")) or s.get("from", "")
        to_city = _get_city_name(s.get("to_city", s.get("to", ""))) or s.get("to", "")
        days[fd]["events"].append({
            "type": "flight_arrival",
            "time": s.get("time", "") or "",
            "description": f"Llegada {airline}{flight_no} desde {from_city}",
            "city": to_city,
        })

    # --- Trenes manuales ---
    for s in segments:
        if s.get("type") != "train":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        op = s.get("operator", "")
        train_no = s.get("train_number", "")
        from_city = _get_city_name(s.get("from", "")) or s.get("from", "")
        to_city = _get_city_name(s.get("to", "")) or s.get("to", "")
        days[fd]["events"].append({
            "type": "train_arrival",
            "time": s.get("time", "") or "",
            "description": f"Llegada {op} {train_no} desde {from_city}",
            "city": to_city,
        })

    # --- Hoteles ---
    for s in segments:
        if s.get("type") != "hotel":
            continue
        hotel_city = _get_city_name(s.get("city", "")) or s.get("city", "")
        name = s.get("name", "")
        ci = s.get("check_in", "")
        co = s.get("check_out", "")
        if ci and ci in days:
            days[ci]["events"].append({
                "type": "hotel_checkin",
                "time": "",
                "description": f"Check-in {name}",
                "city": hotel_city,
            })
        if co and co in days:
            days[co]["events"].append({
                "type": "hotel_checkout",
                "time": "",
                "description": f"Check-out {name}",
                "city": hotel_city,
            })

    # --- Coches ---
    for s in segments:
        if s.get("type") != "car":
            continue
        company = s.get("company", "")
        city = _get_city_name(s.get("city", "")) or s.get("city", "")
        pickup_date = s.get("pickup_date", "")
        return_date = s.get("return_date", "")
        if pickup_date and pickup_date in days:
            days[pickup_date]["events"].append({
                "type": "car_pickup",
                "time": "",
                "description": f"Recogida coche {company}",
                "city": city,
            })
        if return_date and return_date in days:
            days[return_date]["events"].append({
                "type": "car_return",
                "time": "",
                "description": f"Devolución coche {company}",
                "city": city,
            })

    # --- Restaurantes ---
    for s in segments:
        if s.get("type") != "restaurant":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        name = s.get("name", "")
        time_str = s.get("time", "") or ""
        days[fd]["events"].append({
            "type": "restaurant",
            "time": time_str,
            "description": f"Cena: {name}",
            "city": _get_city_name(s.get("city", "")) or s.get("city", ""),
        })

    # --- Actividades ---
    for s in segments:
        if s.get("type") != "activity":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        name = s.get("name", "")
        time_str = s.get("time", "") or ""
        days[fd]["events"].append({
            "type": "activity",
            "time": time_str,
            "description": f"Reserva: {name}",
            "city": _get_city_name(s.get("city", "")) or s.get("city", ""),
        })

    # Ordenar eventos por hora dentro de cada día
    for d in days.values():
        d["events"].sort(key=lambda e: e["time"] or "23:59")

    # Calcular bloques libres usando franjas estándar (no duraciones desconocidas)
    # Mañana: 06:00-12:00, Tarde: 12:00-18:00, Noche: 18:00-24:00
    for d in days.values():
        events_with_time = [e for e in d["events"] if e["time"]]
        occupied_slots: set[str] = set()
        for e in events_with_time:
            h = int(e["time"].split(":")[0])
            if h < 12:
                occupied_slots.add("morning")
            elif h < 18:
                occupied_slots.add("afternoon")
            else:
                occupied_slots.add("evening")

        # Para días en ciudad de origen (vuelta a casa): sin sugerencias
        if d["is_origin_day"]:
            d["free_blocks"] = []
            d["has_fixed_events"] = len(d["events"]) > 0
            continue

        free_blocks = []
        if "morning" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Mañana (06:00—12:00)",
            })
        if "afternoon" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Tarde (12:00—18:00)",
            })
        if "evening" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Noche (18:00—24:00)",
            })
        if not free_blocks:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Día completo con eventos",
            })

        d["free_blocks"] = free_blocks
        d["has_fixed_events"] = len(d["events"]) > 0

    return [days[d] for d in all_dates]


# --- DeepSeek LLM ---

def _build_itinerary_prompt(
    passes: list[dict],
    segments: list[dict],
    weather: list[dict],
    all_dates: list[str],
    num_days: int,
    *,
    trip_title: str | None = None,
) -> str:
    """Construye el prompt para DeepSeek a partir del calendario diario calculado."""

    # Determinar ciudad de origen desde el primer vuelo
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    calendar = _build_daily_calendar(passes, segments, all_dates, origin_city=origin_city)

    # Construir ciudades visitadas y nº de destinos únicos
    # Ciudades visitadas EXCLUYENDO ciudad de origen (no generar contenido sobre ella)
    all_cities = list(dict.fromkeys(
        d["city"] for d in calendar if d["city"]
    ))
    cities = [c for c in all_cities if c != origin_city] or all_cities[:1]
    dest_str = ", ".join(cities) if cities else "destino desconocido"
    unique_destinations = cities

    # --- Formatear CALENDARIO DIARIO como sección central del prompt ---
    calendar_lines = []
    for day in calendar:
        header = f"Día {day['day_number']} — {day['weekday']} {day['date']} — 📍 {day['city'] or '?'}"
        calendar_lines.append(header)

        if day["events"]:
            calendar_lines.append("  Eventos fijos (NO modificar):")
            for ev in day["events"]:
                time_part = f"  {ev['time']}" if ev["time"] else "     --"
                calendar_lines.append(f"  {time_part}  {ev['description']}")
        else:
            calendar_lines.append("  (sin eventos fijos — día libre)")

        if day["free_blocks"]:
            calendar_lines.append("  ⏳ Bloques libres para sugerir actividades:")
            for fb in day["free_blocks"]:
                calendar_lines.append(f"     • {fb['label']}")

        calendar_lines.append("")  # línea en blanco entre días

    calendar_text = "\n".join(calendar_lines)

    # --- Clima ---
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']}: {w['condition']}, max {w['temp_max']}°C, min {w['temp_min']}°C"
            for w in weather[:14]
        )

    # --- Construir el prompt ---
    prompt = f"""Eres un agente de viajes experto. Genera un itinerario enriquecido a partir del calendario base que te proporciono.

=== TÍTULO DEL VIAJE ===
{trip_title or dest_str}
Este es el nombre del viaje. El destino PRINCIPAL es {dest_str}.

=== DATOS DEL VIAJE ===
Destinos: {dest_str}
Días totales: {num_days}
Fechas: {all_dates[0]} → {all_dates[-1]}

=== CALENDARIO BASE (extraído de tus reservas reales) ===
Este es el esqueleto del viaje. Los eventos marcados como "fijos" son inamovibles
(vuelos, trenes, hoteles, restaurantes y actividades ya reservados).
Tu tarea es RELLENAR LOS HUECOS LIBRES con sugerencias.

{calendar_text}

=== CLIMA PREVISTO ===
{weather_str or "No disponible — usa clima histórico de la época."}

=== TU TAREA ===
A partir del calendario base, genera un JSON con:

1. daily_itinerary [{num_days} elementos]: Para cada día, respeta los eventos fijos tal cual aparecen en el calendario base. En los bloques libres, sugiere actividades realistas para esa ciudad, clima y franja horaria. No inventes eventos que contradigan los fijos. La ciudad de cada día ya viene determinada en el calendario base — úsala.
2. hotels: Si NO hay hoteles reservados en el calendario base, sugiere 2-3 hoteles reales en {" cada una de las ciudades: " + dest_str if len(unique_destinations) > 1 else " " + dest_str}. Si YA hay hoteles, NO sugieras otros, solo referencia los existentes.
3. restaurants: 3-4 restaurantes reales en {dest_str}. Si ya hay cenas reservadas, menciónalas en daily_itinerary y sugiere restaurantes para las comidas sin reserva.
4. places_of_interest: 3-5 lugares reales en {dest_str}.
5. historical_sites: 1-2 sitios históricos reales en {dest_str}.
6. transport_tips, general_tips, cultural_notes: tips breves y reales.

=== REGLAS ===
- SOLO nombres reales. PROHIBIDO inventar hoteles, restaurantes o museos.
- Nombres propios en idioma local. Descripciones en español.
- BREVEDAD: cada descripción ≤ 12 palabras. Tips ≤ 8 palabras.
- daily_itinerary usa EXACTAMENTE las fechas del calendario base (no inventes otras).
- Respeta check-in/check-out: el día de check-out NO sugieras actividades vinculadas a ese hotel.
- Si un día es de desplazamiento (tren/vuelo), sugiere actividades ligeras o cercanas a la estación/aeropuerto.
- Precios en €. Categorías: €, €€, €€€, €€€€.

=== FORMATO DE SALIDA ===
Responde ÚNICAMENTE con el JSON. Sin markdown, sin explicaciones.

{{
  "destination_overview": "1 frase descriptiva de {dest_str}",
  "weather_summary": "1 frase resumiendo el clima para las fechas del viaje",
  "hotels": [
    {{
      "name": "Nombre real del hotel",
      "zone": "Barrio o zona",
      "description": "1 frase breve (≤12 palabras)",
      "price_range": "€, €€, €€€ o €€€€",
      "highlights": ["Punto fuerte 1", "Punto fuerte 2"]
    }}
  ],
  "restaurants": [
    {{
      "name": "Nombre real",
      "type": "Tradicional / Fusión / Mercado / etc",
      "description": "Plato estrella (≤8 palabras)",
      "price_range": "€, €€, €€€ o €€€€"
    }}
  ],
  "places_of_interest": [
    {{
      "name": "Nombre real",
      "type": "Museo / Parque / Mirador / etc",
      "description": "1 frase (≤12 palabras)",
      "tips": ["Tip ≤8 palabras"]
    }}
  ],
  "historical_sites": [
    {{
      "name": "Nombre real",
      "period": "Siglo / época",
      "description": "1 frase (≤12 palabras)",
      "curiosity": "Dato curioso ≤10 palabras"
    }}
  ],
  "daily_itinerary": [
    {{
      "day_number": 1,
      "date": "{all_dates[0]}",
      "city": "{cities[0] if cities else '?'}",
      "theme": "Concepto del día (≤5 palabras)",
      "morning": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "afternoon": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "evening": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "meal_suggestions": {{ "lunch": "Restaurante o zona (≤8 palabras)", "dinner": "Restaurante o zona (≤8 palabras)" }}
    }}
  ],
  "transport_tips": ["Tip ≤10 palabras"],
  "general_tips": ["Tip ≤10 palabras"],
  "cultural_notes": ["Nota cultural ≤10 palabras"]
}}"""

    return prompt


def _real_flight_destinations(flights: list[dict], seg_hotels: list[dict], origin: str) -> list[str]:
    """Retorna destinos reales de vuelos: excluye origen y conexiones
    (siguiente vuelo desde misma ciudad el mismo día)."""
    flights_sorted = _sort_by_date(flights)

    def es_real(idx: int) -> bool:
        f = flights_sorted[idx]
        to_city = _get_city_name(f.get("to", ""))
        if not to_city or to_city == origin:
            return False
        for sh in seg_hotels:
            if _get_city_name(sh.get("city", "")).lower() == to_city.lower():
                return True
        if idx == len(flights_sorted) - 1:
            return True
        for f2 in flights_sorted[idx + 1:]:
            if _get_city_name(f2.get("from", "")).lower() == to_city.lower():
                return f2.get("flight_date") != f.get("flight_date")
        return True

    dests = []
    for i, f in enumerate(flights_sorted):
        c = _get_city_name(f.get("to", ""))
        if c and es_real(i) and c not in dests:
            dests.append(c)
    return dests


def generate_trip_name(passes: list[dict], segments: list[dict] | None = None) -> str:
    """Genera un titulo basado en los destinos del viaje: 'Viaje a Sevilla'.
    Excluye origen y ciudades de conexión."""
    if segments is None:
        segments = []

    flights = [p for p in passes if p.get("kind") == "flight"]
    trains = [p for p in passes if p.get("kind") == "train"]
    seg_hotels = [s for s in segments if s.get("type") == "hotel"]

    origin = _get_city_name(flights[0].get("from", "")) if flights else ""

    dests = _real_flight_destinations(flights, seg_hotels, origin)
    for t in trains:
        train = t.get("train", "")
        date = t.get("flight_date", "")
        label = f"Tren {train}" if train else "Tren"
        if date:
            label += f" {_format_short_date(date)}"
        if label not in dests:
            dests.append(label)
    for s in seg_hotels:
        city = s.get("city", "")
        if city and city != origin and city not in dests:
            dests.append(city)

    if dests:
        return f"Viaje a {' y '.join(dests[:3])}"
    if flights:
        return f"Viaje a {_get_city_name(flights[0].get('to',''))}"
    if trains:
        train_no = trains[0].get("train", "?")
        return f"Tren {train_no}"
    return "Viaje sin destino"


def _parse_json_response(content: str) -> dict:
    """Intenta parsear la respuesta del LLM como JSON usando multiples estrategias.

    Los LLMs a veces devuelven JSON con ruido: markdown fences, texto extra,
    comas finales, etc. Esta funcion prueba varias tecnicas de limpieza.
    """
    import re

    if not content or not content.strip():
        return {"raw_response": content, "parse_error": True}

    strategies: list[tuple[str, str]] = []

    # Estrategia 1: texto tal cual
    strategies.append(("raw", content.strip()))

    # Estrategia 2: quitar fences de markdown (```json ... ```)
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        strategies.append(("no-fences", cleaned.strip()))

    # Estrategia 3: extraer el primer objeto JSON valido con regex
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        strategies.append(("regex-extract", match.group(0)))

    # Estrategia 4: quitar comas finales antes de ] o }
    for name, text in list(strategies):
        fixed = re.sub(r",(\s*[}\]])", r"\1", text)
        if fixed != text:
            strategies.append((f"{name}-no-trailing-comma", fixed))

    # Estrategia 5: reparar JSON truncado (cerrar llaves/corchetes abiertos)
    for name, text in list(strategies):
        if text.endswith(","):
            text = text[:-1]
        # Contar aperturas y cierres, añadir los que faltan
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        if open_braces > 0 or open_brackets > 0:
            # Cerrar strings abiertos
            in_string = False
            fixed_text = list(text)
            for i, ch in enumerate(text):
                if ch == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
            if in_string:
                text += '"'
            text += "]" * max(0, open_brackets)
            text += "}" * max(0, open_braces)
            strategies.append((f"{name}-repaired-truncation", text))

    # Probar cada estrategia
    last_error = ""
    for strategy_name, text in strategies:
        try:
            result = json.loads(text)
            print(f"[parse_json] success with strategy: {strategy_name}")
            return result
        except json.JSONDecodeError as e:
            last_error = f"{strategy_name}: {e}"

    print(f"[parse_json] all strategies failed: {last_error}")
    return {
        "raw_response": content[:2000],
        "parse_error": True,
    }


def _build_basic_itinerary(
    passes: list[dict],
    segments: list[dict],
    weather: list[dict],
    all_dates: list[str],
    num_days: int,
) -> dict:
    """Devuelve un itinerario básico (sin LLM) a partir del calendario diario.

    Se usa como fallback cuando no hay DEEPSEEK_API_KEY configurada.
    Contiene solo los eventos fijos extraídos de pases y segmentos, sin
    sugerencias de restaurantes, lugares de interés ni notas culturales.
    """
    # Determinar origen desde el primer vuelo
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    calendar = _build_daily_calendar(passes, segments, all_dates, origin_city=origin_city)

    cities = list(dict.fromkeys(
        d["city"] for d in calendar if d["city"]
    ))

    daily = []
    for day in calendar:
        entry: dict = {
            "day_number": day["day_number"],
            "date": day["date"],
            "city": day["city"],
            "theme": f"Día en {day['city']}" if day["city"] else "Día de viaje",
            "morning": {"activities": [], "description": ""},
            "afternoon": {"activities": [], "description": ""},
            "evening": {"activities": [], "description": ""},
            "meal_suggestions": {"lunch": "", "dinner": ""},
        }
        for ev in day["events"]:
            desc = ev["description"]
            if ev["type"] in ("flight_arrival", "train_arrival"):
                entry["morning"]["activities"].append(desc)
            elif ev["type"] in ("restaurant",):
                entry["evening"]["activities"].append(desc)
                entry["meal_suggestions"]["dinner"] = desc.replace("Cena: ", "")
            elif ev["type"] in ("activity",):
                entry["afternoon"]["activities"].append(desc)
            else:
                entry["morning"]["activities"].append(desc)

        if day["free_blocks"]:
            for fb in day["free_blocks"]:
                if "Mañana" in fb["label"]:
                    entry["morning"]["description"] = fb["label"]
                elif "Día completo" in fb["label"]:
                    entry["morning"]["description"] = "Día libre"
                elif "Noche" in fb["label"]:
                    entry["evening"]["description"] = fb["label"]
                else:
                    entry["afternoon"]["description"] = fb["label"]

        daily.append(entry)

    return {
        "destination_overview": f"Viaje a {', '.join(cities)}" if cities else "Viaje",
        "weather_summary": "",
        "hotels": [],
        "restaurants": [],
        "places_of_interest": [],
        "historical_sites": [],
        "daily_itinerary": daily,
        "transport_tips": [],
        "general_tips": [],
        "cultural_notes": [],
        "basic_mode": True,
    }


async def generate_itinerary(passes: list[dict], segments: list[dict] | None = None) -> dict:
    """Genera un itinerario completo usando DeepSeek LLM y Open-Meteo."""
    from datetime import timedelta

    if segments is None:
        segments = []

    flights = [p for p in passes if p.get("kind") == "flight"]
    seg_flights = [s for s in segments if s.get("type") == "flight"]
    seg_hotels = [s for s in segments if s.get("type") == "hotel"]
    seg_activities = [s for s in segments if s.get("type") == "activity"]

    # 1. Calcular todas las fechas del viaje (de pases + segmentos manuales)
    all_dates_set: set[str] = set()

    # Fechas de vuelos extraidos
    for p in flights:
        fd = p.get("flight_date")
        if fd:
            all_dates_set.add(fd)

    # Fechas de segmentos manuales
    for s in seg_flights + seg_activities:
        fd = s.get("date")
        if fd:
            all_dates_set.add(fd)
    for s in seg_hotels:
        for key in ("check_in", "check_out"):
            fd = s.get(key)
            if fd:
                all_dates_set.add(fd)
    # Fechas de coches
    for s in segments:
        if s.get("type") == "car":
            for key in ("pickup_date", "return_date"):
                fd = s.get(key)
                if fd:
                    all_dates_set.add(fd)

    all_dates: list[str] = sorted(all_dates_set) if all_dates_set else [date.today().isoformat()]

    # Expandir rango (si hay check_in y check_out, rellenar dias intermedios)
    if all_dates:
        try:
            start = date.fromisoformat(all_dates[0])
            end = date.fromisoformat(all_dates[-1])
            expanded = []
            current = start
            while current <= end:
                expanded.append(current.isoformat())
                current += timedelta(days=1)
            all_dates = expanded
        except ValueError:
            pass

    num_days = len(all_dates)

    # Safety: nunca tener más de 31 días (un mes máximo) — evita year-inference bugs
    if num_days > 31:
        print(f"[itinerary] WARNING: {num_days} días es sospechoso, limitando a 31")
        all_dates = all_dates[:31]
        num_days = 31

    # Calcular título del viaje para pasarlo al prompt
    trip_title = generate_trip_name(passes, segments)

    # 2. Guardrail: verificar que hay destinos identificables
    # antes de gastar tokens del LLM en datos inservibles.
    weather: list[dict] = []
    calendar_check = _build_daily_calendar(passes, segments, all_dates)
    identified_cities = [d["city"] for d in calendar_check if d["city"]]
    has_events = any(d["has_fixed_events"] for d in calendar_check)
    if not identified_cities:
        print("[itinerary] ERROR: no se pudo determinar ninguna ciudad de destino")
        return {
            "error": "No se pudo determinar el destino del viaje. Añade al menos un vuelo, tren, hotel o actividad con ciudad.",
            "weather": weather,
        }
    if not has_events and not DEEPSEEK_API_KEY:
        print("[itinerary] ERROR: sin eventos fijos ni API key — imposible generar")
        return {
            "error": "Sin reservas ni eventos. Añade vuelos, hoteles o actividades y configura DEEPSEEK_API_KEY.",
            "weather": weather,
        }

    # 3. Obtener clima para el primer destino con coordenadas
    weather = []
    for src_list in (flights, seg_flights):
        for item in src_list:
            code = item.get("to", item.get("to_city", ""))
            if code and _get_coords(code.upper()):
                weather = await fetch_weather(code.upper(), all_dates[0], all_dates[-1])
                break
        if weather:
            break

    # Si no hay vuelos, usar primera ciudad de hotel
    if not weather:
        for h in seg_hotels:
            city = h.get("city", "")
            # Buscar coordenadas por nombre de ciudad
            for code, name in AIRPORT_CITY_NAMES.items():
                if name.lower() == city.lower() and _get_coords(code):
                    weather = await fetch_weather(code, all_dates[0], all_dates[-1])
                    break
            if weather:
                break

    # 3. Generar recomendaciones con DeepSeek
    # Si no hay API key, devolvemos un itinerario basico (solo clima + estructura)
    if not DEEPSEEK_API_KEY:
        print("[itinerary] DEEPSEEK_API_KEY no configurada: devolviendo itinerario basico")
        basic = _build_basic_itinerary(passes, segments, weather, all_dates, num_days)
        return {
            "warning": "Itinerario basico: configura DEEPSEEK_API_KEY para recomendaciones personalizadas",
            "weather": weather,
            **basic,
        }

    prompt = _build_itinerary_prompt(passes, segments, weather, all_dates, num_days, trip_title=trip_title)

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Eres un asistente de viajes experto. Responde SIEMPRE solo con JSON valido, sin markdown ni texto adicional."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=16384,
        )
        content = response.choices[0].message.content or ""
        print(f"[deepseek] response length: {len(content)} chars")
    except Exception as e:
        print(f"[deepseek] Error: {e}")
        return {
            "error": f"Error al generar itinerario: {e}",
            "weather": weather,
        }

    # 3. Parsear JSON con limpieza robusta
    itinerary = _parse_json_response(content)

    # Añadir clima al resultado
    itinerary["weather"] = weather

    # Añadir metadatos del viaje
    destinations = list(set(
        _get_city_name(p.get("to", ""))
        for p in passes if p.get("kind") == "flight" and p.get("to")
    ))
    itinerary["meta"] = {
        "destinations": destinations,
        "pass_count": len(passes),
        "generated_at": datetime.now().isoformat(),
    }

    return itinerary
