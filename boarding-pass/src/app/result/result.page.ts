import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { BarcodeImage, BoardingPassService, Pass } from '../services/boarding-pass.service';

/** Normaliza nombre de pasajero a formato canonico 'Nombre Apellido1 Apellido2'.
 *  Convierte 'APELLIDO/NOMBRE' -> 'Nombre Apellido', quita acentos.
 *  Maneja tambien formato Renfe con puntos: 'I.Apellido1.Apellido2'
 *  Se usa para DISPLAY (mostrar en la UI), no para comparacion.
 */
function normalizePassengerName(name: string): string {
  if (!name) return name;
  name = name.trim();

  let words: string[];
  // Formato con puntos (Renfe): "R.serena.roas" -> palabras separadas
  if (name.includes('.') && !name.includes(' ')) {
    words = name.split('.').filter(w => w.length > 0);
  } else if (name.includes('/')) {
    const parts = name.split('/');
    const surnames = parts[0].trim();
    const firstName = (parts[1] || '').trim();
    words = [...firstName.split(/\s+/), ...surnames.split(/\s+/)];
  } else {
    words = name.split(/\s+/);
  }

  return words
    .filter(w => w.length > 0)
    .map(w => {
      const normalized = w.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      return normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
    })
    .join(' ');
}

/** Extrae los apellidos de un nombre y devuelve una clave para COMPARACION.
 *  Lowercase, sin acentos, solo letras (sin espacios ni simbolos).
 *  Version TypeScript de get_surname_key() en extraer_qr_pdfs.py.
 *
 *  Formatos: 'APELLIDO/NOMBRE', 'Nombre Apellido', 'I.Apellido1.Apellido2'
 *  Ej: 'R.serena.roas' y 'Ruben Serena Roas' -> ambos 'serenaroas'
 */
function getSurnameKey(name: string): string {
  if (!name) return '';
  name = name.trim();

  let surnamePart: string;
  // Formato con puntos (Renfe): "R.serena.roas" -> saltar inicial
  if (name.includes('.') && !name.includes(' ')) {
    const parts = name.split('.');
    surnamePart = parts.length > 1 ? parts.slice(1).join(' ') : name;
  } else if (name.includes('/')) {
    // APELLIDO/NOMBRE -> apellidos antes de '/'
    surnamePart = name.split('/')[0].trim();
  } else {
    // Nombre Apellido1 Apellido2 -> apellidos = todo tras primer nombre
    const words = name.split(/\s+/);
    if (words.length <= 1) return '';
    surnamePart = words.slice(1).join(' ');
  }

  return surnamePart
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // quitar acentos
    .toLowerCase()
    .replace(/[^a-z]/g, '');  // solo letras
}

/** Selecciona el nombre mas completo del grupo para mostrar en la UI.
 *  Prefiere mas partes (nombre + dos apellidos > nombre + un apellido)
 *  y a igual numero de partes, el string mas largo.
 *  Cuenta partes separadas por espacios O puntos (formato Renfe).
 */
function selectDisplayName(names: string[]): string {
  return names.reduce((best, n) => {
    const current = n.trim();
    if (!current) return best;
    const currParts = current.split(/[.\s]+/).filter(x => x.length > 0).length;
    const bestParts = best.split(/[.\s]+/).filter(x => x.length > 0).length;
    if (currParts > bestParts) return current;
    if (currParts === bestParts && current.length > best.length) return current;
    return best;
  }, names[0]?.trim() || 'Sin nombre');
}

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
    // Agrupar por APELLIDOS (lowercase, solo letras) para detectar
    // el mismo pasajero aunque el nombre cambie de formato entre operadores.
    // Ej: 'GARCIA PEREZ/JUAN' y 'Juan Garcia Perez' -> misma clave 'garciaperez'
    const map = new Map<string, { passes: Pass[]; names: string[] }>();
    for (const p of passes) {
      // Un pase puede tener varios pasajeros (dedup backend). Distribuirlos.
      const names = (p.passenger_names?.length ? p.passenger_names : [p.name || '']);
      for (const n of names) {
        const key = getSurnameKey(n) || 'Sin nombre';
        if (!map.has(key)) map.set(key, { passes: [], names: [] });
        const entry = map.get(key)!;
        if (!entry.passes.includes(p)) entry.passes.push(p);
        if (!entry.names.includes(n)) entry.names.push(n);
      }
    }
    const groups: PassengerGroup[] = [];
    for (const [key, entry] of map) {
      const { passes: list, names } = entry;
      // Orden cronologico: flight_date asc, flight_time asc (nulls al final)
      list.sort((a, b) => {
        const da = a.flight_date || '9999-99-99';
        const db = b.flight_date || '9999-99-99';
        if (da !== db) return da < db ? -1 : 1;
        const ta = a.flight_time || '99:99';
        const tb = b.flight_time || '99:99';
        return ta < tb ? -1 : 1;
      });
      // Mostrar el nombre mas completo de los que coinciden con este grupo
      groups.push({ name: selectDisplayName(names), passes: list });
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
