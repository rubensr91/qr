import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BarcodeImage, Pass } from '../services/boarding-pass.service';

@Component({
  selector: 'app-result',
  templateUrl: './result.page.html',
  styleUrls: ['./result.page.scss'],
  standalone: false,
})
export class ResultPage implements OnInit {
  filename = '';
  passes: Pass[] = [];
  images: BarcodeImage[] = [];

  constructor(private route: ActivatedRoute, private router: Router) {}

  ngOnInit() {
    const state = this.router.getCurrentNavigation()?.extras.state as {
      filename: string;
      passes: Pass[];
      images: BarcodeImage[];
    } | undefined;
    if (state) {
      this.filename = state.filename;
      this.passes = state.passes;
      this.images = state.images;
    }
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
}
