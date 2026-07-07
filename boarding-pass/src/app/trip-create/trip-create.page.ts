import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { LoadingController, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, Pass, TravelSegment } from '../services/boarding-pass.service';

const SEGMENT_TYPES = [
  { type: 'flight', label: 'Vuelo', icon: 'airplane' },
  { type: 'train', label: 'Tren', icon: 'train' },
  { type: 'hotel', label: 'Hotel', icon: 'bed' },
  { type: 'car', label: 'Coche', icon: 'car' },
  { type: 'restaurant', label: 'Restaurante', icon: 'restaurant' },
  { type: 'activity', label: 'Actividad', icon: 'football' },
] as const;

@Component({
  selector: 'app-trip-create',
  templateUrl: './trip-create.page.html',
  styleUrls: ['./trip-create.page.scss'],
  standalone: false,
})
export class TripCreatePage {
  tripName = '';
  busy = false;

  segments = signal<TravelSegment[]>([]);
  uploadedPdfs = signal<{ name: string; passes: Pass[] }[]>([]);
  openForm = signal<string | null>(null);

  editTripId: number | null = null;
  existingTripName = '';

  // Form models
  flightForm = { airline: '', flight_number: '', from: '', to: '', date: '', time: '' };
  trainForm = { operator: '', train_number: '', from: '', to: '', date: '', time: '' };
  hotelForm = { name: '', city: '', check_in: '', check_out: '' };
  carForm = { company: '', city: '', pickup_date: '', return_date: '' };
  restaurantForm = { name: '', city: '', date: '', time: '' };
  activityForm = { name: '', city: '', date: '', description: '' };

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
  ) {}

  ionViewWillEnter() {
    const state = history.state as any;
    if (state?.editTripId) {
      this.editTripId = state.editTripId;
      this.existingTripName = state.tripName || '';
      this.tripName = this.existingTripName;
      if (state.segments) {
        this.segments.set(state.segments);
      }
    }
  }

  toggleForm(type: string) {
    this.openForm.set(this.openForm() === type ? null : type);
  }

  get openFormType(): string | null {
    return this.openForm();
  }

  // --- PDF Upload ---

  async pickPdfs() {
    let picked: any[] = [];
    try {
      const result = await FilePicker.pickFiles({ types: ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'], limit: 0 });
      picked = result.files;
    } catch (e: any) {
      if (String(e?.message ?? e).toLowerCase().includes('cancel')) return;
      await this.toast('No se pudo abrir el selector', 'danger');
      return;
    }
    if (!picked.length) return;

    const loading = await this.loadingCtrl.create({ message: 'Procesando PDFs…' });
    await loading.present();
    this.busy = true;

    for (const file of picked) {
      const name = file.name || 'pdf.pdf';
      try {
        const f = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(f));
        if (resp?.passes?.length) {
          const current = this.uploadedPdfs();
          this.uploadedPdfs.set([...current, { name: resp.filename, passes: resp.passes }]);
        }
      } catch (e: any) {
        this.toast(`Error en ${name}`, 'danger');
      }
    }

    await loading.dismiss();
    this.busy = false;
  }

  removePdf(index: number) {
    const current = this.uploadedPdfs();
    this.uploadedPdfs.set(current.filter((_, i) => i !== index));
  }

  // --- Segment handlers ---

  addSegment(type: string) {
    let seg: TravelSegment | null = null;
    switch (type) {
      case 'flight':
        if (!this.flightForm.airline && !this.flightForm.flight_number) return;
        seg = { type: 'flight', ...this.flightForm };
        this.flightForm = { airline: '', flight_number: '', from: '', to: '', date: '', time: '' };
        break;
      case 'train':
        if (!this.trainForm.operator && !this.trainForm.train_number) return;
        seg = { type: 'train', ...this.trainForm };
        this.trainForm = { operator: '', train_number: '', from: '', to: '', date: '', time: '' };
        break;
      case 'hotel':
        if (!this.hotelForm.name) return;
        seg = { type: 'hotel', ...this.hotelForm };
        this.hotelForm = { name: '', city: '', check_in: '', check_out: '' };
        break;
      case 'car':
        if (!this.carForm.company) return;
        seg = { type: 'car', ...this.carForm };
        this.carForm = { company: '', city: '', pickup_date: '', return_date: '' };
        break;
      case 'restaurant':
        if (!this.restaurantForm.name) return;
        seg = { type: 'restaurant', ...this.restaurantForm };
        this.restaurantForm = { name: '', city: '', date: '', time: '' };
        break;
      case 'activity':
        if (!this.activityForm.name) return;
        seg = { type: 'activity', ...this.activityForm };
        this.activityForm = { name: '', city: '', date: '', description: '' };
        break;
    }
    if (seg) {
      this.segments.set([...this.segments(), seg]);
      this.openForm.set(null);
    }
  }

  removeSegment(index: number) {
    const current = this.segments();
    this.segments.set(current.filter((_, i) => i !== index));
  }

  segmentIcon(type: string): string {
    const s = SEGMENT_TYPES.find(s => s.type === type);
    return s?.icon || 'ellipse';
  }

  segmentLabel(type: string): string {
    const s = SEGMENT_TYPES.find(s => s.type === type);
    return s?.label || type;
  }

  // --- Summary helpers ---

  segmentSummary(seg: TravelSegment): string {
    switch (seg.type) {
      case 'flight': return `${seg.airline || ''}${seg.flight_number || ''} ${seg.from || ''}→${seg.to || ''}`.trim() || 'Vuelo';
      case 'train': return `${seg.operator || ''} ${seg.train_number || ''} ${seg.from || ''}→${seg.to || ''}`.trim() || 'Tren';
      case 'hotel': return `${seg.name || ''} (${seg.city || ''}) ${seg.check_in || ''} → ${seg.check_out || ''}`.trim() || 'Hotel';
      case 'car': return `${seg.company || ''} ${seg.city || ''}`.trim() || 'Coche';
      case 'restaurant': return `${seg.name || ''} (${seg.city || ''}) ${seg.date || ''}`.trim() || 'Restaurante';
      case 'activity': return `${seg.name || ''} (${seg.city || ''})`.trim() || 'Actividad';
      default: return 'Segmento';
    }
  }

  // --- Save ---

  async saveTrip() {
    if (!this.tripName.trim() && this.uploadedPdfs().length === 0) {
      await this.toast('Pon un nombre al viaje o sube al menos un PDF', 'warning');
      return;
    }

    const allPasses = this.uploadedPdfs().reduce((acc, p) => acc.concat(p.passes), [] as Pass[]);
    const allImages: any[] = [];
    const filename = this.uploadedPdfs().map(p => p.name).join(' + ') || 'sin_pdfs.pdf';
    this.busy = true;

    if (this.editTripId) {
      // Solo actualizar segmentos
      try {
        await firstValueFrom(this.svc.updateSegments(this.editTripId, this.segments()));
        await this.toast('Segmentos actualizados', 'success');
        this.router.navigate(['/trips']);
      } catch (e: any) {
        this.toast('Error: ' + (e?.error?.detail ?? e?.message ?? e), 'danger');
      }
      this.busy = false;
      return;
    }

    try {
      const resp = await firstValueFrom(
        this.svc.saveTrip(filename, allPasses, allImages, this.tripName.trim(), this.segments()),
      );

      await this.toast('Viaje guardado', 'success');
      this.router.navigate(['/trips']);
    } catch (e: any) {
      this.busy = false;
      this.toast('Error al guardar: ' + (e?.error?.detail ?? e?.message ?? e), 'danger');
    }
  }

  goBack() {
    this.router.navigate(['/home']);
  }

  // --- Helpers ---

  private async toBlob(picked: any): Promise<File> {
    if (picked.blob instanceof Blob && picked.name) {
      return new File([picked.blob], picked.name, { type: 'application/pdf' });
    }
    const resp = await fetch(picked.path ?? picked.uri);
    const blob = await resp.blob();
    return new File([blob], picked.name ?? 'boarding.pdf', { type: 'application/pdf' });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
