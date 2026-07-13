import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { ToastController } from '@ionic/angular';
import { ScreenBrightness } from '@capacitor-community/screen-brightness';
import { BarcodeImage, BoardingPassService, Pass, TravelSegment } from '../services/boarding-pass.service';
import {
  DailyPlan,
  ExpandResponse,
  HistoricalSite,
  Hotel,
  ItineraryData,
  ItineraryService,
  PlaceOfInterest,
  Restaurant,
  WeatherDay,
} from '../services/itinerary.service';
import { QuizQuestion, QuizService } from '../services/quiz.service';

const SEGMENT_ICONS: Record<string, string> = {
  flight: 'airplane', train: 'train', hotel: 'bed',
  car: 'car', restaurant: 'restaurant', activity: 'football',
};
const SEGMENT_LABELS: Record<string, string> = {
  flight: 'Vuelo', train: 'Tren', hotel: 'Hotel',
  car: 'Coche', restaurant: 'Restaurante', activity: 'Actividad',
};

/** Normaliza nombre de pasajero a formato canonico 'Nombre Apellido1 Apellido2'.
 *  Convierte 'APELLIDO/NOMBRE' -> 'Nombre Apellido', quita acentos.
 *  Maneja tambien formato Renfe con puntos: 'I.Apellido1.Apellido2'
 *  Se usa para DISPLAY (mostrar en la UI), no para comparacion.
 */
function normalizePassengerName(name: string): string {
  if (!name) return name;
  name = name.trim();

  let words: string[];
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
    surnamePart = name.split('/')[0].trim();
  } else {
    const words = name.split(/\s+/);
    if (words.length <= 1) return '';
    surnamePart = words.slice(1).join(' ');
  }

  return surnamePart
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z]/g, '');
}

