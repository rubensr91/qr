import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// --- Tipos del itinerario ---

export interface WeatherDay {
  date: string;
  temp_max: number | null;
  temp_min: number | null;
  precipitation_mm: number | null;
  condition: string;
  wind_kmh: number | null;
}

export interface Restaurant {
  name: string;
  type: string;
  description: string;
  price_range: string;
}

export interface Hotel {
  name: string;
  zone: string;
  description: string;
  price_range: string;
  highlights: string[];
}

export interface PlaceOfInterest {
  name: string;
  type: string;
  description: string;
  tips: string[];
}

export interface HistoricalSite {
  name: string;
  period: string;
  description: string;
  curiosity: string;
}

export interface DaySlot {
  activities: string[];
  description: string;
}

export interface MealSuggestions {
  lunch: string;
  dinner: string;
}

export interface DailyPlan {
  day_number: number;
  date: string;
  theme: string;
  morning: DaySlot;
  afternoon: DaySlot;
  evening: DaySlot;
  meal_suggestions: MealSuggestions;
}

export interface ItineraryData {
  destination_overview?: string;
  weather_summary?: string;
  weather: WeatherDay[];
  restaurants: Restaurant[];
  hotels: Hotel[];
  places_of_interest: PlaceOfInterest[];
  historical_sites: HistoricalSite[];
  daily_itinerary: DailyPlan[];
  transport_tips: string[];
  general_tips: string[];
  cultural_notes: string[];
  meta?: { destinations: string[]; pass_count: number; generated_at: string };
  error?: string;
  raw_response?: string;
  parse_error?: boolean;
}

export interface ItineraryResponse {
  trip_id: number;
  cached: boolean;
  itinerary: ItineraryData;
}

@Injectable({ providedIn: 'root' })
export class ItineraryService {
  constructor(private http: HttpClient) {}

  private _headers(sessionId: string): HttpHeaders {
    let h = new HttpHeaders({ 'X-Session-Id': sessionId });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return h;
  }

  getCached(tripId: number, sessionId: string): Observable<ItineraryResponse> {
    return this.http.get<ItineraryResponse>(
      `${environment.apiUrl}/api/itinerary/${tripId}`,
      { headers: this._headers(sessionId) },
    );
  }

  generate(tripId: number, sessionId: string): Observable<ItineraryResponse> {
    return this.http.post<ItineraryResponse>(
      `${environment.apiUrl}/api/itinerary/${tripId}`,
      {},
      { headers: this._headers(sessionId) },
    );
  }
}
