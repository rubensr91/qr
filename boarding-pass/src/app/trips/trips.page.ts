import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AlertController, LoadingController, ToastController } from '@ionic/angular';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, Pass, Trip } from '../services/boarding-pass.service';

@Component({
  selector: 'app-trips',
  templateUrl: './trips.page.html',
  styleUrls: ['./trips.page.scss'],
  standalone: false,
})
export class TripsPage {
  trips: Trip[] = [];
  loading = true;

  busy = false;
  progress = '';

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private alertCtrl: AlertController,
    private loadingCtrl: LoadingController,
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

  async pickAndUpload() {
    let picked: any[] = [];
    try {
      const result = await FilePicker.pickFiles({
        types: ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'],
        limit: 0,
        readData: true,
      });
      picked = result.files;
    } catch (e: any) {
      if (String(e?.message ?? e).toLowerCase().includes('cancel')) return;
      await this.toast('No se pudo abrir el selector de archivos', 'danger');
      return;
    }

    if (!picked || picked.length === 0) return;

    const loading = await this.loadingCtrl.create({ message: 'Procesando PDFs…' });
    await loading.present();
    this.busy = true;

    const allPasses: Pass[] = [];
    const allImages: any[] = [];
    const filenames: string[] = [];
    let errors = 0;
    const errorMessages: string[] = [];

    for (let i = 0; i < picked.length; i++) {
      const file = picked[i];
      const filename = file.name || `pdf_${i + 1}.pdf`;
      this.progress = `${i + 1}/${picked.length}`;
      loading.message = `Procesando ${i + 1}/${picked.length}: ${filename}`;

      try {
        const f = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(f));
        if (resp) {
          for (const p of resp.passes) {
            p.sourceFile = filename;
          }
          allPasses.push(...resp.passes);
          allImages.push(...resp.images);
          filenames.push(resp.filename);
        }
      } catch (e: any) {
        errors++;
        const msg = e?.error?.detail || e?.message || e?.statusText || String(e);
        errorMessages.push(filename + ': ' + msg);
        console.error('Error ' + filename + ':', msg, e);
      }
    }

    await loading.dismiss();
    this.busy = false;
    this.progress = '';

    // Mostrar errores detallados tras cerrar el loading
    for (const em of errorMessages) {
      await this.toast(em, 'danger');
    }

    if (allPasses.length === 0) {
      await this.toast('No se encontraron tarjetas en ningún archivo', 'danger');
      return;
    }

    if (errors > 0) {
      await this.toast(`${errors} archivo${errors > 1 ? 's' : ''} fallaron, mostrando el resto`, 'warning');
    }

    const combinedName = filenames.join(' + ') || 'varios.pdf';

    try {
      await firstValueFrom(this.svc.saveTrip(combinedName, allPasses, allImages));
    } catch (e: any) {
      console.error('Error guardando viaje:', e);
    }
    this.loadTrips();
  }

  private async toBlob(picked: any): Promise<File> {
    const b64 = picked.data || picked.blob;
    if (typeof b64 === 'string' && b64.length > 0) {
      let clean = b64.includes(',') ? b64.split(',')[1] : b64;
      try {
        const chars = atob(clean);
        const bytes = new Uint8Array(chars.length);
        for (let i = 0; i < chars.length; i++) bytes[i] = chars.charCodeAt(i);
        return new File([bytes], picked.name ?? 'file');
      } catch (e: any) {
        throw new Error('Base64 decode failed: ' + e.message);
      }
    }
    if (picked.blob instanceof Blob) {
      return new File([picked.blob], picked.name ?? 'file');
    }
    const url = picked.path ?? picked.uri ?? '';
    if (url) {
      const resp = await fetch(url);
      return new File([await resp.blob()], picked.name ?? 'file');
    }
    throw new Error('No file data available');
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
    // Primero vuelos
    const flight = trip.pass_data.passes.find(x => x.kind === 'flight');
    if (flight?.from) return flight.from as string;
    // Luego trenes
    const train = trip.pass_data.passes.find(x => x.kind === 'train' && (x as any).train);
    if (train) return 'TREN';
    return (trip.trip_name?.match(/\((\w+)\)/)?.[1]) || '—';
  }

  /** Extrae el código de destino del primer vuelo (no del último — para
   *  vuelta a origen mostraría mismo sitio). Para viaje redondo
   *  BCN→SVQ, SVQ→BCN muestra SVQ, no BCN. */
  getDestCode(trip: Trip): string {
    const flights = trip.pass_data.passes.filter(x => x.kind === 'flight');
    if (flights.length) {
      const first = flights[0];
      return (first?.to as string) || '—';
    }
    const train = trip.pass_data.passes.find(x => x.kind === 'train' && (x as any).train);
    if (train) return (train as any).train || 'TREN';
    return '—';
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
