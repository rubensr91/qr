"""
Modulo de generacion de itinerarios de viaje usando DeepSeek LLM y Open-Meteo.

DeepSeek: recomendaciones personalizadas (restaurantes, hoteles, lugares, historia, tips).
Open-Meteo: prediccion meteorologica gratuita sin API key.
"""

import asyncio
import json
import sys
from datetime import datetime, date
from pathlib import Path

import httpx
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parser import infer_years
from content_validator import validate_itinerary, validate_quiz

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


def _parse_time_to_minutes(time_str: str | None) -> int | None:
    """Convierte una hora HH:MM en minutos desde medianoche."""
    if not time_str:
        return None
    try:
        hh, mm = time_str.strip().split(":", 1)
        hour = int(hh)
        minute = int(mm)
    except (ValueError, AttributeError):
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour * 60 + minute
    return None


def _format_minutes_to_time(total_minutes: int | None) -> str:
    """Convierte minutos a HH:MM y conserva el salto de día si existe."""
    if total_minutes is None:
        return ""
    days, minutes = divmod(max(0, total_minutes), 24 * 60)
    hours, mins = divmod(minutes, 60)
    time_str = f"{hours:02d}:{mins:02d}"
    return f"+{days}d {time_str}" if days else time_str


def _resolve_coords_for_place(place: str) -> tuple[float, float] | None:
    """Obtiene coordenadas desde codigo IATA o nombre de ciudad normalizado."""
    if not place:
        return None
    coords = _get_coords(place)
    if coords:
        return coords
    city = _get_city_name(place)
    city_code = _get_city_code(city)
    if city_code:
        return _get_coords(city_code)
    return None


def _haversine_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """Distancia aproximada entre dos puntos geograficos en kilometros."""
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1 = origin
    lat2, lon2 = destination
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def _estimate_transport_duration_minutes(kind: str, from_place: str, to_place: str) -> int:
    """Estima el tiempo total hasta poder hacer actividades tras llegar."""
    origin = _resolve_coords_for_place(from_place)
    destination = _resolve_coords_for_place(to_place)

    default_minutes = 150 if kind == "flight" else 120
    if not origin or not destination:
        return default_minutes

    distance_km = _haversine_km(origin, destination)
    if distance_km <= 0:
        return default_minutes

    if kind == "flight":
        return max(90, int(round((distance_km / 700.0) * 60 + 75)))
    return max(75, int(round((distance_km / 220.0) * 60 + 30)))


def _build_transport_constraints_text(calendar: list[dict]) -> str:
    """Serializa restricciones de llegada para que el LLM las trate como duras."""
    lines: list[str] = []
    for day in calendar:
        constraints = day.get("transport_constraints") or []
        if not constraints:
            continue
        lines.append(f"Día {day['day_number']} — {day['date']} — {day.get('city') or '?'}")
        for item in constraints:
            route = item.get("route") or "trayecto"
            departure = item.get("departure_time") or "--"
            arrival = item.get("estimated_arrival_time") or "--"
            guard = item.get("no_activities_before") or "--"
            lines.append(
                f"  • {item.get('kind', 'transporte')} {route}: salida {departure}, "
                f"llegada estimada {arrival}, no actividades antes de {guard}"
            )
    return "\n".join(lines) if lines else "No hay transportes con restricción horaria."


def _get_city_name(code: str) -> str:
    """Convierte codigo de aeropuerto o nombre de estacion a ciudad.

    Maneja:
    - Codigos IATA: 'BCN' -> 'Barcelona'
    - Nombres de estacion: 'Sevilla - Santa Justa' -> 'Sevilla'
    - Ciudades en texto: 'MADRID P.ATOCHA' -> 'Madrid'
    """
    if not code:
        return ""
    code_upper = code.upper().strip()
    if code_upper in AIRPORT_CITY_NAMES:
        return AIRPORT_CITY_NAMES[code_upper]
    if code_upper in SPANISH_CITY_ALIASES:
        return SPANISH_CITY_ALIASES[code_upper]
    # Estacion: 'Sevilla - Santa Justa' -> 'Sevilla'
    if " - " in code:
        return code.split(" - ")[0].strip()
    return code


def _get_coords(code: str) -> tuple[float, float] | None:
    """Obtiene coordenadas para un codigo de aeropuerto."""
    return CITY_COORDS.get(code.upper())


# Ciudad -> codigo de aeropuerto (inverso de AIRPORT_CITY_NAMES), para poder
# pedir clima de cualquier ciudad detectada en el calendario, no solo la
# de origen del primer vuelo.
_CITY_NAME_TO_CODE: dict[str, str] = {}
for _code, _name in AIRPORT_CITY_NAMES.items():
    _CITY_NAME_TO_CODE.setdefault(_name, _code)


