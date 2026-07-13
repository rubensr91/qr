import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
}

export interface QuizResponse {
  questions: QuizQuestion[];
  destinations?: string[];
  error?: string;
  _validation?: { is_valid: boolean; errors: string[]; warnings: string[] };
}

@Injectable({ providedIn: 'root' })
export class QuizService {
  constructor(private http: HttpClient) {}

  private _headers(sessionId: string): HttpHeaders {
    let h = new HttpHeaders({ 'X-Session-Id': sessionId });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return h;
  }

  generate(tripId: number, sessionId: string): Observable<QuizResponse> {
    return this.http.post<QuizResponse>(
      `${environment.apiUrl}/api/quiz/${tripId}`,
      {},
      { headers: this._headers(sessionId) },
    );
  }
}
