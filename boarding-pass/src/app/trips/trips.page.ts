import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AlertController, ToastController } from '@ionic/angular';
import { BoardingPassService, Trip } from '../services/boarding-pass.service';

@Component({
  selector: 'app-trips',
  templateUrl: './trips.page.html',
  styleUrls: ['./trips.page.scss'],
  standalone: false,
})
export class TripsPage {
  trips: Trip[] = [];
  loading = true;

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private alertCtrl: AlertController,
    private toastCtrl: ToastController,
  ) {}

  /** Ionic lifecycle: se ejecuta cada vez que la pagina se muestra. */
  ionViewWillEnter() {
    this.loadTrips();
  }

  loadTrips() {
    this.loading = true;
    const sid = this.svc.getSessionId();
    console.debug('[TripsPage] loadTrips session:', sid);
    this.svc.getTrips().subscribe({
      next: (resp) => {
        console.debug('[TripsPage] trips recibidos:', resp.trips.length);
        this.trips = resp.trips;
        this.loading = false;
      },
      error: (err: any) => {
        console.error('[TripsPage] error:', err);
        this.loading = false;
        this.toast('Error al cargar viajes: ' + (err?.error?.detail ?? err?.message ?? err), 'danger');
      },
    });
  }

  viewTrip(trip: Trip) {
    this.router.navigate(['/itinerary'], {
      state: {
        tripId: trip.id,
        passes: trip.pass_data.passes,
        images: trip.pass_data.images,
        segments: trip.segments || [],
        tripName: trip.trip_name || trip.filename,
      },
    });
  }

  async deleteTrip(trip: Trip) {
    const alert = await this.alertCtrl.create({
      header: 'Eliminar viaje',
      message: `¿Borrar "${trip.filename}"?`,
      buttons: [
        { text: 'Cancelar', role: 'cancel' },
        {
          text: 'Eliminar',
          role: 'destructive',
          handler: () => {
            this.svc.deleteTrip(trip.id).subscribe({
              next: () => {
                this.trips = this.trips.filter((t) => t.id !== trip.id);
                this.toast('Viaje eliminado', 'success');
              },
              error: (err: any) =>
                this.toast('Error: ' + (err?.error?.detail ?? err?.message ?? err), 'danger'),
            });
          },
        },
      ],
    });
    await alert.present();
  }

  labelFor(pass: any): string {
    if (pass.kind === 'flight' || pass.airline) {
      const route = `${pass.from ?? '?'} → ${pass.to ?? '?'}`;
      const fl = pass.flight ? ` · ${pass.airline ?? ''}${pass.flight}` : '';
      return `${route}${fl}`;
    }
    if (pass.kind === 'train' || pass.train) {
      return `Tren ${pass.train ?? '?'}`;
    }
    return pass.format ?? 'Desconocido';
  }

  goHome() {
    this.router.navigate(['/home']);
  }

  goToItinerary(trip: Trip) {
    this.viewTrip(trip);
  }

  editTrip(trip: Trip) {
    this.router.navigate(['/trip-create'], {
      state: { editTripId: trip.id, tripName: trip.trip_name, segments: trip.segments },
    });
  }

  /** Extrae el código de aeropuerto de origen del primer vuelo. */
  getOriginCode(trip: Trip): string {
    const p = trip.pass_data.passes.find(x => x.kind === 'flight');
    return (p?.from as string) || (trip.trip_name?.match(/\((\w+)\)/)?.[1]) || '—';
  }

  /** Extrae el código de destino del último vuelo. */
  getDestCode(trip: Trip): string {
    const flights = trip.pass_data.passes.filter(x => x.kind === 'flight');
    const last = flights[flights.length - 1];
    return (last?.to as string) || '—';
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
