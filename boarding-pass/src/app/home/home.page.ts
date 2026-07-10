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
    console.log('[toBlob] picked:', JSON.stringify({ name: picked.name, mimeType: picked.mimeType, hasBlob: !!picked.blob, blobType: typeof picked.blob, blobLen: picked.blob?.length, hasPath: !!picked.path }));
    if (picked.blob instanceof Blob && picked.name) {
      console.log('[toBlob] using native Blob');
      return new File([picked.blob], picked.name);
    }
    if (typeof picked.blob === 'string' && picked.blob.length > 0) {
      let b64 = picked.blob;
      if (b64.includes(',')) {
        b64 = b64.split(',')[1];
      }
      try {
        const byteChars = atob(b64);
        const bytes = new Uint8Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) {
          bytes[i] = byteChars.charCodeAt(i);
        }
        console.log('[toBlob] base64 -> ' + bytes.length + ' bytes');
        return new File([bytes], picked.name ?? 'boarding.pdf');
      } catch (e: any) {
        console.error('[toBlob] base64 decode failed:', e);
      }
    }
    const url = picked.path ?? picked.uri ?? '';
    console.log('[toBlob] fetch fallback:', url);
    const resp = await fetch(url);
    const blob = await resp.blob();
    return new File([blob], picked.name ?? 'boarding.pdf');
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 4000, color });
    await t.present();
  }
}
