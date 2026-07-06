import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { LoadingController, ToastController } from '@ionic/angular';
import { BoardingPassService } from '../services/boarding-pass.service';
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

@Component({
  selector: 'app-itinerary',
  templateUrl: './itinerary.page.html',
  styleUrls: ['./itinerary.page.scss'],
  standalone: false,
})
export class ItineraryPage {
  tripId = 0;
  itinerary: ItineraryData | null = null;
  loading = true;
  error = '';
  activeTab: 'plan' | 'eat' | 'sleep' | 'visit' | 'tips' = 'plan';

  constructor(
    private router: Router,
    private itinerarySvc: ItineraryService,
    private bpSvc: BoardingPassService,
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
  ) {}

  ionViewWillEnter() {
    const state = history.state as { tripId: number } | undefined;
    if (state?.tripId) {
      this.tripId = state.tripId;
      this.generate();
    } else {
      this.error = 'No se recibió el ID del viaje';
      this.loading = false;
    }
  }

  async generate() {
    this.loading = true;
    this.error = '';

    const sid = this.bpSvc.getSessionId();

    // Intentar cache primero (instantaneo)
    this.itinerarySvc.getCached(this.tripId, sid).subscribe({
      next: (resp) => {
        this.itinerary = resp.itinerary;
        this.loading = false;
      },
      error: async (err: any) => {
        // 404 = no cacheado aun, generar
        if (err?.status === 404) {
          await this.doGenerate(sid);
        } else {
          this.loading = false;
          this.error = err?.error?.detail ?? err?.message ?? 'Error desconocido';
          this.toast('Error: ' + this.error, 'danger');
        }
      },
    });
  }

  private async doGenerate(sid: string) {
    const loading = await this.loadingCtrl.create({ message: 'Creando itinerario con IA…' });
    await loading.present();

    this.itinerarySvc.generate(this.tripId, sid).subscribe({
      next: async (resp) => {
        await loading.dismiss();
        this.itinerary = resp.itinerary;
        this.loading = false;
      },
      error: async (err: any) => {
        await loading.dismiss();
        this.loading = false;
        this.error = err?.error?.detail ?? err?.message ?? 'Error desconocido';
        this.toast('Error: ' + this.error, 'danger');
      },
    });
  }

  goBack() {
    history.back();
  }

  // --- Helpers de clima ---
  weatherForDate(date: string): WeatherDay | undefined {
    return this.itinerary?.weather?.find((w) => w.date === date);
  }

  // --- Helpers de display ---
  priceIcon(price: string): string {
    return price.replace(/€/g, '💰').replace(/\$/g, '💵');
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