def _get_city_code(city_name: str) -> str | None:
    """Convierte un nombre de ciudad ('Roma') a su codigo de aeropuerto ('FCO')."""
    if not city_name:
        return None
    return _CITY_NAME_TO_CODE.get(city_name)


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


async def fetch_weather_for_calendar(calendar: list[dict]) -> list[dict]:
    """Obtiene el clima real de CADA ciudad del calendario (no solo la primera).

    Agrupa las fechas por ciudad, pide el clima de cada una en paralelo y
    devuelve una lista con un elemento por fecha (con la ciudad a la que
    corresponde), en el mismo orden que `calendar`.
    """
    city_dates: dict[str, list[str]] = {}
    for day in calendar:
        city = day.get("city")
        if city:
            city_dates.setdefault(city, []).append(day["date"])

    cities = list(city_dates.keys())
    codes = [_get_city_code(c) for c in cities]
    tasks = [
        fetch_weather(code, min(city_dates[city]), max(city_dates[city]))
        if code and _get_coords(code) else _empty_weather()
        for city, code in zip(cities, codes)
    ]
    results = await asyncio.gather(*tasks)

    weather_by_date: dict[str, dict] = {}
    for city, city_weather in zip(cities, results):
        for w in city_weather:
            weather_by_date[w["date"]] = {**w, "city": city}

    return [weather_by_date[d["date"]] for d in calendar if d["date"] in weather_by_date]