/** Selecciona el nombre mas completo del grupo para mostrar en la UI. */
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
  activeTab: 'plan' | 'cards' | 'bookings' | 'eat' | 'sleep' | 'visit' | 'tips' | 'quiz' = 'plan';

  enlargedBarcode: BarcodeImage | null = null;
  private previousBrightness: number | undefined;

  expanding: Record<string, boolean> = {};
  expandErrors: Record<string, string> = {};

  // Quiz state
  quizQuestions: QuizQuestion[] = [];
  quizAnswers: (number | null)[] = [];
  quizSubmitted = false;
  quizScore = 0;
  quizLoading = false;
  quizError = '';
  quizDestinations: string[] = [];

  constructor(
    private router: Router,
    private itinerarySvc: ItineraryService,
    private bpSvc: BoardingPassService,
    private toastCtrl: ToastController,
    private quizSvc: QuizService,
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

  private afterLoad(preserveTab = false) {
    if (!preserveTab) {
      this.activeTab = 'cards';
      this.loadItinerary();
    } else {
      this.loading = false;
    }
  }

  private fetchTripData(preserveTab = false) {
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
        this.afterLoad(preserveTab);
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
        if (resp.itinerary?.daily_itinerary?.length) {
          this.activeTab = 'plan';
        }
        this._showValidation(resp.itinerary?._validation);
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
    const sid = this.bpSvc.getSessionId();

    this.itinerarySvc.generate(this.tripId, sid).subscribe({
      next: (resp) => {
        this.itinerary = resp.itinerary;
        this.generating = false;
        this.activeTab = 'plan';
        this._showValidation(resp.itinerary?._validation);
      },
      error: (err: any) => {
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

  async openBarcode(img: BarcodeImage) {
    this.enlargedBarcode = img;
    try {
      const { brightness } = await ScreenBrightness.getBrightness();
      this.previousBrightness = brightness;
      await ScreenBrightness.setBrightness({ brightness: 1.0 });
    } catch (e) {
      console.warn('ScreenBrightness no disponible:', e);
    }
  }

  async closeBarcode() {
    this.enlargedBarcode = null;
    try {
      if (this.previousBrightness !== undefined) {
        await ScreenBrightness.setBrightness({ brightness: this.previousBrightness });
        this.previousBrightness = undefined;
      }
    } catch (e) {
      console.warn('ScreenBrightness restauro no disponible:', e);
    }
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

  /**
   * Compara fechas de vuelo manejando cruces de año entre PNRs distintos.
   * Cuando dos fechas comparten el mismo año inferido pero una es final de año (mes ≥ 10)
   * y la otra es principio (mes ≤ 3), asumimos que cruzan el cambio de año.
   */
  private compareFlightDates(a: Pass, b: Pass): number {
    const da = a.flight_date;
    const db = b.flight_date;
    if (!da && !db) return 0;
    if (!da) return 1;
    if (!db) return -1;

    const [ay, am, ad] = da.split('-').map(Number);
    const [by, bm, bd] = db.split('-').map(Number);

    // Si años distintos o años explícitos → comparación directa
    if (ay !== by || a.has_explicit_year || b.has_explicit_year) {
      if (ay !== by) return ay - by;
      if (am !== bm) return am - bm;
      return ad - bd;
    }

    // Ambos comparten año inferido y sin año explícito.
    // Si hay un salto grande de mes (≥ 6 meses de diferencia), la fecha
    // con mes más bajo pertenece al año siguiente.
    const monthGap = Math.abs(am - bm);
    if (monthGap >= 6) {
      // El mes más bajo (enero-marzo) va DESPUÉS → es del año siguiente
      if (am <= 3 && bm >= 10) return 1;
      if (bm <= 3 && am >= 10) return -1;
    }
    // Mismo año: orden natural por mes y día
    if (am !== bm) return am - bm;
    return ad - bd;
  }

  private buildGroups(passes: Pass[]): { name: string; passes: Pass[] }[] {
    // Agrupar por APELLIDOS (lowercase, solo letras) para detectar
    // el mismo pasajero aunque el nombre cambie de formato entre operadores.
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
    const groups: { name: string; passes: Pass[] }[] = [];
    for (const [groupKey, entry] of map) {
      const { passes: list, names } = entry;
      list.sort((a, b) => {
        const dateCmp = this.compareFlightDates(a, b);
        if (dateCmp !== 0) return dateCmp;
        const ta = a.flight_time || '99:99';
        const tb = b.flight_time || '99:99';
        return ta < tb ? -1 : 1;
      });
      // Mostrar el nombre mas completo de los que coinciden con este grupo
      groups.push({ name: selectDisplayName(names), passes: list });
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

  onRefresh(event: any) {
    if (this.tripId) {
      this.fetchTripData(true);
      this.loadItinerary();
    }
    event.target.complete();
  }

  retryLoad() {
    if (this.tripId) {
      this.error = '';
      this.loading = true;
      this.fetchTripData();
    } else {
      this.goBack();
    }
  }

  editSegments() {
    this.router.navigate(['/trip-create'], {
      state: { editTripId: this.tripId, tripName: this.tripName, segments: this.segments },
    });
  }

  expandSection(section: string) {
    if (this.expanding[section]) return;

    this.expanding[section] = true;
    this.expandErrors[section] = '';
    const sid = this.bpSvc.getSessionId();

    this.itinerarySvc.expandSection(this.tripId, section, sid).subscribe({
      next: (resp: ExpandResponse) => {
        this.expanding[section] = false;
        if (resp.error) {
          this.expandErrors[section] = resp.error;
          this.toast(resp.error, 'danger');
          return;
        }
        const count = this.countExpandedItems(section, resp);
        if (!count) {
          this.toast('No se encontraron más sugerencias', 'warning');
          return;
        }
        this.appendExpandResult(section, resp);
        this.toast(`${count} sugerencias añadidas`, 'success');
        try { Haptics.impact({ style: ImpactStyle.Medium }); } catch {}
      },
      error: (err: any) => {
        this.expanding[section] = false;
        const msg = err?.error?.detail?.error || err?.error?.detail || err?.message || 'Error';
        this.expandErrors[section] = msg;
        this.toast('Error: ' + msg, 'danger');
      },
    });
  }

  private countExpandedItems(section: string, resp: ExpandResponse): number {
    switch (section) {
      case 'restaurants': return (resp.items || []).length;
      case 'hotels': return (resp.items || []).length;
      case 'visit': return (resp.places_of_interest || []).length + (resp.historical_sites || []).length;
      case 'tips': return (resp.transport_tips || []).length + (resp.general_tips || []).length + (resp.cultural_notes || []).length;
      default: return 0;
    }
  }

  private appendExpandResult(section: string, resp: ExpandResponse) {
    if (!this.itinerary) return;
    switch (section) {
      case 'restaurants':
        this.itinerary.restaurants = [...(this.itinerary.restaurants || []), ...(resp.items || [])];
        break;
      case 'hotels':
        this.itinerary.hotels = [...(this.itinerary.hotels || []), ...(resp.items || [])];
        break;
      case 'visit':
        this.itinerary.places_of_interest = [...(this.itinerary.places_of_interest || []), ...(resp.places_of_interest || [])];
        this.itinerary.historical_sites = [...(this.itinerary.historical_sites || []), ...(resp.historical_sites || [])];
        break;
      case 'tips':
        this.itinerary.transport_tips = [...(this.itinerary.transport_tips || []), ...(resp.transport_tips || [])];
        this.itinerary.general_tips = [...(this.itinerary.general_tips || []), ...(resp.general_tips || [])];
        this.itinerary.cultural_notes = [...(this.itinerary.cultural_notes || []), ...(resp.cultural_notes || [])];
        break;
    }
    this.itinerary = { ...this.itinerary };
  }

  generateQuiz() {
    this.quizLoading = true;
    this.quizError = '';
    this.quizQuestions = [];
    this.quizSubmitted = false;
    const sid = this.bpSvc.getSessionId();

    this.quizSvc.generate(this.tripId, sid).subscribe({
      next: (resp) => {
        this.quizLoading = false;
        if (resp.error) {
          this.quizError = resp.error;
          this.toast(resp.error, 'danger');
          return;
        }
        this.quizQuestions = resp.questions || [];
        this.quizAnswers = this.quizQuestions.map(() => null);
        this.quizDestinations = resp.destinations || [];
        this.activeTab = 'quiz';
        this._showValidation(resp._validation);
      },
      error: (err: any) => {
        this.quizLoading = false;
        const msg = err?.error?.detail?.error || err?.error?.detail || err?.message || 'Error al generar quiz';
        this.quizError = msg;
        this.toast('Error: ' + msg, 'danger');
      },
    });
  }

  selectAnswer(index: number, optionIndex: number) {
    if (this.quizSubmitted) return;
    this.quizAnswers[index] = optionIndex;
  }

  quizIncomplete(): boolean {
    return this.quizAnswers.some(a => a === null);
  }

  quizAnsweredCount(): number {
    return this.quizAnswers.filter(a => a !== null).length;
  }

  submitQuiz() {
    let correct = 0;
    for (let i = 0; i < this.quizQuestions.length; i++) {
      if (this.quizAnswers[i] === this.quizQuestions[i].correct_index) {
        correct++;
      }
    }
    this.quizScore = correct;
    this.quizSubmitted = true;
  }

  resetQuiz() {
    this.quizQuestions = [];
    this.quizAnswers = [];
    this.quizSubmitted = false;
    this.quizScore = 0;
    this.quizError = '';
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }

  private _showValidation(v?: { is_valid: boolean; errors: string[]; warnings: string[] }): void {
    if (!v) return;
    const all = [...(v.errors || []), ...(v.warnings || [])];
    if (!all.length) return;
    const summary = all.slice(0, 3).join('; ');
    const tail = all.length > 3 ? ` (+${all.length - 3} más)` : '';
    this.toast(`⚠️ ${summary}${tail}`, v.is_valid ? 'warning' : 'danger');
  }
}
