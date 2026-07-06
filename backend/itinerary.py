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

DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY_PLACEHOLDER"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

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


def _get_city_name(code: str) -> str:
    """Convierte codigo de aeropuerto a nombre de ciudad."""
    return AIRPORT_CITY_NAMES.get(code.upper(), code)


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


# --- DeepSeek LLM ---

def _build_itinerary_prompt(passes: list[dict], segments: list[dict], weather: list[dict], all_dates: list[str], num_days: int) -> str:
    """Construye el prompt para DeepSeek basado en los datos del viaje."""

    # Extraer info de pases (PDFs escaneados)
    flights = [p for p in passes if p.get("kind") == "flight"]
    trains = [p for p in passes if p.get("kind") == "train"]

    # Extraer info de segmentos manuales
    seg_flights = [s for s in segments if s.get("type") == "flight"]
    seg_trains = [s for s in segments if s.get("type") == "train"]
    seg_hotels = [s for s in segments if s.get("type") == "hotel"]
    seg_cars = [s for s in segments if s.get("type") == "car"]
    seg_restaurants = [s for s in segments if s.get("type") == "restaurant"]
    seg_activities = [s for s in segments if s.get("type") == "activity"]

    # Destinos (de vuelos extraidos + manuales)
    destinations = []
    for p in flights:
        to_city = _get_city_name(p.get("to", ""))
        if to_city and to_city not in destinations:
            destinations.append(to_city)
    for s in seg_flights:
        city = s.get("to_city", s.get("to", ""))
        if city and city not in destinations:
            destinations.append(city)
    for s in seg_hotels:
        city = s.get("city", "")
        if city and city not in destinations:
            destinations.append(city)
    for s in seg_activities:
        city = s.get("city", "")
        if city and city not in destinations:
            destinations.append(city)

    dest_str = ", ".join(destinations) if destinations else "el destino indicado"

    # Fechas explicitas
    dates_list = ", ".join(all_dates)
    date_range = f"del {all_dates[0]} al {all_dates[-1]}" if all_dates else ""

    # Info de vuelos (PDFs)
    flight_info = ""
    for p in flights:
        airline = p.get("airline", "")
        flight = p.get("flight", "")
        from_city = _get_city_name(p.get("from", ""))
        to_city = _get_city_name(p.get("to", ""))
        flight_date = p.get("flight_date", "")
        flight_info += f"- {airline}{flight}: {from_city} → {to_city} ({flight_date})\n"

    # Info de vuelos manuales
    for s in seg_flights:
        flight_info += f"- {s.get('airline','')}{s.get('flight_number','')}: {s.get('from','')} → {s.get('to','')} ({s.get('date','')} {s.get('time','')})\n"

    # Info de trenes
    for p in trains:
        flight_info += f"- Tren {p.get('train','')}: PNR {p.get('pnr','')} ({p.get('flight_date','')} {p.get('flight_time','')})\n"
    for s in seg_trains:
        flight_info += f"- Tren {s.get('operator','')} {s.get('train_number','')}: {s.get('from','')} → {s.get('to','')} ({s.get('date','')} {s.get('time','')})\n"

    # Hoteles
    hotel_info = ""
    for s in seg_hotels:
        hotel_info += f"- {s.get('name','')}: {s.get('city','')}, check-in {s.get('check_in','')}, check-out {s.get('check_out','')}\n"

    # Coches
    car_info = ""
    for s in seg_cars:
        car_info += f"- {s.get('company','')}: {s.get('city','')}, {s.get('pickup_date','')} → {s.get('return_date','')}\n"

    # Restaurantes reservados
    rest_info = ""
    for s in seg_restaurants:
        rest_info += f"- {s.get('name','')}: {s.get('city','')}, {s.get('date','')} {s.get('time','')}\n"

    # Actividades reservadas
    act_info = ""
    for s in seg_activities:
        act_info += f"- {s.get('name','')}: {s.get('city','')}, {s.get('date','')}\n"

    # Clima
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']}: {w['condition']}, max {w['temp_max']}°C, min {w['temp_min']}°C"
            for w in weather[:14]
        )

    prompt = f"""Eres un agente de viajes experto y un motor de generacion de datos estructurados. Tu objetivo es diseñar un itinerario de viaje hiper-personalizado y realista basado estrictamente en los datos proporcionados.

=== DATOS DEL VIAJE ===
- Destino: {dest_str}
- Fechas: {date_range}
- Dias a planificar: {num_days} dias
- Lista de fechas exactas: {dates_list}

=== VUELOS / LOGISTICA DE TRANSPORTE ===
{flight_info or "No disponible de momento. Asume flexibilidad completa de horarios."}

=== ALOJAMIENTO ===
{hotel_info or "No especificado. Sugiere hoteles en las ciudades del viaje."}

=== COCHE DE ALQUILER ===
{car_info or "No especificado."}

=== RESTAURANTES RESERVADOS ===
{rest_info or "No especificado."}

=== ACTIVIDADES RESERVADAS ===
{act_info or "No especificado."}

=== CLIMA PREVISTO ===
{weather_str or "No disponible. Sugiere ropa y planes basados en el clima historico de esta epoca."}

=== INSTRUCCIONES DE CONTENIDO OBLIGATORIAS ===
1. REALISMO ABSOLUTO: Todos los nombres de hoteles, restaurantes, museos y lugares de interes DEBEN existir en la realidad. Esta prohibido inventar o alucinar nombres. Si el usuario ya tiene hotel/reservas, NO sugieras otros para esos dias, integra los existentes.
2. IDIOMAS: Los nombres propios de lugares, calles, hoteles y restaurantes deben ir en su idioma original o de uso local. Los consejos, descripciones y notas culturales deben estar en perfecto español.
3. LOGISTICA DE VUELOS Y HOTELES: 
   - El Dia 1 DEBE adaptarse al horario de llegada. Si el transporte llega tarde, la mañana/tarde debe marcarse como "En transito".
   - El Ultimo Dia DEBE adaptarse al horario de salida. No programes actividades tarde si el transporte sale por la mañana.
   - Si hay hoteles especificados, el check-in/check-out DEBE reflejarse en el daily_itinerary.
4. CONSISTENCIA: Los hoteles, restaurantes y actividades YA RESERVADOS deben aparecer integrados en el daily_itinerary. No sugieras alternativas para dias donde ya hay algo reservado.
5. CANTIDADES: Genera exactamente entre 3 y 4 hoteles (si no hay ya reservados), 4 y 6 restaurantes, 5 y 8 lugares de interes, y 2 y 4 sitios historicos.
6. MULTI-CIUDAD: Si el viaje incluye varias ciudades, el daily_itinerary debe reflejar los desplazamientos entre ellas.

=== FORMATO DE SALIDA ===
Genera UNICAMENTE un objeto JSON estrictamente valido que cumpla con el siguiente esquema. No incluyas explicaciones, no incluyas texto introductorio ni de cierre. El resultado debe ser parseable directamente por un sistema.

{{
  "destination_overview": "Breve descripcion del destino y que esperar de este viaje.",
  "weather_summary": "Analisis del clima proporcionado y recomendacion de vestimenta.",
  "hotels": [
    {{
      "name": "Nombre real en idioma local",
      "zone": "Barrio o zona de la ciudad",
      "description": "Por que se elige este hotel.",
      "price_range": "Selecciona uno: €, €€, €€€, €€€€",
      "highlights": ["Ventaja 1", "Ventaja 2"]
    }}
  ],
  "restaurants": [
    {{
      "name": "Nombre real",
      "type": "Tipo de cocina (ej: Tradicional, Fusion, Street food)",
      "description": "Plato recomendado o por que destaca.",
      "price_range": "Selecciona uno: €, €€, €€€, €€€€"
    }}
  ],
  "places_of_interest": [
    {{
      "name": "Nombre real",
      "type": "Categoria (ej: Museo, Parque, Mirador)",
      "description": "Que ver aqui.",
      "tips": ["Consejo practico de visita o mejor hora."]
    }}
  ],
  "historical_sites": [
    {{
      "name": "Nombre real",
      "period": "Epoca historica relevante",
      "description": "Contexto de su importancia.",
      "curiosity": "Dato curioso o anecdota historica poco conocida."
    }}
  ],
  "daily_itinerary": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "theme": "Enfoque o concepto de este dia (ej: Introduccion al centro historico)",
      "morning": {{
        "activities": ["Actividad 1 o estado de transito", "Actividad 2"],
        "description": "Detalle del plan matutino."
      }},
      "afternoon": {{
        "activities": ["Actividad 1", "Actividad 2"],
        "description": "Detalle del plan de la tarde."
      }},
      "evening": {{
        "activities": ["Actividad 1", "Actividad 2"],
        "description": "Detalle del plan nocturno."
      }},
      "meal_suggestions": {{
        "lunch": "Sugerencia de almuerzo (referenciando un restaurante de la lista o zona)",
        "dinner": "Sugerencia de cena (referenciando un restaurante de la lista o zona)"
      }}
    }}
  ],
  "transport_tips": ["Consejo 1 sobre como moverse en el destino", "Consejo 2"],
  "general_tips": ["Consejo de seguridad, dinero o costumbres locales"],
  "cultural_notes": ["Dato cultural relevante para entender a los locales"]
}}

REGLAS OBLIGATORIAS:
- Responde SOLO el JSON, sin markdown, sin texto adicional.
- daily_itinerary DEBE tener EXACTAMENTE {num_days} elementos, con estas fechas: {dates_list}.
- El dia 1 es SIEMPRE el dia de llegada. El ultimo dia es el de salida.
- Precios en euros (€). Usa categorias: € (economico), €€ (medio), €€€ (alto), €€€€ (lujo)."""

    return prompt


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

    # 2. Obtener clima para el primer destino con coordenadas
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
    prompt = _build_itinerary_prompt(passes, segments, weather, all_dates, num_days)

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
            temperature=0.7,
            max_tokens=4096,
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
