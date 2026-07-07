import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { LoadingController, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, ExtractResponse, Pass } from '../services/boarding-pass.service';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,
})
export class HomePage implements OnInit {
  busy = false;
  progress = '';
  hasTrips = false;

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
  ) {}

  async ngOnInit() {
    this.refreshHasTrips();
  }

  /** Llamar al volver a la home (p.ej. despues de borrar el ultimo viaje)
   *  para que el CTA vuelva al estado "sin viajes". */
  async ionViewWillEnter() {
    await this.refreshHasTrips();
  }

  private async refreshHasTrips() {
    try {
      const resp = await firstValueFrom(this.svc.getTrips());
      this.hasTrips = (resp?.trips?.length ?? 0) > 0;
    } catch {
      this.hasTrips = false;
    }
  }

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
        console.error(`Error procesando ${filename}:`, e);
      }
    }

    await loading.dismiss();
    this.busy = false;
    this.progress = '';

    if (allPasses.length === 0) {
      await this.toast('No se encontraron tarjetas en ningún archivo', 'danger');
      return;
    }

    if (errors > 0) {
      await this.toast(`${errors} archivo${errors > 1 ? 's' : ''} fallaron, mostrando el resto`, 'warning');
    }

    const combinedName = filenames.join(' + ') || 'varios.pdf';

    // Mostrar resultados YA (flujo directo como en main), guardar en segundo plano
    this.router.navigate(['/result'], {
      state: { filename: combinedName, passes: allPasses, images: allImages },
    });
    firstValueFrom(this.svc.saveTrip(combinedName, allPasses, allImages))
      .then(() => console.log('Viaje guardado en segundo plano'))
      .catch(e => console.error('Error guardando viaje en segundo plano:', e));
  }

  private async toBlob(picked: any): Promise<File> {
    if (picked.blob instanceof Blob && picked.name) {
      return new File([picked.blob], picked.name, { type: 'application/pdf' });
    }
    const resp = await fetch(picked.path ?? picked.uri);
    const blob = await resp.blob();
    return new File([blob], picked.name ?? 'boarding.pdf', { type: 'application/pdf' });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 4000, color });
    await t.present();
  }
}
