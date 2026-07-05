import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { LoadingController, ToastController } from '@ionic/angular';
import { BoardingPassService } from '../services/boarding-pass.service';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,
})
export class HomePage {
  busy = false;

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
        types: ['application/pdf'],
        limit: 1,
      });
      picked = result.files;
    } catch (e: any) {
      // El usuario cancela -> no es error
      if (String(e?.message ?? e).toLowerCase().includes('cancel')) return;
      await this.toast('No se pudo abrir el selector de archivos', 'danger');
      return;
    }

    if (!picked || picked.length === 0) return;
    const file = picked[0];

    const loading = await this.loadingCtrl.create({ message: 'Procesando PDF…' });
    await loading.present();
    this.busy = true;

    try {
      const f = await this.toBlob(file);
      const resp = await this.svc.uploadPdf(f).toPromise();
      await loading.dismiss();
      this.busy = false;
      if (!resp) throw new Error('Respuesta vacía del servidor');
      this.router.navigate(['/result'], {
        state: { filename: resp.filename, passes: resp.passes, images: resp.images },
      });
    } catch (e: any) {
      await loading.dismiss();
      this.busy = false;
      await this.toast('Error: ' + (e?.error?.detail ?? e?.message ?? e), 'danger');
    }
  }

  private async toBlob(picked: any): Promise<File> {
    // El plugin da un blob "raw" con path/uri; en web solo tenemos el File directo.
    if (picked.blob instanceof Blob && picked.name) {
      return new File([picked.blob], picked.name, { type: 'application/pdf' });
    }
    // Fallback: fetch desde la URI
    const resp = await fetch(picked.path ?? picked.uri);
    const blob = await resp.blob();
    return new File([blob], picked.name ?? 'boarding.pdf', { type: 'application/pdf' });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
