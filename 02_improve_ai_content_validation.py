#!/usr/bin/env python3
"""
Generador de archivo con validación para contenido generado por IA.
Implementa verificación de consistencia, coherencia y detección de problemas
como alucinaciones, repeticiones e incoherencias en itinerarios y cuestionarios.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

# Tipos basados en el backend actual
class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.valid: bool = True
        
    def add_error(self, message: str):
        self.errors.append(message)
        self.valid = False
        
    def add_warning(self, message: str):
        self.warnings.append(message)
        
    def is_passed(self) -> bool:
        return self.valid

class ContentValidator:
    """Validador principal de contenido para itinerarios y cuestionarios."""
    
    # Ciudades y aeropuertos válidos basados en el backend
    VALID_CITIES = {
        'Madrid', 'Barcelona', 'Londres', 'París', 'Roma', 'Amsterdam',
        'Milán', 'Venecia', 'Nápoles', 'Lisboa', 'Oporto', 'Faro',
        'Sevilla', 'Bilbao', 'Valencia', 'Alicante', 'Palma de Mallorca',
        'Málaga', 'San Sebastián', 'Santiago de Compostela', 'Granada',
        'Zaragoza', 'Almería', 'Murcia', 'Ciudad de México', 'Buenos Aires',
        'São Paulo', 'Bogotá', 'Quito', 'Lima', 'La Paz'
    }
    
    VALID_AIRPORTS = {
        'MAD', 'BCN', 'LHR', 'ORY', 'CDG', 'AMS', 'FCO', 'PMI', 'AGP', 'SVQ',
        'BIO', 'VLC', 'ALC', 'IBZ', 'TFN', 'LPA', 'TFS', 'EAS', 'SCQ', 'VGO',
        'SDR', 'ZAZ', 'GRX', 'XRY', 'LEI', 'BRU', 'FRA', 'MUC', 'BER', 'MXP',
        'LIN', 'VCE', 'NAP', 'LIS', 'OPO', 'FAO', 'ATH', 'VIE', 'PRG', 'BUD',
        'WAW', 'CPH', 'OSL', 'ARN', 'HEL', 'IST', 'DXB', 'AUH', 'JFK', 'EWR',
        'MIA', 'LAX', 'MEX', 'BOG', 'EZE', 'GRU', 'NRT', 'HND', 'SIN', 'BKK',
        'DOH'
    }
    
    # Tipos de actividades válidas según el schema de diario diario
    VALID_ACTIVITY_TYPES = {
        'flight_arrival', 'train_arrival', 'hotel_checkin', 'car_pickup',
        'restaurant', 'activity'
    }
    
    # Etapas del día válidas
    VALID_DAY_SLOTS = {'morning', 'afternoon', 'evening'}
    
    def validate_itinerary(self, itinerary_data: Dict[str, Any]) -> ValidationResult:
        """Valida un itinerario completo generado por IA."""
        result = ValidationResult()
        
        # 1. Validación de estructura general
        self._validate_itinerary_structure(itinerary_data, result)
        
        # 2. Validación de itinerario diario
        self._validate_daily_itinerary(itinerary_data, result)
        
        # 3. Validación de lugares
        self._validate_places(itinerary_data, result)
        
        # 4. Validación de coherencia
        self._validate_coherence(itinerary_data, result)
        
        # 5. Detección de alucinaciones
        self._detect_hallucinations(itinerary_data, result)
        
        # 6. Detección de repeticiones
        self._detect_repetitions(itinerary_data, result)
        
        return result
    
    def validate_quiz(self, quiz_data: Dict[str, Any]) -> ValidationResult:
        """Valida un cuestionario generado por IA."""
        result = ValidationResult()
        
        # 1. Validación de estructura básica
        if not isinstance(quiz_data, dict):
            result.add_error("El cuestionario debe ser un objeto JSON válido")
            return result
            
        questions = quiz_data.get('questions', [])
        if not isinstance(questions, list):
            result.add_error("El campo 'questions' debe ser una lista")
            return result
            
        if len(questions) < 8:
            result.add_warning(f"El cuestionario tiene {len(questions)} preguntas, recomendado mínimo 8")
        
        # 2. Validación de cada pregunta
        for i, question in enumerate(questions):
            self._validate_quiz_question(question, i, result)
        
        # 3. Validación de destinos
        self._validate_quiz_destinations(quiz_data, result)
        
        return result
    
    def _validate_itinerary_structure(self, data: Dict[str, Any], result: ValidationResult):
        """Valida la estructura general del itinerario."""
        required_fields = {
            'destination_overview': str,
            'daily_itinerary': list,
        }
        
        for field, field_type in required_fields.items():
            if field not in data:
                result.add_error(f"Campo requerido faltante: '{field}'")
            elif not isinstance(data[field], field_type):
                result.add_error(f"Campo '{field}' debe ser de tipo {field_type.__name__}")
        
        # Campos opcionales pero importantes
        optional_fields = {
            'weather_summary': str,
            'weather': list,
            'hotels': list,
            'restaurants': list,
            'places_of_interest': list,
            'historical_sites': list,
            'transport_tips': list,
            'general_tips': list,
            'cultural_notes': list,
        }
        
        for field, field_type in optional_fields.items():
            if field in data and not isinstance(data[field], field_type):
                result.add_error(f"Campo opcional '{field}' debe ser de tipo {field_type.__name__}")
    
    def _validate_daily_itinerary(self, data: Dict[str, Any], result: ValidationResult):
        """Valida el itinerario diario detallado."""
        daily_itinerary = data.get('daily_itinerary', [])
        
        if not daily_itinerary:
            result.add_error("El itinerario diario no puede estar vacío")
            return
        
        for day_index, day in enumerate(daily_itinerary):
            if not isinstance(day, dict):
                result.add_error(f"Elemento {day_index} del itinerario diario debe ser un objeto")
                continue
            
            self._validate_daily_plan(day, day_index, result)
    
    def _validate_daily_plan(self, day: Dict[str, Any], day_index: int, result: ValidationResult):
        """Valida un plan diario individual."""
        required_day_fields = {
            'day_number': int,
            'date': str,
            'city': str,
            'theme': str,
            'morning': dict,
            'afternoon': dict,
            'evening': dict,
            'travel_reminders': list,
            'meal_suggestions': dict,
        }
        
        for field, field_type in required_day_fields.items():
            if field not in day:
                result.add_error(f"Día {day_index + 1}: Campo requerido faltante '{field}'")
            elif not isinstance(day[field], field_type):
                result.add_error(f"Día {day_index + 1}: Campo '{field}' debe ser de tipo {field_type.__name__}")
        
        # Validar cada franja horaria
        for slot in ['morning', 'afternoon', 'evening']:
            slot_data = day.get(slot, {})
            self._validate_day_slot(slot_data, slot, day_index, result)
        
        # Validar fecha
        date_str = day.get('date')
        if date_str:
            self._validate_date(date_str, f"Día {day_index + 1}", result)
    
    def _validate_day_slot(self, slot: Dict[str, Any], slot_name: str, day_index: int, result: ValidationResult):
        """Valida un slot específico del día."""
        required_fields = {
            'activities': list,
            'description': str,
        }
        
        for field in required_fields:
            if field not in slot:
                result.add_warning(f"Día {day_index + 1}, {slot_name}: Campo opcional faltante '{field}'")
            elif not isinstance(slot[field], required_fields[field]):
                result.add_error(f"Día {day_index + 1}, {slot_name}: Campo '{field}' debe ser {required_fields[field].__name__}")
    
    def _validate_places(self, data: Dict[str, Any], result: ValidationResult):
        """Valida hoteles, restaurantes, lugares de interés y sitios históricos."""
        # Validar hotels
        hotels = data.get('hotels', [])
        for i, hotel in enumerate(hotels):
            self._validate_place_entry(hotel, f"hotel[{i}]", ['name', 'zone', 'description', 'price_range', 'highlights'], result)
        
        # Validar restaurants
        restaurants = data.get('restaurants', [])
        for i, restaurant in enumerate(restaurants):
            self._validate_place_entry(restaurant, f"restaurant[{i}]", ['name', 'type', 'description', 'price_range'], result)
        
        # Validar places_of_interest
        poi = data.get('places_of_interest', [])
        for i, place in enumerate(poi):
            self._validate_place_entry(place, f"place_of_interest[{i}]", ['name', 'type', 'description', 'tips'], result)
        
        # Validar historical_sites
        sites = data.get('historical_sites', [])
        for i, site in enumerate(sites):
            self._validate_place_entry(site, f"historical_site[{i}]", ['name', 'period', 'description', 'curiosity'], result)
    
    def _validate_place_entry(self, entry: Dict[str, Any], path: str, required_fields: List[str], result: ValidationResult):
        """Valida una entrada de lugar individual."""
        if not isinstance(entry, dict):
            result.add_error(f"{path}: Debe ser un objeto")
            return
        
        for field in required_fields:
            if field not in entry:
                result.add_error(f"{path}: Campo requerido faltante '{field}'")
            elif not isinstance(entry[field], str) or not entry[field].strip():
                result.add_error(f"{path}: Campo '{field}' debe ser un string no vacío")
        
        # Validar campos específicos según el tipo de lugar
        if 'price_range' in entry and isinstance(entry['price_range'], str):
            valid_prices = ['€', '€€', '€€€', '€€€€']
            if entry['price_range'] not in valid_prices:
                result.add_warning(f"{path}: price_range '{entry['price_range']}' no es estándar. Usar: {', '.join(valid_prices)}")
    
    def _validate_coherence(self, data: Dict[str, Any], result: ValidationResult):
        """Valida la coherencia interna del itinerario."""
        daily_itinerary = data.get('daily_itinerary', [])
        
        # 1. Validar que cada día tiene numeración consecutiva
        for day_index, day in enumerate(daily_itinerary):
            expected_day_num = day_index + 1
            actual_day_num = day.get('day_number')
            if actual_day_num != expected_day_num:
                result.add_error(f"Día {day_index + 1}: El número de día es {actual_day_num}, esperado {expected_day_num}")
        
        # 2. Validar coherencia de ciudades
        self._validate_city_coherence(daily_itinerary, result)
        
        # 3. Validar que las fechas son consecutivas (dentro del rango)
        self._validate_date_sequence(daily_itinerary, result)
        
        # 4. Validar coherencia de slots
        self._validate_slot_coherence(daily_itinerary, result)
    
    def _validate_city_coherence(self, daily_itinerary: List[Dict], result: ValidationResult):
        """Valida que las ciudades son plausibles."""
        cities_seen = set()
        
        for day in daily_itinerary:
            city = day.get('city')
            if city:
                # Normalizar ciudad para comparación
                normalized_city = city.strip().title()
                if normalized_city not in self.VALID_CITIES:
                    result.add_warning(f"Ciudad '{normalized_city}' no está en la lista de ciudades conocidas. ¿Posible alucinación?")
                
                if normalized_city in cities_seen:
                    result.add_warning(f"Ciudad '{normalized_city}' aparece en múltiples días - posible incoherencia o itinerario circular")
                
                cities_seen.add(normalized_city)
    
    def _validate_date_sequence(self, daily_itinerary: List[Dict], result: ValidationResult):
        """Valida que las fechas siguen un patrón lógico."""
        dates = []
        
        for day in daily_itinerary:
            date_str = day.get('date')
            if date_str:
                try:
                    # Intentar parsear como ISO date
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                        dates.append(date_str)
                    else:
                        # Intentarparsear como DD/MM o DD/MM/YYYY
                        parts = date_str.split('/')
                        if len(parts) == 2:
                            result.add_warning(f"Formato de fecha '{date_str}' no es estándar ISO YYYY-MM-DD")
                        elif len(parts) == 3:
                            if len(parts[2]) == 4:
                                dates.append(f"{parts[2]}-{parts[1]}-{parts[0]}")
                except ValueError:
                    result.add_error(f"Fecha inválida: {date_str}")
        
        # Si tenemos todas las fechas parseadas, validar que sean consecutivas
        if len(dates) >= 2:
            try:
                parsed_dates = [datetime.fromisoformat(d) for d in dates]
                parsed_dates.sort()
                
                for i in range(1, len(parsed_dates)):
                    diff = (parsed_dates[i] - parsed_dates[i-1]).days
                    if diff != 1:
                        result.add_warning(f"Salto de fecha de {diff} días entre {parsed_dates[i-1].date()} y {parsed_dates[i].date()}")
            except Exception as e:
                result.add_warning(f"No se pudo validar secuencia de fechas: {e}")
    
    def _validate_slot_coherence(self, daily_itinerary: List[Dict], result: ValidationResult):
        """Valida la coherencia de las actividades por slot."""
        for day in daily_itinerary:
            morning = day.get('morning', {})
            afternoon = day.get('afternoon', {})
            evening = day.get('evening', {})
            
            # Las descripciones no deberían ser completamente idénticas
            morning_desc = morning.get('description', '').strip()
            afternoon_desc = afternoon.get('description', '').strip()
            evening_desc = evening.get('description', '').strip()
            
            if morning_desc and afternoon_desc and morning_desc == afternoon_desc:
                result.add_warning(f"Día {day.get('day_number', '?')}: Descripción de mañana y tarde son idénticas")
            
            if afternoon_desc and evening_desc and afternoon_desc == evening_desc:
                result.add_warning(f"Día {day.get('day_number', '?')}: Descripción de tarde y noche son idénticas")
    
    def _detect_hallucinations(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta posibles alucinaciones o contenido inventado."""
        # 1. Detectar lugares que parecen-inventados
        self._detect_suspicious_places(data, result)
        
        # 2. Detectar caracteres especiales o contenido sospechoso
        self._detect_suspicious_content(data, result)
        
        # 3. Validar rangos de precios
        self._validate_price_ranges(data, result)
        
        # 4. Validar longitudes de texto (filterno-)alguien
        self._validate_text_lengths(data, result)
    
    def _detect_suspicious_places(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta nombres de lugares que parecen sospechosos."""
        # Diccionario de palabras sospechosas en nombres de lugares
        suspicious_patterns = [
            r'\bbogus\b', r'\bfake\b', r'\binvented\b', r'\trolling\b',
            r'\bdummy\b', r'\ttest\b', r'\tdemo\b', r'\tsample\b',
            r'\btemp\b', r'\temoji\b', r'\tunicode\b'
        ]
        
        # Inspeccionar todos los campos de texto de lugares
        place_fields = ['name', 'zone', 'description', 'title', 'theme']
        
        # Hoteles
        for i, hotel in enumerate(data.get('hotels', [])):
            self._check_suspicious_text(hotel, f"hotel[{i}]", suspicious_patterns, place_fields, result)
        
        # Restaurantes
        for i, restaurant in enumerate(data.get('restaurants', [])):
            self._check_suspicious_text(restaurant, f"restaurant[{i}]", suspicious_patterns, place_fields, result)
        
        # Puntos de interés
        for i, poi in enumerate(data.get('places_of_interest', [])):
            self._check_suspicious_text(poi, f"place_of_interest[{i}]", suspicious_patterns, place_fields, result)
        
        # Sitios históricos
        for i, site in enumerate(data.get('historical_sites', [])):
            self._check_suspicious_text(site, f"historical_site[{i}]", suspicious_patterns, place_fields, result)
    
    def _check_suspicious_text(self, entry: Dict[str, Any], path: str, patterns: List[str], fields: List[str], result: ValidationResult):
        """Verifica si algún campo contiene texto sospechoso."""
        if not isinstance(entry, dict):
            return
        
        for field in fields:
            if field in entry:
                text = str(entry[field])
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        result.add_warning(f"{path}.{field}: Contiene texto sospechoso '{text}' - posible alucinación")
    
    def _detect_suspicious_content(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta contenido o formateo sospechoso."""
        # Validar que las URLs no estén mezcladas con itinerarios de viaje (muestran código malo)
        def check_for_urls(obj: Any, path: str):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_for_urls(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_for_urls(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                # Detectar URLs sospechosas en campos que no deberían tenerlas
                if re.search(r'https?://|www\.|ftp://', obj) and any(word in obj.lower() for word in ['hotel', 'restaurante', 'lugar', 'actividad']):
                    result.add_warning(f"{path}: Contiene URL '{obj}' - posible contenido de créditos o error de formateo")
        
        check_for_urls(data, "root")
    
    def _validate_price_ranges(self, data: Dict[str, Any], result: ValidationResult):
        """Valida que los rangos de precios sean consistentes."""
        hotels = data.get('hotels', [])
        for i, hotel in enumerate(hotels):
            price = hotel.get('price_range', '')
            if price and not re.match(r'^[€€€€ ]+$', price):
                result.add_warning(f"hotel[{i}].price_range: Formato de precio inválido '{price}'")
    
    def _validate_text_lengths(self, data: Dict[str, Any], result: ValidationResult):
        """Valida longitudes de texto razonables."""
        # Descripciones muy largas pueden indicar contenido copiado
        max_description_length = 200
        max_tip_length = 100
        max_theme_length = 50
        
        # Descripciones de lugares
        for i, hotel in enumerate(data.get('hotels', [])):
            if len(hotel.get('description', '')) > max_description_length:
                result.add_warning(f"hotel[{i}].description: Descripción muy larga ({len(hotel.get('description', ''))} chars), posible contenido copiado")
        
        for i, restaurant in enumerate(data.get('restaurants', [])):
            if len(restaurant.get('description', '')) > max_description_length:
                result.add_warning(f"restaurant[{i}].description: Descripción muy larga ({len(restaurant.get('description', ''))} chars), posible contenido copiado")
        
        # Tipos de tema
        for i, day in enumerate(data.get('daily_itinerary', [])):
            theme = day.get('theme', '')
            if len(theme) > max_theme_length:
                result.add_warning(f"daily_itinerary[{i}].theme: Tema muy largo ({len(theme)} chars), posible contenido copiado")
    
    def _detect_repetitions(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta contenido repetitivo o redundante."""
        # 1. Detectar descripciones idénticas
        self._detect_identical_descriptions(data, result)
        
        # 2. Detectar descripciones similares (similarword count)
        self._detect_similar_descriptions(data, result)
        
        # 3. Detectar días con actividades idénticas
        self._detect_identical_days(data, result)
    
    def _detect_identical_descriptions(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta descripciones idénticas entre diferentes entradas."""
        # Recopilar todas las descripciones
        descriptions = []
        place_types = []
        
        # Hoteles
        for i, hotel in enumerate(data.get('hotels', [])):
            desc = hotel.get('description', '').strip()
            if desc:
                descriptions.append((f"hotel[{i}]".description, desc))
        
        # Restaurantes
        for i, restaurant in enumerate(data.get('restaurants', [])):
            desc = restaurant.get('description', '').strip()
            if desc:
                descriptions.append((f"restaurant[{i}]", desc))
        
        # Verificar duplicados
        seen = set()
        for path, desc in descriptions:
            if desc in seen:
                result.add_warning(f"Contenido duplicado: {path} tiene descripción idéntica a otra entrada")
            seen.add(desc)
    
    def _detect_similar_descriptions(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta descripciones altamente similares."""
        # Para descripciones similares, podemos usar un enfoque simple de palabras comunes
        # o simplemente detectar secuencias de palabras largas idénticas
        
        all_descriptions = []
        
        # Reunir todas las descripciones
        for place_type in ['hotels', 'restaurants']:
            for place in data.get(place_type, []):
                desc = place.get('description', '').strip()
                if desc:
                    all_descriptions.append((place_type, desc))
        
        # Comparar cada descripción con las demás
        for i, (type1, desc1) in enumerate(all_descriptions):
            for j, (type2, desc2) in enumerate(all_descriptions):
                if i < j:  # Evitar comparación de uno mismo
                    # Si una descripción es muy larga y parece contener la otra
                    if len(desc1) > 50 and len(desc2) > 50:
                        # Detectar si una es un substring de la otra (con tolerancia)
                        words1 = set(desc1.lower().split())
                        words2 = set(desc2.lower().split())
                        
                        if words1 and words2:
                            intersection = words1.intersection(words2)
                            union = words1.union(words2)
                            
                            # Si > 80% de las palabras son comunes y al menos una descripción es larga
                            if len(union) > 0 and (len(intersection) / len(union)) > 0.8:
                                result.add_warning(f"{type1}[{i}]: Descripción {type1} altamente similar a {type2}")
    
    def _detect_identical_days(self, data: Dict[str, Any], result: ValidationResult):
        """Detecta días con patrones idénticos."""
        daily_itinerary = data.get('daily_itinerary', [])
        
        # Para cada día, crear una representación compacta
        day_signatures = []
        
        for day in daily_itinerary:
            signature = {
                'day_number': day.get('day_number'),
                'city': day.get('city'),
                'morning_desc': day.get('morning', {}).get('description', ''),
                'afternoon_desc': day.get('afternoon', {}).get('description', ''),
                'evening_desc': day.get('evening', {}).get('description', ''),
            }
            day_signatures.append(signature)
        
        # Detectar días idénticos
        for i, sig1 in enumerate(day_signatures):
            for j, sig2 in enumerate(day_signatures):
                if i < j:
                    if sig1 == sig2:
                        result.add_warning(f"Día {sig1.get('day_number')} y Día {sig2.get('day_number')}: Patrones idénticos - posible contenido generado automáticamente")
    
    def _validate_quiz_question(self, question: Dict[str, Any], index: int, result: ValidationResult):
        """Valida una pregunta de cuestionario individual."""
        if not isinstance(question, dict):
            result.add_error(f"Pregunta {index}: Debe ser un objeto")
            return
        
        # Campos requeridos
        required_fields = ['question', 'options', 'correct_index']
        for field in required_fields:
            if field not in question:
                result.add_error(f"Pregunta {index}: Campo requerido faltante '{field}'")
        
        # Validar opciones
        options = question.get('options', [])
        if not isinstance(options, list) or len(options) != 3:
            result.add_error(f"Pregunta {index}: Debe tener exactamente 3 opciones")
        else:
            # Validar que cada opción es un string no vacío
            for i, option in enumerate(options):
                if not isinstance(option, str) or not option.strip():
                    result.add_error(f"Pregunta {index}: Opción {i} debe ser un string no vacío")
            
            # Validar índice correcto dentro de rangos
            correct_index = question.get('correct_index')
            if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= len(options):
                result.add_error(f"Pregunta {index}: correct_index {correct_index} está fuera de rango para {len(options)} opciones")
        
        # Validar texto de la pregunta
        question_text = question.get('question', '')
        if not isinstance(question_text, str) or not question_text.strip():
            result.add_error(f"Pregunta {index}: El texto de la pregunta debe ser un string no vacío")
        
        # Detectar posibles patrones de cuestionario generado por IA (muy similares)
        self._detect_similar_questions([question], index, result)
    
    def _detect_similar_questions(self, questions: List[Dict], base_index: int, result: ValidationResult):
        """Detecta preguntas o respuestas similares (posible IA)."""
        # Para cada pregunta, comparar con las anteriores
        for i in range(1, len(questions)):
            q1 = questions[i-1]
            q2 = questions[i]
            
            # Comparar texto de preguntas (opcional, puede ser similar por diseño)
            text1 = q1.get('question', '').strip().lower()
            text2 = q2.get('question', '').strip().lower()
            
            # Si las preguntas son casi idénticas (con algunas variaciones triviales)
            words1 = set(re.findall(r'\w+', text1))
            words2 = set(re.findall(r'\w+', text2))
            
            if len(words1) > 10 and len(words2) > 10:
                intersection = words1.intersection(words2)
                union = words1.union(words2)
                
                # Si > 90% de las palabras son idénticas (contenido casi idéntico)
                if len(union) > 0 and (len(intersection) / len(union)) > 0.9:
                    result.add_warning(f"Pregunta {i+1}: Texto de pregunta casi idéntico a Pregunta {i}, posible patrón generado por IA")
                
                # Para las opciones, si son casi idénticas, es sospechoso
                opts1 = set([opt.lower().strip() for opt in q1.get('options', [])])
                opts2 = set([opt.lower().strip() for opt in q2.get('options', [])])
                
                if len(opts1) > 2 and len(opts2) > 2:
                    opts_intersection = opts1.intersection(opts2)
                    opts_union = opts1.union(opts2)
                    
                    if len(opts_union) > 0 and (len(opts_intersection) / len(opts_union)) > 0.7:
                        result.add_warning(f"Pregunta {i+1}: Opciones casi idénticas a Pregunta {i}, posible contenido generado por IA")
    
    def _validate_quiz_destinations(self, quiz_data: Dict[str, Any], result: ValidationResult):
        """Valida que los destinos sean plausibles."""
        destinations = quiz_data.get('destinations', [])
        
        for i, dest in enumerate(destinations):
            if dest and isinstance(dest, str):
                # Normalizar para comparación
                normalized = dest.strip().title()
                if normalized not in self.VALID_CITIES:
                    result.add_warning(f"Destino '{dest}': No está en la lista de ciudades conocidas - posible alucinación")
    
    def _validate_date(self, date_str: str, context: str, result: ValidationResult):
        """Valida un string de fecha."""
        if not date_str:
            return
        
        # Intentar varios formatos
        patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # ISO
            r'^\d{2}/\d{2}$',        # DD/MM
            r'^\d{2}/\d{2}/\d{4}$', # DD/MM/YYYY
        ]
        
        valid_format = False
        for pattern in patterns:
            if re.match(pattern, date_str):
                valid_format = True
                break
        
        if not valid_format:
            result.add_warning(f"{context}: Formato de fecha '{date_str}' no es estándar")
        
        # Intentar parsear como ISO para más validación
        if valid_format:
            try:
                if '-' in date_str:  # ISO format
                    datetime.fromisoformat(date_str)
                else:  # DD/MM or DD/MM/YYYY
                    pass  # Simpler para ahora
            except ValueError:
                result.add_error(f"{context}: Fecha inválida '{date_str}'")

# Función principal para demostración y uso
if __name__ == "__main__":
    # Ejemplo de itinerario generado por IA (posibles problemas)
    example_itinerary = {
        "destination_overview": "Un destino mágico en el futuro llamado Eldoria, donde riquezas y maravillas sorprendentes llenan cada rincón.",
        "daily_itinerary": [
            {
                "day_number": 1,
                "date": "2024-12-20",
                "city": "Eldoria",
                "theme": "Viaje de descubrimiento y exploración del reino místico.",
                "morning": {
                    "activities": ["Explorar las ruinas antiguas", "Volar hacia el observatorio de estrellas"],
                    "description": "Explorar las ruinas antiguas y comenzar el viaje místico."
                },
                "afternoon": {
                    "activities": ["Visitar el mercado místico", "Probar cocinazione mágica"],
                    "description": "Explorar el comercio místico y probar deliciosas pociones místicas."
                },
                "evening": {
                    "activities": ["Asistir al baile celestial", "Disfrutar del espectáculo de luces nocturnas"],
                    "description": "Disfrutar del baile celestial del reino y espectáculo de luces nocturnas."
                },
                "travel_reminders": ["Sal temprano por la mañana hacia el aeropuerto distante."],
                "meal_suggestions": {"lunch": "Resto de los Platillos del Rey", "dinner": "Taller de Cocina Místico"}
            },
            {
                "day_number": 2,
                "date": "2024-12-21",  # Inconsistente - debería ser 2024-12-21 pero el anterior era 2024-12-20
                "city": "Eldoria",  # Misma ciudad - posible error
                "theme": "Viaje de descubrimiento y exploración del reino místico.",  # Tema idéntico - sin variación
                "morning": {
                    "activities": ["Explorar las ruinas antiguas", "Volar hacia el observatorio de estrellas"],
                    "description": "Explorar las ruinas antiguas y comenzar el viaje místico."
                },
                "afternoon": {
                    "activities": ["Visitar el mercado místico", "Probar cocinazione mágica"],
                    "description": "Explorar el comercio místico y probar deliciosas pociones místicas."
                },
                "evening": {
                    "activities": ["Asistir al baile celestial", "Disfrutar del espectáculo de luces nocturnas"],
                    "description": "Disfrutar del baile celestial del reino y espectáculo de luces nocturnas."
                },
                "travel_reminders": ["Sal temprano por la mañana por la mañana."],
                "meal_suggestions": {"lunch": "Resto de los Platillos del Rey", "dinner": "Taller de Cocina Místico"}
            }
        ],
        "hotels": [
            {
                "name": "Posada de los Sueños Desaparecidos",
                "zone": "Centro de Eldoria",
                "description": "Un hotel elegante ubicado en el corazón del centro de Eldoria, fácil acceso a todas las atracciones turísticas principales del reino. Ofrece comodidad y vistas impresionantes a los paisajes circundantes del reino.",
                "price_range": "€€€€",
                "highlights": ["WiFi gratuito", "Desayuno buffet", "Relación calidad-precio excelente"]
            },
            {
                "name": "Posada del Amanecer Dorado",
                "zone": "Aldea",
                "description": "Un hotel elegante ubicado en el corazón de la aldea, fácil acceso a todas las atracciones turísticas principales del reino. Ofrece comodidad y vistas impresionantes a los paisajes circundantes del reino.",
                "price_range": "€€",
                "highlights": ["Estacionamiento gratuito", "Relación calidad-precio excelente"]
            }
        ],
        "restaurants": [
            {
                "name": "El Gastronómico de los Sueños Desaparecidos",
                "type": "Alta cocina",
                "description": "Ofrece deliciosos platos gourmet con un toque mágico, incluyendo algunos platos exitosos del famoso chef Pierre Laurent del hotel o restaurante. Ofrece una variedad única de platos exóticos y tradicionales.",
                "price_range": "€€€"
            },
            {
                "name": "La Cocina de los Sueños Desaparecidos",
                "type": "Comida rápida",
                "description": "Ofrece deliciosos platos gourmet con un toque mágico, incluyendo algunos platos exitosos del famoso chef Pierre Laurent del hotel o restaurante. Ofrece una variedad única de platos exóticos y tradicionales.",
                "price_range": "€€"
            }
        ],
        "transport_tips": ["Lleva ropa ligera para el día, el clima en Eldoria puede ser variable."],
        "general_tips": ["Lleva mucho dinero como señuelo para evitar monstruos."],
        "cultural_notes": ["Los ciudadanos locales a menudo usan código secreto 'BADULARDD' para indicaciones en las calles."],
        "places_of_interest": [],
        "historical_sites": [],
        "weather": [
            {"date": "2024-12-20", "temp_max": 22, "temp_min": 8, "precipitation_mm": 0.5, "condition": "☀️ Despejado", "wind_kmh": 10},
            {"date": "2024-12-21", "temp_max": 23, "temp_min": 9, "precipitation_mm": 1.2, "condition": "🌧️ Lluvia", "wind_kmh": 15}
        ]
    }
    
    # Ejemplo de cuestionario generado por IA (posibles problemas)
    example_quiz = {
        "questions": [
            {
                "question": "¿Cuál es la capital de Francia?",
                "options": ["Londres", "Berlín", "Madrid"],
                "correct_index": 0
            },
            {
                "question": "¿Cuál es la capital de Francia?",  # Idéntica
                "options": ["Londres", "Roma", "París"],  # Diferente orden
                "correct_index": 2
            },
            {
                "question": "¿Cuál es la moneda oficial de España?",
                "options": ["Euro", "Dólar", "Libra"],
                "correct_index": 0
            },
            {
                "question": "¿Cuál es el río más largo del mundo?",  # No relacionada
                "options": ["Nilo", "Amazonas", "Yangtsé"],
                "correct_index": 1
            }
        ],
        "destinations": ["Eldoria", "El Palacio de los Sueños Desaparecidos", "Londres"]
    }
    
    def main():
        print("=" * 80)
        print("VALIDACIÓN DE CONTENIDO GENERADO POR IA")
        print("=" * 80)
        
        validator = ContentValidator()
        
        print("\n🔍 VALIDANDO EJEMPLO DE ITINERARIO")
        print("-" * 80)
        itinerary_result = validator.validate_itinerary(example_itinerary)
        
        if itinerary_result.is_passed():
            print("✅ VALIDACIÓN PASÓ")
        else:
            print(f"❌ VALIDACIÓN FALLÓ ({len(itinerary_result.errors)} errores, {len(itinerary_result.warnings)} advertencias)")
            print("\nErrores:")
            for i, error in enumerate(itinerary_result.errors, 1):
                print(f"  {i}. {error}")
            print("\nAdvertencias:")
            for i, warning in enumerate(itinerary_result.warnings, 1):
                print(f"  {i}. {warning}")
        
        print("\n" + "=" * 80)
        print("VALIDANDO EJEMPLO DE CUESTIONARIO")
        print("=" * 80)
        quiz_result = validator.validate_quiz(example_quiz)
        
        if quiz_result.is_passed():
            print("✅ VALIDACIÓN PASÓ")
        else:
            print(f"❌ VALIDACIÓN FALLÓ ({len(quiz_result.errors)} errores, {len(quiz_result.warnings)} advertencias)")
            print("\nErrores:")
            for i, error in enumerate(quiz_result.errors, 1):
                print(f"  {i}. {error}")
            print("\nAdvertencias:")
            for i, warning in enumerate(quiz_result.warnings, 1):
                print(f"  {i}. {warning}")
        
        print("\n" + "=" * 80)
        print("FIN DE VALIDACIÓN")
        print("=" * 80)
    
    if __name__ == "__main__":
        main()
