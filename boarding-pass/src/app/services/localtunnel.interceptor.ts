import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HTTP_INTERCEPTORS,
} from '@angular/common/http';
import { Observable } from 'rxjs';

/** Añade el header Bypass-Tunnel-Reminder para saltar la página de password de localtunnel. */
@Injectable()
export class LocaltunnelInterceptor implements HttpInterceptor {
  intercept(
    req: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    if (req.url.includes('loca.lt')) {
      req = req.clone({
        setHeaders: { 'Bypass-Tunnel-Reminder': 'true' },
      });
    }
    return next.handle(req);
  }
}

export const LOCALTUNNEL_INTERCEPTOR_PROVIDER = {
  provide: HTTP_INTERCEPTORS,
  useClass: LocaltunnelInterceptor,
  multi: true,
};
