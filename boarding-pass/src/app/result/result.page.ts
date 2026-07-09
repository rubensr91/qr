import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { BarcodeImage, BoardingPassService, Pass } from '../services/boarding-pass.service';

export interface PassengerGroup {
  name: string;
  passes: Pass[];
}

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
  groups: PassengerGroup[] = [];
  expandedGroup: string | null = null;
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
    const state = history.state as {
      filename: string;
      passes: Pass[];
      images: BarcodeImage[];
    } | undefined;
    if (state?.passes) {
      this.filename = state.filename || '';
      this.passes = state.passes;
      this.images = state.images || [];
      this.groups = this.buildGroups(state.passes);
      this.expandedGroup = null;
      this.saved = false;
    }
  }

  private buildGroups(passes: Pass[]): PassengerGroup[] {
    const map = new Map<string, Pass[]>();
    for (const p of passes) {
      const key = (p.name || 'Sin nombre').toUpperCase();
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    }
    const groups: PassengerGroup[] = [];
    for (const [key, list] of map) {
      // Orden cronologico: flight_date asc, flight_time asc (nulls al final)
      list.sort((a, b) => {
        const da = a.flight_date || '9999-99-99';
        const db = b.flight_date || '9999-99-99';
        if (da !== db) return da < db ? -1 : 1;
        const ta = a.flight_time || '99:99';
        const tb = b.flight_time || '99:99';
        return ta < tb ? -1 : 1;
      });
      // Usar el nombre original del primer pase del grupo
      const originalName = list[0].name || 'Sin nombre';
      groups.push({ name: originalName, passes: list });
    }
    // Ordenar grupos alfabeticamente por nombre
    groups.sort((a, b) => a.name.localeCompare(b.name));
    return groups;
  }

  toggleGroup(name: string) {
    this.expandedGroup = this.expandedGroup === name ? null : name;
  }

  isGroupExpanded(name: string): boolean {
    return this.expandedGroup === name;
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

  /** Codigo grande que aparece en la cabecera (airline o "RENFE"/"AVANT"). */
  airlineLabel(pass: Pass): string {
    if (pass.airline) return pass.airline;
    if (pass.kind === 'train') return 'TREN';
    return pass.format || '—';
  }

  /** Nombre completo del operador (para mostrar debajo del codigo). */
  airlineName(code: string): string {
    const names: Record<string, string> = {
      VY: 'Vueling', IB: 'Iberia', FR: 'Ryanair', AA: 'American Airlines',
      BA: 'British Airways', LH: 'Lufthansa', AF: 'Air France', KL: 'KLM',
      U2: 'easyJet', W6: 'Wizz Air', EW: 'Eurowings', TP: 'TAP',
    };
    return names[code] || code;
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
