import { Injectable } from '@angular/core';
import {
  DailyPlan,
  HistoricalSite,
  Hotel,
  ItineraryData,
  PlaceOfInterest,
  Restaurant,
} from '../../services/itinerary.service';
import { QuizQuestion } from '../../services/quiz.service';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/** Frases tipicas de IA que delatan contenido generado automaticamente. */
const AI_PHRASING_PATTERNS: RegExp[] = [
  /como (agente|modelo|asistente) de (viajes|IA|inteligencia artificial)/i,
  /según (mis|nuestros) (datos|registros|conocimientos)/i,
  /(espero que|esperamos que) (disfrutes|disfruten)/i,
  /(no dudes|no duden) en (consultar|preguntar)/i,
  /¡?(buen viaje|feliz viaje|disfruta tu estancia)!?/i,
  /basado en (mi|nuestra) (experiencia|base de datos)/i,
  /ten en cuenta que (soy|somos) (un|una)/i,
  /como (agente|modelo) (de lenguaje|LLM|IA)/i,
  /(recuerda|recuerden) (siempre|llevar|traer|consultar)/i,
  /(aquí|aquí tienes|te presento) (tu|el) (itinerario|plan|guía)/i,
  /(por favor|por favor,) (ten en cuenta|recuerda|consulta)/i,
  /gracias por (confiar|elegir|usar)/i,
  /estoy aquí para (ayudarte|servirte|asistirte)/i,
];

@Injectable({ providedIn: 'root' })
export class ContentValidator {

  private readonly validCities = new Set([
    'Madrid', 'Barcelona', 'Londres', 'París', 'Roma', 'Ámsterdam',
    'Milán', 'Venecia', 'Nápoles', 'Lisboa', 'Oporto', 'Faro',
    'Sevilla', 'Bilbao', 'Valencia', 'Alicante', 'Palma de Mallorca',
    'Málaga', 'San Sebastián', 'Santiago de Compostela', 'Granada',
    'Zaragoza', 'Almería', 'Murcia', 'Ciudad de México', 'Buenos Aires',
    'São Paulo', 'Bogotá', 'Quito', 'Lima', 'La Paz',
  ]);

  private readonly validAirports = new Set([
    'MAD', 'BCN', 'LHR', 'ORY', 'CDG', 'AMS', 'FCO', 'PMI', 'AGP', 'SVQ',
    'BIO', 'VLC', 'ALC', 'IBZ', 'TFN', 'LPA', 'TFS', 'EAS', 'SCQ', 'VGO',
    'SDR', 'ZAZ', 'GRX', 'XRY', 'LEI', 'BRU', 'FRA', 'MUC', 'BER', 'MXP',
    'LIN', 'VCE', 'NAP', 'LIS', 'OPO', 'FAO', 'ATH', 'VIE', 'PRG', 'BUD',
    'WAW', 'CPH', 'OSL', 'ARN', 'HEL', 'IST', 'DXB', 'AUH', 'JFK', 'EWR',
    'MIA', 'LAX', 'MEX', 'BOG', 'EZE', 'GRU', 'NRT', 'HND', 'SIN', 'BKK',
    'DOH',
  ]);

  private readonly validPrices = new Set(['€', '€€', '€€€', '€€€€']);

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  validateItinerary(itinerary: ItineraryData | null): ValidationResult {
    const r = this._fresh();
    if (!itinerary) {
      r.isValid = false;
      r.errors.push('Itinerario no puede estar vacío');
      return r;
    }
    this._validateStructure(itinerary, r);
    this._validateDailyItinerary(itinerary.daily_itinerary || [], r);
    this._validatePlaces(itinerary, r);
    this._validateCoherence(itinerary, r);
    this._detectHallucinations(itinerary, r);
    this._detectRepetitions(itinerary, r);
    this._detectAiPhrasing(itinerary, r);
    return r;
  }

