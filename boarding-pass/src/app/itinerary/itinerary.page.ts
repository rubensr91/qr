import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { LoadingController, ToastController } from '@ionic/angular';
import { BarcodeImage, BoardingPassService, Pass, TravelSegment } from '../services/boarding-pass.service';
import {
  DailyPlan,
  HistoricalSite,
  Hotel,
  ItineraryData,
  ItineraryService,
  PlaceOfInterest,
  Restaurant,
  WeatherDay,
} from '../services/itinerary.service';

const SEGMENT_ICONS: Record<string, string> = {
  flight: 'airplane', train: 'train', hotel: 'bed',
  car: 'car', restaurant: 'restaurant', activity: 'football',
};
const SEGMENT_LABELS: Record<string, string> = {
  flight: 'Vuelo', train: 'Tren', hotel: 'Hotel',
  car: 'Coche', restaurant: 'Restaurante', activity: 'Actividad',
};

const AIRLINE_NAMES: Record<string, string> = {
  IB: 'Iberia', I2: 'Iberia Express', VY: 'Vueling', V7: 'Volotea',
  FR: 'Ryanair', U2: 'easyJet', W6: 'Wizz Air', EW: 'Eurowings',
  LH: 'Lufthansa', BA: 'British Airways', AF: 'Air France',
  KL: 'KLM', AZ: 'ITA Airways', UX: 'Air Europa', NT: 'Binter',
  AA: 'American Airlines', UA: 'United', DL: 'Delta', AC: 'Air Canada',
  AM: 'Aeroméxico', LA: 'LATAM', AD: 'Azul', AV: 'Avianca',
  TP: 'TAP Portugal', SU: 'Aeroflot', TK: 'Turkish Airlines',
  QR: 'Qatar Airways', EK: 'Emirates', EY: 'Etihad',
  SQ: 'Singapore Airlines', JL: 'Japan Airlines', NH: 'ANA',
  AI: 'Air India', QF: 'Qantas',
  SNCF: 'SNCF', RENFE: 'Renfe', OUIGO: 'OUIGO España',
  IRYO: 'Iryo', AVE: 'Renfe AVE',
};

function getAirlineName(code: string | undefined): string {
  if (!code) return '';
  return AIRLINE_NAMES[code.toUpperCase()] || code;
}

@Component({
  selector: 'app-itinerary',
  templateUrl: './itinerary.page.html',
  styleUrls: ['./itinerary.page.scss'],
  standalone: false,
})
export class ItineraryPage {
  tripId = 0;
  tripName = '';
  passes: Pass[] = [];
  images: BarcodeImage[] = [];
  groups: { name: string; passes: Pass[] }[] = [];
  expandedGroup: string | null = null;
  segments: TravelSegment[] = [];
  itinerary: ItineraryData | null = null;
  loading = true;
  generating = false;
  error = '';
  activeTab: 'plan' | 'cards' | 'bookings' | 'eat' | 'sleep' | 'visit' | 'tips' = 'plan';

  constructor(
    private router: Router,
    private itinerarySvc: ItineraryService,
    private bpSvc: BoardingPassService,
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
  ) {}

  ionViewWillEnter() {
    const state = history.state as {
      tripId: number; passes?: Pass[]; segments?: TravelSegment[]; images?: BarcodeImage[]; tripName?: string;
    } | undefined;
    if (state?.tripId) {
      this.tripId = state.tripId;
      this.tripName = state.tripName || '';
      // Si no nos llegan passes/segments por el state, los pedimos a la API
      if (state.passes?.length || state.segments?.length) {
        this.passes = state.passes || [];
        this.groups = this.buildGroups(this.passes);
        this.segments = state.segments || [];
        this.images = state.images || [];
        this.afterLoad();
      } else {
        this.fetchTripData();
      }
    } else {
      this.error = 'No se recibió el ID del viaje';
      this.loading = false;
    }
  }

  private afterLoad() {
    this.activeTab = 'cards';
    this.loadItinerary();
  }

  private fetchTripData() {
    this.loading = true;
    this.bpSvc.getTrips().subscribe({
      next: (resp: any) => {
        const trip = resp.trips.find((t: any) => t.id === this.tripId);
        if (trip) {
          this.passes = trip.pass_data.passes || [];
          this.groups = this.buildGroups(this.passes);
          this.images = trip.pass_data.images || [];
          this.segments = trip.segments || [];
          this.tripName = trip.trip_name || trip.filename;
        }
        this.loading = false;
        this.afterLoad();
      },
      error: (err: any) => {
        this.loading = false;
        this.error = err?.error?.detail ?? err?.message ?? 'Error';
      },
    });
  }