async def _empty_weather() -> list[dict]:
    """Placeholder para ciudades sin coordenadas conocidas, mantiene la forma awaitable de las tareas paralelas."""
    return []


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

    trains = [p for p in passes if p.get("kind") == "train"]
    trains_sorted = _sort_by_date(trains, date_key="flight_date", time_key="flight_time")

    # Ciudad inicial: origen del primer vuelo o tren
    current_city: str | None = None
    if flights_sorted:
        current_city = _get_city_name(flights_sorted[0].get("from", ""))
    elif trains_sorted:
        current_city = _get_city_name(trains_sorted[0].get("from", ""))

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
    for t in trains_sorted:
        fd = t.get("flight_date", "")
        if not fd:
            continue
        transport_events.append({
            "date": fd,
            "time": t.get("flight_time", "") or "12:00",
            "to_city": _get_city_name(t.get("to", "")),
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

    # --- Vuelos (PDF/imagen) ---
    for f in flights_sorted:
        fd = f.get("flight_date", "")
        if fd not in days:
            continue
        flight_time = f.get("flight_time", "") or ""
        gate_close = f.get("gate_close_time", "") or ""
        airline = f.get("airline", "")
        flight_no = f.get("flight", "")
        from_city = _get_city_name(f.get("from", ""))
        to_city = _get_city_name(f.get("to", ""))
        duration_min = _estimate_transport_duration_minutes("flight", f.get("from", ""), f.get("to", ""))
        arrival_guard_min = _parse_time_to_minutes(flight_time)
        if arrival_guard_min is not None:
            arrival_guard_min += duration_min
        # Enriquecer descripcion con horas reales si existen
        time_extra = ""
        if flight_time:
            time_extra += f" (salida {flight_time})"
        if gate_close:
            time_extra += f" — cierre puertas {gate_close}"
        days[fd]["events"].append({
            "type": "flight_arrival",
            "transport_kind": "flight",
            "time": flight_time,
            "gate_close": gate_close,
            "from_city": from_city,
            "to_city": to_city,
            "estimated_duration_min": duration_min,
            "estimated_arrival_time": _format_minutes_to_time(arrival_guard_min),
            "no_activities_before_minute": arrival_guard_min,
            "no_activities_before": _format_minutes_to_time(arrival_guard_min),
            "description": f"Llegada {airline}{flight_no} desde {from_city}{time_extra}",
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
        duration_min = _estimate_transport_duration_minutes("train", from_raw, to_raw)
        arrival_guard_min = _parse_time_to_minutes(time_str)
        if arrival_guard_min is not None:
            arrival_guard_min += duration_min
        days[fd]["events"].append({
            "type": "train_arrival",
            "transport_kind": "train",
            "time": time_str,
            "from_city": from_city,
            "to_city": to_city,
            "estimated_duration_min": duration_min,
            "estimated_arrival_time": _format_minutes_to_time(arrival_guard_min),
            "no_activities_before_minute": arrival_guard_min,
            "no_activities_before": _format_minutes_to_time(arrival_guard_min),
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
        duration_min = _estimate_transport_duration_minutes("flight", s.get("from", ""), s.get("to_city", s.get("to", "")))
        arrival_guard_min = _parse_time_to_minutes(s.get("time", "") or "")
        if arrival_guard_min is not None:
            arrival_guard_min += duration_min
        days[fd]["events"].append({
            "type": "flight_arrival",
            "transport_kind": "flight",
            "time": s.get("time", "") or "",
            "from_city": from_city,
            "to_city": to_city,
            "estimated_duration_min": duration_min,
            "estimated_arrival_time": _format_minutes_to_time(arrival_guard_min),
            "no_activities_before_minute": arrival_guard_min,
            "no_activities_before": _format_minutes_to_time(arrival_guard_min),
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
        duration_min = _estimate_transport_duration_minutes("train", s.get("from", ""), s.get("to", ""))
        arrival_guard_min = _parse_time_to_minutes(s.get("time", "") or "")
        if arrival_guard_min is not None:
            arrival_guard_min += duration_min
        days[fd]["events"].append({
            "type": "train_arrival",
            "transport_kind": "train",
            "time": s.get("time", "") or "",
            "from_city": from_city,
            "to_city": to_city,
            "estimated_duration_min": duration_min,
            "estimated_arrival_time": _format_minutes_to_time(arrival_guard_min),
            "no_activities_before_minute": arrival_guard_min,
            "no_activities_before": _format_minutes_to_time(arrival_guard_min),
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
        extra = s.get("description", "") or ""
        label = f"Reserva: {name}" + (f" — {extra}" if extra else "")
        days[fd]["events"].append({
            "type": "activity",
            "time": time_str,
            "description": label,
            "city": _get_city_name(s.get("city", "")) or s.get("city", ""),
        })

    # Ordenar eventos por hora dentro de cada día
    for d in days.values():
        d["events"].sort(key=lambda e: e["time"] or "23:59")

    for d in days.values():
        transport_constraints = [
            {
                "kind": e.get("transport_kind", "transporte"),
                "route": (
                    f"{e.get('from_city', '')} → {e.get('to_city', '')}"
                    if e.get("from_city") and e.get("to_city")
                    else e.get("to_city") or e.get("from_city") or "trayecto"
                ),
                "departure_time": e.get("time") or "",
                "estimated_arrival_time": e.get("estimated_arrival_time") or "",
                "no_activities_before": e.get("no_activities_before") or "",
                "no_activities_before_minute": e.get("no_activities_before_minute"),
            }
            for e in d["events"]
            if e.get("type") in ("flight_arrival", "train_arrival") and e.get("no_activities_before")
        ]
        d["transport_constraints"] = transport_constraints

    # Calcular bloques libres aprovechando horas reales de vuelos/trenes
    for d in days.values():
        events_with_time = [e for e in d["events"] if e["time"]]
        occupied_slots: set[str] = set()
        earliest_event: int | None = None
        for e in events_with_time:
            h = int(e["time"].split(":")[0])
            if earliest_event is None or h < earliest_event:
                earliest_event = h
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
        if d.get("transport_constraints"):
            latest_guard_item = max(
                d["transport_constraints"],
                key=lambda c: c.get("no_activities_before_minute")
                if isinstance(c.get("no_activities_before_minute"), int)
                else -1,
            )
            latest_guard = latest_guard_item.get("no_activities_before") or ""
            if latest_guard:
                free_blocks.append({
                    "start": None,
                    "end": None,
                    "label": f"No sugerir actividades antes de {latest_guard} (llegada estimada)",
                })
        # Si sabemos que el primer evento es tarde (ej: vuelo llega a las 09:15),
        # ajustamos las franjas para que el LLM sepa que la mañana está ocupada
        # solo hasta cierta hora y el resto del día queda libre
        if "morning" in occupied_slots and earliest_event is not None and earliest_event < 12:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Mañana ocupada hasta ~%d:00 (llegada de vuelo)" % earliest_event,
            })
        if "afternoon" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Tarde libre (12:00—18:00)",
            })
        if "evening" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Noche libre (18:00—24:00)",
            })
        elif "afternoon" not in occupied_slots:
            # Si la tarde está libre, mencionamos la noche también aunque esté ocupada
            pass

        # Si no hay franjas ocupadas, día completamente libre
        if not occupied_slots:
            free_blocks = [
                {"start": None, "end": None, "label": "Mañana (06:00—12:00)"},
                {"start": None, "end": None, "label": "Tarde (12:00—18:00)"},
                {"start": None, "end": None, "label": "Noche (18:00—24:00)"},
            ]

        if not free_blocks:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Día completo con eventos — tiempo libre entre medias",
            })

        d["free_blocks"] = free_blocks
        d["has_fixed_events"] = len(d["events"]) > 0

    return [days[d] for d in all_dates]


# --- DeepSeek LLM ---

def _extract_travelers(passes: list[dict]) -> list[str]:
    """Nombres unicos de pasajeros detectados en los billetes escaneados."""
    return list(dict.fromkeys(
        p.get("name", "").strip() for p in passes if p.get("name")
    ))


def _travelers_group_label(count: int) -> str:
    """Etiqueta de composicion del grupo segun el nº de pasajeros detectados."""
    if count <= 1:
        return "viaje individual"
    if count == 2:
        return "pareja o dos acompañantes"
    return f"grupo de {count} personas"


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

    transport_constraints_text = _build_transport_constraints_text(calendar)

    # --- Clima ---
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']} ({w.get('city', dest_str)}): {w['condition']}, "
            f"{w['temp_min']}–{w['temp_max']}°C, precip {w.get('precipitation_mm') or 0}mm, "
            f"viento {w.get('wind_kmh', '?')}km/h"
            for w in weather[:num_days]
        )

    # --- Viajeros ---
    travelers = _extract_travelers(passes)
    travelers_block = ""
    if travelers:
        n = len(travelers)
        travelers_block = f"""
=== VIAJEROS ===
{n} pasajero(s) detectado(s): {", ".join(travelers)} — {_travelers_group_label(n)}.
Ajusta el tamaño de las reservas sugeridas (mesas, habitaciones) y prioriza
actividades y restaurantes aptos para este grupo.
"""

    # --- Construir el prompt ---
    prompt = f"""Eres un agente de viajes experto. Genera un itinerario enriquecido a partir del calendario base que te proporciono.

=== TÍTULO DEL VIAJE ===
{trip_title or dest_str}
Este es el nombre del viaje. El destino PRINCIPAL es {dest_str}.

=== DATOS DEL VIAJE ===
Destinos: {dest_str}
Días totales: {num_days}
Fechas: {all_dates[0]} → {all_dates[-1]}
{travelers_block}
=== CALENDARIO BASE (extraído de tus reservas reales) ===
Este es el esqueleto del viaje. Los eventos marcados como "fijos" son inamovibles
(vuelos, trenes, hoteles, restaurantes y actividades ya reservados).
Tu tarea es RELLENAR LOS HUECOS LIBRES con sugerencias.

{calendar_text}

=== RESTRICCIONES DE LLEGADA (OBLIGATORIAS) ===
{transport_constraints_text}

=== CLIMA PREVISTO (por ciudad y fecha reales) ===
{weather_str or "No disponible — usa clima histórico de la época."}

=== TU TAREA ===
A partir del calendario base, genera un JSON con:

1. daily_itinerary [{num_days} elementos]: Para cada día, respeta los eventos fijos tal cual aparecen en el calendario base. En los bloques libres, sugiere actividades realistas para esa ciudad, EL CLIMA DE ESE DÍA CONCRETO y la franja horaria. No inventes eventos que contradigan los fijos. La ciudad de cada día ya viene determinada en el calendario base — úsala. Incluye "travel_reminders": array de recordatorios breves; obligatorio en días con vuelo/tren y vacío en el resto.
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
- Si un día tiene transporte, NO programes actividades antes de la hora indicada en "RESTRICCIONES DE LLEGADA".
- Las restricciones de llegada son duras y tienen prioridad sobre los bloques libres.
- Si un vuelo o tren llega tarde, deja vacíos morning y/o afternoon hasta la hora segura de llegada.
- En cada día con vuelo o tren (ida o vuelta), añade 2-4 "travel_reminders" breves y accionables: antelación recomendada, posible hora punta y cómo llegar a aeropuerto/estación.
- Si hay "cierre puertas" en un vuelo, sugiere salir hacia el aeropuerto al menos 45 min antes de esa hora.
- CLIMA: si ese día hay lluvia, tormenta o nieve, prioriza planes bajo techo (museos, mercados, gastronomía) sobre planes al aire libre; con buen tiempo, favorece miradores, parques o rutas a pie.
- RITMO: no metas más de una visita "pesada" (museo grande, ruta larga) por franja horaria, y suaviza el día siguiente a un desplazamiento largo o llegada nocturna.
- VARIEDAD: no repitas el mismo lugar, restaurante o tipo de actividad (p.ej. dos museos el mismo día) salvo que sea imprescindible.
- COHERENCIA: los restaurantes y lugares sugeridos en daily_itinerary deben coincidir con los listados en "restaurants"/"places_of_interest" — no inventes nombres adicionales sueltos.
- Si hay varios viajeros, prioriza actividades y reservas aptas para grupo (aforo, mesas, habitaciones).
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
      "travel_reminders": ["Recordatorio breve ≤10 palabras"],
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

    origin = ""
    if flights:
        origin = _get_city_name(flights[0].get("from", ""))
    elif trains:
        # Ordenar trenes por fecha para detectar correctamente el origen
        sorted_trains = sorted(
            [t for t in trains if t.get("flight_date")],
            key=lambda t: t["flight_date"]
        )
        if sorted_trains:
            origin = _get_city_name(sorted_trains[0].get("from", ""))
        else:
            origin = _get_city_name(trains[0].get("from", ""))

    dests = _real_flight_destinations(flights, seg_hotels, origin)
    for t in trains:
        city = _get_city_name(t.get("to", ""))
        if city and city != origin and city not in dests:
            dests.append(city)
        elif not city:
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
        prefix = "Viaje en tren a " if (not flights and trains) else "Viaje a "
        return f"{prefix}{' y '.join(dests[:3])}"
    if flights:
        return f"Viaje a {_get_city_name(flights[0].get('to',''))}"
    if trains:
        to_city = _get_city_name(trains[0].get("to", ""))
        if to_city:
            return f"Viaje en tren a {to_city}"
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
            "travel_reminders": [],
            "meal_suggestions": {"lunch": "", "dinner": ""},
        }
        for ev in day["events"]:
            desc = ev["description"]
            if ev["type"] in ("flight_arrival", "train_arrival"):
                entry["morning"]["activities"].append(desc)
                kind = "aeropuerto" if ev["type"] == "flight_arrival" else "estación"
                no_before = ev.get("no_activities_before")
                if no_before:
                    entry["travel_reminders"].append(
                        f"Evita planes antes de {no_before} por traslado."
                    )
                entry["travel_reminders"].append(
                    f"Sal con antelación extra hacia {kind} en hora punta."
                )
                entry["travel_reminders"].append(
                    f"Prioriza tren/metro o taxi directo hacia {kind}."
                )
            elif ev["type"] in ("restaurant",):
                entry["evening"]["activities"].append(desc)
                entry["meal_suggestions"]["dinner"] = desc.replace("Cena: ", "")
            elif ev["type"] in ("activity",):
                entry["afternoon"]["activities"].append(desc)
            else:
                entry["morning"]["activities"].append(desc)

        if entry["travel_reminders"]:
            deduped = list(dict.fromkeys(entry["travel_reminders"]))
            entry["travel_reminders"] = deduped[:4]

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


async def generate_itinerary(
    passes: list[dict],
    segments: list[dict] | None = None,
    session_id: str | None = None,
) -> dict:
    """Genera un itinerario completo usando DeepSeek LLM y Open-Meteo.

    Args:
        passes: Lista de pases extraidos de billetes.
        segments: Segmentos manuales (hoteles, vuelos, etc.).
        session_id: ID de sesion para tracking de tokens (opcional).
    """
    from datetime import timedelta

    if segments is None:
        segments = []

    # Re-ejecutar infer_years con TODOS los pases juntos:
    # en la API cada extract corre infer_years por separado y no detecta
    # rollover de año (DOY 365 -> 002). Aqui con todos los pases juntos
    # sí detecta el cruce y corrige las fechas.
    infer_years(passes)

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

    # Fechas de trenes (pases)
    for p in passes:
        if p.get("kind") == "train":
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

    # 3. Obtener clima real de cada ciudad visitada (no solo la primera),
    # usando el calendario ya calculado para el guardrail anterior.
    weather = await fetch_weather_for_calendar(calendar_check)

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

        # Registrar consumo real de tokens de la API
        if session_id and response.usage:
            from token_tracker import record_usage
            token_stats = record_usage(
                session_id,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            print(f"[deepseek] tokens: {response.usage.prompt_tokens} in + "
                  f"{response.usage.completion_tokens} out = "
                  f"{response.usage.total_tokens} total "
                  f"(sesion: {token_stats['total_tokens_used']}/"
                  f"{token_stats['max_tokens']})")
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

    # Incluir estadisticas de tokens (app.py las extrae con pop)
    if session_id and response.usage:
        itinerary["_token_usage"] = token_stats

    # Segundo check de contenido IA: coherencia, alucinaciones, repeticiones
    validation = validate_itinerary(itinerary)
    itinerary["_validation"] = validation

    return itinerary


def _serialize_for_prompt(items: list[dict], keys: list[str]) -> str:
    """Serializa items para incluir en el prompt."""
    lines = []
    for i, item in enumerate(items, 1):
        parts = [f"{i}. "]
        for k in keys:
            val = item.get(k)
            if val:
                if isinstance(val, list):
                    parts.append(f"{k}: {', '.join(val)}")
                else:
                    parts.append(f"{k}: {val}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if lines else "(ninguno)"


def expand_section(
    passes: list[dict],
    segments: list[dict],
    existing_itinerary: dict,
    section: str,
    session_id: str | None = None,
) -> dict:
    """Genera mas recomendaciones de una seccion concreta del itinerario.

    Returns dict with either:
      - {"items": [...], "section": str}
      - {"error": str}
      - For "visit": {"places_of_interest": [...], "historical_sites": [...], "section": "visit"}
      - For "tips": {"transport_tips": [...], "general_tips": [...], "cultural_notes": [...], "section": "tips"}
    """
    from datetime import timedelta

    if segments is None:
        segments = []

    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    all_dates_set = set()
    for p in passes:
        fd = p.get("flight_date")
        if fd:
            all_dates_set.add(fd)
    for s in segments:
        fd = s.get("date") or s.get("check_in")
        if fd:
            all_dates_set.add(fd)

    all_dates = sorted(all_dates_set)
    dates_str = ", ".join(all_dates) if all_dates else "fechas no especificadas"

    all_cities = list(dict.fromkeys(
        d.get("city") for d in _build_daily_calendar(passes, segments, all_dates)
        if d.get("city")
    ))
    cities = [c for c in all_cities if c != origin_city] or all_cities[:1]
    dest_str = ", ".join(cities) if cities else "destino desconocido"

    passenger_names = list(dict.fromkeys(
        p.get("name", "") for p in passes if p.get("name")
    ))
    passengers_str = ", ".join(passenger_names) if passenger_names else "no especificado"

    overview = existing_itinerary.get("destination_overview", "")
    weather = existing_itinerary.get("weather", [])
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']}: {w['condition']}, max {w['temp_max']}°C, min {w['temp_min']}°C"
            for w in weather[:7]
        )

    passes_str = ""
    for p in passes:
        route = f"{p.get('from', '?')} → {p.get('to', '?')}"
        d = p.get("flight_date", "")
        t = p.get("flight_time", "")
        carrier = p.get("train") or f"{p.get('airline', '')}{p.get('flight', '')}"
        passes_str += f"  - {route} | {d} {t} | {carrier} | {p.get('kind', 'flight')}\n"

    seg_str = ""
    for s in segments:
        stype = s.get("type", "")
        if stype == "flight":
            seg_str += f"  - Vuelo: {s.get('airline','')}{s.get('flight_number','')} {s.get('from','')}→{s.get('to','')} {s.get('date','')} {s.get('time','')}\n"
        elif stype == "train":
            seg_str += f"  - Tren: {s.get('operator','')} {s.get('train_number','')} {s.get('from','')}→{s.get('to','')} {s.get('date','')}\n"
        elif stype == "hotel":
            seg_str += f"  - Hotel: {s.get('name','')} {s.get('city','')} {s.get('check_in','')}→{s.get('check_out','')}\n"
        elif stype == "car":
            seg_str += f"  - Coche: {s.get('company','')} {s.get('city','')} {s.get('pickup_date','')}→{s.get('return_date','')}\n"
        elif stype == "restaurant":
            seg_str += f"  - Restaurante: {s.get('name','')} {s.get('city','')} {s.get('date','')}\n"
        elif stype == "activity":
            seg_str += f"  - Actividad: {s.get('name','')} {s.get('city','')} {s.get('date','')} - {s.get('description','')}\n"

    section_prompts = {
        "restaurants": {
            "section_name": "restaurantes",
            "existing": _serialize_for_prompt(existing_itinerary.get("restaurants", []), ["name", "type", "price_range"]),
            "instruction": "Devuelve un array JSON con 3-5 nuevos restaurantes que sean DIFERENTES a los ya listados.",
            "output_schema": '{"name": "Nombre restaurante", "type": "cocina catalana", "description": "2-3 frases llamativas", "price_range": "15-30€"}',
        },
        "hotels": {
            "section_name": "hospedaje",
            "existing": _serialize_for_prompt(existing_itinerary.get("hotels", []), ["name", "zone", "price_range"]),
            "instruction": "Devuelve un array JSON con 3-5 nuevos hoteles/alojamientos DIFERENTES a los ya listados.",
            "output_schema": '{"name": "Nombre hotel", "zone": "barrio o zona", "description": "2-3 frases", "price_range": "80-150€", "highlights": ["piscina", "vistas"]}',
        },
        "visit": {
            "section_name": "lugares que visitar",
            "existing": _serialize_for_prompt(
                existing_itinerary.get("places_of_interest", []) + existing_itinerary.get("historical_sites", []),
                ["name", "type", "period"],
            ),
            "instruction": "Devuelve un objeto JSON con dos arrays: 'places_of_interest' (no historicos) y 'historical_sites' (sitios historicos con 'period' y 'curiosity'). 2-3 por categoria. DIFERENTES a los ya listados.",
            "output_schema": '{"places_of_interest": [{"name": "...", "type": "museo", "description": "...", "tips": ["..."]}], "historical_sites": [{"name": "...", "period": "s.XIX", "description": "...", "curiosity": "... rumor curioso"}]}',
        },
        "tips": {
            "section_name": "consejos",
            "existing": _serialize_for_prompt(
                [{"tip": t} for t in existing_itinerary.get("transport_tips", [])]
                + [{"tip": t} for t in existing_itinerary.get("general_tips", [])]
                + [{"tip": t} for t in existing_itinerary.get("cultural_notes", [])],
                ["tip"],
            ),
            "instruction": "Devuelve un objeto JSON con 3 arrays: 'transport_tips', 'general_tips', 'cultural_notes'. 2-3 tips por categoria. DIFERENTES a los ya listados.",
            "output_schema": '{"transport_tips": ["tip transporte..."], "general_tips": ["tip general..."], "cultural_notes": ["nota cultural..."]}',
        },
    }

    sec = section_prompts.get(section)
    if not sec:
        return {"error": "Seccion desconocida"}

    prompt = f"""Eres un guia local experto. El usuario pide MAS recomendaciones para su viaje.

VIAJE: {dest_str}
FECHAS: {dates_str}
PASAJEROS: {passengers_str}
{chr(10) + "RESUMEN: " + overview[:500] if overview else ""}

CLIMA PREVISTO:
{weather_str or "(no disponible)"}

BILLETES:
{passes_str if passes_str else "(sin billetes)"}
RESERVAS MANUALES:
{seg_str if seg_str else "(ninguna)"}

YA RECOMENDADO ({sec['section_name']}):
{sec['existing']}

{sec['instruction']}

Estructura esperada del JSON:
{sec['output_schema']}

Responde SOLO el JSON, sin markdown ni texto alrededor."""

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Eres un guia de viajes experto. Responde solo JSON valido, sin markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=4096,
        )
        content = response.choices[0].message.content or "{}"

        if session_id and response.usage:
            from token_tracker import record_usage
            record_usage(session_id, response.usage.prompt_tokens, response.usage.completion_tokens)

    except Exception as e:
        print(f"[deepseek expand] Error: {e}")
        return {"error": f"Error al expandir {sec['section_name']}: {e}"}

    new_items = _parse_expand_response(content, section)

    if section == "visit":
        return {
            "places_of_interest": new_items.get("places_of_interest", []),
            "historical_sites": new_items.get("historical_sites", []),
            "section": section,
        }
    if section == "tips":
        return {
            "transport_tips": new_items.get("transport_tips", []),
            "general_tips": new_items.get("general_tips", []),
            "cultural_notes": new_items.get("cultural_notes", []),
            "section": section,
        }
    if isinstance(new_items, list):
        return {"items": new_items, "section": section}
    return {"items": [], "section": section}


def _parse_expand_response(content: str, section: str) -> dict | list:
    """Parsea la respuesta JSON del LLM con fallback robusto."""
    import re

    try:
        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return [] if section in ("restaurants", "hotels") else {}


def _infer_origin_city_from_transport(passes: list[dict], segments: list[dict]) -> str:
    flight_legs: list[tuple[date, str, str]] = []
    for p in passes:
        if p.get("kind") != "flight":
            continue
        from_city = _get_city_name(p.get("from", ""))
        to_city = _get_city_name(p.get("to", ""))
        flight_date = p.get("flight_date", "")
        if not (from_city and to_city and flight_date):
            continue
        try:
            flight_legs.append((date.fromisoformat(flight_date), from_city, to_city))
        except (ValueError, TypeError):
            continue

    if len(flight_legs) >= 2:
        flight_legs.sort(key=lambda leg: leg[0])
        first_leg = flight_legs[0]
        last_leg = flight_legs[-1]
        same_year = first_leg[0].year == last_leg[0].year
        long_gap = (last_leg[0] - first_leg[0]).days > 180
        reversed_route = first_leg[1] == last_leg[2] and first_leg[2] == last_leg[1]
        year_rollover_pattern = first_leg[0].month <= 2 and last_leg[0].month >= 11
        if same_year and long_gap and reversed_route and year_rollover_pattern:
            return last_leg[1]

    transport_starts: list[tuple[str, str, str]] = []

    for p in passes:
        kind = p.get("kind")
        if kind not in ("flight", "train"):
            continue
        from_city = _get_city_name(p.get("from", ""))
        travel_date = p.get("flight_date", "")
        travel_time = p.get("flight_time", "") or ""
        if from_city and travel_date:
            transport_starts.append((travel_date, travel_time, from_city))

    for s in segments:
        seg_type = s.get("type")
        if seg_type not in ("flight", "train"):
            continue
        from_city = _get_city_name(s.get("from", ""))
        travel_date = s.get("date", "")
        travel_time = s.get("time", "") or ""
        if from_city and travel_date:
            transport_starts.append((travel_date, travel_time, from_city))

    if transport_starts:
        transport_starts.sort(key=lambda item: (item[0], item[1]))
        return transport_starts[0][2]

    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    if flights_sorted:
        return _get_city_name(flights_sorted[0].get("from", ""))

    trains = [p for p in passes if p.get("kind") == "train"]
    trains_sorted = _sort_by_date(trains)
    if trains_sorted:
        return _get_city_name(trains_sorted[0].get("from", ""))

    return ""


async def generate_quiz(
    passes: list[dict],
    segments: list[dict] | None = None,
    session_id: str | None = None,
) -> dict:
    if segments is None:
        segments = []

    infer_years(passes)

    flights = [p for p in passes if p.get("kind") == "flight"]
    origin_city = _infer_origin_city_from_transport(passes, segments)
    all_dates_set: set[str] = set()
    for p in passes:
        fd = p.get("flight_date")
        if fd:
            all_dates_set.add(fd)
    for s in segments:
        fd = s.get("date") or s.get("check_in")
        if fd:
            all_dates_set.add(fd)

    all_dates = sorted(all_dates_set) if all_dates_set else []
    calendar = _build_daily_calendar(passes, segments, all_dates, origin_city=origin_city)

    all_cities = list(dict.fromkeys(d["city"] for d in calendar if d["city"]))
    destinations = [c for c in all_cities if c and c != origin_city]

    if not destinations:
        seg_hotels = [s for s in segments if s.get("type") == "hotel"]
        destinations = _real_flight_destinations(flights, seg_hotels, origin_city)

    if not destinations:
        trains = [p for p in passes if p.get("kind") == "train"]
        for t in trains:
            city = _get_city_name(t.get("to", ""))
            if city and city != origin_city and city not in destinations:
                destinations.append(city)

    if not destinations:
        return {"error": "No se pudieron determinar los destinos del viaje", "questions": []}

    dest_str = ", ".join(destinations)

    prompt = f"""Eres un creador de quizzes de viaje. Genera 10 preguntas tipo test sobre los destinos de este viaje.

DESTINOS: {dest_str}
VIAJE: {', '.join(all_dates) if all_dates else "fechas no especificadas"}

=== REGLAS ===
- 10 preguntas cortas y faciles, en español
- Cada pregunta tiene 3 opciones de respuesta, solo UNA correcta
- Las preguntas deben ser entretenidas y educativas sobre {dest_str}
- Basate en hechos reales: historia, cultura, gastronomia, geografia, monumentos, curiosidades
- NO incluir preguntas sobre el origen del viaje ({origin_city}), SOLO sobre los destinos
- Dificultad: facil — apto para viajeros casuales
- La respuesta correcta debe estar mezclada aleatoriamente entre las 3 opciones
- Las opciones incorrectas deben ser verosimiles, no absurdas

=== FORMATO DE SALIDA ===
Responde UNICAMENTE con el JSON. Sin markdown, sin explicaciones.

{{
  "questions": [
    {{
      "question": "Texto de la pregunta?",
      "options": ["opcion A", "opcion B", "opcion C"],
      "correct_index": 0
    }}
  ]
}}"""

    if not DEEPSEEK_API_KEY:
        return {
            "error": "DEEPSEEK_API_KEY no configurada",
            "questions": [],
            "destinations": destinations,
        }

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Eres un creador de quizzes de viaje. Responde solo JSON valido, sin markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=8192,
        )
        content = response.choices[0].message.content or "{}"

        if session_id and response.usage:
            from token_tracker import record_usage
            record_usage(session_id, response.usage.prompt_tokens, response.usage.completion_tokens)

    except Exception as e:
        print(f"[deepseek quiz] Error: {e}")
        return {"error": f"Error generando quiz: {e}", "questions": []}

    questions = _parse_quiz_response(content)
    if not questions:
        return {
            "error": "No se pudo parsear la respuesta del quiz",
            "questions": [],
            "destinations": destinations,
            "raw_response": content[:1000],
        }

    validated = _validate_quiz_questions(questions)
    _shuffle_quiz_options(validated)

    # Segundo check de contenido IA para el cuestionario
    quiz_validation = validate_quiz(validated)

    return {"questions": validated, "destinations": destinations, "_validation": quiz_validation}


def _shuffle_quiz_options(questions: list[dict]):
    import random
    for q in questions:
        opts = q.get("options", [])
        if len(opts) != 3:
            continue
        idx = q.get("correct_index", 0)
        if not isinstance(idx, int) or idx < 0 or idx >= 3:
            idx = 0
        correct_text = opts[idx]
        indices = list(range(3))
        random.shuffle(indices)
        q["options"] = [opts[i] for i in indices]
        q["correct_index"] = q["options"].index(correct_text)


def _validate_quiz_questions(questions: list[dict]) -> list[dict]:
    valid = []
    for q in questions:
        if not q.get("question") or not q.get("options"):
            continue
        opts = q["options"]
        if len(opts) != 3:
            continue
        idx = q.get("correct_index", 0)
        if not isinstance(idx, int) or idx < 0 or idx >= 3:
            idx = 0
        valid.append({
            "question": q["question"],
            "options": opts,
            "correct_index": idx,
        })
    return valid if len(valid) >= 8 else questions


def _parse_quiz_response(content: str) -> list[dict] | None:
    import re

    try:
        parsed = json.loads(content)
        questions = parsed.get("questions", [])
        if questions and isinstance(questions, list):
            return questions
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            parsed = json.loads(match.group())
            return parsed.get("questions", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return None
