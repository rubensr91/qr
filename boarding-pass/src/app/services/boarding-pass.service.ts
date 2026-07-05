import { HttpClient } from '@angular/common/http';
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
  train?: string;
  class?: string;
  seat?: string;
  check_in_seq?: string;
  origin?: string;
  raw?: string;
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

@Injectable({ providedIn: 'root' })
export class BoardingPassService {
  constructor(private http: HttpClient) {}

  uploadPdf(file: File): Observable<ExtractResponse> {
    const fd = new FormData();
    fd.append('file', file, file.name);
    return this.http.post<ExtractResponse>(`${environment.apiUrl}/api/extract`, fd);
  }
}
