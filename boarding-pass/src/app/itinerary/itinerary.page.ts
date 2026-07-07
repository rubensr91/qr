import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { LoadingController, ToastController } from '@ionic/angular';
import { BoardingPassService, Pass, TravelSegment } from '../services/boarding-pass.service';
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
      tripId: number; passes?: Pass[]; segments?: TravelSegment[]; tripName?: string;
    } | undefined;
    if (state?.tripId) {
      this.tripId = state.tripId;
      this.tripName = state.tripName || '';
      this.passes = state.passes || [];
      this.segments = state.segments || [];
      this.loadItinerary();
    } else {
      this.error = 'No se recibió el ID del viaje';
      this.loading = false;
    }
  }

  loadItinerary() {
    this.loading = true;
    this.error = '';
    const sid = this.bpSvc.getSessionId();

    this.itinerarySvc.getCached(this.tripId, sid).subscribe({
      next: (resp) => {
        this.itinerary = resp.itinerary;
        this.loading = false;
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
