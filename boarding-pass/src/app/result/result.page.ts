import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { BarcodeImage, BoardingPassService, Pass } from '../services/boarding-pass.service';

@Component({
  selector: 'app-result',
  templateUrl: './result.page.html',
  styleUrls: ['./result.page.scss'],
  standalone: false,
})
export class ResultPage {
  filename = '';
  passes: Pass[] = [];
  images: BarcodeImage[] = [];
  saved = false;
  saving = false;
  savedTripId = 0;

  constructor(
    private router: Router,
    private svc: BoardingPassService,
    private toastCtrl: ToastController,
  ) {}

  /** Ionic lifecycle: se ejecuta cada vez que la pagina se muestra. */
  ionViewWillEnter() {
    // Usamos history.state en vez de getCurrentNavigation para navegaciones
    // desde cualquier origen (routerLink, navigate, back button).
    const state = history.state as {
      filename: string;
      passes: Pass[];
      images: BarcodeImage[];
    } | undefined;
    if (state?.passes) {
      this.filename = state.filename || '';
      this.passes = state.passes;
      this.images = state.images || [];
      this.saved = false;
    }
  }

  saveTrip() {
    if (this.saving || this.saved) return;

    // Verificar que hay pases antes de guardar
    if (!this.passes || this.passes.length === 0) {
      this.toast('No hay pases para guardar', 'warning');
      return;
    }

    this.saving = true;
    const sid = this.svc.getSessionId();
    console.debug('[ResultPage] saveTrip session:', sid, 'passes:', this.passes.length);

    this.svc.saveTrip(this.filename, this.passes, this.images).subscribe({
      next: (resp) => {
        console.debug('[ResultPage] saveTrip response:', resp.status);
        if (resp.status !== 'duplicate') {
          this.savedTripId = resp.id;
        }
        this.saved = resp.status !== 'duplicate';
        this.saving = false;
        if (resp.status === 'duplicate') {
          this.toast('Este viaje ya estaba guardado, sin cambios', 'warning');
        } else if (resp.status === 'updated') {
          this.toast('Viaje actualizado con nuevos datos', 'success');
        } else {
          this.toast('Viaje guardado', 'success');
        }
      },
      error: (err: any) => {
        console.error('[ResultPage] saveTrip error:', err);
        this.saving = false;
        this.toast('Error al guardar: ' + (err?.error?.detail ?? err?.message ?? err), 'danger');
      },
    });
  }

  imageFor(pass: Pass): BarcodeImage | undefined {
    return this.images.find(i => i.page === pass.page);
  }

  labelFor(pass: Pass): string {
    if (pass.kind === 'flight' || pass.airline) {
      const route = `${pass.from ?? '?'} → ${pass.to ?? '?'}`;
      const fl = pass.flight ? ` · ${pass.airline ?? ''}${pass.flight}` : '';
      return `${route}${fl}`;
    }
    if (pass.kind === 'train' || pass.train) {
      return `Tren ${pass.train ?? '?'}`;
    }
    return pass.format;
  }

  goHome() {
    this.router.navigate(['/home']);
  }

  goToItinerary() {
    if (!this.savedTripId) return;
    this.router.navigate(['/itinerary'], {
      state: { tripId: this.savedTripId },
    });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
