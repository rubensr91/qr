import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { AlertController, ToastController } from '@ionic/angular';
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
  private cancelled = false;

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private alertCtrl: AlertController,
    private toastCtrl: ToastController,
  ) {}

  cancel() {
    this.cancelled = true;
    this.busy = false;
    this.progress = '';
  }

  onRefresh(event: any) {
    this.loadTrips();
    event.target.complete();
  }

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
            try { Haptics.impact({ style: ImpactStyle.Heavy }); } catch {}
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

    this.busy = true;

    const allPasses: Pass[] = [];
    const allImages: any[] = [];
    const filenames: string[] = [];
    let errors = 0;
    const errorMessages: string[] = [];

    for (let i = 0; i < picked.length; i++) {
      if (this.cancelled) break;
      const file = picked[i];
      const filename = file.name || `pdf_${i + 1}.pdf`;
      this.progress = `${i + 1}/${picked.length}`;

      try {
        const blob = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(blob, file.name));
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
      if (this.cancelled) break;
    }
    if (this.cancelled) {
      this.cancelled = false;
      this.busy = false;
      this.progress = '';
      return;
    }

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

  private async toBlob(picked: any): Promise<Blob> {
    const name = picked.name ?? 'file';
    const mime = picked.mimeType || '';
    const b64 = picked.data || picked.blob;
    if (typeof b64 === 'string' && b64.length > 0) {
      let clean = b64.includes(',') ? b64.split(',')[1] : b64;
      try {
        const chars = atob(clean);
        const bytes = new Uint8Array(chars.length);
        for (let i = 0; i < chars.length; i++) bytes[i] = chars.charCodeAt(i);
        return new Blob([bytes], { type: mime });
      } catch (e: any) {
        throw new Error('Base64 decode failed: ' + e.message);
      }
    }
    if (picked.blob instanceof Blob) {
      return picked.blob;
    }
    const url = picked.path ?? picked.uri ?? '';
    if (url) {
      const resp = await fetch(url);
      const blob = await resp.blob();
      return blob;
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

  tripDateRange(trip: Trip): string {
    const dates = trip.pass_data.passes
      .map(p => p.flight_date)
      .filter((d): d is string => !!d)
      .sort();
    if (!dates.length) return '';
    if (dates.length === 1) return this.formatShortDate(dates[0]);
    const first = this.formatShortDate(dates[0]);
    const last = this.formatShortDate(dates[dates.length - 1]);
    return `${first} — ${last}`;
  }

  private formatShortDate(date: string): string {
    const parts = date.split('-');
    if (parts.length !== 3) return date;
    return `${parts[2]}/${parts[1]}`;
  }

  /** Determina el icono de modo de transporte para la tarjeta del viaje. */
  tripModeIcon(trip: Trip): string {
    const hasTrain = trip.pass_data.passes.some(p => p.kind === 'train');
    return hasTrain ? 'train-outline' : 'airplane-outline';
  }

  /** Extrae el código de origen del primer vuelo o tren. */
  getOriginCode(trip: Trip): string {
    const flight = trip.pass_data.passes.find(x => x.kind === 'flight');
    if (flight?.from) return flight.from as string;
    const train = trip.pass_data.passes.find(x => x.kind === 'train');
    if (train?.from) {
      const from = train.from as string;
      return from.includes(' - ') ? from.split(' - ')[0] : from;
    }
    return '—';
  }

  /** Extrae el destino del primer vuelo o tren (ida, no vuelta). */
  getDestCode(trip: Trip): string {
    const flights = trip.pass_data.passes.filter(x => x.kind === 'flight');
    if (flights.length) {
      return (flights[0]?.to as string) || '—';
    }
    const train = trip.pass_data.passes.find(x => x.kind === 'train');
    if (train?.to) {
      const to = train.to as string;
      return to.includes(' - ') ? to.split(' - ')[0] : to;
    }
    return '—';
  }

  /** Ruta completa: origen → destino → destino → ...
   *  Deduplica pasajeros (misma ruta, mismo tren/vuelo, misma hora). */
  getRoute(trip: Trip): string {
    const passes = [...(trip.pass_data.passes || [])];
    if (!passes.length) return '—';

    // Ordenar por fecha y hora
    passes.sort((a, b) => {
      const da = a.flight_date || '';
      const db = b.flight_date || '';
      if (da !== db) return da < db ? -1 : 1;
      const ta = a.flight_time || '';
      const tb = b.flight_time || '';
      return ta < tb ? -1 : ta > tb ? 1 : 0;
    });

    // Deduplicar misma ruta (mismo tren/vuelo, misma fecha-hora, mismo from→to)
    const seen = new Set<string>();
    const unique: { from: string; to: string }[] = [];
    for (const p of passes) {
      const from = (p.from || '').replace(/ - .*$/, '').trim();
      const to = (p.to || '').replace(/ - .*$/, '').trim();
      const key = `${p.flight_date}|${p.flight_time}|${from}|${to}`;
      if (seen.has(key)) continue;
      seen.add(key);
      unique.push({ from, to });
    }

    // Construir ruta: origen + todos los destinos
    if (!unique.length) return '—';
    const cities: string[] = [];
    for (const u of unique) {
      if (!cities.length || cities[cities.length - 1] !== u.from) {
        cities.push(u.from);
      }
      cities.push(u.to);
    }

    // Si es viaje redondo (vuelta al origen), mostrar solo ciudades únicas
    // ej: Sevilla→Madrid→Toledo→Madrid→Sevilla → Sevilla→Madrid→Toledo
    if (cities.length >= 3 && cities[0] === cities[cities.length - 1]) {
      const seen = new Set<string>();
      const deduped: string[] = [];
      for (const c of cities) {
        if (!seen.has(c)) {
          seen.add(c);
          deduped.push(c);
        }
      }
      return deduped.join(' → ');
    }

    return cities.join(' → ');
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