  loadItinerary() {
    this.loading = true;
    this.error = '';
    const sid = this.bpSvc.getSessionId();

    this.itinerarySvc.getCached(this.tripId, sid).subscribe({
      next: (resp) => {
        this.itinerary = resp.itinerary;
        this.loading = false;
        // Si hay itinerario, saltar al Plan automaticamente
        if (resp.itinerary?.daily_itinerary?.length) {
          this.activeTab = 'plan';
        }
      },
      error: (err: any) => {
        if (err?.status === 404) {
          this.loading = false;
          this.error = '';
        } else {
          this.loading = false;
          this.error = err?.error?.detail ?? err?.message ?? 'Error';
        }
      },
    });
  }

  async generateItinerary() {
    this.generating = true;
    const loading = await this.loadingCtrl.create({ message: 'Creando itinerario…' });
    await loading.present();
    const sid = this.bpSvc.getSessionId();

    this.itinerarySvc.generate(this.tripId, sid).subscribe({
      next: async (resp) => {
        await loading.dismiss();
        this.itinerary = resp.itinerary;
        this.generating = false;
      },
      error: async (err: any) => {
        await loading.dismiss();
        this.generating = false;
        this.error = err?.error?.detail ?? err?.message ?? 'Error';
        this.toast('Error: ' + this.error, 'danger');
      },
    });
  }

  weatherForDate(date: string): WeatherDay | undefined {
    return this.itinerary?.weather?.find((w) => w.date === date);
  }

  imageFor(pass: Pass): BarcodeImage | undefined {
    return this.images.find((i) => i.page === pass.page);
  }

  /** Formatea fecha: DD/MM si año inferido, DD/MM/YYYY si explícito. */
  formatDate(pass: any): string {
    if (!pass.flight_date) return '—';
    const parts = pass.flight_date.split('-');
    if (parts.length !== 3) return pass.flight_date;
    const [y, m, d] = parts;
    if (pass.has_explicit_year === false) {
      return `${d}/${m}`;
    }
    return `${d}/${m}/${y}`;
  }

  segmentIcon(type: string): string {
    return SEGMENT_ICONS[type] || 'ellipse';
  }

  segmentLabel(type: string): string {
    return SEGMENT_LABELS[type] || type;
  }

  segmentSummary(seg: TravelSegment): string {
    switch (seg.type) {
      case 'flight': return `${seg.airline || ''}${seg.flight_number || ''} ${seg.from || ''}→${seg.to || ''}`.trim() || 'Vuelo';
      case 'train': return `${seg.operator || ''} ${seg.train_number || ''}`.trim() || 'Tren';
      case 'hotel': return `${seg.name || ''} ${seg.check_in || ''} → ${seg.check_out || ''}`.trim() || 'Hotel';
      case 'car': return `${seg.company || ''} ${seg.pickup_date || ''}`.trim() || 'Coche';
      case 'restaurant': return `${seg.name || ''} ${seg.date || ''}`.trim() || 'Restaurante';
      case 'activity': return `${seg.name || ''} ${seg.date || ''}`.trim() || 'Actividad';
      default: return 'Segmento';
    }
  }

  labelFor(pass: Pass): string {
    if (pass.kind === 'flight' || pass.airline) {
      return `${pass.from ?? '?'} → ${pass.to ?? '?'} · ${pass.airline ?? ''}${pass.flight ?? ''}`;
    }
    if (pass.kind === 'train' || pass.train) {
      return `Tren ${pass.train ?? '?'}`;
    }
    return pass.format || 'Pase';
  }

  private buildGroups(passes: Pass[]): { name: string; passes: Pass[] }[] {
    const map = new Map<string, Pass[]>();
    for (const p of passes) {
      const key = (p.name || 'Sin nombre').toUpperCase();
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    }
    const groups: { name: string; passes: Pass[] }[] = [];
    for (const [, list] of map) {
      list.sort((a, b) => {
        const da = a.flight_date || '9999-99-99';
        const db = b.flight_date || '9999-99-99';
        if (da !== db) return da < db ? -1 : 1;
        const ta = a.flight_time || '99:99';
        const tb = b.flight_time || '99:99';
        return ta < tb ? -1 : 1;
      });
      const originalName = list[0].name || 'Sin nombre';
      groups.push({ name: originalName, passes: list });
    }
    groups.sort((a, b) => a.name.localeCompare(b.name));
    return groups;
  }

  toggleGroup(name: string) {
    this.expandedGroup = this.expandedGroup === name ? null : name;
  }

  isGroupExpanded(name: string): boolean {
    return this.expandedGroup === name;
  }

  getAirlineName(code: string | undefined): string {
    return getAirlineName(code);
  }

  goBack() {
    history.back();
  }

  editSegments() {
    this.router.navigate(['/trip-create'], {
      state: { editTripId: this.tripId, tripName: this.tripName, segments: this.segments },
    });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
