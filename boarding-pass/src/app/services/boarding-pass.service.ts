import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Pass {
  page: number;
  format: string;
  kind?: string;
  name?: string | null;
  pnr?: string | null;
  from?: string;
  to?: string;
  airline?: string;
  flight?: string;
  flight_date?: string | null;
  flight_time?: string | null;
  gate_close_time?: string | null;
  train?: string;
  class?: string;
  seat?: string;
  check_in_seq?: string;
  origin?: string;
  raw?: string;
  sourceFile?: string;
  has_explicit_year?: boolean;
}

export interface BarcodeImage {
  page: number;
  format: string;
  filename: string;
  base64: string;
}

export interface ExtractResponse {
  filename: string;
  passes: Pass[];
  images: BarcodeImage[];
  count: number;
}

export interface Trip {
  id: number;
  session_id: string;
  filename: string;
  trip_name?: string;
  pass_data: { passes: Pass[]; images: BarcodeImage[] };
  segments?: TravelSegment[];
  created_at: string;
  updated_at?: string;
}

export interface TravelSegment {
  type: 'flight' | 'train' | 'hotel' | 'car' | 'restaurant' | 'activity';
  // Flight / Train
  airline?: string;
  operator?: string;
  flight_number?: string;
  train_number?: string;
  from?: string;
  to?: string;
  // Hotel
  name?: string;
  city?: string;
  check_in?: string;
  check_out?: string;
  // Car
  company?: string;
  pickup_date?: string;
  return_date?: string;
  // Restaurant
  // name + city + date + time (reuses above)
  // Activity
  description?: string;
  date?: string;
  time?: string;
}

export interface TripListResponse {
  trips: Trip[];
  session_id: string;
}

export interface SaveTripResponse {
  status: 'created' | 'updated' | 'duplicate';
  id: number;
  session_id: string;
  filename: string;
  trip_name?: string;
  message: string;
}

const SESSION_KEY = 'bp_session_id';

@Injectable({ providedIn: 'root' })
export class BoardingPassService {
  constructor(private http: HttpClient) {}

  private _headers(extra?: Record<string, string>): { headers: HttpHeaders } {
    let h = new HttpHeaders(extra || {});
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return { headers: h };
  }

  // --- PDF extraction ---

  uploadPdf(file: File): Observable<ExtractResponse> {
    const fd = new FormData();
    fd.append('file', file, file.name);
    return this.http.post<ExtractResponse>(
      `${environment.apiUrl}/api/extract`, fd, this._headers()
    );
  }

  // --- Trips CRUD ---

  /** Obtiene o crea el session_id persistente en localStorage. */
  getSessionId(): string {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = 'ses_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  private sessionHeaders(): { headers: HttpHeaders } {
    let h = new HttpHeaders({ 'X-Session-Id': this.getSessionId() });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return { headers: h };
  }

  /** Lista todos los viajes de la sesion actual. */
  getTrips(): Observable<TripListResponse> {
    return this.http.get<TripListResponse>(
      `${environment.apiUrl}/api/trips`,
      this.sessionHeaders(),
    );
  }

  /** Guarda un viaje tras la extraccion. */
  saveTrip(filename: string, passes: Pass[], images: BarcodeImage[], tripName?: string, segments?: TravelSegment[]): Observable<SaveTripResponse> {
    // Forzar Content-Type con charset UTF-8 para que las tildes/ñ se preserven
    const headers = new HttpHeaders({
      'Content-Type': 'application/json; charset=utf-8',
      'X-Session-Id': this.getSessionId(),
    });
    return this.http.post<SaveTripResponse>(
      `${environment.apiUrl}/api/trips`,
      { filename, passes, images, trip_name: tripName || '', segments: segments || [] },
      { headers },
    );
  }

  /** Actualiza los segmentos manuales de un viaje. */
  updateSegments(tripId: number, segments: TravelSegment[]): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(
      `${environment.apiUrl}/api/trips/${tripId}/segments`,
      { segments },
      this.sessionHeaders(),
    );
  }

  /** Borra un viaje por ID. */
  deleteTrip(id: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(
      `${environment.apiUrl}/api/trips/${id}`,
      this.sessionHeaders(),
    );
  }
}