  validateQuiz(questions: QuizQuestion[] | null): ValidationResult {
    const r = this._fresh();
    if (!questions) {
      r.isValid = false;
      r.errors.push('Las preguntas del cuestionario no pueden estar vacías');
      return r;
    }
    if (questions.length < 8) {
      r.warnings.push(`El cuestionario tiene ${questions.length} preguntas (recomendado mínimo 8)`);
    }
    questions.forEach((q, i) => this._validateQuizQuestion(q, i, r));
    this._detectQuizRepetitions(questions, r);
    this._detectQuizAiPhrasing(questions, r);
    return r;
  }

  // ---------------------------------------------------------------------------
  // Private: helpers
  // ---------------------------------------------------------------------------

  private _fresh(): ValidationResult {
    return { isValid: true, errors: [], warnings: [] };
  }

  private _normalize(s: string): string {
    return (s ?? '').trim();
  }

  private _capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  }

  private _datePatterns(): RegExp[] {
    return [/^\d{4}-\d{2}-\d{2}$/, /^\d{2}\/\d{2}(?:\/\d{4})?$/];
  }

  // ---------------------------------------------------------------------------
  // Private: structure
  // ---------------------------------------------------------------------------

  private _validateStructure(itinerary: ItineraryData, r: ValidationResult): void {
    const required: [string, string][] = [
      ['destination_overview', 'string'],
      ['daily_itinerary', 'object'],
    ];
    for (const [field, type] of required) {
      if (!(field in itinerary)) {
        r.isValid = false;
        r.errors.push(`Campo requerido faltante: '${field}'`);
      } else if (typeof (itinerary as any)[field] !== type && !Array.isArray((itinerary as any)[field])) {
        r.isValid = false;
        r.errors.push(`Campo '${field}' debe ser de tipo ${type}`);
      }
    }
  }

  private _validateDailyItinerary(days: DailyPlan[], r: ValidationResult): void {
    if (!Array.isArray(days) || !days.length) {
      r.isValid = false;
      r.errors.push('El itinerario diario no puede estar vacío');
      return;
    }
    days.forEach((day, i) => this._validateSingleDay(day, i, r));
  }

  private _validateSingleDay(day: DailyPlan, idx: number, r: ValidationResult): void {
    const required: [string, string][] = [
      ['day_number', 'number'],
      ['date', 'string'],
      ['city', 'string'],
      ['theme', 'string'],
      ['morning', 'object'],
      ['afternoon', 'object'],
      ['evening', 'object'],
      ['travel_reminders', 'object'],
      ['meal_suggestions', 'object'],
    ];
    for (const [field, type] of required) {
      if (!(field in day)) {
        r.isValid = false;
        r.errors.push(`Día ${idx + 1}: falta campo '${field}'`);
      } else if (type === 'object' && (typeof (day as any)[field] !== 'object' || (day as any)[field] === null)) {
        r.isValid = false;
        r.errors.push(`Día ${idx + 1}: '${field}' debe ser un objeto`);
      } else if (type !== 'object' && typeof (day as any)[field] !== type) {
        r.isValid = false;
        r.errors.push(`Día ${idx + 1}: '${field}' debe ser tipo ${type}`);
      }
    }
    (['morning', 'afternoon', 'evening'] as const).forEach(slot =>
      this._validateSlot((day as any)[slot], slot, idx, r),
    );
    this._validateDate(day.date, `Día ${idx + 1}`, r);
  }

  private _validateSlot(slot: any, name: string, dayIdx: number, r: ValidationResult): void {
    if (!slot || typeof slot !== 'object') {
      r.isValid = false;
      r.errors.push(`Día ${dayIdx + 1}, ${name}: debe ser un objeto`);
      return;
    }
    if (!Array.isArray(slot.activities)) {
      r.warnings.push(`Día ${dayIdx + 1}, ${name}: falta 'activities' (array)`);
    }
    if (typeof slot.description !== 'string' || !this._normalize(slot.description)) {
      r.warnings.push(`Día ${dayIdx + 1}, ${name}: falta 'description'`);
    }
  }

  // ---------------------------------------------------------------------------
  // Private: places
  // ---------------------------------------------------------------------------

  private _validatePlaces(itinerary: ItineraryData, r: ValidationResult): void {
    this._validatePlaceList(itinerary.hotels || [], 'hotel', ['name', 'zone', 'description', 'price_range', 'highlights'], r);
    this._validatePlaceList(itinerary.restaurants || [], 'restaurant', ['name', 'type', 'description', 'price_range'], r);
    this._validatePlaceList(itinerary.places_of_interest || [], 'place_of_interest', ['name', 'type', 'description', 'tips'], r);
    this._validatePlaceList(itinerary.historical_sites || [], 'historical_site', ['name', 'period', 'description', 'curiosity'], r);
  }

  private _validatePlaceList(items: any[], type: string, requiredFields: string[], r: ValidationResult): void {
    items.forEach((entry, i) => {
      if (!entry || typeof entry !== 'object') {
        r.isValid = false;
        r.errors.push(`${type}[${i}]: debe ser un objeto`);
        return;
      }
      for (const field of requiredFields) {
        if (!(field in entry)) {
          r.isValid = false;
          r.errors.push(`${type}[${i}]: falta '${field}'`);
        } else if (typeof entry[field] !== 'string' || !this._normalize(entry[field])) {
          // highlights y tips son arrays de strings
          if (Array.isArray(entry[field])) {
            if (!entry[field].length) {
              r.warnings.push(`${type}[${i}].${field}: array vacío`);
            }
            continue;
          }
          r.isValid = false;
          r.errors.push(`${type}[${i}]: '${field}' debe ser string no vacío`);
        }
      }
      if (typeof entry.price_range === 'string' && !this.validPrices.has(entry.price_range)) {
        r.warnings.push(`${type}[${i}].price_range: '${entry.price_range}' no es estándar (usar €/€€/€€€/€€€€)`);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Private: coherence
  // ---------------------------------------------------------------------------

  private _validateCoherence(itinerary: ItineraryData, r: ValidationResult): void {
    const days = itinerary.daily_itinerary || [];
    this._validateDaySequence(days, r);
    this._validateCityCoherence(days, r);
    this._validateSlotCoherence(days, r);
  }

  private _validateDaySequence(days: DailyPlan[], r: ValidationResult): void {
    for (let i = 0; i < days.length; i++) {
      if (days[i].day_number !== i + 1) {
        r.isValid = false;
        r.errors.push(`Día ${i + 1}: day_number=${days[i].day_number}, esperado ${i + 1}`);
      }
    }
  }

  private _validateCityCoherence(days: DailyPlan[], r: ValidationResult): void {
    const seen = new Set<string>();
    days.forEach(day => {
      const raw = this._normalize(day.city ?? '');
      if (!raw) return;
      const city = this._capitalize(raw);
      if (!this.validCities.has(city)) {
        r.warnings.push(`Ciudad '${city}' no está en la lista de ciudades conocidas — ¿posible alucinación?`);
      }
      if (seen.has(city)) {
        r.warnings.push(`Ciudad '${city}' repetida en varios días`);
      } else {
        seen.add(city);
      }
    });
  }

  private _validateSlotCoherence(days: DailyPlan[], r: ValidationResult): void {
    days.forEach(day => {
      const m = day.morning?.description ?? '';
      const a = day.afternoon?.description ?? '';
      const e = day.evening?.description ?? '';
      if (m && a && m === a) r.warnings.push(`Día ${day.day_number}: descripción mañana === tarde`);
      if (a && e && a === e) r.warnings.push(`Día ${day.day_number}: descripción tarde === noche`);
      if (m && e && m === e) r.warnings.push(`Día ${day.day_number}: descripción mañana === noche`);
    });
  }

  // ---------------------------------------------------------------------------
  // Private: hallucinations
  // ---------------------------------------------------------------------------

  private _detectHallucinations(itinerary: ItineraryData, r: ValidationResult): void {
    this._detectSuspiciousPlaces(itinerary, r);
    this._detectUrlInContent(itinerary, 'root', r);
    this._detectSuspiciousText(itinerary, r);
    this._validatePriceFormat(itinerary, r);
    this._validateTextLengths(itinerary, r);
  }

  private _detectSuspiciousPlaces(itinerary: ItineraryData, r: ValidationResult): void {
    const patterns = [/\bfake\b/i, /\btest\b/i, /\bdemo\b/i, /\bdummy\b/i, /\btemp\b/i, /\bsample\b/i];
    const fields = ['name', 'zone', 'description', 'theme', 'period', 'curiosity'];

    const check = (entry: any, type: string, i: number) => {
      if (!entry) return;
      for (const f of fields) {
        if (typeof entry[f] !== 'string') continue;
        for (const p of patterns) {
          if (p.test(entry[f])) {
            r.warnings.push(`${type}[${i}].${f}: texto sospechoso ('${entry[f].substring(0, 40)}')`);
          }
        }
      }
    };

    (itinerary.hotels || []).forEach((h, i) => check(h, 'hotel', i));
    (itinerary.restaurants || []).forEach((h, i) => check(h, 'restaurant', i));
    (itinerary.places_of_interest || []).forEach((h, i) => check(h, 'place_of_interest', i));
    (itinerary.historical_sites || []).forEach((h, i) => check(h, 'historical_site', i));
    (itinerary.daily_itinerary || []).forEach((d, i) => check(d, 'daily_itinerary', i));
  }

  private _detectUrlInContent(obj: any, path: string, r: ValidationResult): void {
    if (Array.isArray(obj)) {
      obj.forEach((item, i) => this._detectUrlInContent(item, `${path}[${i}]`, r));
    } else if (obj && typeof obj === 'object') {
      Object.entries(obj).forEach(([k, v]) => this._detectUrlInContent(v, `${path}.${k}`, r));
    } else if (typeof obj === 'string') {
      if (/https?:\/\/|www\.|ftp:\/\//i.test(obj)) {
        r.warnings.push(`${path}: contiene URL ('${obj.substring(0, 60)}')`);
      }
    }
  }

  private _detectSuspiciousText(itinerary: ItineraryData, r: ValidationResult): void {
    const longWordsPattern = /\b[A-Za-z]{35,}\b/;
    const randomCharsPattern = /[¢§¶•ªº][¢§¶•ªº]{2,}/;

    const check = (text: string, label: string) => {
      if (longWordsPattern.test(text)) {
        r.warnings.push(`${label}: palabra excesivamente larga — posible alucinación`);
      }
      if (randomCharsPattern.test(text)) {
        r.warnings.push(`${label}: caracteres aleatorios — posible alucinación`);
      }
    };

    (itinerary.daily_itinerary || []).forEach(d => check(d.theme ?? '', `Día ${d.day_number} theme`));
    (itinerary.hotels || []).forEach((h, i) => check(h.description ?? '', `hotel[${i}] description`));
    (itinerary.restaurants || []).forEach((h, i) => check(h.description ?? '', `restaurant[${i}] description`));
  }

  private _validatePriceFormat(itinerary: ItineraryData, r: ValidationResult): void {
    (itinerary.hotels || []).forEach((h, i) => {
      if (h.price_range && !this.validPrices.has(h.price_range)) {
        r.warnings.push(`hotel[${i}].price_range: '${h.price_range}' inválido`);
      }
    });
    (itinerary.restaurants || []).forEach((h, i) => {
      if (h.price_range && !this.validPrices.has(h.price_range)) {
        r.warnings.push(`restaurant[${i}].price_range: '${h.price_range}' inválido`);
      }
    });
  }

  private _validateTextLengths(itinerary: ItineraryData, r: ValidationResult): void {
    const MAX_DESC = 200;
    const MAX_THEME = 50;

    (itinerary.hotels || []).forEach((h, i) => {
      if ((h.description ?? '').length > MAX_DESC) r.warnings.push(`hotel[${i}].description muy largo (${h.description.length} chars)`);
    });
    (itinerary.restaurants || []).forEach((h, i) => {
      if ((h.description ?? '').length > MAX_DESC) r.warnings.push(`restaurant[${i}].description muy largo (${h.description.length} chars)`);
    });
    (itinerary.daily_itinerary || []).forEach((d, i) => {
      if ((d.theme ?? '').length > MAX_THEME) r.warnings.push(`daily_itinerary[${i}].theme muy largo (${d.theme.length} chars)`);
    });
  }

  // ---------------------------------------------------------------------------
  // Private: repetitions
  // ---------------------------------------------------------------------------

  private _detectRepetitions(itinerary: ItineraryData, r: ValidationResult): void {
    this._detectDuplicateNames(itinerary, r);
    this._detectDuplicateDescriptions(itinerary, r);
    this._detectSimilarDays(itinerary, r);
  }

  private _detectDuplicateNames(itinerary: ItineraryData, r: ValidationResult): void {
    const extract = (items: any[], type: string): void => {
      const seen = new Map<string, number>();
      items.forEach((item, i) => {
        const name = this._normalize(item.name ?? '');
        if (!name) return;
        const key = name.toLowerCase();
        if (seen.has(key)) {
          r.warnings.push(`${type}: nombre duplicado '${name}' (índices ${seen.get(key)} y ${i})`);
        } else {
          seen.set(key, i);
        }
      });
    };

    extract(itinerary.hotels || [], 'hotel');
    extract(itinerary.restaurants || [], 'restaurant');
    extract(itinerary.places_of_interest || [], 'place_of_interest');
    extract(itinerary.historical_sites || [], 'historical_site');
  }

  private _detectDuplicateDescriptions(itinerary: ItineraryData, r: ValidationResult): void {
    const extract = (items: any[], type: string): void => {
      const seen = new Map<string, number>();
      items.forEach((item, i) => {
        const desc = this._normalize(item.description ?? '');
        if (!desc) return;
        const key = desc.toLowerCase();
        if (seen.has(key)) {
          r.warnings.push(`${type}: descripción duplicada (índices ${seen.get(key)} y ${i})`);
        } else {
          seen.set(key, i);
        }
      });
    };

    extract(itinerary.hotels || [], 'hotel');
    extract(itinerary.restaurants || [], 'restaurant');
    extract(itinerary.places_of_interest || [], 'place_of_interest');
    extract(itinerary.historical_sites || [], 'historical_site');
  }

  private _detectSimilarDays(itinerary: ItineraryData, r: ValidationResult): void {
    const days = itinerary.daily_itinerary || [];
    for (let i = 0; i < days.length; i++) {
      for (let j = i + 1; j < days.length; j++) {
        const a = days[i];
        const b = days[j];
        if (
          a.morning?.description === b.morning?.description &&
          a.afternoon?.description === b.afternoon?.description &&
          a.evening?.description === b.evening?.description
        ) {
          r.warnings.push(`Día ${a.day_number} y ${b.day_number}: patrones idénticos — ¿contenido generado automáticamente?`);
        }
      }
    }

    // Also detect theme repetition
    const themeCount = new Map<string, number>();
    days.forEach(d => {
      const t = this._normalize(d.theme ?? '').toLowerCase();
      if (t) themeCount.set(t, (themeCount.get(t) ?? 0) + 1);
    });
    themeCount.forEach((count, theme) => {
      if (count >= 3) {
        r.warnings.push(`Tema '${theme}' repetido ${count} veces en el itinerario`);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Private: AI phrasing detection
  // ---------------------------------------------------------------------------

  private _detectAiPhrasing(itinerary: ItineraryData, r: ValidationResult): void {
    const checkText = (text: string, label: string): void => {
      if (!text) return;
      for (const pattern of AI_PHRASING_PATTERNS) {
        if (pattern.test(text)) {
          r.warnings.push(`${label}: posible frase de IA ('${text.substring(0, 50)}…')`);
          break;
        }
      }
    };

    checkText(itinerary.destination_overview ?? '', 'destination_overview');
    checkText(itinerary.weather_summary ?? '', 'weather_summary');
    (itinerary.daily_itinerary || []).forEach(d => checkText(d.theme ?? '', `Día ${d.day_number} theme`));
    (itinerary.hotels || []).forEach((h, i) => checkText(h.description ?? '', `hotel[${i}]`));
    (itinerary.restaurants || []).forEach((h, i) => checkText(h.description ?? '', `restaurant[${i}]`));
    (itinerary.places_of_interest || []).forEach((h, i) => checkText(h.description ?? '', `place_of_interest[${i}]`));
    (itinerary.historical_sites || []).forEach((h, i) => checkText(h.description ?? '', `historical_site[${i}]`));
    (itinerary.transport_tips || []).forEach((t, i) => checkText(t, `transport_tip[${i}]`));
    (itinerary.general_tips || []).forEach((t, i) => checkText(t, `general_tip[${i}]`));
    (itinerary.cultural_notes || []).forEach((t, i) => checkText(t, `cultural_note[${i}]`));
  }

  // ---------------------------------------------------------------------------
  // Private: quiz validation
  // ---------------------------------------------------------------------------

  private _validateQuizQuestion(q: QuizQuestion, idx: number, r: ValidationResult): void {
    if (!q) {
      r.isValid = false;
      r.errors.push(`Pregunta ${idx}: no puede estar vacía`);
      return;
    }
    if (typeof q.question !== 'string' || !this._normalize(q.question)) {
      r.isValid = false;
      r.errors.push(`Pregunta ${idx}: texto inválido`);
    }
    if (!Array.isArray(q.options) || q.options.length !== 3) {
      r.isValid = false;
      r.errors.push(`Pregunta ${idx}: debe tener exactamente 3 opciones`);
    } else {
      q.options.forEach((opt, oi) => {
        if (typeof opt !== 'string' || !this._normalize(opt)) {
          r.isValid = false;
          r.errors.push(`Pregunta ${idx}, opción ${oi}: vacía o inválida`);
        }
      });
      if (typeof q.correct_index !== 'number' || q.correct_index < 0 || q.correct_index > 2) {
        r.isValid = false;
        r.errors.push(`Pregunta ${idx}: correct_index=${q.correct_index} fuera de rango [0,2]`);
      }
    }
  }

  private _detectQuizRepetitions(questions: QuizQuestion[], r: ValidationResult): void {
    const seenQuestions = new Map<string, number>();
    questions.forEach((q, i) => {
      const key = this._normalize(q.question).toLowerCase();
      if (!key) return;
      if (seenQuestions.has(key)) {
        r.warnings.push(`Quiz: pregunta duplicada (índices ${seenQuestions.get(key)} y ${i}): '${q.question.substring(0, 60)}'`);
      } else {
        seenQuestions.set(key, i);
      }
    });

    // Detectar opciones casi idénticas entre preguntas
    for (let i = 0; i < questions.length; i++) {
      for (let j = i + 1; j < questions.length; j++) {
        const optsI = new Set(questions[i].options.map(o => o.toLowerCase().trim()));
        const optsJ = new Set(questions[j].options.map(o => o.toLowerCase().trim()));
        let common = 0;
        optsI.forEach(o => { if (optsJ.has(o)) common++; });
        if (common >= 3) {
          r.warnings.push(`Quiz: pregunta ${i} y ${j} comparten todas las opciones`);
        } else if (common >= 2) {
          r.warnings.push(`Quiz: pregunta ${i} y ${j} comparten ${common}/3 opciones`);
        }
      }
    }
  }

  private _detectQuizAiPhrasing(questions: QuizQuestion[], r: ValidationResult): void {
    questions.forEach((q, i) => {
      const text = `${q.question} ${(q.options || []).join(' ')}`;
      for (const pattern of AI_PHRASING_PATTERNS) {
        if (pattern.test(text)) {
          r.warnings.push(`Quiz pregunta ${i}: posible frase de IA`);
          break;
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Private: date validation
  // ---------------------------------------------------------------------------

  private _validateDate(dateStr: string, ctx: string, r: ValidationResult): void {
    if (!dateStr) return;
    const valid = this._datePatterns().some(p => p.test(dateStr));
    if (!valid) {
      r.warnings.push(`${ctx}: formato de fecha no estándar ('${dateStr}')`);
    }
    if (valid && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      try {
        new Date(dateStr);
      } catch {
        r.isValid = false;
        r.errors.push(`${ctx}: fecha inválida '${dateStr}'`);
      }
    }
  }
}
