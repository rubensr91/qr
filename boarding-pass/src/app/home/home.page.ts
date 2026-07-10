import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { LoadingController, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, Pass } from '../services/boarding-pass.service';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,
})
export class HomePage {
  busy = false;
  progress = '';

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
  ) {}

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

    // Guardar viaje y navegar directo a /trips
    try {
      await firstValueFrom(this.svc.saveTrip(combinedName, allPasses, allImages));
    } catch (e: any) {
      console.error('Error guardando viaje:', e);
    }
    this.router.navigate(['/trips']);
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

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 4000, color });
    await t.present();
  }
}
