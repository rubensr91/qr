This file is a merged representation of a subset of the codebase, containing specifically included files, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.py, **/*.ts, **/*.html, **/*.scss, **/*.json
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
.omo/
  run-continuation/
    ses_0a445a64affeEfKJXq9EuVzKnP.json
    ses_0b5416f7dffeZ8e2uzYg4p50hM.json
    ses_0c80a8dcfffeFLDprGR3TdXF9d.json
backend/
  __init__.py
  admin.py
  app.py
  itinerary.py
  parser.py
  qr_client.py
  token_tracker.py
boarding-pass/
  src/
    app/
      home/
        home-routing.module.ts
        home.module.ts
        home.page.html
        home.page.scss
        home.page.spec.ts
        home.page.ts
      itinerary/
        itinerary.module.ts
        itinerary.page.html
        itinerary.page.scss
        itinerary.page.ts
      result/
        result.module.ts
        result.page.html
        result.page.scss
        result.page.ts
      services/
        boarding-pass.service.ts
        itinerary.service.ts
        localtunnel.interceptor.ts
      trip-create/
        trip-create.module.ts
        trip-create.page.html
        trip-create.page.scss
        trip-create.page.ts
      trips/
        trips.module.ts
        trips.page.html
        trips.page.scss
        trips.page.ts
      app-routing.module.ts
      app.component.html
      app.component.scss
      app.component.spec.ts
      app.component.ts
      app.module.ts
    environments/
      environment.prod.ts
      environment.ts
    theme/
      variables.scss
    global.scss
    index.html
    main.ts
    polyfills.ts
    test.ts
    zone-flags.ts
  .eslintrc.json
  angular.json
  capacitor.config.json
  ionic.config.json
  ionic.starter.json
  package.json
  tsconfig.app.json
  tsconfig.json
  tsconfig.spec.json
dashboard/
  index.html
qr_service/
  client.py
  main.py
extraer_qr_pdfs.py
```

# Files

## File: .omo/run-continuation/ses_0a445a64affeEfKJXq9EuVzKnP.json
````json
{
  "sessionID": "ses_0a445a64affeEfKJXq9EuVzKnP",
  "updatedAt": "2026-07-13T13:56:58.462Z",
  "sources": {
    "background-task": {
      "state": "idle",
      "updatedAt": "2026-07-13T13:56:58.462Z"
    }
  }
}
````

## File: .omo/run-continuation/ses_0b5416f7dffeZ8e2uzYg4p50hM.json
````json
{
  "sessionID": "ses_0b5416f7dffeZ8e2uzYg4p50hM",
  "updatedAt": "2026-07-10T06:48:12.040Z",
  "sources": {
    "background-task": {
      "state": "idle",
      "updatedAt": "2026-07-10T06:48:12.040Z"
    }
  }
}
````

## File: backend/__init__.py
````python
"""
Paquete backend del Boarding Pass Extractor.
"""
````

## File: backend/token_tracker.py
````python
"""
Control de gasto de tokens por sesion.

Limita las llamadas a DeepSeek por session_id para evitar abuso.
Usa SQLite para persistir el consumo acumulado.

Soporta:
- Limite global por env var DEEPSEEK_MAX_TOKENS_PER_SESSION
- Limite personalizado por sesion (grant manual)
- Bloqueo/desbloqueo manual de sesiones
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# --- Configuracion ---

DB_PATH = Path(__file__).resolve().parent / "trips.db"
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS_PER_SESSION", "200000"))


def _get_db() -> sqlite3.Connection:
    """Abre conexion a la BD con row_factory para acceso por nombre."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table():
    """Crea la tabla token_usage y aplica migraciones si es necesario."""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            session_id TEXT PRIMARY KEY,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            request_count INTEGER NOT NULL DEFAULT 0,
            blocked INTEGER NOT NULL DEFAULT 0,
            token_limit INTEGER,
            last_updated TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Migraciones para BDs existentes
    for col, col_type in [
        ("blocked", "INTEGER NOT NULL DEFAULT 0"),
        ("token_limit", "INTEGER"),
    ]:
        try:
            conn.execute(f"SELECT {col} FROM token_usage LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE token_usage ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def _effective_limit(row: sqlite3.Row | None) -> int:
    """Devuelve el limite efectivo de tokens para una fila (o el global)."""
    if row and row["token_limit"] is not None:
        return row["token_limit"]
    return MAX_TOKENS


def _build_stats(row: sqlite3.Row | None, session_id: str) -> dict:
    """Construye el diccionario de estadisticas a partir de una fila."""
    limit = _effective_limit(row)
    used = row["total_tokens"] if row else 0
    blocked = bool(row["blocked"]) if row else False
    return {
        "session_id": session_id,
        "input_tokens": row["input_tokens"] if row else 0,
        "output_tokens": row["output_tokens"] if row else 0,
        "total_tokens_used": used,
        "max_tokens": limit,
        "remaining": max(0, limit - used),
        "request_count": row["request_count"] if row else 0,
        "blocked": blocked,
        "has_custom_limit": bool(row and row["token_limit"] is not None),
        "last_updated": row["last_updated"] if row else None,
    }


# --- Funciones publicas ---

def check_limit(session_id: str) -> tuple[bool, dict]:
    """Verifica si la sesion aun tiene tokens disponibles.

    Returns:
        (allowed, stats) donde allowed=True si la sesion puede seguir
        haciendo llamadas a DeepSeek (no bloqueada y bajo el limite).
    """
    _ensure_table()
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return (True, _build_stats(None, session_id))

    stats = _build_stats(row, session_id)
    if stats["blocked"]:
        return (False, stats)

    limit = _effective_limit(row)
    return (row["total_tokens"] < limit, stats)


def record_usage(session_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Registra el consumo de tokens de una llamada a DeepSeek.

    Si la sesion esta bloqueada, igual registra el consumo (para auditoria)
    aunque la llamada no deberia haberse producido.
    """
    _ensure_table()
    total = input_tokens + output_tokens
    now = datetime.now(timezone.utc).isoformat()

    conn = _get_db()
    conn.execute("""
        INSERT INTO token_usage
            (session_id, input_tokens, output_tokens, total_tokens,
             request_count, last_updated)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            input_tokens = input_tokens + excluded.input_tokens,
            output_tokens = output_tokens + excluded.output_tokens,
            total_tokens = total_tokens + excluded.total_tokens,
            request_count = request_count + 1,
            last_updated = excluded.last_updated
    """, (session_id, input_tokens, output_tokens, total, now))

    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def get_usage(session_id: str) -> dict:
    """Obtiene las estadisticas de uso de tokens de una sesion."""
    _ensure_table()
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return _build_stats(None, session_id)
    return _build_stats(row, session_id)


def grant_tokens(session_id: str, additional_tokens: int) -> dict:
    """Concede tokens extra a una sesion (aumenta su limite personalizado).

    Si la sesion no tenia limite personalizado, se crea uno basado en
    el limite global + el extra.
    Si ya tenia limite personalizado, se incrementa.
    """
    _ensure_table()
    conn = _get_db()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    if row and row["token_limit"] is not None:
        new_limit = row["token_limit"] + additional_tokens
    else:
        new_limit = MAX_TOKENS + additional_tokens

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO token_usage (session_id, token_limit, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            token_limit = excluded.token_limit,
            last_updated = excluded.last_updated
    """, (session_id, new_limit, now))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def block_session(session_id: str, blocked: bool = True) -> dict:
    """Bloquea o desbloquea una sesion manualmente.

    Cuando blocked=True, la sesion no puede hacer mas llamadas a DeepSeek
    independientemente de los tokens que le queden.
    """
    _ensure_table()
    conn = _get_db()

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO token_usage (session_id, blocked, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            blocked = excluded.blocked,
            last_updated = excluded.last_updated
    """, (session_id, 1 if blocked else 0, now))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    return _build_stats(row, session_id)


def list_all_sessions() -> list[dict]:
    """Lista todas las sesiones con uso de tokens, incluyendo
    sesiones que tienen viajes pero aun no han consumido tokens.

    Hace un LEFT JOIN con trips para enriquecer con contexto:
    numero de viajes y ultimo viaje creado.
    """
    _ensure_table()
    conn = _get_db()

    rows = conn.execute("""
        SELECT
            tu.session_id,
            tu.input_tokens,
            tu.output_tokens,
            tu.total_tokens,
            tu.request_count,
            tu.blocked,
            tu.token_limit,
            tu.last_updated,
            COUNT(t.id) as trip_count,
            MAX(t.created_at) as last_trip_at,
            GROUP_CONCAT(DISTINCT t.trip_name) as trip_names
        FROM token_usage tu
        LEFT JOIN trips t ON t.session_id = tu.session_id
        GROUP BY tu.session_id
        ORDER BY tu.total_tokens DESC
    """).fetchall()

    sessions = []
    for row in rows:
        stats = _build_stats(row, row["session_id"])
        stats["trip_count"] = row["trip_count"] or 0
        stats["last_trip_at"] = row["last_trip_at"]
        # Reconstruir trip_names como lista
        names_raw = row["trip_names"] or ""
        stats["trip_names"] = [n.strip() for n in names_raw.split(",") if n.strip()] if names_raw else []
        sessions.append(stats)

    conn.close()
    return sessions
````

## File: boarding-pass/src/app/home/home-routing.module.ts
````typescript
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { HomePage } from './home.page';

const routes: Routes = [
  {
    path: '',
    component: HomePage,
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class HomePageRoutingModule {}
````

## File: boarding-pass/src/app/home/home.module.ts
````typescript
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';
import { HomePage } from './home.page';

import { HomePageRoutingModule } from './home-routing.module';


@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    HomePageRoutingModule
  ],
  declarations: [HomePage]
})
export class HomePageModule {}
````

## File: boarding-pass/src/app/home/home.page.spec.ts
````typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { IonicModule } from '@ionic/angular';

import { HomePage } from './home.page';

describe('HomePage', () => {
  let component: HomePage;
  let fixture: ComponentFixture<HomePage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [HomePage],
      imports: [IonicModule.forRoot()]
    }).compileComponents();

    fixture = TestBed.createComponent(HomePage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
````

## File: boarding-pass/src/app/itinerary/itinerary.module.ts
````typescript
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { RouterModule, Routes } from '@angular/router';

import { ItineraryPage } from './itinerary.page';

const routes: Routes = [{ path: '', component: ItineraryPage }];

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, RouterModule.forChild(routes)],
  declarations: [ItineraryPage],
})
export class ItineraryPageModule {}
````

## File: boarding-pass/src/app/result/result.module.ts
````typescript
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { RouterModule, Routes } from '@angular/router';

import { ResultPage } from './result.page';

const routes: Routes = [
  { path: '', component: ResultPage },
];

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, RouterModule.forChild(routes)],
  declarations: [ResultPage],
})
export class ResultPageModule {}
````

## File: boarding-pass/src/app/services/localtunnel.interceptor.ts
````typescript
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
````

## File: boarding-pass/src/app/trip-create/trip-create.module.ts
````typescript
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TripCreatePage } from './trip-create.page';

const routes: Routes = [{ path: '', component: TripCreatePage }];

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, RouterModule.forChild(routes)],
  declarations: [TripCreatePage],
})
export class TripCreatePageModule {}
````

## File: boarding-pass/src/app/trips/trips.module.ts
````typescript
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { RouterModule, Routes } from '@angular/router';

import { TripsPage } from './trips.page';

const routes: Routes = [{ path: '', component: TripsPage }];

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, RouterModule.forChild(routes)],
  declarations: [TripsPage],
})
export class TripsPageModule {}
````

## File: boarding-pass/src/app/app.component.html
````html
<ion-app>
  <ion-router-outlet></ion-router-outlet>
</ion-app>
````

## File: boarding-pass/src/app/app.component.scss
````scss

````

## File: boarding-pass/src/app/app.component.spec.ts
````typescript
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AppComponent } from './app.component';

describe('AppComponent', () => {

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AppComponent],
      schemas: [CUSTOM_ELEMENTS_SCHEMA],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

});
````

## File: boarding-pass/src/app/app.component.ts
````typescript
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: 'app.component.html',
  styleUrls: ['app.component.scss'],
  standalone: false,
})
export class AppComponent {
  constructor() {}
}
````

## File: boarding-pass/src/theme/variables.scss
````scss
// For information on how to create your own theme, please refer to:
// https://ionicframework.com/docs/theming/
````

## File: boarding-pass/src/index.html
````html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="utf-8" />
  <title>Ionic App</title>

  <base href="/" />

  <meta name="color-scheme" content="light dark" />
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta name="format-detection" content="telephone=no" />
  <meta name="msapplication-tap-highlight" content="no" />

  <link rel="icon" type="image/png" href="assets/icon/favicon.png" />

  <!-- add to homescreen for ios -->
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black" />
</head>

<body>
  <app-root></app-root>
</body>

</html>
````

## File: boarding-pass/src/main.ts
````typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';

import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.log(err));
````

## File: boarding-pass/src/polyfills.ts
````typescript
/**
 * This file includes polyfills needed by Angular and is loaded before the app.
 * You can add your own extra polyfills to this file.
 *
 * This file is divided into 2 sections:
 *   1. Browser polyfills. These are applied before loading ZoneJS and are sorted by browsers.
 *   2. Application imports. Files imported after ZoneJS that should be loaded before your main
 *      file.
 *
 * The current setup is for so-called "evergreen" browsers; the last versions of browsers that
 * automatically update themselves. This includes recent versions of Safari, Chrome (including
 * Opera), Edge on the desktop, and iOS and Chrome on mobile.
 *
 * Learn more in https://angular.io/guide/browser-support
 */

/***************************************************************************************************
 * BROWSER POLYFILLS
 */

/**
 * By default, zone.js will patch all possible macroTask and DomEvents
 * user can disable parts of macroTask/DomEvents patch by setting following flags
 * because those flags need to be set before `zone.js` being loaded, and webpack
 * will put import in the top of bundle, so user need to create a separate file
 * in this directory (for example: zone-flags.ts), and put the following flags
 * into that file, and then add the following code before importing zone.js.
 * import './zone-flags';
 *
 * The flags allowed in zone-flags.ts are listed here.
 *
 * The following flags will work for all browsers.
 *
 * (window as any).__Zone_disable_requestAnimationFrame = true; // disable patch requestAnimationFrame
 * (window as any).__Zone_disable_on_property = true; // disable patch onProperty such as onclick
 * (window as any).__zone_symbol__UNPATCHED_EVENTS = ['scroll', 'mousemove']; // disable patch specified eventNames
 *
 *  in IE/Edge developer tools, the addEventListener will also be wrapped by zone.js
 *  with the following flag, it will bypass `zone.js` patch for IE/Edge
 *
 *  (window as any).__Zone_enable_cross_context_check = true;
 *
 */
 
import './zone-flags';

/***************************************************************************************************
 * Zone JS is required by default for Angular itself.
 */
import 'zone.js';  // Included with Angular CLI.


/***************************************************************************************************
 * APPLICATION IMPORTS
 */
````

## File: boarding-pass/src/test.ts
````typescript
// This file is required by karma.conf.js and loads recursively all the .spec and framework files

import 'zone.js/testing';
import { getTestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting
} from '@angular/platform-browser-dynamic/testing';

// First, initialize the Angular testing environment.
getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
);
````

## File: boarding-pass/src/zone-flags.ts
````typescript
/**
 * Prevents Angular change detection from
 * running with certain Web Component callbacks
 */
// eslint-disable-next-line no-underscore-dangle
(window as any).__Zone_disable_customElements = true;
````

## File: boarding-pass/.eslintrc.json
````json
{
  "root": true,
  "ignorePatterns": ["projects/**/*"],
  "overrides": [
    {
      "files": ["*.ts"],
      "parserOptions": {
        "project": ["tsconfig.json"],
        "createDefaultProgram": true
      },
      "extends": [
        "plugin:@angular-eslint/recommended",
        "plugin:@angular-eslint/template/process-inline-templates"
      ],
      "rules": {
        "@angular-eslint/prefer-standalone": "off",
        "@angular-eslint/component-class-suffix": [
          "error",
          {
            "suffixes": ["Page", "Component"]
          }
        ],
        "@angular-eslint/component-selector": [
          "error",
          {
            "type": "element",
            "prefix": "app",
            "style": "kebab-case"
          }
        ],
        "@angular-eslint/directive-selector": [
          "error",
          {
            "type": "attribute",
            "prefix": "app",
            "style": "camelCase"
          }
        ]
      }
    },
    {
      "files": ["*.html"],
      "extends": ["plugin:@angular-eslint/template/recommended"],
      "rules": {}
    }
  ]
}
````

## File: boarding-pass/capacitor.config.json
````json
{
  "appId": "com.qrextractor.boardingpass",
  "appName": "Boarding Pass",
  "webDir": "www",
  "server": {
    "androidScheme": "https"
  }
}
````

## File: boarding-pass/ionic.config.json
````json
{
  "name": "boarding-pass",
  "integrations": {
    "capacitor": {}
  },
  "type": "angular"
}
````

## File: boarding-pass/ionic.starter.json
````json
{
  "name": "Blank Starter",
  "baseref": "main",
  "tarignore": [
    "node_modules",
    "package-lock.json",
    "www"
  ],
  "scripts": {
    "test": "npm run lint && npm run build && npm run test -- --configuration=ci --browsers=ChromeHeadless"
  }
}
````

## File: boarding-pass/tsconfig.app.json
````json
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": [
    "src/main.ts",
    "src/polyfills.ts"
  ],
  "include": [
    "src/**/*.d.ts"
  ]
}
````

## File: boarding-pass/tsconfig.json
````json
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "./",
    "outDir": "./dist/out-tsc",
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "moduleResolution": "node",
    "importHelpers": true,
    "target": "es2022",
    "module": "es2020",
    "lib": [
      "es2018",
      "dom"
    ],
    "skipLibCheck": true,
    "useDefineForClassFields": false
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  }
}
````

## File: boarding-pass/tsconfig.spec.json
````json
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/spec",
    "types": [
      "jasmine"
    ]
  },
  "files": [
    "src/test.ts",
    "src/polyfills.ts"
  ],
  "include": [
    "src/**/*.spec.ts",
    "src/**/*.d.ts"
  ]
}
````

## File: dashboard/index.html
````html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QR Extractor — Admin Dashboard</title>
<style>
  :root {
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2d3a;
    --text: #e1e4ed;
    --muted: #6b7280;
    --green: #22c55e;
    --red: #ef4444;
    --amber: #f59e0b;
    --blue: #3b82f6;
    --purple: #8b5cf6;
    --bar-bg: #2a2d3a;
    --bar-fill: linear-gradient(90deg, #3b82f6, #8b5cf6);
    --bar-warn: linear-gradient(90deg, #f59e0b, #ef4444);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 0;
  }
  .header {
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .header h1 {
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
  .status-dot.online { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .status-dot.offline { background: var(--red); }
  .status-dot.loading { background: var(--amber); animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .url-config {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .url-config input {
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    width: 280px;
    font-family: monospace;
  }
  .url-config input:focus {
    outline: none;
    border-color: var(--blue);
  }
  .refresh-btn {
    background: var(--blue);
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
  }
  .refresh-btn:hover { opacity: 0.9; }
  .main {
    padding: 24px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .stats-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }
  .stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    flex: 1;
    min-width: 180px;
  }
  .stat-card .label {
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .stat-card .value {
    font-size: 24px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .table-wrap {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .table-header {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .auto-refresh {
    font-size: 12px;
    color: var(--muted);
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    text-align: left;
    padding: 10px 16px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    font-weight: 600;
  }
  td {
    padding: 12px 16px;
    font-size: 13px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  .session-id {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px;
    color: var(--blue);
    word-break: break-all;
    max-width: 200px;
  }
  .session-id.short {
    font-size: 11px;
    color: var(--muted);
  }
  .trips-cell {
    font-size: 12px;
  }
  .trip-name-tag {
    display: inline-block;
    background: var(--border);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin: 1px 2px;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .bar-cell { min-width: 140px; }
  .bar-outer {
    background: var(--bar-bg);
    border-radius: 4px;
    height: 6px;
    margin-top: 4px;
    overflow: hidden;
  }
  .bar-inner {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;
  }
  .bar-inner.ok { background: var(--bar-fill); }
  .bar-inner.warn { background: var(--bar-warn); }
  .token-text {
    font-size: 11px;
    color: var(--muted);
    margin-top: 2px;
    font-variant-numeric: tabular-nums;
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge.ok { background: rgba(34,197,94,0.15); color: var(--green); }
  .badge.blocked { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge.warn { background: rgba(245,158,11,0.15); color: var(--amber); }
  .badge.custom { background: rgba(139,92,246,0.15); color: var(--purple); }
  .actions-cell {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .btn {
    padding: 5px 10px;
    border: 1px solid var(--border);
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    color: var(--text);
    white-space: nowrap;
    transition: all 0.15s;
  }
  .btn:hover { border-color: var(--text); }
  .btn.grant { color: var(--blue); border-color: rgba(59,130,246,0.4); }
  .btn.grant:hover { background: rgba(59,130,246,0.1); border-color: var(--blue); }
  .btn.block { color: var(--red); border-color: rgba(239,68,68,0.4); }
  .btn.block:hover { background: rgba(239,68,68,0.1); border-color: var(--red); }
  .btn.unblock { color: var(--green); border-color: rgba(34,197,94,0.4); }
  .btn.unblock:hover { background: rgba(34,197,94,0.1); border-color: var(--green); }
  .empty {
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
  }
  .empty .icon { font-size: 40px; margin-bottom: 12px; }
  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--card);
    border: 1px solid var(--border);
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 100;
    animation: slideIn 0.3s ease;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }
  .toast.success { border-color: var(--green); }
  .toast.error { border-color: var(--red); }
  @keyframes slideIn {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 200;
  }
  .modal {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px;
    width: 360px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
  }
  .modal h3 { margin-bottom: 16px; font-size: 16px; }
  .modal label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
  .modal input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 16px;
    font-size: 14px;
  }
  .modal input:focus { outline: none; border-color: var(--blue); }
  .modal .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
  .modal .btn-primary {
    background: var(--blue);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
  }
  .modal .btn-primary:hover { opacity: 0.9; }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>⚡ QR Extractor Admin</h1>
    <span class="status-dot loading" id="statusDot"></span>
    <span style="font-size:12px;color:var(--muted)" id="statusText">Conectando...</span>
  </div>
  <div class="url-config">
    <input type="text" id="apiUrl" placeholder="http://localhost:8765" spellcheck="false">
    <button class="refresh-btn" onclick="refresh()">↻ Actualizar</button>
  </div>
</div>

<div class="main">
  <div class="stats-bar">
    <div class="stat-card">
      <div class="label">Sesiones activas</div>
      <div class="value" id="statSessions">—</div>
    </div>
    <div class="stat-card">
      <div class="label">Tokens totales gastados</div>
      <div class="value" id="statTokens">—</div>
    </div>
    <div class="stat-card">
      <div class="label">Sesiones bloqueadas</div>
      <div class="value" style="color:var(--red)" id="statBlocked">—</div>
    </div>
    <div class="stat-card">
      <div class="label">Límite por defecto</div>
      <div class="value" style="font-size:18px" id="statDefaultLimit">—</div>
    </div>
  </div>

  <div class="table-wrap">
    <div class="table-header">
      <span>Sesiones</span>
      <span class="auto-refresh" id="refreshLabel">Auto-refresh: 10s</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Sesión</th>
          <th>Viajes</th>
          <th>Tokens usados</th>
          <th>Límite</th>
          <th>Restante</th>
          <th>Uso</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody id="sessionsBody">
        <tr><td colspan="8" class="empty"><div class="icon">⏳</div>Cargando sesiones...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<div id="toastContainer"></div>
<div id="modalContainer"></div>

<script>
const DEFAULT_API = 'http://localhost:8765';
const REFRESH_SEC = 10;
let countdown = REFRESH_SEC;
let apiBase = localStorage.getItem('dashboard_api_url') || DEFAULT_API;

document.getElementById('apiUrl').value = apiBase;

document.getElementById('apiUrl').addEventListener('change', function() {
  apiBase = this.value.trim().replace(/\/+$/, '') || DEFAULT_API;
  localStorage.setItem('dashboard_api_url', apiBase);
  refresh();
});

function fmt(n) {
  if (n == null) return '—';
  return n.toLocaleString('es-ES');
}

function toast(msg, type) {
  const el = document.createElement('div');
  el.className = 'toast ' + (type || 'success');
  el.textContent = msg;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function setStatus(online) {
  const dot = document.getElementById('statusDot');
  const txt = document.getElementById('statusText');
  dot.className = 'status-dot';
  if (online === null) {
    dot.classList.add('loading');
    txt.textContent = 'Conectando...';
  } else if (online) {
    dot.classList.add('online');
    txt.textContent = 'Conectado';
  } else {
    dot.classList.add('offline');
    txt.textContent = 'Sin conexión';
  }
}

async function apiCall(method, path, body) {
  const res = await fetch(apiBase + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
  }
  return res.json();
}

async function refresh() {
  setStatus(null);
  try {
    const data = await apiCall('GET', '/api/admin/sessions');
    setStatus(true);
    render(data.sessions);
  } catch (e) {
    setStatus(false);
    console.error('Refresh error:', e);
  }
}

function render(sessions) {
  const tbody = document.getElementById('sessionsBody');

  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty"><div class="icon">📭</div>No hay sesiones registradas aún</td></tr>';
    updateStats(sessions);
    return;
  }

  tbody.innerHTML = sessions.map(s => {
    const pct = s.max_tokens > 0 ? Math.min(100, (s.total_tokens_used / s.max_tokens) * 100) : 0;
    const barClass = pct > 80 ? 'warn' : 'ok';
    const sid = s.session_id;
    const isShort = sid.length > 26;

    let statusBadge = '';
    if (s.blocked) {
      statusBadge = '<span class="badge blocked">🔒 Bloqueada</span>';
    } else if (pct >= 100) {
      statusBadge = '<span class="badge warn">⚠️ Sin tokens</span>';
    } else if (pct > 80) {
      statusBadge = '<span class="badge warn">⚠️ Próxima al límite</span>';
    } else {
      statusBadge = '<span class="badge ok">✅ Activa</span>';
    }
    if (s.has_custom_limit) {
      statusBadge += ' <span class="badge custom">⚙️ Custom</span>';
    }

    const tripsHtml = s.trip_count > 0
      ? `<span style="color:var(--text)">${s.trip_count} viaje${s.trip_count !== 1 ? 's' : ''}</span>` +
        (s.trip_names.length ? '<br>' + s.trip_names.slice(0, 3).map(n =>
          `<span class="trip-name-tag">${escapeHtml(n)}</span>`
        ).join('') + (s.trip_names.length > 3 ? `<span class="trip-name-tag">+${s.trip_names.length - 3}</span>` : '') : '')
      : '<span style="color:var(--muted)">—</span>';

    const actionsHtml = s.blocked
      ? `<button class="btn unblock" onclick="toggleBlock('${sid}', false)">🔓 Desbloquear</button>`
      : `<button class="btn grant" onclick="showGrant('${sid}')">💰 +Tokens</button>
         <button class="btn block" onclick="toggleBlock('${sid}', true)">🔒 Bloquear</button>`;

    return `<tr>
      <td><div class="session-id${isShort ? ' short' : ''}" title="${sid}">${isShort ? sid.slice(0,20)+'…' : sid}</div></td>
      <td class="trips-cell">${tripsHtml}</td>
      <td style="font-variant-numeric:tabular-nums">${fmt(s.total_tokens_used)}</td>
      <td style="font-variant-numeric:tabular-nums">${fmt(s.max_tokens)}</td>
      <td style="font-variant-numeric:tabular-nums;color:${s.remaining === 0 ? 'var(--red)' : 'var(--green)'}">${fmt(s.remaining)}</td>
      <td class="bar-cell">
        <span style="font-size:11px">${pct.toFixed(0)}%</span>
        <div class="bar-outer"><div class="bar-inner ${barClass}" style="width:${pct}%"></div></div>
        <div class="token-text">${s.request_count} peticion${s.request_count !== 1 ? 'es' : ''}</div>
      </td>
      <td>${statusBadge}</td>
      <td><div class="actions-cell">${actionsHtml}</div></td>
    </tr>`;
  }).join('');

  updateStats(sessions);
}

function updateStats(sessions) {
  document.getElementById('statSessions').textContent = sessions.length;
  const totalTokens = sessions.reduce((sum, s) => sum + s.total_tokens_used, 0);
  document.getElementById('statTokens').textContent = fmt(totalTokens);
  const blocked = sessions.filter(s => s.blocked).length;
  document.getElementById('statBlocked').textContent = blocked;
  // Default limit from first session without custom limit, or env var
  const defaultSes = sessions.find(s => !s.has_custom_limit);
  document.getElementById('statDefaultLimit').textContent = defaultSes ? fmt(defaultSes.max_tokens) : '200k';
}

async function toggleBlock(sid, block) {
  try {
    const data = await apiCall('POST', '/api/admin/block', { session_id: sid, blocked: block });
    toast(data.message, 'success');
    refresh();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

function showGrant(sid) {
  const html = `
    <div class="modal-overlay" id="grantModal" onclick="if(event.target===this)closeGrant()">
      <div class="modal">
        <h3>💰 Conceder tokens extra</h3>
        <label>Sesión</label>
        <input type="text" value="${sid}" readonly style="font-family:monospace;font-size:12px;color:var(--muted)">
        <label>Cantidad de tokens a añadir</label>
        <input type="number" id="grantAmount" placeholder="Ej: 100000" min="1000" step="10000" value="100000" autofocus>
        <div class="actions">
          <button class="btn" onclick="closeGrant()">Cancelar</button>
          <button class="btn-primary" onclick="doGrant('${sid}')">Conceder</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modalContainer').innerHTML = html;
  setTimeout(() => document.getElementById('grantAmount')?.focus(), 50);
}

function closeGrant() {
  document.getElementById('modalContainer').innerHTML = '';
}

async function doGrant(sid) {
  const amount = parseInt(document.getElementById('grantAmount').value);
  if (!amount || amount < 1) {
    toast('Cantidad inválida', 'error');
    return;
  }
  try {
    const data = await apiCall('POST', '/api/admin/grant', { session_id: sid, amount });
    closeGrant();
    toast(data.message, 'success');
    refresh();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Auto-refresh countdown
setInterval(() => {
  countdown--;
  if (countdown <= 0) {
    refresh();
    countdown = REFRESH_SEC;
  }
  document.getElementById('refreshLabel').textContent = `Auto-refresh: ${countdown}s`;
}, 1000);

// Initial load
refresh();
</script>

</body>
</html>
````

## File: qr_service/client.py
````python
"""Cliente CLI minimo para el servicio QR (solo para smoke tests)."""
import sys
import requests

def main():
    if len(sys.argv) < 2:
        print("Uso: python client.py <ruta_archivo>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        r = requests.post("http://localhost:8766/extract", files={"file": f}, timeout=120)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"Items: {d['count']}")
        for it in d.get("items", []):
            print(f"  page={it['page']} format={it['format']} text={it['text'][:60]!r} b64_len={len(it['base64'])}")
    else:
        print(r.text)

if __name__ == "__main__":
    main()
````

## File: qr_service/main.py
````python
"""
================================================================================
                         ⚠️  SERVICIO INTOCABLE  ⚠️
================================================================================

Este servicio extrae y recorta codigos de barras / QR de PDFs e imagenes.
ES UN SERVICIO AISLADO. Cualquier cambio en su comportamiento rompe el
contrato con todos los clientes que lo consumen.

NO MODIFICAR salvo autorizacion EXPLICITA y por escrito del dueno del
proyecto. Si necesitas un cambio, abre un issue y esperate a la revision.

API:
  POST /extract    multipart con campo "file" (PDF o imagen)
                   -> 200 JSON con {filename, items: [{page, format, text, base64}]}
                   -> 400 si formato no soportado
                   -> 500 si error interno
  GET  /health      -> 200 {"status": "ok"}

Formatos soportados: PDF, PNG, JPG, JPEG, WebP, BMP, TIFF
================================================================================
"""

import base64
import io
import os
import re
import sys
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import zxingcpp
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image


# Limites de tamano (MB)
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
RENDER_DPI = 300
CROP_PADDING = 20
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


app = FastAPI(
    title="QR Extraction Service",
    version="1.0.0",
    description="Servicio aislado de extraccion y recorte de codigos QR/barcodes",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _should_skip(text: str) -> bool:
    """Detecta URLs de publicidad que no son billetes."""
    if not text:
        return True
    return bool(URL_PATTERN.match(text.strip()))


def _decode(pil_image: Image.Image):
    """Decodifica codigos 2D con zxing-cpp (soporta QR, PDF417, Aztec, etc)."""
    return zxingcpp.read_barcodes(
        pil_image,
        formats=(
            zxingcpp.BarcodeFormat.QRCode,
            zxingcpp.BarcodeFormat.PDF417,
            zxingcpp.BarcodeFormat.Aztec,
        ),
        try_rotate=True,
        try_invert=True,
    )


def _crop_to_hit(pil_image: Image.Image, hit) -> Image.Image:
    """Recorta el bounding box del codigo detectado con padding."""
    pos = hit.position
    xs = [pos.top_left.x, pos.top_right.x, pos.bottom_right.x, pos.bottom_left.x]
    ys = [pos.top_left.y, pos.top_right.y, pos.bottom_right.y, pos.bottom_left.y]
    return pil_image.crop((
        max(int(min(xs)) - CROP_PADDING, 0),
        max(int(min(ys)) - CROP_PADDING, 0),
        min(int(max(xs)) + CROP_PADDING, pil_image.width),
        min(int(max(ys)) + CROP_PADDING, pil_image.height),
    ))


def _image_to_base64(pil_image: Image.Image) -> str:
    """Convierte una imagen PIL a PNG base64."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _extract_from_pdf(pdf_path: str, out_dir: str) -> list[dict]:
    """Extrae codigos de un PDF: imagenes embebidas + rasterizado."""
    results: dict[tuple, dict] = {}  # (page, format, text) -> item
    counter: dict[int, int] = {}

    def _next_idx(page_num: int) -> int:
        counter[page_num] = counter.get(page_num, 0) + 1
        return counter[page_num]

    def _save_entry(page_num: int, pil_img: Image.Image, hit, origin: str) -> dict:
        idx = _next_idx(page_num)
        crop = _crop_to_hit(pil_img, hit)
        return {
            "page": page_num,
            "format": hit.format.name,
            "text": hit.text or "",
            "origin": origin,
            "base64": _image_to_base64(crop),
        }

    doc = fitz.open(pdf_path)
    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_num_1based = page_num + 1

            # 1) Imagenes embebidas
            for img_meta in page.get_images(full=True):
                try:
                    info = doc.extract_image(img_meta[0])
                    pil_img = Image.open(io.BytesIO(info["image"]))
                except Exception:
                    continue
                for hit in _decode(pil_img):
                    if not hit.text or _should_skip(hit.text):
                        continue
                    key = (page_num_1based, hit.format.name, hit.text)
                    if key in results:
                        continue
                    results[key] = _save_entry(page_num_1based, pil_img, hit, "embedded")

            # 2) Rasterizado (cubre vector y mejora resolucion)
            pix = page.get_pixmap(dpi=RENDER_DPI)
            page_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            for hit in _decode(page_img):
                if not hit.text or _should_skip(hit.text):
                    continue
                key = (page_num_1based, hit.format.name, hit.text)
                if key in results:
                    # Reemplaza la version embedded por la rendered (mas nitida)
                    old_fname = results[key].get("filename", "")
                    if old_fname:
                        try:
                            os.remove(os.path.join(out_dir, old_fname))
                        except OSError:
                            pass
                results[key] = _save_entry(page_num_1based, page_img, hit, "rendered")
    finally:
        doc.close()

    return list(results.values())


def _extract_from_image(image_path: str) -> list[dict]:
    """Extrae codigos de una imagen suelta."""
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo abrir la imagen: {e}")

    results = []
    seen: set = set()
    for hit in _decode(pil_img):
        if not hit.text or _should_skip(hit.text):
            continue
        key = (hit.format.name, hit.text)
        if key in seen:
            continue
        seen.add(key)
        crop = _crop_to_hit(pil_img, hit)
        results.append({
            "page": 1,
            "format": hit.format.name,
            "text": hit.text or "",
            "origin": "screenshot",
            "base64": _image_to_base64(crop),
        })
    return results


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Falta el nombre del archivo")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {ext}. Usa PDF, PNG, JPG, WebP, BMP o TIFF",
        )

    is_image = ext in IMG_EXTS

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = os.path.join(tmp, f"upload{ext}")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande (>{MAX_FILE_SIZE_MB}MB)",
            )
        with open(upload_path, "wb") as f:
            f.write(contents)

        try:
            if is_image:
                items = _extract_from_image(upload_path)
            else:
                items = _extract_from_pdf(upload_path, out_dir)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extrayendo: {e}")

    return {
        "filename": file.filename,
        "items": items,
        "count": len(items),
    }
````

## File: .omo/run-continuation/ses_0c80a8dcfffeFLDprGR3TdXF9d.json
````json
{
  "sessionID": "ses_0c80a8dcfffeFLDprGR3TdXF9d",
  "updatedAt": "2026-07-07T12:24:42.301Z",
  "sources": {
    "background-task": {
      "state": "active",
      "reason": "1 background task(s) active",
      "updatedAt": "2026-07-07T12:24:42.301Z"
    }
  }
}
````

## File: backend/admin.py
````python
"""
Router de administracion para el dashboard de monitoreo de tokens.

Endpoints:
  GET  /api/admin/sessions   -> lista todas las sesiones con uso
  POST /api/admin/grant      -> concede tokens extra a una sesion
  POST /api/admin/block      -> bloquea/desbloquea una sesion
"""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
from token_tracker import block_session, grant_tokens, list_all_sessions

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas ---

class GrantRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="ID de sesion")
    amount: int = Field(..., gt=0, description="Cantidad de tokens a conceder")


class BlockRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="ID de sesion")
    blocked: bool = Field(..., description="True para bloquear, False para desbloquear")


# --- Endpoints ---

@router.get("/sessions")
def admin_list_sessions():
    """Lista todas las sesiones con sus estadisticas de tokens y viajes."""
    return {"sessions": list_all_sessions()}


@router.post("/grant")
def admin_grant_tokens(body: GrantRequest):
    """Concede tokens extra al limite de una sesion."""
    try:
        stats = grant_tokens(body.session_id, body.amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conceder tokens: {e}")

    return {
        "ok": True,
        "message": f"Concedidos {body.amount:,} tokens a {body.session_id}",
        "session": stats,
    }


@router.post("/block")
def admin_block_session(body: BlockRequest):
    """Bloquea o desbloquea una sesion."""
    try:
        stats = block_session(body.session_id, body.blocked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al {'bloquear' if body.blocked else 'desbloquear'} sesion: {e}")

    action = "Bloqueada" if body.blocked else "Desbloqueada"
    return {
        "ok": True,
        "message": f"{action} sesion {body.session_id}",
        "session": stats,
    }
````

## File: boarding-pass/src/app/app-routing.module.ts
````typescript
import { NgModule } from '@angular/core';
import { PreloadAllModules, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'home',
    loadChildren: () => import('./home/home.module').then( m => m.HomePageModule)
  },
  {
    path: 'result',
    loadChildren: () => import('./result/result.module').then( m => m.ResultPageModule)
  },
  {
    path: 'trips',
    loadChildren: () => import('./trips/trips.module').then( m => m.TripsPageModule)
  },
  {
    path: 'trip-create',
    loadChildren: () => import('./trip-create/trip-create.module').then( m => m.TripCreatePageModule)
  },
  {
    path: 'itinerary',
    loadChildren: () => import('./itinerary/itinerary.module').then( m => m.ItineraryPageModule)
  },
  {
    path: '',
    redirectTo: 'home',
    pathMatch: 'full'
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, { preloadingStrategy: PreloadAllModules })
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
````

## File: boarding-pass/src/app/app.module.ts
````typescript
import { LOCALE_ID, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { RouteReuseStrategy } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { IonicModule, IonicRouteStrategy } from '@ionic/angular';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';

registerLocaleData(localeEs, 'es');

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, IonicModule.forRoot(), AppRoutingModule, HttpClientModule],
  providers: [
    { provide: RouteReuseStrategy, useClass: IonicRouteStrategy },
    { provide: LOCALE_ID, useValue: 'es' },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
````

## File: boarding-pass/angular.json
````json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "app": {
      "projectType": "application",
      "schematics": {},
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "www",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.app.json",
            "inlineStyleLanguage": "scss",
            "assets": [
              {
                "glob": "**/*",
                "input": "src/assets",
                "output": "assets"
              },
              {
                "glob": "**/*.svg",
                "input": "node_modules/ionicons/dist/ionicons/svg",
                "output": "./svg"
              }
            ],
            "styles": ["src/global.scss", "src/theme/variables.scss"],
            "scripts": []
          },
          "configurations": {
            "production": {
              "budgets": [
                {
                  "type": "initial",
                  "maximumWarning": "2mb",
                  "maximumError": "5mb"
                },
                {
                  "type": "anyComponentStyle",
                  "maximumWarning": "10kb",
                  "maximumError": "20kb"
                }
              ],
              "fileReplacements": [
                {
                  "replace": "src/environments/environment.ts",
                  "with": "src/environments/environment.prod.ts"
                }
              ],
              "outputHashing": "all"
            },
            "development": {
              "buildOptimizer": false,
              "optimization": false,
              "vendorChunk": true,
              "extractLicenses": false,
              "sourceMap": true,
              "namedChunks": true
            },
            "ci": {
              "progress": false
            }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "configurations": {
            "production": {
              "buildTarget": "app:build:production"
            },
            "development": {
              "buildTarget": "app:build:development"
            },
            "ci": {
              "progress": false
            }
          },
          "defaultConfiguration": "development"
        },
        "extract-i18n": {
          "builder": "@angular-devkit/build-angular:extract-i18n",
          "options": {
            "buildTarget": "app:build"
          }
        },
        "test": {
          "builder": "@angular-devkit/build-angular:karma",
          "options": {
            "main": "src/test.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.spec.json",
            "karmaConfig": "karma.conf.js",
            "inlineStyleLanguage": "scss",
            "assets": [
              {
                "glob": "**/*",
                "input": "src/assets",
                "output": "assets"
              },
              {
                "glob": "**/*.svg",
                "input": "node_modules/ionicons/dist/ionicons/svg",
                "output": "./svg"
              }
            ],
            "styles": ["src/global.scss", "src/theme/variables.scss"],
            "scripts": []
          },
          "configurations": {
            "ci": {
              "progress": false,
              "watch": false
            }
          }
        },
        "lint": {
          "builder": "@angular-eslint/builder:lint",
          "options": {
            "lintFilePatterns": [
              "src/**/*.ts",
              "src/**/*.html"
            ]
          }
        }
      }
    }
  },
  "cli": {
    "schematicCollections": [
      "@ionic/angular-toolkit"
    ]
  },
  "schematics": {
    "@ionic/angular-toolkit:component": {
      "styleext": "scss"
    },
    "@ionic/angular-toolkit:page": {
      "styleext": "scss"
    }
  }
}
````

## File: boarding-pass/package.json
````json
{
  "name": "ionic-app-base",
  "version": "0.0.0",
  "author": "Ionic Framework",
  "homepage": "https://ionicframework.com/",
  "scripts": {
    "ng": "ng",
    "start": "ng serve",
    "build": "ng build",
    "watch": "ng build --watch --configuration development",
    "test": "ng test",
    "lint": "ng lint"
  },
  "private": true,
  "dependencies": {
    "@angular/animations": "20.3.25",
    "@angular/common": "20.3.25",
    "@angular/compiler": "20.3.25",
    "@angular/core": "20.3.25",
    "@angular/forms": "20.3.25",
    "@angular/platform-browser": "20.3.25",
    "@angular/platform-browser-dynamic": "20.3.25",
    "@angular/router": "20.3.25",
    "@capacitor-community/screen-brightness": "^8.0.0",
    "@capacitor/android": "^8.4.1",
    "@capacitor/app": "^8.1.0",
    "@capacitor/core": "8.4.1",
    "@capacitor/haptics": "^8.0.2",
    "@capacitor/keyboard": "^8.0.5",
    "@capacitor/status-bar": "^8.0.2",
    "@capawesome/capacitor-file-picker": "^8.0.3",
    "@ionic/angular": "^8.0.0",
    "ionicons": "^7.0.0",
    "rxjs": "~7.8.0",
    "tslib": "^2.3.0",
    "zone.js": "~0.15.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "20.3.28",
    "@angular-eslint/builder": "20.7.0",
    "@angular-eslint/eslint-plugin": "20.7.0",
    "@angular-eslint/eslint-plugin-template": "20.7.0",
    "@angular-eslint/schematics": "20.7.0",
    "@angular-eslint/template-parser": "20.7.0",
    "@angular/cli": "20.3.28",
    "@angular/compiler-cli": "20.3.25",
    "@angular/language-service": "20.3.25",
    "@capacitor/cli": "8.4.1",
    "@ionic/angular-toolkit": "^12.0.0",
    "@types/jasmine": "~5.1.0",
    "@typescript-eslint/eslint-plugin": "^8.18.0",
    "@typescript-eslint/parser": "^8.18.0",
    "eslint": "^9.16.0",
    "eslint-plugin-import": "^2.29.1",
    "eslint-plugin-jsdoc": "^48.2.1",
    "eslint-plugin-prefer-arrow": "1.2.2",
    "jasmine-core": "~5.1.0",
    "jasmine-spec-reporter": "~5.0.0",
    "karma": "~6.4.0",
    "karma-chrome-launcher": "~3.2.0",
    "karma-coverage": "~2.2.0",
    "karma-jasmine": "~5.1.0",
    "karma-jasmine-html-reporter": "~2.1.0",
    "typescript": "~5.9.0"
  }
}
````

## File: boarding-pass/src/app/trip-create/trip-create.page.html
````html
<ion-header>
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-button (click)="goBack()">
        <ion-icon name="arrow-back"></ion-icon>
      </ion-button>
    </ion-buttons>
    <ion-title>{{ editTripId ? 'Editar viaje' : 'Nuevo viaje' }}</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content>
  <div class="page">
    <!-- Trip Name -->
    <ion-item class="name-input">
      <ion-input
        label="Nombre del viaje"
        labelPlacement="stacked"
        placeholder="Ej: París y Disneyland 2026"
        [(ngModel)]="tripName"
        [disabled]="!!editTripId"
      ></ion-input>
    </ion-item>

    <!-- Archivos -->
    <div class="section" *ngIf="!editTripId">
      <h3 class="section__title">
        <ion-icon name="documents-outline"></ion-icon>
        Subir archivos (billetes, reservas, capturas…)
      </h3>
      <ion-button expand="block" fill="outline" (click)="pickPdfs()" [disabled]="busy">
        <ion-icon name="cloud-upload-outline" slot="start"></ion-icon>
        Seleccionar archivos
      </ion-button>

      <!-- Uploaded files list -->
      <div class="chip-list" *ngIf="uploadedPdfs().length">
        <ion-chip *ngFor="let pdf of uploadedPdfs(); let i = index" color="primary">
          <ion-label>{{ pdf.name }} ({{ pdf.passes.length }} pases)</ion-label>
          <ion-icon name="close-circle" (click)="removePdf(i)"></ion-icon>
        </ion-chip>
      </div>
    </div>

    <!-- Manual Segments -->
    <div class="section">
      <h3 class="section__title">
        <ion-icon name="add-circle-outline"></ion-icon>
        Añadir manualmente
      </h3>

      <ion-accordion-group>
        <ion-accordion *ngFor="let st of [
          {type:'flight',label:'Vuelo',icon:'airplane'},
          {type:'train',label:'Tren',icon:'train'},
          {type:'hotel',label:'Hotel',icon:'bed'},
          {type:'car',label:'Coche',icon:'car'},
          {type:'restaurant',label:'Restaurante',icon:'restaurant'},
          {type:'activity',label:'Actividad',icon:'football'}
        ]" [value]="openFormType === st.type ? st.type : ''">
          <ion-item slot="header" (click)="toggleForm(st.type)" button>
            <ion-icon [name]="st.icon + '-outline'" slot="start" color="primary"></ion-icon>
            <ion-label>{{ st.label }}</ion-label>
          </ion-item>

          <div slot="content" class="seg-form">
            <!-- Flight -->
            <ng-container *ngIf="st.type === 'flight'">
              <ion-item><ion-input label="Aerolínea" placeholder="IB, VY, FR…" [(ngModel)]="flightForm.airline"></ion-input></ion-item>
              <ion-item><ion-input label="Nº vuelo" placeholder="1234" [(ngModel)]="flightForm.flight_number"></ion-input></ion-item>
              <ion-item><ion-input label="Origen" placeholder="BCN" [(ngModel)]="flightForm.from"></ion-input></ion-item>
              <ion-item><ion-input label="Destino" placeholder="CDG" [(ngModel)]="flightForm.to"></ion-input></ion-item>
              <ion-item><ion-input label="Fecha" type="date" [(ngModel)]="flightForm.date"></ion-input></ion-item>
              <ion-item><ion-input label="Hora" type="time" [(ngModel)]="flightForm.time"></ion-input></ion-item>
            </ng-container>

            <!-- Train -->
            <ng-container *ngIf="st.type === 'train'">
              <ion-item><ion-input label="Operador" placeholder="Renfe, SNCF…" [(ngModel)]="trainForm.operator"></ion-input></ion-item>
              <ion-item><ion-input label="Nº tren" placeholder="12345" [(ngModel)]="trainForm.train_number"></ion-input></ion-item>
              <ion-item><ion-input label="Origen" placeholder="Paris" [(ngModel)]="trainForm.from"></ion-input></ion-item>
              <ion-item><ion-input label="Destino" placeholder="Disneyland" [(ngModel)]="trainForm.to"></ion-input></ion-item>
              <ion-item><ion-input label="Fecha" type="date" [(ngModel)]="trainForm.date"></ion-input></ion-item>
              <ion-item><ion-input label="Hora" type="time" [(ngModel)]="trainForm.time"></ion-input></ion-item>
            </ng-container>

            <!-- Hotel -->
            <ng-container *ngIf="st.type === 'hotel'">
              <ion-item><ion-input label="Nombre" placeholder="Hotel Ritz" [(ngModel)]="hotelForm.name"></ion-input></ion-item>
              <ion-item><ion-input label="Ciudad" placeholder="Paris" [(ngModel)]="hotelForm.city"></ion-input></ion-item>
              <ion-item><ion-input label="Check-in" type="date" [(ngModel)]="hotelForm.check_in"></ion-input></ion-item>
              <ion-item><ion-input label="Check-out" type="date" [(ngModel)]="hotelForm.check_out"></ion-input></ion-item>
            </ng-container>

            <!-- Car -->
            <ng-container *ngIf="st.type === 'car'">
              <ion-item><ion-input label="Compañía" placeholder="Hertz, Avis…" [(ngModel)]="carForm.company"></ion-input></ion-item>
              <ion-item><ion-input label="Ciudad" placeholder="Paris" [(ngModel)]="carForm.city"></ion-input></ion-item>
              <ion-item><ion-input label="Recogida" type="date" [(ngModel)]="carForm.pickup_date"></ion-input></ion-item>
              <ion-item><ion-input label="Devolución" type="date" [(ngModel)]="carForm.return_date"></ion-input></ion-item>
            </ng-container>

            <!-- Restaurant -->
            <ng-container *ngIf="st.type === 'restaurant'">
              <ion-item><ion-input label="Nombre" placeholder="Le Jules Verne" [(ngModel)]="restaurantForm.name"></ion-input></ion-item>
              <ion-item><ion-input label="Ciudad" placeholder="Paris" [(ngModel)]="restaurantForm.city"></ion-input></ion-item>
              <ion-item><ion-input label="Fecha" type="date" [(ngModel)]="restaurantForm.date"></ion-input></ion-item>
              <ion-item><ion-input label="Hora" type="time" [(ngModel)]="restaurantForm.time"></ion-input></ion-item>
            </ng-container>

            <!-- Activity -->
            <ng-container *ngIf="st.type === 'activity'">
              <ion-item><ion-input label="Nombre" placeholder="Disneyland Paris" [(ngModel)]="activityForm.name"></ion-input></ion-item>
              <ion-item><ion-input label="Ciudad" placeholder="Paris" [(ngModel)]="activityForm.city"></ion-input></ion-item>
              <ion-item><ion-input label="Fecha" type="date" [(ngModel)]="activityForm.date"></ion-input></ion-item>
              <ion-item><ion-input label="Descripción" placeholder="Entrada 2 parques" [(ngModel)]="activityForm.description"></ion-input></ion-item>
            </ng-container>

            <ion-button expand="block" size="small" (click)="addSegment(st.type)" class="add-btn">
              <ion-icon name="add" slot="start"></ion-icon>
              Añadir {{ st.label }}
            </ion-button>
            <ion-text color="danger" class="seg-form__error" *ngIf="formErrors[st.type]">
              {{ formErrors[st.type] }}
            </ion-text>
          </div>
        </ion-accordion>
      </ion-accordion-group>
    </div>

    <!-- Summary -->
    <div class="section" *ngIf="segments().length || uploadedPdfs().length">
      <h3 class="section__title">
        <ion-icon name="list-outline"></ion-icon>
        Resumen del viaje
      </h3>

      <div class="summary-list">
        <div class="summary-item" *ngFor="let seg of segments(); let i = index">
          <ion-icon [name]="segmentIcon(seg.type)" color="primary"></ion-icon>
          <span class="summary-label">{{ segmentSummary(seg) }}</span>
          <ion-badge color="medium">{{ segmentLabel(seg.type) }}</ion-badge>
          <ion-icon name="close-circle" color="danger" (click)="removeSegment(i)" class="remove-btn"></ion-icon>
        </div>
        <div class="summary-item" *ngFor="let pdf of uploadedPdfs()">
          <ion-icon name="document-text"></ion-icon>
          <span class="summary-label">{{ pdf.name }}</span>
          <ion-badge color="primary">Archivo · {{ pdf.passes.length }} pases</ion-badge>
        </div>
      </div>
    </div>

    <!-- Save -->
    <div class="save-section">
      <ion-button expand="block" size="large" (click)="saveTrip()" [disabled]="busy">
        <ion-icon name="save-outline" slot="start"></ion-icon>
        {{ editTripId ? 'Actualizar segmentos' : 'Guardar viaje' }}
      </ion-button>
    </div>
  </div>
</ion-content>

<!-- Processing overlay -->
<div class="proc-overlay" *ngIf="busy">
  <div class="proc-card">
    <ion-spinner name="dots" color="primary"></ion-spinner>
    <p class="proc-card__title">Procesando archivos</p>
  </div>
</div>
````

## File: boarding-pass/src/app/trip-create/trip-create.page.scss
````scss
.page {
  max-width: 640px;
  margin: 0 auto;
  padding-bottom: var(--space-12);
  position: relative;
  z-index: 1;
}

.name-input {
  margin: var(--space-3);
  --background: var(--paper);
  --border-radius: var(--radius);
  --padding-start: var(--space-4);
  --padding-end: var(--space-4);
  border: 1px solid var(--paper-line);
  box-shadow: var(--shadow-1);

  ion-input {
    --placeholder-color: var(--navy-muted);
    font-size: var(--fs-h3);
    font-weight: 500;
    --padding-top: 14px;
    --padding-bottom: 14px;
  }
}

.section {
  padding: var(--space-3) var(--space-3) var(--space-4);

  &__title {
    font-size: var(--fs-tiny);
    font-weight: 600;
    margin: 0 0 var(--space-3);
    display: flex;
    align-items: center;
    gap: var(--space-2);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--navy-muted);

    ion-icon { font-size: 1rem; color: var(--teal); }
  }
}

ion-button[expand="block"][fill="outline"] {
  --border-color: var(--paper-line);
  --color: var(--navy);
  --border-radius: var(--radius);
  --background-hover: var(--paper-soft);
  font-weight: 500;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

ion-chip {
  font-weight: 500;
  font-size: var(--fs-tiny);
  --background: var(--teal-soft);
  --color: var(--teal);

  ion-icon { font-size: 0.9rem; }
}

ion-accordion-group {
  margin: 0 calc(-1 * var(--space-3));
}

ion-accordion {
  --background: var(--paper);
  border-top: 1px solid var(--paper-line);
  border-bottom: 1px solid var(--paper-line);
  margin-bottom: -1px;

  &[slot="header"] {
    --background: var(--paper);
  }
}

.seg-form {
  padding: var(--space-3) var(--space-4) var(--space-4);
  background: var(--paper-soft);

  ion-item {
    --background: transparent;
    --inner-padding-end: 0;
    --padding-start: 0;
    font-size: var(--fs-body);
    --border-color: var(--paper-line);
    margin-bottom: var(--space-2);
  }
}

.add-btn {
  margin: var(--space-3) 0 0;
  --background: var(--teal);
  --color: white;
  --border-radius: var(--radius);
  font-weight: 500;
}

.seg-form__error {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--fs-small);
  font-weight: 500;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.summary-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--paper);
  border-radius: var(--radius);
  font-size: var(--fs-body);
  border: 1px solid var(--paper-line);

  ion-icon { font-size: 1.2rem; flex-shrink: 0; color: var(--teal); }
}

.summary-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--navy);
  font-weight: 500;
}

.remove-btn {
  cursor: pointer;
  opacity: 0.5;
  transition: opacity var(--dur-fast) var(--ease);

  &:hover { opacity: 1; }
}

.save-section {
  padding: var(--space-3);
  position: sticky;
  bottom: 0;
  background: linear-gradient(180deg, transparent 0%, var(--paper) 30%);
}
````

## File: boarding-pass/src/global.scss
````scss
/*
 * App Global CSS
 * ----------------------------------------------------------------------------
 * Put style rules here that you want to apply globally. These styles are for
 * the entire app and not just one component. Additionally, this file can be
 * used as an entry point to import other CSS/Sass files to be included in the
 * output CSS.
 * For more information on global stylesheets, visit the documentation:
 * https://ionicframework.com/docs/layout/global-stylesheets
 */

/* Core CSS required for Ionic components to work properly */
@import "@ionic/angular/css/core.css";

/* Basic CSS for apps built with Ionic */
@import "@ionic/angular/css/normalize.css";
@import "@ionic/angular/css/structure.css";
@import "@ionic/angular/css/typography.css";
@import "@ionic/angular/css/display.css";

/* Optional CSS utils that can be commented out */
@import "@ionic/angular/css/padding.css";
@import "@ionic/angular/css/float-elements.css";
@import "@ionic/angular/css/text-alignment.css";
@import "@ionic/angular/css/text-transformation.css";
@import "@ionic/angular/css/flex-utils.css";

/**
 * Ionic Dark Mode
 * -----------------------------------------------------
 * For more info, please see:
 * https://ionicframework.com/docs/theming/dark-mode
 */

/* @import "@ionic/angular/css/palettes/dark.always.css"; */
/* @import "@ionic/angular/css/palettes/dark.class.css"; */
@import "@ionic/angular/css/palettes/dark.system.css";

/* =========================================================
   EDITORIAL TRAVEL THEME — global tokens
   ========================================================= */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  // ---- Brand palette: warm paper-white + aviation navy ----
  --paper:        #faf8f5;
  --paper-soft:   #f4ede4;
  --paper-line:   #e8e1d4;
  --navy:         #0f2942;
  --navy-soft:    #2a4660;
  --navy-muted:   #5a6b7e;

  --teal:         #0d7377;
  --teal-light:   #14a098;
  --teal-soft:    #d4eaea;

  --coral:        #e85d4d;
  --coral-soft:   #fae0db;

  --amber:        #d97706;
  --amber-soft:   #fef3c7;

  --success:      #14b8a6;
  --success-soft: #d1fae5;

  // ---- Typography ----
  --font-sans:    'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'SF Mono', Menlo, monospace;

  --fs-hero:      clamp(2rem, 5vw, 2.75rem);
  --fs-h1:        clamp(1.5rem, 3vw, 1.875rem);
  --fs-h2:        clamp(1.25rem, 2.5vw, 1.5rem);
  --fs-h3:        1.125rem;
  --fs-body:      0.9375rem;
  --fs-small:     0.8125rem;
  --fs-tiny:      0.6875rem;

  // ---- Spacing (4px grid) ----
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  // ---- Radii ----
  --radius-sm: 6px;
  --radius:    12px;
  --radius-lg: 20px;
  --radius-xl: 28px;

  // ---- Shadows (soft, layered) ----
  --shadow-1: 0 1px 2px rgba(15, 41, 66, 0.04), 0 1px 1px rgba(15, 41, 66, 0.03);
  --shadow-2: 0 4px 12px rgba(15, 41, 66, 0.06), 0 2px 4px rgba(15, 41, 66, 0.04);
  --shadow-3: 0 12px 32px rgba(15, 41, 66, 0.08), 0 4px 12px rgba(15, 41, 66, 0.05);
  --shadow-pop: 0 20px 48px rgba(15, 41, 66, 0.12);

  // ---- Motion ----
  --ease:        cubic-bezier(0.2, 0, 0, 1);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --dur-fast:    120ms;
  --dur:         240ms;
  --dur-slow:    400ms;

  // ---- Tabular numbers for codes ----
  --tabular: 'tnum' 1, 'lnum' 1;

  // ---- Glassmorphism ----
  --glass-bg:    rgba(250, 248, 245, 0.75);
  --glass-blur:  saturate(180%) blur(20px);
  --glass-line:  rgba(15, 41, 66, 0.08);

  // ---- Ionic overrides (so ionic components match our palette) ----
  --ion-color-primary:        var(--teal);
  --ion-color-primary-rgb:    13, 115, 119;
  --ion-color-primary-shade:  #0b6163;
  --ion-color-primary-tint:   #2a8a8e;
  --ion-color-secondary:      var(--navy);
  --ion-color-secondary-rgb:  15, 41, 66;
  --ion-color-secondary-shade:#0a1f33;
  --ion-color-secondary-tint: #2a4660;
  --ion-color-danger:         var(--coral);
  --ion-color-success:        var(--success);
  --ion-color-warning:        var(--amber);
  --ion-background-color:     var(--paper);
  --ion-text-color:           var(--navy);
  --ion-toolbar-background:   var(--paper);
  --ion-border-color:         var(--paper-line);
}

// ---- Dark mode (system) ----
@media (prefers-color-scheme: dark) {
  :root {
    --paper:        #0e1419;
    --paper-soft:   #1a2128;
    --paper-line:   #2a323b;
    --navy:         #e6e8ef;
    --navy-soft:    #b8c0cc;
    --navy-muted:   #9aa3b2;
    --teal-soft:    #1a3839;
    --coral-soft:   #3d1d19;
    --amber-soft:   #3d2e0e;
    --shadow-1: 0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 1px rgba(0, 0, 0, 0.2);
    --shadow-2: 0 4px 12px rgba(0, 0, 0, 0.35), 0 2px 4px rgba(0, 0, 0, 0.25);
    --shadow-3: 0 12px 32px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(0, 0, 0, 0.3);
    --glass-bg: rgba(14, 20, 25, 0.75);
  }
}

// ---- Global editorial typography ----
body, ion-app, ion-content, ion-item, ion-label, ion-button {
  font-family: var(--font-sans) !important;
  font-feature-settings: var(--tabular);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.tabular, .mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

// ---- Paper background texture (subtle) ----
ion-content {
  --background: var(--paper);
  position: relative;
}
ion-content::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    radial-gradient(circle at 20% 10%, rgba(13, 115, 119, 0.03) 0%, transparent 40%),
    radial-gradient(circle at 80% 80%, rgba(232, 93, 77, 0.02) 0%, transparent 40%);
  pointer-events: none;
  z-index: 0;
}

// ---- Glassmorphism toolbar ----
ion-toolbar.glass, ion-header.glass ion-toolbar {
  --background: var(--glass-bg);
  --border-color: var(--glass-line);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}

// ---- Boarding-pass-stub with notched edges (clip-path) ----
.pass-stub {
  position: relative;
  background: var(--paper);
  border-radius: var(--radius);
  box-shadow: var(--shadow-2);
  padding: var(--space-5);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
  overflow: hidden;
}
.pass-stub::before, .pass-stub::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 24px; height: 24px;
  background: var(--paper);
  border-radius: 50%;
  transform: translateY(-50%);
  z-index: 2;
}
.pass-stub::before { left: -12px; box-shadow: 1px 0 0 var(--paper-line); }
.pass-stub::after  { right: -12px; box-shadow: -1px 0 0 var(--paper-line); }
.pass-stub:hover { transform: translateY(-2px); box-shadow: var(--shadow-3); }

// ---- Flight strip decoration (origin ●----✈----● destination) ----
.flight-strip {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--navy);
}
.flight-strip__dot { width: 8px; height: 8px; border-radius: 50%; background: var(--teal); flex-shrink: 0; }
.flight-strip__line {
  flex: 1;
  height: 1px;
  background-image: linear-gradient(to right, var(--navy-muted) 50%, transparent 50%);
  background-size: 6px 1px;
  background-repeat: repeat-x;
  position: relative;
}
.flight-strip__line::after {
  content: '✈';
  position: absolute;
  left: 50%; top: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.9rem;
  color: var(--coral);
  background: var(--paper);
  padding: 0 4px;
}

// ---- Departure-board codes (large monospaced for cities, dates) ----
.board-code {
  font-family: var(--font-mono);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1;
  color: var(--navy);
}
.board-code--xl { font-size: clamp(1.75rem, 4vw, 2.25rem); }
.board-code--lg { font-size: 1.5rem; }
.board-code--md { font-size: 1.125rem; }

// ---- Animated underline on active tabs ----
ion-segment-button {
  --indicator-color: var(--teal);
  --color-checked: var(--teal);
  --color: var(--navy-muted);
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  min-width: auto;
  font-size: var(--fs-small);
}

// ---- Primary CTA button (gradient teal) ----
ion-button.primary-cta {
  --background: linear-gradient(135deg, var(--teal) 0%, var(--teal-light) 100%);
  --background-activated: var(--teal);
  --background-hover: var(--teal-light);
  --color: white;
  --border-radius: 14px;
  --padding-top: 18px;
  --padding-bottom: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  box-shadow: 0 6px 16px rgba(13, 115, 119, 0.25), 0 2px 4px rgba(13, 115, 119, 0.15);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
ion-button.primary-cta:active {
  transform: scale(0.98);
  box-shadow: 0 3px 8px rgba(13, 115, 119, 0.2);
}

// ---- Page entry animation ----
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.page-enter { animation: fadeUp var(--dur-slow) var(--ease) both; }
.page-enter-1 { animation-delay: 50ms; }
.page-enter-2 { animation-delay: 100ms; }
.page-enter-3 { animation-delay: 150ms; }

// ---- Soft scrollbar (webkit) ----
*::-webkit-scrollbar { width: 6px; height: 6px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb { background: var(--paper-line); border-radius: 3px; }
*::-webkit-scrollbar-thumb:hover { background: var(--navy-muted); }

// ---- Reduced motion ----
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

// ---- Processing overlay (used by home, trips, trip-create, itinerary) ----
.proc-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 41, 66, 0.55);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  animation: overlayIn 250ms var(--ease) both;
}
@keyframes overlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.proc-card {
  background: var(--paper);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-3);
  padding: var(--space-8) var(--space-6);
  text-align: center;
  max-width: 340px;
  width: 100%;
  animation: cardPop 400ms var(--ease-bounce) both;
  animation-delay: 80ms;
}
@keyframes cardPop {
  from { opacity: 0; transform: scale(0.9) translateY(16px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
.proc-card__title {
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--navy);
  margin: var(--space-4) 0 var(--space-1);
  letter-spacing: -0.01em;
}
.proc-card__count {
  font-family: var(--font-mono);
  font-size: var(--fs-tiny);
  color: var(--navy-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 var(--space-3);
  font-variant-numeric: tabular-nums;
}
.proc-card__bar {
  --background: var(--paper-soft);
  --progress-background: linear-gradient(90deg, var(--teal), var(--teal-light));
  height: 4px;
  border-radius: 2px;
  margin-top: var(--space-2);
}
````

## File: backend/qr_client.py
````python
"""
Cliente HTTP para el servicio de extraccion de QR (qr_service/).

Este modulo reemplaza el import directo de extraer_qr_pdfs.py. Mantiene
la misma API que el script legacy (mismas funciones, mismos returns)
para que app.py no note la diferencia.

El servicio qr_service es INTOCABLE (ver qr_service/README.md). Si
necesitas cambiar la extraccion de QR, modifica este cliente, no el
servicio.
"""

import base64
import os
import re
import sys
import time

import requests

# URL del servicio qr_service. Configurable por env var.
QR_SERVICE_URL = os.getenv("QR_SERVICE_URL", "http://127.0.0.1:8766")
TIMEOUT = 120  # segundos para PDFs grandes


def _ocr_flight_time(image_path: str) -> dict[str, str | None]:
    """Extrae hora de salida y cierre de puertas de una imagen via Tesseract OCR.

    Busca patrones como:
      Salida   La puerta cierra a las   Fecha
      07:00    06:30                    02 ene.

    Returns dict con 'flight_time' y 'gate_close_time'.
    """
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    except Exception as e:
        print(f"[ocr] Error importando pytesseract: {e}", file=sys.stderr, flush=True)
        return {"flight_time": None, "gate_close_time": None}

    try:
        img = Image.open(image_path)
        w, h = img.size
        if max(w, h) < 1200:
            img = img.resize((w * 2, h * 2), Image.LANCZOS)
        text = pytesseract.image_to_string(
            img, lang='spa+eng', config='--psm 6 --oem 1',
        )
    except Exception as e:
        print(f"[ocr] Error en OCR: {e}", file=sys.stderr, flush=True)
        return {"flight_time": None, "gate_close_time": None}

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    flight_time: str | None = None
    gate_close_time: str | None = None

    time_re = re.compile(r"(\d{1,2})[:.](\d{2})")

    for i, line in enumerate(lines):
        has_salida = 'salida' in line.lower()
        has_puerta = 'puerta' in line.lower()

        if not (has_salida or has_puerta):
            continue

        data_line = ''
        for j in range(i + 1, min(i + 3, len(lines))):
            if lines[j] and time_re.search(lines[j]):
                data_line = lines[j]
                break

        if not data_line:
            continue

        times = []
        for m in time_re.finditer(data_line):
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                times.append(f"{hh:02d}:{mm:02d}")

        if has_salida and len(times) > 0 and flight_time is None:
            flight_time = times[0]
        if has_puerta and len(times) > 1 and gate_close_time is None:
            gate_close_time = times[1]
        elif has_puerta and len(times) == 1 and gate_close_time is None:
            gate_close_time = times[0]

    if flight_time is None or gate_close_time is None:
        all_times = []
        for m in time_re.finditer(text):
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                all_times.append(f"{hh:02d}:{mm:02d}")

        seen = set()
        unique_times = []
        for t in all_times:
            if t not in seen:
                seen.add(t)
                unique_times.append(t)

        if flight_time is None and len(unique_times) > 0:
            flight_time = unique_times[0]
        if gate_close_time is None and len(unique_times) > 1:
            gate_close_time = unique_times[1]

    return {"flight_time": flight_time, "gate_close_time": gate_close_time}


def _service_extract(file_path: str, is_image: bool) -> dict:
    """Llama al endpoint /extract del qr_service. Devuelve el JSON."""
    endpoint = "extract"
    url = f"{QR_SERVICE_URL.rstrip('/')}/{endpoint}"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        try:
            r = requests.post(url, files=files, timeout=TIMEOUT)
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"No se puede conectar al qr_service en {url}. "
                f"¿Esta arrancado? Error: {e}"
            ) from e

    if r.status_code != 200:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"qr_service devolvio {r.status_code}: {detail}")

    return r.json()


def _items_to_tuples(items: list[dict], out_dir: str) -> list[tuple]:
    """Convierte la respuesta JSON del servicio al formato de tuplas
    que espera app.py: (page, fname, b64, text, fmt, origin).
    """
    tuples = []
    for i, it in enumerate(items):
        page = it.get("page", 1)
        fmt = it.get("format", "Unknown")
        text = it.get("text", "")
        b64 = it.get("base64", "")
        origin = it.get("origin", "service")
        fname = f"qr_p{page}_{i+1}_{fmt}.png"
        tuples.append((page, fname, b64, text, fmt, origin))
    return tuples


def extract_codes(pdf_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de un PDF via qr_service."""
    data = _service_extract(pdf_path, is_image=False)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    text_fields = {}
    try:
        import extraer_qr_pdfs  # noqa: E402
        text_fields = extraer_qr_pdfs.extract_text_fields(pdf_path)
    except Exception:
        pass

    return codes, text_fields


def extract_codes_from_image(image_path: str, out_dir: str) -> tuple[list[tuple], dict]:
    """Extrae codigos de una imagen via qr_service + OCR de hora de salida."""
    data = _service_extract(image_path, is_image=True)
    items = data.get("items", [])
    codes = _items_to_tuples(items, out_dir)

    ocr_data = _ocr_flight_time(image_path)

    return codes, ocr_data
````

## File: boarding-pass/src/app/services/itinerary.service.ts
````typescript
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// --- Tipos del itinerario ---

export interface WeatherDay {
  date: string;
  temp_max: number | null;
  temp_min: number | null;
  precipitation_mm: number | null;
  condition: string;
  wind_kmh: number | null;
}

export interface Restaurant {
  name: string;
  type: string;
  description: string;
  price_range: string;
}

export interface Hotel {
  name: string;
  zone: string;
  description: string;
  price_range: string;
  highlights: string[];
}

export interface PlaceOfInterest {
  name: string;
  type: string;
  description: string;
  tips: string[];
}

export interface HistoricalSite {
  name: string;
  period: string;
  description: string;
  curiosity: string;
}

export interface DaySlot {
  activities: string[];
  description: string;
}

export interface MealSuggestions {
  lunch: string;
  dinner: string;
}

export interface DailyPlan {
  day_number: number;
  date: string;
  theme: string;
  morning: DaySlot;
  afternoon: DaySlot;
  evening: DaySlot;
  meal_suggestions: MealSuggestions;
}

export interface ItineraryData {
  destination_overview?: string;
  weather_summary?: string;
  weather: WeatherDay[];
  restaurants: Restaurant[];
  hotels: Hotel[];
  places_of_interest: PlaceOfInterest[];
  historical_sites: HistoricalSite[];
  daily_itinerary: DailyPlan[];
  transport_tips: string[];
  general_tips: string[];
  cultural_notes: string[];
  meta?: { destinations: string[]; pass_count: number; generated_at: string };
  error?: string;
  raw_response?: string;
  parse_error?: boolean;
}

export interface ItineraryResponse {
  trip_id: number;
  cached: boolean;
  itinerary: ItineraryData;
}

export interface ExpandResponse {
  section: string;
  items?: any[];
  places_of_interest?: any[];
  historical_sites?: any[];
  transport_tips?: string[];
  general_tips?: string[];
  cultural_notes?: string[];
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class ItineraryService {
  constructor(private http: HttpClient) {}

  private _headers(sessionId: string): HttpHeaders {
    let h = new HttpHeaders({ 'X-Session-Id': sessionId });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return h;
  }

  getCached(tripId: number, sessionId: string): Observable<ItineraryResponse> {
    return this.http.get<ItineraryResponse>(
      `${environment.apiUrl}/api/itinerary/${tripId}`,
      { headers: this._headers(sessionId) },
    );
  }

  generate(tripId: number, sessionId: string): Observable<ItineraryResponse> {
    return this.http.post<ItineraryResponse>(
      `${environment.apiUrl}/api/itinerary/${tripId}`,
      {},
      { headers: this._headers(sessionId) },
    );
  }

  expandSection(tripId: number, section: string, sessionId: string): Observable<ExpandResponse> {
    return this.http.post<ExpandResponse>(
      `${environment.apiUrl}/api/itinerary/${tripId}/expand`,
      { section },
      { headers: this._headers(sessionId) },
    );
  }
}
````

## File: boarding-pass/src/app/trip-create/trip-create.page.ts
````typescript
import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, Pass, TravelSegment } from '../services/boarding-pass.service';

const SEGMENT_TYPES = [
  { type: 'flight', label: 'Vuelo', icon: 'airplane' },
  { type: 'train', label: 'Tren', icon: 'train' },
  { type: 'hotel', label: 'Hotel', icon: 'bed' },
  { type: 'car', label: 'Coche', icon: 'car' },
  { type: 'restaurant', label: 'Restaurante', icon: 'restaurant' },
  { type: 'activity', label: 'Actividad', icon: 'football' },
] as const;

@Component({
  selector: 'app-trip-create',
  templateUrl: './trip-create.page.html',
  styleUrls: ['./trip-create.page.scss'],
  standalone: false,
})
export class TripCreatePage {
  tripName = '';
  busy = false;

  segments = signal<TravelSegment[]>([]);
  uploadedPdfs = signal<{ name: string; passes: Pass[] }[]>([]);
  openForm = signal<string | null>(null);
  formErrors: Record<string, string> = {};

  editTripId: number | null = null;
  existingTripName = '';

  // Form models
  flightForm = { airline: '', flight_number: '', from: '', to: '', date: '', time: '' };
  trainForm = { operator: '', train_number: '', from: '', to: '', date: '', time: '' };
  hotelForm = { name: '', city: '', check_in: '', check_out: '' };
  carForm = { company: '', city: '', pickup_date: '', return_date: '' };
  restaurantForm = { name: '', city: '', date: '', time: '' };
  activityForm = { name: '', city: '', date: '', description: '' };

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private toastCtrl: ToastController,
  ) {}

  ionViewWillEnter() {
    const state = history.state as any;
    if (state?.editTripId) {
      this.editTripId = state.editTripId;
      this.existingTripName = state.tripName || '';
      this.tripName = this.existingTripName;
      if (state.segments) {
        this.segments.set(state.segments);
      }
    }
  }

  toggleForm(type: string) {
    this.openForm.set(this.openForm() === type ? null : type);
  }

  get openFormType(): string | null {
    return this.openForm();
  }

  // --- PDF Upload ---

  async pickPdfs() {
    let picked: any[] = [];
    try {
      const result = await FilePicker.pickFiles({ types: ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'], limit: 0 });
      picked = result.files;
    } catch (e: any) {
      if (String(e?.message ?? e).toLowerCase().includes('cancel')) return;
      await this.toast('No se pudo abrir el selector', 'danger');
      return;
    }
    if (!picked.length) return;

    this.busy = true;

    for (const file of picked) {
      const name = file.name || 'pdf.pdf';
      try {
        const f = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(f));
        if (resp?.passes?.length) {
          const current = this.uploadedPdfs();
          this.uploadedPdfs.set([...current, { name: resp.filename, passes: resp.passes }]);
        }
      } catch (e: any) {
        this.toast(`Error en ${name}`, 'danger');
      }
    }

    this.busy = false;
  }

  removePdf(index: number) {
    const current = this.uploadedPdfs();
    this.uploadedPdfs.set(current.filter((_, i) => i !== index));
  }

  // --- Segment handlers ---

  private validateRequired(value: string, label: string): string | null {
    if (!value?.trim()) return `El campo "${label}" es obligatorio`;
    return null;
  }

  addSegment(type: string) {
    this.formErrors = {};
    let seg: TravelSegment | null = null;

    switch (type) {
      case 'flight': {
        const err = this.validateRequired(this.flightForm.airline, 'Aerolínea') || this.validateRequired(this.flightForm.flight_number, 'Nº vuelo');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'flight', ...this.flightForm };
        this.flightForm = { airline: '', flight_number: '', from: '', to: '', date: '', time: '' };
        break;
      }
      case 'train': {
        const err = this.validateRequired(this.trainForm.operator, 'Operador');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'train', ...this.trainForm };
        this.trainForm = { operator: '', train_number: '', from: '', to: '', date: '', time: '' };
        break;
      }
      case 'hotel': {
        const err = this.validateRequired(this.hotelForm.name, 'Nombre');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'hotel', ...this.hotelForm };
        this.hotelForm = { name: '', city: '', check_in: '', check_out: '' };
        break;
      }
      case 'car': {
        const err = this.validateRequired(this.carForm.company, 'Compañía');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'car', ...this.carForm };
        this.carForm = { company: '', city: '', pickup_date: '', return_date: '' };
        break;
      }
      case 'restaurant': {
        const err = this.validateRequired(this.restaurantForm.name, 'Nombre');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'restaurant', ...this.restaurantForm };
        this.restaurantForm = { name: '', city: '', date: '', time: '' };
        break;
      }
      case 'activity': {
        const err = this.validateRequired(this.activityForm.name, 'Nombre');
        if (err) { this.formErrors[type] = err; return; }
        seg = { type: 'activity', ...this.activityForm };
        this.activityForm = { name: '', city: '', date: '', description: '' };
        break;
      }
    }
    if (seg) {
      this.segments.set([...this.segments(), seg]);
      this.openForm.set(null);
      this.formErrors = {};
      try { Haptics.impact({ style: ImpactStyle.Light }); } catch {}
    }
  }

  removeSegment(index: number) {
    const current = this.segments();
    this.segments.set(current.filter((_, i) => i !== index));
  }

  segmentIcon(type: string): string {
    const s = SEGMENT_TYPES.find(s => s.type === type);
    return s?.icon || 'ellipse';
  }

  segmentLabel(type: string): string {
    const s = SEGMENT_TYPES.find(s => s.type === type);
    return s?.label || type;
  }

  // --- Summary helpers ---

  segmentSummary(seg: TravelSegment): string {
    switch (seg.type) {
      case 'flight': return `${seg.airline || ''}${seg.flight_number || ''} ${seg.from || ''}→${seg.to || ''}`.trim() || 'Vuelo';
      case 'train': return `${seg.operator || ''} ${seg.train_number || ''} ${seg.from || ''}→${seg.to || ''}`.trim() || 'Tren';
      case 'hotel': return `${seg.name || ''} (${seg.city || ''}) ${seg.check_in || ''} → ${seg.check_out || ''}`.trim() || 'Hotel';
      case 'car': return `${seg.company || ''} ${seg.city || ''}`.trim() || 'Coche';
      case 'restaurant': return `${seg.name || ''} (${seg.city || ''}) ${seg.date || ''}`.trim() || 'Restaurante';
      case 'activity': return `${seg.name || ''} (${seg.city || ''})`.trim() || 'Actividad';
      default: return 'Segmento';
    }
  }

  // --- Save ---

  async saveTrip() {
    if (!this.tripName.trim() && this.uploadedPdfs().length === 0) {
      await this.toast('Pon un nombre al viaje o sube al menos un PDF', 'warning');
      return;
    }

    const allPasses = this.uploadedPdfs().reduce((acc, p) => acc.concat(p.passes), [] as Pass[]);
    const allImages: any[] = [];
    const filename = this.uploadedPdfs().map(p => p.name).join(' + ') || 'sin_pdfs.pdf';
    this.busy = true;

    if (this.editTripId) {
      // Solo actualizar segmentos
      try {
        await firstValueFrom(this.svc.updateSegments(this.editTripId, this.segments()));
        await this.toast('Segmentos actualizados', 'success');
        this.router.navigate(['/trips']);
      } catch (e: any) {
        this.toast('Error: ' + (e?.error?.detail ?? e?.message ?? e), 'danger');
      }
      this.busy = false;
      return;
    }

    try {
      const resp = await firstValueFrom(
        this.svc.saveTrip(filename, allPasses, allImages, this.tripName.trim(), this.segments()),
      );

      await this.toast('Viaje guardado', 'success');
      try { Haptics.impact({ style: ImpactStyle.Medium }); } catch {}
      this.router.navigate(['/trips']);
    } catch (e: any) {
      this.busy = false;
      this.toast('Error al guardar: ' + (e?.error?.detail ?? e?.message ?? e), 'danger');
    }
  }

  goBack() {
    this.router.navigate(['/home']);
  }

  // --- Helpers ---

  private async toBlob(picked: any): Promise<File> {
    if (picked.blob instanceof Blob && picked.name) {
      return new File([picked.blob], picked.name, { type: 'application/pdf' });
    }
    const resp = await fetch(picked.path ?? picked.uri);
    const blob = await resp.blob();
    return new File([blob], picked.name ?? 'boarding.pdf', { type: 'application/pdf' });
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
````

## File: boarding-pass/src/app/home/home.page.scss
````scss
.hero {
  text-align: center;
  padding: clamp(2rem, 8vw, 3.5rem) 1.5rem;
  max-width: 480px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100%;
  justify-content: center;

  &__emblem {
    position: relative;
    width: 88px;
    height: 88px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-5);
  }

  &__emblem-icon {
    font-size: 2.25rem;
    color: var(--teal);
    position: relative;
    z-index: 1;
    transform: rotate(-8deg);
  }

  &__emblem-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2px solid var(--teal-soft);
    animation: emblemPulse 3s ease-in-out infinite;
  }
}

@keyframes emblemPulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.08); opacity: 1; }
}

.hero__strip {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  padding: 0 var(--space-4);
  opacity: 0.45;
}
.hero__strip .flight-strip__line { flex: 1; }

.hero__title {
  font-size: var(--fs-hero);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--navy);
  margin: 0 0 var(--space-4);

  em {
    font-style: normal;
    background: linear-gradient(135deg, var(--teal) 0%, var(--teal-light) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
  }
}

.hero__sub {
  font-size: var(--fs-body);
  color: var(--navy-muted);
  line-height: 1.5;
  margin: 0 0 var(--space-8);
}

.hero__divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-6) 0;
  color: var(--navy-muted);
  font-size: var(--fs-tiny);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 500;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--paper-line);
  }
}

:host .proc-card__cancel {
  margin-top: var(--space-4);
  --color: var(--navy-muted);
  font-size: var(--fs-small);
}

ion-button[fill="clear"] .mono {
  font-size: var(--fs-small);
  letter-spacing: 0;
  text-transform: lowercase;
  color: var(--navy-muted);
}

.btn-saved-trips {
  --background: var(--paper);
  --color: var(--navy);
  --border-radius: 14px;
  --border-color: var(--paper-line);
  --border-style: solid;
  --border-width: 1.5px;
  --padding-top: 14px;
  --padding-bottom: 14px;
  font-weight: 600;
  font-size: 0.95rem;
  margin-top: 12px;
  letter-spacing: 0.02em;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: transform 0.15s ease, box-shadow 0.15s ease;

  ion-icon {
    font-size: 1.15rem;
    color: var(--teal);
  }

  &::part(native) {
    border: 1.5px solid var(--paper-line);
  }

  &:active {
    transform: scale(0.97);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }
}
````

## File: boarding-pass/src/app/trips/trips.page.scss
````scss
.trip-list {
  padding: var(--space-4) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 640px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.trip-card {
  cursor: pointer;
  padding: var(--space-5) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.trip-card__head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.trip-card__title-block {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  min-width: 0;

  .board-code {
    font-size: var(--fs-body);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 45%;
    flex-shrink: 1;
  }
}
.trip-card__title-block .flight-strip__line { flex: 1; min-width: 20px; }

.trip-card__title-block .flight-strip__line::after {
  display: none;
}

.trip-card__strip-icon {
  position: absolute;
  left: 50%; top: 50%;
  transform: translate(-50%, -50%);
  font-size: 1rem;
  color: var(--coral);
  background: var(--paper);
  padding: 0 4px;
}

.trip-card__name {
  margin: 0;
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--navy);
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.trip-card__date {
  font-size: var(--fs-tiny);
  color: var(--navy-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.trip-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: var(--fs-tiny);
  font-weight: 500;
  background: var(--paper-soft);
  color: var(--navy-soft);
  border: 1px solid var(--paper-line);

  ion-icon { font-size: 0.85rem; }
}
.chip--muted { color: var(--navy-muted); font-style: italic; }
.chip--bookings {
  background: var(--teal-soft);
  color: var(--teal);
  border-color: transparent;
}

.trip-card__actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-1);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--paper-line);

  ion-button {
    --padding-start: 0.5rem;
    --padding-end: 0.5rem;
    margin: 0;
  }
}

// --- Empty state ---
.empty-state {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  max-width: 420px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__icon {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: var(--paper-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-5);

    ion-icon { font-size: 2.5rem; color: var(--teal); }
  }

  h2 { font-size: var(--fs-h2); font-weight: 600; margin: 0 0 var(--space-2); color: var(--navy); }
  p { color: var(--navy-muted); margin: 0 0 var(--space-6); line-height: 1.5; }
}

// --- Skeleton loader ---
.skeleton {
  background: linear-gradient(90deg, var(--paper-soft) 0%, var(--paper-line) 50%, var(--paper-soft) 100%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: skeleton-shimmer 1.5s infinite linear;
  height: 14px;
  margin-bottom: var(--space-2);

  &:last-child { margin-bottom: 0; }
}
.skeleton-line { width: 100%; }
.skeleton-line.w-full { width: 100%; }
.skeleton-line.w-80 { width: 80%; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.trip-card__date {
  font-size: var(--fs-tiny);
  color: var(--navy-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: var(--space-1);
}

// Processing cancel button
.proc-card__cancel {
  margin-top: var(--space-4);
  --color: var(--navy-muted);
  font-size: var(--fs-small);
}
````

## File: boarding-pass/src/environments/environment.ts
````typescript
// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
  production: false,
  // Para navegador local: localhost.
  // Para emulador Android: cambiar a http://10.0.2.2:8765
  // Para dispositivo real: cambiar a http://<IP_LAN>:8765
  apiUrl: 'http://localhost:8765',
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
````

## File: backend/parser.py
````python
"""
Parser de los datos decodificados de las tarjetas de embarque / billetes.

Formatos soportados:
  - IATA BCBP (M1 = 1 trayecto, M2 = multiples). Usado por Vueling, Iberia,
    Ryanair, AA, Lufthansa, etc.
  - Renfe / OUIGO (formato propietario Renfe). Extrae fecha, hora, tren,
    clase y localizador.

Devuelve un dict con campos normalizados. Si no reconoce el formato, devuelve
el texto crudo en `raw` para mostrar tal cual.
"""

import re
from datetime import date, timedelta


def _doy_to_date(year, doy):
    try:
        return date(year, 1, 1) + timedelta(days=int(doy) - 1)
    except (ValueError, TypeError):
        return None


# --- IATA BCBP ---------------------------------------------------------------
#
# Layout fijo (IATA Resolution 792) tras M1/M2:
#   0-1     : "M1" / "M2"
#   2-21    : nombre pasajero (20 chars, right-padded)
#   22      : electronic ticket indicator (E o espacio)
#   23-29   : PNR (7 chars, right-padded)
#   30-32   : aeropuerto origen
#   33-35   : aeropuerto destino
#   36-38   : aerolinea (3 chars, right-padded, p.ej. "VY " para VY)
#   39-43   : vuelo (5 chars, right-padded, p.ej. " 2225")
#   44-46   : dia del ano (3 chars)
#   47      : clase
#   48-51   : asiento (4 chars, p.ej. "024C")
#   52-55   : secuencia check-in (4 chars)
#   56+     : datos variables
#
# No hay separadores entre los campos: es un layout empaquetado.
# Por eso mejor parsear por posicion fija que por regex.

def _parse_iata_bcbp(text, year=None):
    if len(text) < 56:
        return None
    if text[0] != "M" or text[1] not in "12":
        return None
    name = text[2:22].strip()
    if not name or "/" not in name:
        # Un BCBP valido siempre tiene nombre con formato APELLIDO/NOMBRE
        return None
    pnr = text[23:30].strip()
    from_ = text[30:33]
    to = text[33:36]
    airline = text[36:39].strip()
    flight = text[39:44].strip().lstrip("0") or text[39:44].strip()
    doy_str = text[44:47]
    clas = text[47]
    seat = text[48:52].strip()
    chkseq = text[52:56].strip()

    if not doy_str.isdigit():
        return None
    flight_date = _doy_to_date(year or date.today().year, int(doy_str))

    # Intentar extraer hora de salida de la seccion de datos variables (pos 56+)
    # Algunas aerolineas incluyen el campo condicional "14" (Departure Time).
    # Formatos posibles en variable data:
    #   - "14HHMM"        (6 chars: campo 14 + 4 digitos HHMM)
    #   - "1404HHMM"      (8 chars: campo 14 + len 04 + 4 digitos)
    #   - "+HHMM" o " HH:MM" en Ryanair (no incluido, pero otras lo hacen)
    flight_time = None
    var_data = text[56:]
    # Buscar campo IATA "14" seguido de HHMM
    m = re.search(r"14\d{2}(\d{2})(\d{2})", var_data)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            flight_time = f"{hh:02d}:{mm:02d}"
    # Fallback: buscar cualquier HH:MM o HHMM en datos variables
    if not flight_time:
        m = re.search(r"(\d{2}):(\d{2})", var_data)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                flight_time = f"{hh:02d}:{mm:02d}"
    if not flight_time:
        m = re.search(r"\b([01]\d|2[0-3])([0-5]\d)\b", var_data)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            flight_time = f"{hh:02d}:{mm:02d}"

    return {
        "format": "IATA_BCBP",
        "kind": "flight",
        "name": name,
        "pnr": pnr,
        "from": from_,
        "to": to,
        "airline": airline,
        "flight": flight,
        "flight_date": flight_date.isoformat() if flight_date else None,
        "flight_time": flight_time,
        "class": clas,
        "seat": seat,
        "check_in_seq": chkseq,
        "raw": text,
        "has_explicit_year": False,
        "doy": doy_str,
    }


# --- Renfe / OUIGO (formato propietario) ------------------------------------
#
# No esta estandarizado. Lo que SI hemos confirmado en los PDFs:
#   - Aztec: "DD/MM/YYYY" + "HH:MM" + tren + clase + localizador
#   - QR:    "MMDD" + "HHMM" pegados + tren + clase + localizador
#   - Localizador: 6-10 chars alfanum (puede acabar en ".." o padding de 0s)
#
# Renfe: 6 digitos tren + 1 letra clase + 6-10 alnum localizador
# OUIGO: 6 digitos tren + 1 letra clase + el localizador esta a veces
#         cifrado en base64 dentro del mismo bloque.

_RENFE_DATE_SLASH_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")  # DD/MM/YYYY
_RENFE_TIME_RE = re.compile(r"(\d{2}):(\d{2})")                  # HH:MM
# MMDD + HHMM pegados (formato QR Renfe, p.ej. "07260831" = 26-jul 08:31).
# Sin lookbehind/lookahead porque los digitos van pegados a otros en el bloque.
_RENFE_DATE_COMPACT_RE = re.compile(r"([01]\d)([0-3]\d)(\d{2})(\d{2})")
_RENFE_TRAIN_RE = re.compile(
    r"(?P<train>\d{5,6})"
    r"(?P<clas>[A-Z])"
    r"(?P<loc>[A-Z0-9.=]{6,12})"
)


def _parse_renfe(text):
    flight_date = None
    flight_time = None

    # 1) Intentar formato con slashes (Aztec, ticket completo)
    date_match = _RENFE_DATE_SLASH_RE.search(text)
    if date_match:
        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        try:
            flight_date = date(y, m, d).isoformat()
        except ValueError:
            pass

    time_match = _RENFE_TIME_RE.search(text)
    if time_match:
        h, mn = int(time_match.group(1)), int(time_match.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            flight_time = f"{h:02d}:{mn:02d}"

    # 2) Si no habia fecha con slashes, buscar formato MMDD y HHMM.
    #    En el QR compacto de Renfe la fecha puede estar embebida en una
    #    cadena de digitos mas larga (ej: "00004 0726 0831 200111").
    #    Tomamos el ULTIMO candidato valido cerca del localizador.
    if flight_date is None or flight_time is None:
        # Primero intentamos MMDDHHMM seguido (8 digitos exactos)
        for compact in reversed(list(_RENFE_DATE_COMPACT_RE.finditer(text))):
            mm, dd, hh, mn = (
                int(compact.group(1)),
                int(compact.group(2)),
                int(compact.group(3)),
                int(compact.group(4)),
            )
            if 1 <= mm <= 12 and 1 <= dd <= 31 and 0 <= hh <= 23 and 0 <= mn <= 59:
                if flight_date is None:
                    try:
                        flight_date = date(date.today().year, mm, dd).isoformat()
                    except ValueError:
                        pass
                if flight_time is None:
                    flight_time = f"{hh:02d}:{mn:02d}"
                break

        # Si no se encontro, buscar MMDD y HHMM por separado (sin lookbehind)
        if flight_date is None or flight_time is None:
            mmdd_candidates = []
            for m in re.finditer(r"([01]\d)([0-3]\d)", text):
                mm, dd = int(m.group(1)), int(m.group(2))
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    mmdd_candidates.append((m.start(), mm, dd))

            for _, mm, dd in reversed(mmdd_candidates):
                if flight_date is None:
                    try:
                        flight_date = date(date.today().year, mm, dd).isoformat()
                    except ValueError:
                        pass
                    break

            if flight_time is None:
                # Buscar HHMM cerca del MMDD encontrado
                for pos, mm, dd in mmdd_candidates:
                    # Buscar HHMM en los siguientes 8 digitos
                    window = text[pos+4:pos+20] if pos+4 < len(text) else ""
                    hmm_match = re.search(r"(\d{2})(\d{2})", window)
                    if hmm_match:
                        hh, mn = int(hmm_match.group(1)), int(hmm_match.group(2))
                        if 0 <= hh <= 23 and 0 <= mn <= 59:
                            flight_time = f"{hh:02d}:{mn:02d}"
                            break

    # 3) Tren + clase + localizador. Cogemos el ULTIMO match (los registros
    #    Aztecs concatenan padding "CNO0000000000..." que no es el localizador
    #    real; el real viene al final).
    train_matches = list(_RENFE_TRAIN_RE.finditer(text))
    if not train_matches:
        return None
    train_match = train_matches[-1]

    # Limpiar ceros de padding al final del localizador
    pnr = train_match["loc"].rstrip("0").rstrip(".")

    # Marcar PNRs sospechosos como vacios (se rellenaran del texto PDF)
    if len(pnr) < 4 or pnr.upper() in ("NO", "SI", "CNO", "ANO", "BNO", "DNO"):
        pnr = ""
    if not flight_date:
        return None

    return {
        "format": "RENFE",
        "kind": "train",
        "name": None,
        "pnr": pnr,
        "train": train_match["train"],
        "flight_date": flight_date,
        "flight_time": flight_time,
        "class": train_match["clas"],
        "seat": None,
        "raw": text,
        "has_explicit_year": True,
    }


# --- Year inference ---------------------------------------------------------
# Para billetes sin año explicito (IATA BCBP: solo dia del año),
# inferimos el año minimizando el lapso entre vuelos consecutivos.
# Ej: 31-Dic (DOY=365) + 3-Ene (DOY=3) → 2026 y 2027 (gap de 3 días).

def infer_years(passes: list[dict]) -> None:
    """Infiere años para vuelos sin año explícito minimizando el lapso.

    Agrupa por (pnr, kind), mantiene orden original de páginas,
    detecta cruce de año cuando DOY decrece (ej: DOY=365 → DOY=3).
    Modifica los pases in-place.
    """
    groups: dict[tuple, list[dict]] = {}
    for p in passes:
        if p.get("has_explicit_year", True):
            continue
        key = (p.get("pnr"), p.get("kind"))
        groups.setdefault(key, []).append(p)

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        base_year = date.today().year
        prev_doy = int(group[0].get("doy", 0))

        for p in group:
            doy = int(p.get("doy", 0))
            if prev_doy > 180 and doy < prev_doy and doy < 180:
                base_year += 1
            try:
                corrected = date(base_year, 1, 1) + timedelta(days=doy - 1)
                p["flight_date"] = corrected.isoformat()
            except (ValueError, TypeError):
                pass
            prev_doy = doy


# --- Dispatcher -------------------------------------------------------------

def _has_essential_data(parsed):
    """Comprueba que un pase tiene los datos minimos para ser util.
    Descarta pases sin fecha o sin localizador/codigo de vuelo."""
    fmt = parsed.get("format")
    if fmt in ("URL", "EMPTY", "UNKNOWN"):
        return False
    if not parsed.get("flight_date"):
        return False
    if fmt == "IATA_BCBP":
        if not parsed.get("airline") or not parsed.get("flight"):
            return False
    if fmt == "RENFE":
        if not parsed.get("train"):
            return False
    return True


def parse_code(text, year=None):
    """Detecta el formato y devuelve dict con campos normalizados.
    Devuelve None si el pase no tiene los datos esenciales (fecha, codigo, etc.)
    para que sea descartado por el caller."""
    if not text or not text.strip():
        return None

    text = text.strip()

    # URLs de publicidad -> descartar (no son billetes)
    if text.lower().startswith(("http://", "https://")):
        return None

    result = None

    # IATA BCBP
    if text.startswith("M1") or text.startswith("M2"):
        result = _parse_iata_bcbp(text, year=year)

    # Renfe / OUIGO / Iryo etc.
    if result is None and len(text) > 30 and _RENFE_TRAIN_RE.search(text):
        result = _parse_renfe(text)

    if result is None:
        return None

    # Validacion final: descartar si faltan datos esenciales
    if not _has_essential_data(result):
        return None

    return result
````

## File: boarding-pass/src/app/result/result.page.scss
````scss
// --- Accordion group list ---
.bill-list {
  padding: var(--space-4) var(--space-3) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 560px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

// --- Person accordion group ---
.person-group {
  background: var(--paper);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.person-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  cursor: pointer;
  user-select: none;
  background: var(--paper);
  transition: background 0.15s ease;

  &:hover {
    background: var(--paper-soft);
  }

  &__left {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-width: 0;
    flex: 1;
  }

  &__chevron {
    font-size: 1.5rem;
    color: var(--teal);
    flex-shrink: 0;
    transition: transform 0.2s ease;
  }

  &__name {
    font-size: var(--fs-h3, 1.1rem);
    font-weight: 600;
    color: var(--navy);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__right {
    flex-shrink: 0;
    margin-left: var(--space-3);
  }

  &__count {
    font-size: var(--fs-tiny);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--navy-muted);
    font-weight: 500;
  }
}

.person-passes {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 0 var(--space-4) var(--space-4);
  // Each child .boarding-pass keeps its internal padding
}

// --- Boarding pass card ---
.boarding-pass {
  padding: 0;
  overflow: hidden;
  background: var(--paper);
}

.bp-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
  color: var(--paper);
  position: relative;
  z-index: 1;
}

// Cabecera con color distinto para trenes (teal) vs aviones (navy)
.boarding-pass.bp-train .bp-header {
  background: linear-gradient(135deg, var(--teal) 0%, var(--teal-light, var(--teal)) 100%);
}
.boarding-pass.bp-flight .bp-header {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
}

// Icono redondo en la cabecera
.bp-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}
.bp-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  ion-icon {
    font-size: 1.5rem;
    color: var(--paper);
  }
  .bp-icon-train { transform: rotate(0deg); }
}

.bp-airline { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.bp-airline__code {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--paper);
}
.bp-airline__name {
  font-size: var(--fs-tiny);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.6;
}

.bp-class {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;

  &__label {
    font-size: 9px;
    letter-spacing: 0.15em;
    opacity: 0.5;
  }
  .board-code { color: var(--paper); }
}

.bp-source {
  display: none;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-tiny);
  opacity: 0.5;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  ion-icon { font-size: 0.9rem; }
}

// --- Flight strip ---
.bp-strip {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-5);
  position: relative;
  z-index: 1;
}

.bp-strip__end {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 0 0 auto;
  &:last-child { align-items: flex-end; }
}

.bp-strip__line {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  min-width: 80px;

  .flight-strip__line { width: 100%; }
}

.bp-strip__label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--navy-muted);
  margin-top: 4px;
}

.bp-strip__time {
  font-size: var(--fs-small);
  color: var(--navy-soft);
  font-weight: 500;
}

// --- Info grid ---
.bp-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3) var(--space-4);
  padding: var(--space-4) var(--space-5) var(--space-5);
  position: relative;
  z-index: 1;
}

.bp-info__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.bp-info__label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--navy-muted);
  font-weight: 500;
}
.bp-info__value {
  font-size: var(--fs-body);
  color: var(--navy);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// --- Barcode ---
.bp-barcode {
  background: var(--paper-soft);
  padding: var(--space-4) var(--space-5);
  text-align: center;
  border-top: 1px dashed var(--paper-line);
  position: relative;
  z-index: 1;

  img {
    max-width: 220px;
    margin: 0 auto;
    display: block;
    background: white;
    padding: 8px;
    border-radius: 4px;
  }
}
.bp-barcode__hint {
  display: block;
  margin-top: var(--space-2);
  font-size: 9px;
  letter-spacing: 0.15em;
  color: var(--navy-muted);
  text-transform: uppercase;
}

.bp-source {
  padding: 6px var(--space-5) var(--space-3);
  margin: 0;
  font-size: 9px;
  color: var(--navy-muted);
  text-align: right;
  opacity: 0.6;
}

// Perforacion lateral (look de boarding pass)
.bp-new-badge {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--paper);
  background: var(--teal);
  padding: 3px 8px;
  border-radius: 4px;
  z-index: 3;
}

.result-actions {
  padding: var(--space-2) 0 var(--space-8);
}

.bp-perforation {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 8px;
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    var(--paper-line) 0,
    var(--paper-line) 4px,
    transparent 4px,
    transparent 8px
  );
  opacity: 0.5;
  z-index: 2;
  pointer-events: none;
}

// --- Raw fallback ---
.bp-raw {
  padding: var(--space-4) var(--space-5);
  font-family: var(--font-mono);
  font-size: var(--fs-tiny);
  word-break: break-all;
  color: var(--navy-muted);
  background: var(--paper-soft);
  margin: 0;
}

// --- Empty state ---
.empty-state {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  max-width: 420px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__icon {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: var(--paper-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-5);

    ion-icon { font-size: 2.5rem; color: var(--teal); }
  }

  h2 { font-size: var(--fs-h2); font-weight: 600; margin: 0 0 var(--space-2); color: var(--navy); }
  p { color: var(--navy-muted); margin: 0; line-height: 1.5; }
}
````

## File: boarding-pass/src/app/result/result.page.ts
````typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
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
  justCreated = false;

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
          this.justCreated = true;
        }
        this.saved = resp.status !== 'duplicate';
        this.saving = false;
        try { Haptics.impact({ style: ImpactStyle.Medium }); } catch {}
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
````

## File: boarding-pass/src/app/trips/trips.page.html
````html
<ion-header class="glass">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-button (click)="goHome()" fill="clear">
        <ion-icon name="arrow-back"></ion-icon>
      </ion-button>
    </ion-buttons>
    <ion-title class="mono">viajes</ion-title>
    <ion-buttons slot="end">
      <ion-button (click)="pickAndUpload()" [disabled]="busy" fill="clear">
        <ion-icon name="cloud-upload-outline"></ion-icon>
      </ion-button>
    </ion-buttons>
  </ion-toolbar>
</ion-header>

<ion-content>
  <ion-refresher slot="fixed" (ionRefresh)="onRefresh($event)">
    <ion-refresher-content></ion-refresher-content>
  </ion-refresher>

  <!-- Loading skeleton -->
  <div *ngIf="loading" class="trip-list">
    <div class="trip-card pass-stub" *ngFor="let i of [1,2,3]">
      <div class="skeleton skeleton-line w-full"></div>
      <div class="skeleton skeleton-line w-60"></div>
      <div class="skeleton skeleton-line w-80"></div>
      <div class="skeleton skeleton-line w-40"></div>
    </div>
  </div>

  <!-- Empty state -->
  <div *ngIf="!loading && trips.length === 0" class="empty-state page-enter">
    <div class="empty-state__icon">
      <ion-icon name="airplane-outline"></ion-icon>
    </div>
    <h2>Sin viajes guardados</h2>
    <p>Sube archivos pdf o imágenes de tus tarjetas de embarque para crear viajes.</p>
    <ion-button class="primary-cta" (click)="pickAndUpload()" [disabled]="busy">
      <ion-icon name="cloud-upload-outline" slot="start"></ion-icon>
      {{ busy ? 'Procesando…' : 'Subir archivos' }}
    </ion-button>
  </div>

  <!-- Trip list (boarding pass stub cards) -->
  <div class="trip-list" *ngIf="!loading && trips.length">
    <div class="trip-card pass-stub page-enter" *ngFor="let trip of trips; let i = index"
         [style.animation-delay.ms]="i * 50"
         (click)="viewTrip(trip)">

      <div class="trip-card__head">
        <div class="trip-card__title-block">
          <span class="board-code board-code--md">{{ getOriginCode(trip) }}</span>
          <div class="flight-strip__line">
            <ion-icon [name]="tripModeIcon(trip)" class="trip-card__strip-icon"></ion-icon>
          </div>
          <span class="board-code board-code--md">{{ getDestCode(trip) }}</span>
        </div>
        <h3 class="trip-card__name">{{ trip.trip_name || trip.filename }}</h3>
        <span class="trip-card__date" *ngIf="tripDateRange(trip) as dr">{{ dr }}</span>
      </div>

      <div class="trip-card__chips">
        <span class="chip" *ngFor="let pass of trip.pass_data.passes.slice(0, 3)">
          <ion-icon [name]="pass.kind === 'train' ? 'train-outline' : 'airplane-outline'"></ion-icon>
          {{ pass.from || '?' }} → {{ pass.to || '?' }}
        </span>
        <span class="chip chip--muted" *ngIf="trip.pass_data.passes.length > 3">
          +{{ trip.pass_data.passes.length - 3 }}
        </span>
        <span class="chip chip--bookings" *ngIf="trip.segments?.length">
          <ion-icon name="reader-outline"></ion-icon>
          {{ trip.segments!.length }} reserva{{ trip.segments!.length > 1 ? 's' : '' }}
        </span>
      </div>

      <div class="trip-card__actions">
        <ion-button fill="clear" size="small" (click)="goToItinerary(trip); $event.stopPropagation()">
          <span>Itinerario</span>
        </ion-button>
        <ion-button fill="clear" size="small" color="medium" (click)="editTrip(trip); $event.stopPropagation()">
          <ion-icon name="create-outline" slot="icon-only"></ion-icon>
        </ion-button>
        <ion-button fill="clear" size="small" color="danger" (click)="deleteTrip(trip); $event.stopPropagation()">
          <ion-icon name="trash-outline" slot="icon-only"></ion-icon>
        </ion-button>
      </div>
    </div>
  </div>
</ion-content>

<div class="proc-overlay" *ngIf="busy">
  <div class="proc-card">
    <ion-spinner name="dots" color="primary"></ion-spinner>
    <p class="proc-card__title">Procesando tarjetas de embarque</p>
    <p class="proc-card__count" *ngIf="progress">{{ progress }}</p>
    <ion-progress-bar *ngIf="progress" [value]="0.5" color="primary" class="proc-card__bar"></ion-progress-bar>
    <ion-button fill="clear" size="small" color="medium" class="proc-card__cancel" (click)="cancel()">
      Cancelar
    </ion-button>
  </div>
</div>
````

## File: boarding-pass/src/app/result/result.page.html
````html
<ion-header class="glass">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-button (click)="goHome()" fill="clear">
        <ion-icon name="arrow-back"></ion-icon>
      </ion-button>
    </ion-buttons>
    <ion-title class="mono">{{ filename || 'resultado' }}</ion-title>
    <ion-buttons slot="end">
      <ion-button (click)="saveTrip()" [disabled]="saved || saving" fill="clear">
        <ion-icon [name]="saved ? 'checkmark-circle' : 'bookmark-outline'" slot="icon-only"></ion-icon>
      </ion-button>
      <ion-button *ngIf="saved" (click)="goToItinerary()" fill="clear" color="primary">
        <ion-icon name="calendar-outline" slot="icon-only"></ion-icon>
      </ion-button>
    </ion-buttons>
  </ion-toolbar>
</ion-header>

<ion-content>
  <div *ngIf="passes.length === 0" class="empty-state page-enter">
    <div class="empty-state__icon">
      <ion-icon name="search-outline"></ion-icon>
    </div>
    <h2>Sin billetes</h2>
    <p>No se encontraron billetes con datos completos en los archivos seleccionados.</p>
  </div>

  <div class="bill-list" *ngIf="groups.length">
    <div class="person-group page-enter" *ngFor="let grp of groups; let i = index"
         [style.animation-delay.ms]="i * 80">

      <!-- Person header (clickable accordion) -->
      <div class="person-header" (click)="toggleGroup(grp.name)">
        <div class="person-header__left">
          <ion-icon [name]="isGroupExpanded(grp.name) ? 'chevron-down-circle' : 'chevron-forward-circle'"
                    class="person-header__chevron"></ion-icon>
          <span class="person-header__name">{{ grp.name }}</span>
        </div>
        <div class="person-header__right">
          <span class="person-header__count">{{ grp.passes.length }} billete{{ grp.passes.length > 1 ? 's' : '' }}</span>
        </div>
      </div>

      <!-- Pass cards (shown when expanded) -->
      <div class="person-passes" *ngIf="isGroupExpanded(grp.name)">
        <article class="boarding-pass pass-stub"
                 *ngFor="let pass of grp.passes; let j = index"
                 [class.bp-train]="pass.kind === 'train'"
                 [class.bp-flight]="pass.kind === 'flight' || !pass.kind">
          <div *ngIf="justCreated && j === 0" class="bp-new-badge">NUEVO</div>

          <div class="bp-perforation"></div>

          <!-- Header -->
          <header class="bp-header">
            <div class="bp-header__left">
              <div class="bp-icon">
                <ion-icon [name]="pass.kind === 'train' ? 'train' : 'airplane'"
                          [class.bp-icon-train]="pass.kind === 'train'"></ion-icon>
              </div>
              <div class="bp-airline">
                <span class="bp-airline__code mono">{{ airlineLabel(pass) }}</span>
                <span class="bp-airline__name">{{ pass.kind === 'train' ? 'TREN' : (pass.airline ? airlineName(pass.airline) : 'VUELO') }}</span>
              </div>
            </div>
            <div class="bp-class">
              <span class="bp-class__label">CLASE</span>
              <span class="board-code board-code--md">{{ pass.class || '—' }}</span>
            </div>
          </header>

          <!-- Strip -->
          <div class="bp-strip">
            <ng-container *ngIf="pass.kind === 'train' && pass.train; else flightStrip">
              <div class="bp-strip__end">
                <span class="board-code board-code--xl mono">{{ pass.train }}</span>
                <span class="bp-strip__label">TREN</span>
              </div>
              <div class="bp-strip__line">
                <div class="strip-line"></div>
                <span class="bp-strip__time">{{ pass.flight_time || '—' }}</span>
              </div>
              <div class="bp-strip__end">
                <span class="board-code board-code--md mono">{{ pass.pnr || '—' }}</span>
                <span class="bp-strip__label">LOCALIZADOR</span>
              </div>
            </ng-container>
            <ng-template #flightStrip>
              <div class="bp-strip__end">
                <span class="board-code board-code--xl">{{ pass.from || '???' }}</span>
                <span class="bp-strip__label">DESDE</span>
              </div>
              <div class="bp-strip__line">
                <div class="strip-line"></div>
                <span class="bp-strip__time">{{ pass.flight_time || '—' }}</span>
              </div>
              <div class="bp-strip__end">
                <span class="board-code board-code--xl">{{ pass.to || '???' }}</span>
                <span class="bp-strip__label">HASTA</span>
              </div>
            </ng-template>
          </div>

          <!-- Info grid -->
          <div class="bp-info">
            <ng-container *ngIf="pass.kind === 'train'; else flightInfo">
              <div class="bp-info__cell">
                <span class="bp-info__label">PASAJERO</span>
                <span class="bp-info__value">{{ pass.name || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">LOCALIZADOR</span>
                <span class="bp-info__value mono">{{ pass.pnr || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">TREN</span>
                <span class="bp-info__value mono">{{ pass.train || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">FECHA</span>
                <span class="bp-info__value mono">{{ formatDate(pass) }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">HORA</span>
                <span class="bp-info__value mono">{{ pass.flight_time || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">CLASE</span>
                <span class="bp-info__value mono">{{ pass.class || '—' }}</span>
              </div>
            </ng-container>
            <ng-template #flightInfo>
              <div class="bp-info__cell">
                <span class="bp-info__label">PASAJERO</span>
                <span class="bp-info__value">{{ pass.name || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">PNR / LOCALIZADOR</span>
                <span class="bp-info__value mono">{{ pass.pnr || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">VUELO</span>
                <span class="bp-info__value mono">{{ pass.airline }}{{ pass.flight }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">FECHA</span>
                <span class="bp-info__value mono">{{ formatDate(pass) }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">HORA</span>
                <span class="bp-info__value mono">{{ pass.flight_time || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">ASIENTO</span>
                <span class="bp-info__value mono">{{ pass.seat || '—' }}</span>
              </div>
            </ng-template>
          </div>

          <!-- Barcode -->
          <div *ngIf="imageFor(pass) as img" class="bp-barcode">
            <img [src]="'data:image/png;base64,' + img.base64" alt="barcode" />
            <span class="bp-barcode__hint mono">{{ pass.format }} · {{ pass.kind === 'train' ? 'TREN' : 'VUELO' }}</span>
          </div>

          <p *ngIf="pass.sourceFile" class="bp-source mono">origen: {{ pass.sourceFile }}</p>
        </article>
      </div>
    </div>

    <div class="result-actions" *ngIf="saved && savedTripId">
      <ion-button expand="block" class="primary-cta" (click)="goToItinerary()">
        <ion-icon name="calendar-outline" slot="start"></ion-icon>
        Ver itinerario
      </ion-button>
    </div>
  </div>
</ion-content>
````

## File: boarding-pass/src/environments/environment.prod.ts
````typescript
export const environment = { production: true, apiUrl: "https://separately-cpu-tiles-move.trycloudflare.com" };
````

## File: boarding-pass/src/app/home/home.page.html
````html
<ion-header class="glass" [translucent]="true">
  <ion-toolbar>
    <ion-title></ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <div class="hero page-enter">
    <div class="hero__emblem page-enter-0">
      <ion-icon name="airplane-outline" class="hero__emblem-icon"></ion-icon>
      <div class="hero__emblem-ring"></div>
    </div>

    <h1 class="hero__title">Tu próximo<br><em>viaje</em> empieza aquí</h1>
    <p class="hero__sub">Sube tus tarjetas de embarque o billetes y organiza tu viaje al instante.</p>

    <ion-button expand="block" class="primary-cta page-enter-1" (click)="pickAndUpload()" [disabled]="busy">
      <ion-icon name="cloud-upload-outline" slot="start"></ion-icon>
      {{ busy ? 'Procesando…' : 'Crear nuevo viaje' }}
    </ion-button>

    <ion-button expand="block" fill="clear" class="btn-saved-trips page-enter-2" routerLink="/trips">
      <ion-icon name="briefcase-outline" slot="start"></ion-icon>
      Ver viajes guardados
    </ion-button>
  </div>
</ion-content>

<!-- Processing overlay -->
<div class="proc-overlay" *ngIf="busy">
  <div class="proc-card">
    <ion-spinner name="dots" color="primary"></ion-spinner>
    <p class="proc-card__title">Procesando tarjetas de embarque</p>
    <p class="proc-card__count" *ngIf="progress">{{ progress }}</p>
    <ion-progress-bar *ngIf="progress" [value]="0.5" color="primary" class="proc-card__bar"></ion-progress-bar>
    <ion-button fill="clear" size="small" color="medium" class="proc-card__cancel" (click)="cancel()">
      Cancelar
    </ion-button>
  </div>
</div>
````

## File: extraer_qr_pdfs.py
````python
"""
Extrae codigos 2D (QR, PDF417, Aztec) de cualquier PDF.
Sin nombres hardcodeados: detecta y decodifica automaticamente
lo que haya, sea imagen embebida o vector en la pagina.

Uso:
  python extraer_qr_pdfs.py tarjeta1.pdf tarjeta2.pdf ...
  python extraer_qr_pdfs.py *.pdf

Salida en ./qr_extraidos/:
  <nombre_pdf>/
    code_pN_M.png    recortes de los codigos encontrados
    qr_data.txt      datos decodificados
    qr_base64.txt    base64 para embeber en HTML
  _all_data.txt      consolidado de todos los PDFs
  _all_base64.txt    base64 consolidado

Dependencias:
  pip install pymupdf pillow zxing-cpp
"""

import base64
import io
import os
import re
import sys
import re
import sys

import fitz
from PIL import Image


# Resolucion del rasterizado de fallback. 300 DPI = buen balance para
# PDF417 / Aztec / QR en PDFs reales.
RENDER_DPI = 300

# Margen en pixeles alrededor del bounding box detectado al recortar.
CROP_PADDING = 20

# Formatos 2D que decodificamos. Anade o quita segun necesites.
SUPPORTED_FORMATS = (
    "QRCode",
    "PDF417",
    "Aztec",
)

# Patrones de codigos que NO nos interesan (publicidad propia del operador).
# Ejemplos: Renfe Tiempo Real (https://tiempo-real.largorecorrido.renfe.com/),
# OUIGO (https://qrco.de/...). Anade aqui mas si encuentras otros.
SKIP_PATTERNS = (
    re.compile(r"^https?://", re.IGNORECASE),
)


def _should_skip(text):
    return any(p.match(text) for p in SKIP_PATTERNS)


def _decode(pil_image):
    """Devuelve la lista de hits (zxingcpp.Barcode) que zxing-cpp encuentra
    en una imagen PIL, probando los formatos dados y rotaciones / inversiones."""
    import zxingcpp
    fmt = [getattr(zxingcpp.BarcodeFormat, name) for name in SUPPORTED_FORMATS]
    return zxingcpp.read_barcodes(
        pil_image,
        formats=fmt,
        try_rotate=True,
        try_invert=True,
    )


def _save_png(pil_image, out_dir, fname):
    """Guarda una imagen PIL como PNG y devuelve (bytes_png, base64_str)."""
    path = os.path.join(out_dir, fname)
    pil_image.save(path, "PNG")
    with open(path, "rb") as f:
        png_bytes = f.read()
    return png_bytes, base64.b64encode(png_bytes).decode()


def _crop_to_hit(page_img, hit):
    """Recorta el bounding box del codigo detectado en la imagen de pagina."""
    pos = hit.position
    xs = [pos.top_left.x, pos.top_right.x, pos.bottom_right.x, pos.bottom_left.x]
    ys = [pos.top_left.y, pos.top_right.y, pos.bottom_right.y, pos.bottom_left.y]
    return page_img.crop((
        max(int(min(xs)) - CROP_PADDING, 0),
        max(int(min(ys)) - CROP_PADDING, 0),
        min(int(max(xs)) + CROP_PADDING, page_img.width),
        min(int(max(ys)) + CROP_PADDING, page_img.height),
    ))


def extract_codes(pdf_path, out_dir):
    """Extrae todos los codigos 2D de un PDF.

    Estrategia, en orden, y si ambos paths detectan el mismo codigo
    gana el RENDERIZADO (mayor resolucion):
      1. Imagenes embebidas en cada pagina  (rapido, no rasteriza)
      2. Rasterizado de la pagina a RENDER_DPI  (cubre codigos en vector
         y ademas aporta la version en alta resolucion del mismo codigo)

    Devuelve una lista de tuplas:
        (page_num, fname, b64, texto, formato, origen)
    donde origen es "embedded" o "rendered".
    """
    doc = fitz.open(pdf_path)
    # Extraer campos de texto del PDF (origen, destino, plaza, etc.)
    # Se hace aqui mismo para evitar abrir el PDF dos veces (fitz falla
    # con rutas 8.3 / caracteres especiales en Windows al reabrir).
    text_fields = _extract_text_fields_from_doc(doc)

    # Dict para que la version rendered pueda SUSTITUIR a la embedded
    # cuando ambas detectan el mismo codigo (mismo page/format/text).
    results = {}  # (page_num, format_name, text) -> result_tuple
    counter = {}  # (page_num) -> siguiente idx de filename

    def _next_idx(page_num):
        counter[page_num] = counter.get(page_num, 0) + 1
        return counter[page_num]

    def _save_entry(page_num, pil_img, hit, origin):
        idx = _next_idx(page_num)
        fname = f"code_p{page_num}_{idx}.png"
        _, b64 = _save_png(pil_img, out_dir, fname)
        return (page_num, fname, b64, hit.text, hit.format.name, origin)

    for page_num in range(doc.page_count):
        page_num_1based = page_num + 1
        page = doc[page_num]

        # --- 1. Imagenes embebidas ----------------------------------------
        for img_meta in page.get_images(full=True):
            try:
                info = doc.extract_image(img_meta[0])
                pil_img = Image.open(io.BytesIO(info["image"]))
            except Exception:
                continue
            for hit in _decode(pil_img):
                if not hit.text:
                    continue
                if _should_skip(hit.text):
                    print(
                        f"  P{page_num_1based} skipped  "
                        f"[{hit.format.name:<7}]  {hit.text[:60]}  "
                        f"(advertising)"
                    )
                    continue
                key = (page_num_1based, hit.format.name, hit.text)
                if key in results:
                    continue
                results[key] = _save_entry(page_num_1based, pil_img, hit, "embedded")
                print(
                    f"  P{page_num_1based} embedded  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}"
                )

        # --- 2. Rasterizado de la pagina (cubre vector + mejora resol.) ---
        pix = page.get_pixmap(dpi=RENDER_DPI)
        page_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        for hit in _decode(page_img):
            if not hit.text:
                continue
            if _should_skip(hit.text):
                # El path rendered tambien puede re-detectar codigos
                # publicitarios que ya habiamos saltado arriba; lo
                # silenciamos para no duplicar el mensaje.
                continue
            key = (page_num_1based, hit.format.name, hit.text)
            if key in results:
                # Ya tenemos una version embedded: la descartamos y
                # nos quedamos con la renderizada (mas nitida y bien recortada).
                old_fname = results[key][1]
                old_path = os.path.join(out_dir, old_fname)
                try:
                    os.remove(old_path)
                except OSError:
                    pass
                print(
                    f"  P{page_num_1based} upgrade  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}  "
                    f"(embedded -> rendered)"
                )
            else:
                print(
                    f"  P{page_num_1based} rendered  "
                    f"[{hit.format.name:<7}]  {hit.text[:90]}"
                )
            crop = _crop_to_hit(page_img, hit)
            results[key] = _save_entry(page_num_1based, crop, hit, "rendered")

    # --- 3. Dedup post-extraccion: Renfe y otros tienen el mismo ticket
    # en QR (compacto, mal decodificado) y en Aztec (completo). Aqui
    # parseamos cada resultado y eliminamos los duplicados quedandonos
    # con el que tenga mas datos. Solo si la extraccion devolvio
    # algo que se pueda parsear.
    try:
        # El parser esta en backend/; anyadimos al path si no esta
        import sys as _sys
        _HERE = os.path.dirname(os.path.abspath(__file__))
        _BACKEND = os.path.join(_HERE, "backend")
        if os.path.isdir(_BACKEND) and _BACKEND not in _sys.path:
            _sys.path.insert(0, _BACKEND)
        from parser import parse_code
        # Agrupar por (pagina, identificador-de-ticket)
        groups: dict[tuple, list[tuple]] = {}
        for tup in results.values():
            page, fname, b64, text, fmt, origin = tup
            parsed = parse_code(text)
            if not parsed:
                continue
            # Identificador unico del ticket segun el formato
            # NO usamos la fecha porque en QR compacto sale mal; usamos
            # solo (page, tipo, codigo) y descartamos por texto mas largo.
            if parsed.get("kind") == "train":
                tid = ("train", parsed.get("train"), parsed.get("pnr"))
            elif parsed.get("airline"):
                tid = ("flight", parsed.get("airline"), parsed.get("flight"))
            else:
                continue
            groups.setdefault((page,) + tid, []).append(tup)
        print(f"  [dedup] {len(groups)} grupos unicos")

        # Para cada grupo, conservar el que tenga el texto mas largo
        # (mas datos = barcode completo vs compacto) y borrar el resto
        total_dropped = 0
        for key, tups in groups.items():
            if len(tups) <= 1:
                continue
            # Ordenar por longitud de texto descendente
            tups.sort(key=lambda t: len(t[3]), reverse=True)
            keep = tups[0]
            for drop in tups[1:]:
                # Encontrar y borrar la entrada con este filename
                for k in list(results.keys()):
                    if results[k] is drop:
                        del results[k]
                        # Borrar el archivo PNG
                        drop_path = os.path.join(out_dir, drop[1])
                        try:
                            os.remove(drop_path)
                        except OSError:
                            pass
                        total_dropped += 1
                        break
            print(f"  [dedup] p{keep[0]} {key}: kept {keep[1]} (len={len(keep[3])}), dropped {len(tups)-1}")
        if total_dropped:
            print(f"  [dedup] total dropped: {total_dropped}")
    except ImportError as e:
        print(f"  [dedup] Error import: {e}")
    except Exception as e:
        import traceback
        print(f"  [dedup] Error: {e}")
        traceback.print_exc()

    doc.close()
    # Devolvemos (codes, text_fields). codes mantiene la forma antigua
    # para no romper compatibilidad.
    return list(results.values()), text_fields


def _extract_text_fields_from_doc(doc):
    """Extrae campos de texto de un fitz.Document ya abierto.

    Devuelve dict {page_num_1based: {from, to, seat, coach, name}}.
    Funcion auxiliar: separada para poder llamarla con un doc compartido.
    """
    fields_by_page = {}
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text()
        page_fields = {}

        # Origen (ciudad o estacion, texto corto)
        m = re.search(r"(?:Origen|Desde|Salida\s+de)\s*:?\s*\n?\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if not m:
            m = re.search(r"Origen\s*\n\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Filtrar falsos positivos: texto demasiado generico
            if not any(w in val.lower() for w in ('minutos','antes','salida','llegada','añadir','puedes','información','billete','tarjeta')):
                page_fields["from"] = val

        # Destino (ciudad o estacion, texto corto)
        m = re.search(r"(?:Destino|Hasta|Llegada\s+a)\s*:?\s*\n?\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if not m:
            m = re.search(r"Destino\s*\n\s*(\S[\S ]{0,40})", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not any(w in val.lower() for w in ('minutos','antes','salida','llegada','añadir','puedes','información','billete','tarjeta')):
                page_fields["to"] = val

        # Plaza / Asiento: patron de asiento real (digitos+letra, ej: "14A", "23B")
        m = re.search(r"(?:Plaza|Asiento|Coche)\s*:?\s*\n?\s*(\d{1,2}\s*[A-Z])", text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?:Plaza|Asiento)\s*:?\s*\n?\s*(\S+)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if len(val) <= 6 and not val.lower() in ('información','importante','billete'):
                page_fields["seat"] = val

        # Coche
        m = re.search(r"Coche:\s*\n?\s*(\S+)", text, re.IGNORECASE)
        if m:
            page_fields["coach"] = m.group(1).strip()

        # Fecha con año (formato DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD,
        # o DD MES YYYY como "06 DIC 2026" / "06 December 2026")
        date_match = re.search(
            r"(\d{2})[\s/-](\d{2}|[A-Za-z]{3,})[\s/-](\d{4})",
            text,
        )
        if date_match:
            d, m, y = date_match.group(1), date_match.group(2), date_match.group(3)
            # Si el mes es texto, convertir a número
            month_map = {
                "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05",
                "jun": "06", "jul": "07", "ago": "08", "sep": "09", "oct": "10",
                "nov": "11", "dic": "12",
                "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05",
                "jun": "06", "jul": "07", "aug": "08", "sep": "09", "oct": "10",
                "nov": "11", "dec": "12",
            }
            if m.lower()[:3] in month_map:
                m = month_map[m.lower()[:3]]
            try:
                from datetime import date as dt_date
                dt_date(int(y), int(m), int(d))
                page_fields["flight_date"] = f"{y}-{int(m):02d}-{int(d):02d}"
            except (ValueError, TypeError):
                pass

        # Nombre del pasajero (varios formatos segun operador)
        m = None
        # 1) Etiqueta + formato APELLIDO/NOMBRE o Nombre Apellido
        for pat in [
            r"(?:Pasajero|Titular|Nombre|Viajero|Viajero\s+General)\s*:?\s*\n?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s/]{3,40})",
            r"DNI\s*[óo]?\s*DOC\.?ID:?\s*\n\s*\*+\S+\s*\n\s*(\S+)",
            r"S(?:r|ra)\.\s+(\S[\S ]+)",
            # OUIGO: nombre en formato "Nombre Apellido" en linea propia
            r"\n([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\n",
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                break
        if m:
            val = m.group(1).strip()
            if '/' in val or (' ' in val and len(val) >= 6) or len(val) >= 4:
                # Evitar falsos positivos
                if not any(w in val.lower() for w in ('minutos','antes','salida','mascotas','olvides','equipaje','billete','ouigo')):
                    page_fields["name"] = val

        # OUIGO: origen/destino en formato "Ciudad - Estacion" (lineas propias)
        if not page_fields.get("from") or not page_fields.get("to"):
            ouigo_cities = re.findall(
                r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ - .+)$",
                text, re.MULTILINE,
            )
            real = [c.strip() for c in ouigo_cities if len(c.strip()) > 8]
            if len(real) >= 2:
                page_fields["from"] = real[0]
                page_fields["to"] = real[-1]

        # OUIGO: nombre (antes de "Viajero General")
        if not page_fields.get("name"):
            m = re.search(
                r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\s*\n\s*Viajero General",
                text,
            )
            if m:
                page_fields["name"] = m.group(1).strip()

        # OUIGO: tren (5 digitos tras la fecha)
        m = re.search(r"\d{2}\.\d{2}\.\d{4}\s*\n\s*(\d{5})", text)
        if m:
            page_fields["train"] = m.group(1)

        # OUIGO: coche (digito tras la hora)
        m = re.search(r"\d{2}:\d{2}\s*\n\s*(\d)\s*\n", text)
        if m:
            page_fields["coach"] = m.group(1)

        # OUIGO: fecha en formato DD.MM.YYYY
        if not page_fields.get("flight_date"):
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
            if m:
                d, mo, y = m.group(1), m.group(2), m.group(3)
                page_fields["flight_date"] = f"{y}-{mo}-{d}"

        # OUIGO: localizador (6 caracteres alfanumericos en linea propia)
        if not page_fields.get("pnr"):
            m = re.search(r"\n([A-Z0-9]{6})\n", text)
            if m and m.group(1) not in ('ALTURA','OUIGO','VENTA'):
                page_fields["pnr"] = m.group(1)

        # Operador: Renfe / Iryo / OUIGO (buscar en orden de especificidad)
        op_match = re.search(r"\b(?:IRYO|iryo|Iryo|OUIGO|Ouigo|ouigo)\b", text)
        if op_match:
            page_fields["operator"] = op_match.group(0).upper()
        elif re.search(r"\bRenfe\b", text, re.IGNORECASE):
            page_fields["operator"] = "RENFE"

        # Hora de salida (varios formatos segun aerolinea)
        # Ryanair: "Departs", "Departure", "Salida"
        # Vueling: "Salida", "Hora", "Departure"
        # Iberia: "Salida", "Hora"
        time_patterns = [
            r"(?:Hora de salida|Hora salida|Salida|Departs|Departure|Hora)[:\s]*\n?\s*(\d{1,2}[:.]\d{2})",
            r"(?:Salida|Hora)[:\s]*\n?\s*(\d{1,2}[:.]\d{2})",
            r"(\d{1,2}[:.]\d{2})\s*(?:Hora de salida|Salida|Departs)",
        ]
        for pat in time_patterns:
            tm = re.search(pat, text, re.IGNORECASE)
            if tm:
                raw_time = tm.group(1).replace(".", ":")
                h, mn = raw_time.split(":")
                page_fields["flight_time"] = f"{int(h):02d}:{int(mn):02d}"
                break

        if page_fields:
            fields_by_page[page_num + 1] = page_fields

    return fields_by_page


def extract_text_fields(pdf_path):
    """Extrae campos de texto del PDF: origen, destino, plaza, coche, nombre.

    Util para Renfe/OUIGO que no llevan esos datos en el codigo de barras.
    Acepta una ruta de archivo o un objeto fitz.Document ya abierto.
    Devuelve un dict {page_num_1based: {from, to, seat, coach, name}}.
    """
    if isinstance(pdf_path, fitz.Document):
        return _extract_text_fields_from_doc(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        import sys as _sys
        print(f"[extract_text_fields] Error abriendo PDF: {e}", file=_sys.stderr, flush=True)
        return {}
    result = _extract_text_fields_from_doc(doc)
    doc.close()
    return result


def extract_codes_from_image(image_path, out_dir):
    """Extrae todos los codigos 2D de una imagen (screenshot, foto, etc.).

    Soporta PNG, JPG, WebP, BMP, TIFF y cualquier formato que PIL pueda abrir.

    Devuelve el mismo formato que extract_codes():
        [(page_num, fname, b64, texto, formato, origen)]
    donde page_num es siempre 1 y origen es "screenshot".
    """
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  Error abriendo imagen: {e}")
        return []

    results = []
    seen = set()
    counter = 0

    for hit in _decode(pil_img):
        if not hit.text:
            continue
        if _should_skip(hit.text):
            print(
                f"  skipped  [{hit.format.name:<7}]  {hit.text[:60]}  "
                f"(advertising)"
            )
            continue
        key = (hit.format.name, hit.text)
        if key in seen:
            continue
        seen.add(key)

        counter += 1
        fname = f"code_p1_{counter}.png"
        crop = _crop_to_hit(pil_img, hit)
        _, b64 = _save_png(crop, out_dir, fname)

        print(
            f"  [{hit.format.name:<7}]  {hit.text[:90]}"
        )
        results.append((1, fname, b64, hit.text, hit.format.name, "screenshot"))

    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdfs = sys.argv[1:]
    # Carpeta de salida junto al primer PDF. Cada PDF va a su propia
    # subcarpeta para que los nombres de archivo no se pisen entre PDFs.
    base_dir = os.path.join(os.path.dirname(os.path.abspath(pdfs[0])), "qr_extraidos")
    os.makedirs(base_dir, exist_ok=True)

    consolidated_data = []
    consolidated_b64 = []

    for pdf in pdfs:
        print(f"\n{'=' * 64}")
        print(f"Procesando: {os.path.basename(pdf)}")
        print(f"{'=' * 64}")

        # Subcarpeta = nombre del PDF sin extension, saneado.
        stem = os.path.splitext(os.path.basename(pdf))[0]
        sub = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
        out_dir = os.path.join(base_dir, sub)
        os.makedirs(out_dir, exist_ok=True)

        res = extract_codes(pdf, out_dir)
        if not res:
            print(f"  (sin codigos)")
            continue

        # Ficheros por PDF (facil de navegar).
        with open(os.path.join(out_dir, "qr_data.txt"), "w", encoding="utf-8") as f:
            f.write(
                "\n".join(f"  P{page} [{fmt}]: {text}" for page, _, _, text, fmt, _ in res)
            )
        with open(os.path.join(out_dir, "qr_base64.txt"), "w", encoding="utf-8") as f:
            for page, fname, b64, _text, _fmt, _origin in res:
                stem_png = os.path.splitext(fname)[0]
                f.write(f"  {stem_png} = data:image/png;base64,{b64}\n")

        # Y ademas un consolidado a nivel raiz para vision global.
        consolidated_data.append(f"\n=== {os.path.basename(pdf)} ===")
        for page, _fn, _b64, text, fmt, _origin in res:
            consolidated_data.append(f"  P{page} [{fmt}]: {text}")
        consolidated_b64.append(f"\n=== {os.path.basename(pdf)} ===")
        for page, fname, b64, _text, _fmt, _origin in res:
            stem_png = f"{sub}/{os.path.splitext(fname)[0]}"
            consolidated_b64.append(f"  {stem_png} = data:image/png;base64,{b64}\n")

    with open(os.path.join(base_dir, "_all_data.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(consolidated_data))
    with open(os.path.join(base_dir, "_all_base64.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(consolidated_b64))

    print(f"\nListo. {len(pdfs)} PDF(s) -> {base_dir}/")


if __name__ == "__main__":
    main()
````

## File: boarding-pass/src/app/services/boarding-pass.service.ts
````typescript
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Pass {
  page: number;
  format: string;
  kind?: string;
  name?: string | null;
  pnr?: string | null;
  from?: string;
  to?: string;
  airline?: string;
  flight?: string;
  flight_date?: string | null;
  flight_time?: string | null;
  gate_close_time?: string | null;
  train?: string;
  class?: string;
  seat?: string;
  check_in_seq?: string;
  origin?: string;
  raw?: string;
  sourceFile?: string;
  has_explicit_year?: boolean;
}

export interface BarcodeImage {
  page: number;
  format: string;
  filename: string;
  base64: string;
}

export interface ExtractResponse {
  filename: string;
  passes: Pass[];
  images: BarcodeImage[];
  count: number;
}

export interface Trip {
  id: number;
  session_id: string;
  filename: string;
  trip_name?: string;
  pass_data: { passes: Pass[]; images: BarcodeImage[] };
  segments?: TravelSegment[];
  created_at: string;
  updated_at?: string;
}

export interface TravelSegment {
  type: 'flight' | 'train' | 'hotel' | 'car' | 'restaurant' | 'activity';
  // Flight / Train
  airline?: string;
  operator?: string;
  flight_number?: string;
  train_number?: string;
  from?: string;
  to?: string;
  // Hotel
  name?: string;
  city?: string;
  check_in?: string;
  check_out?: string;
  // Car
  company?: string;
  pickup_date?: string;
  return_date?: string;
  // Restaurant
  // name + city + date + time (reuses above)
  // Activity
  description?: string;
  date?: string;
  time?: string;
}

export interface TripListResponse {
  trips: Trip[];
  session_id: string;
}

export interface SaveTripResponse {
  status: 'created' | 'updated' | 'duplicate';
  id: number;
  session_id: string;
  filename: string;
  trip_name?: string;
  message: string;
}

const SESSION_KEY = 'bp_session_id';

@Injectable({ providedIn: 'root' })
export class BoardingPassService {
  constructor(private http: HttpClient) {}

  private _headers(extra?: Record<string, string>): { headers: HttpHeaders } {
    let h = new HttpHeaders(extra || {});
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return { headers: h };
  }

  // --- PDF extraction ---

  uploadPdf(blob: Blob, filename?: string): Observable<ExtractResponse> {
    const fd = new FormData();
    fd.append('file', blob, (filename as string) || 'file');
    return this.http.post<ExtractResponse>(
      `${environment.apiUrl}/api/extract`, fd, this._headers()
    );
  }

  // --- Trips CRUD ---

  /** Obtiene o crea el session_id persistente en localStorage. */
  getSessionId(): string {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = 'ses_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  private sessionHeaders(): { headers: HttpHeaders } {
    let h = new HttpHeaders({ 'X-Session-Id': this.getSessionId() });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return { headers: h };
  }

  /** Lista todos los viajes de la sesion actual. */
  getTrips(): Observable<TripListResponse> {
    return this.http.get<TripListResponse>(
      `${environment.apiUrl}/api/trips`,
      this.sessionHeaders(),
    );
  }

  /** Guarda un viaje tras la extraccion. */
  saveTrip(filename: string, passes: Pass[], images: BarcodeImage[], tripName?: string, segments?: TravelSegment[]): Observable<SaveTripResponse> {
    let h = new HttpHeaders({
      'Content-Type': 'application/json; charset=utf-8',
      'X-Session-Id': this.getSessionId(),
    });
    if (environment.apiUrl.includes('loca.lt')) {
      h = h.set('Bypass-Tunnel-Reminder', 'true');
    }
    return this.http.post<SaveTripResponse>(
      `${environment.apiUrl}/api/trips`,
      { filename, passes, images, trip_name: tripName || '', segments: segments || [] },
      { headers: h },
    );
  }

  /** Actualiza los segmentos manuales de un viaje. */
  updateSegments(tripId: number, segments: TravelSegment[]): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(
      `${environment.apiUrl}/api/trips/${tripId}/segments`,
      { segments },
      this.sessionHeaders(),
    );
  }

  /** Borra un viaje por ID. */
  deleteTrip(id: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(
      `${environment.apiUrl}/api/trips/${id}`,
      this.sessionHeaders(),
    );
  }
}
````

## File: boarding-pass/src/app/itinerary/itinerary.page.scss
````scss
// --- State containers ---
.state-container {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  max-width: 420px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;

  ion-icon { font-size: 3rem; color: var(--teal); margin-bottom: var(--space-3); }
  h2 { font-size: var(--fs-h2); font-weight: 600; margin: 0 0 var(--space-2); color: var(--navy); }
  p { color: var(--navy-muted); margin: 0 0 var(--space-4); line-height: 1.5; }

  &.error ion-icon { color: var(--coral); }
}

// --- Editorial hero ---
.hero {
  padding: var(--space-6) var(--space-5);
  background:
    radial-gradient(ellipse at 50% 100%, rgba(13, 115, 119, 0.08) 0%, transparent 60%),
    var(--paper);
  color: var(--navy);
  text-align: center;
  position: relative;
  z-index: 1;
  border-bottom: 1px solid var(--paper-line);

  &__strip {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
    opacity: 0.6;
    .flight-strip__line { flex: 1; }
  }

  &__destinations {
    display: flex;
    justify-content: center;
    gap: var(--space-2);
    flex-wrap: wrap;
    margin-bottom: var(--space-3);

    ion-chip {
      font-size: var(--fs-small);
      font-weight: 600;
      height: auto;
      padding: 6px 14px;
      margin: 0;
      border-radius: 20px;
      --background: var(--teal-soft);
      --color: var(--teal);
      border: none;
      letter-spacing: 0;
      text-transform: none;
    }
  }

  &__overview {
    font-size: var(--fs-body);
    line-height: 1.6;
    color: var(--navy-soft);
    max-width: 600px;
    margin: 0 auto;
    font-style: italic;
  }
}

// --- Section ---
.section {
  padding: var(--space-4) var(--space-3) var(--space-8);
  max-width: 720px;
  margin: 0 auto;
  position: relative;
  z-index: 1;

  &__title {
    font-size: var(--fs-tiny);
    font-weight: 600;
    margin: 0 0 var(--space-3);
    display: flex;
    align-items: center;
    gap: var(--space-2);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--navy-muted);

    ion-icon { font-size: 1rem; }
  }

  &__weather-summary {
    color: var(--navy-soft);
    font-size: var(--fs-body);
    margin-bottom: var(--space-4);
    line-height: 1.5;
    font-style: italic;
  }
}

// --- Weather strip ---
.weather-grid {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding: 0 var(--space-1) var(--space-2);
  -webkit-overflow-scrolling: touch;
  scroll-snap-type: x mandatory;

  > * { scroll-snap-align: start; }
}

.weather-card {
  flex: 0 0 auto;
  min-width: 100px;
  text-align: center;
  background: var(--paper-soft);
  border-radius: var(--radius);
  padding: var(--space-3) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--paper-line);

  &__date {
    font-size: var(--fs-tiny);
    color: var(--navy-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  &__icon { font-size: var(--fs-body); margin: 2px 0; }

  &__temps {
    display: flex;
    justify-content: center;
    gap: var(--space-2);
    font-size: var(--fs-body);

    .max { font-weight: 700; color: var(--coral); }
    .min { color: var(--teal); font-weight: 500; }
  }
}

// --- Tabs ---
.tabs {
  margin: 0;
  padding: 0 var(--space-2);
  --background: transparent;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--glass-line);

  ion-segment-button {
    --indicator-color: var(--teal);
    --color: var(--navy-muted);
    --color-checked: var(--teal);
    --padding-start: var(--space-3);
    --padding-end: var(--space-3);
    min-width: auto;
    flex: 0 0 auto;
    text-transform: none;
    letter-spacing: 0;
    font-weight: 500;
    font-size: var(--fs-small);

    ion-icon { font-size: 1.1rem; margin-bottom: 2px; }
    ion-label { font-size: var(--fs-tiny); font-weight: 500; }
  }
}

// --- Day cards (timeline) ---
.day-card {
  margin-bottom: var(--space-4);
  background: var(--paper);
  border-radius: var(--radius);
  padding: var(--space-4) var(--space-5);
  box-shadow: var(--shadow-1);
  border: 1px solid var(--paper-line);
  position: relative;
  z-index: 1;

  &__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
    padding-bottom: var(--space-3);
    border-bottom: 1px dashed var(--paper-line);
  }

  &__day-label {
    font-size: var(--fs-tiny);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--navy-muted);
    font-weight: 600;
  }

  &__date {
    font-family: var(--font-mono);
    font-size: var(--fs-tiny);
    color: var(--navy-soft);
    font-weight: 500;
  }

  &__theme {
    font-size: var(--fs-h3);
    font-weight: 600;
    color: var(--navy);
    margin: 0 0 var(--space-4);
    letter-spacing: -0.01em;
  }

  &__slot {
    display: flex;
    gap: var(--space-3);
    margin-bottom: var(--space-3);
    align-items: flex-start;

    ion-icon {
      font-size: 1.25rem;
      margin-top: 2px;
      flex-shrink: 0;
      padding: 4px;
      background: var(--paper-soft);
      border-radius: 6px;
    }

    strong {
      display: block;
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      color: var(--navy-muted);
      font-weight: 600;
      margin-bottom: 2px;
    }
    p { margin: 0; font-size: var(--fs-body); line-height: 1.4; color: var(--navy-soft); }
  }

  &__meal {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-3);
    padding-top: var(--space-3);
    border-top: 1px dashed var(--paper-line);
    font-size: var(--fs-small);
    color: var(--teal);

    ion-icon { flex-shrink: 0; margin-top: 2px; }
    div { display: flex; flex-direction: column; gap: var(--space-1); width: 100%; }
    strong { color: var(--navy-muted); font-weight: 500; }
  }

  &__activities {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-top: var(--space-2);

    ion-chip {
      font-size: var(--fs-small);
      height: auto;
      padding: 6px 14px;
      margin: 0;
      --background: var(--teal-soft);
      --color: var(--teal);
      border: none;
      text-transform: none;
      letter-spacing: 0;
      font-weight: 600;
      border-radius: 20px;
    }
  }

  &__weather {
    margin-top: var(--space-3);
    padding-top: var(--space-3);
    border-top: 1px dashed var(--paper-line);
    font-size: var(--fs-tiny);
    color: var(--navy-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
}

// --- Recommendation cards ---
.rec-card {
  margin-bottom: var(--space-3);
  background: var(--paper);
  border-radius: var(--radius);
  padding: var(--space-4);
  box-shadow: var(--shadow-1);
  border: 1px solid var(--paper-line);
  position: relative;
  z-index: 1;

  ion-chip {
    font-size: var(--fs-small);
    font-weight: 600;
    height: auto;
    padding: 6px 14px;
    margin: 0;
    border-radius: 20px;
    --background: var(--teal-soft);
    --color: var(--teal);
    border: none;
  }

  .card-chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-top: var(--space-3);
  }

  // highlight for historical sites
  .curiosity {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-3);
    padding: var(--space-3);
    background: var(--amber-soft);
    border-radius: var(--radius-sm);
    font-size: var(--fs-small);
    font-style: italic;
    color: var(--navy);

    ion-icon { color: var(--amber); flex-shrink: 0; margin-top: 1px; }
  }

  .tips-list {
    margin: var(--space-2) 0 0;
    padding-left: var(--space-5);
    font-size: var(--fs-small);

    li {
      margin-bottom: var(--space-1);
      color: var(--navy-soft);
    }
  }

  &.historical {
    border-left: 3px solid var(--amber);
  }
}

// --- Tips ---
.tips-card {
  margin-bottom: var(--space-3);
  background: var(--paper);
  border-radius: var(--radius);
  padding: var(--space-4);
  box-shadow: var(--shadow-1);
  border: 1px solid var(--paper-line);
  position: relative;
  z-index: 1;

  .tips-list {
    padding-left: var(--space-5);
    font-size: var(--fs-body);
    line-height: 1.6;
    color: var(--navy-soft);

    li { margin-bottom: var(--space-2); }
  }
}

// --- Pass card (tarjetas tab) ---
.pass-card {
  margin-bottom: var(--space-3);
  background: var(--paper);
  border-radius: var(--radius);
  padding: var(--space-4);
  box-shadow: var(--shadow-1);
  border: 1px solid var(--paper-line);
  position: relative;
  z-index: 1;
}

.source-file {
  display: inline-block;
  background: var(--teal-soft);
  color: var(--teal);
  font-size: var(--fs-tiny);
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: var(--space-2);
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

// --- Segments list (reservas tab) ---
.summary-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.summary-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--paper);
  border-radius: var(--radius);
  font-size: var(--fs-body);
  border: 1px solid var(--paper-line);
  position: relative;
  z-index: 1;

  ion-icon { font-size: 1.2rem; flex-shrink: 0; color: var(--teal); }

  ion-badge {
    font-size: var(--fs-small);
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 20px;
    --background: var(--teal-soft);
    --color: var(--teal);
  }
}

.summary-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--navy);
  font-weight: 500;
}

.edit-segments-btn {
  margin-top: var(--space-2);
  --border-radius: 12px;
}

.empty-tab {
  text-align: center;
  padding: var(--space-10) var(--space-4);
  color: var(--navy-muted);
  font-size: var(--fs-body);
  font-style: italic;
}

// --- Barcode (boarding pass) ---
.bp-barcode {
  background: var(--paper-soft);
  padding: var(--space-4) var(--space-5);
  text-align: center;
  border-top: 1px dashed var(--paper-line);
  position: relative;
  z-index: 1;

  img {
    max-width: 220px;
    margin: 0 auto;
    display: block;
    background: white;
    padding: 8px;
    border-radius: 4px;
  }
}
.bp-barcode__hint {
  display: block;
  margin-top: var(--space-2);
  font-size: 9px;
  letter-spacing: 0.15em;
  color: var(--navy-muted);
  text-transform: uppercase;
}

// --- Boarding pass stub (tarjetas) ---
// Header redesign: ruta (origen → destino) como protagonista, lo demás abajo
.bp-header {
  padding: var(--space-5) var(--space-5) var(--space-4);
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
  color: var(--paper);
  position: relative;
  z-index: 1;
  text-align: center;
}

.bp-route-hero {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);

  &__side {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 0;

    &--dest {
      .bp-route-hero__label { color: var(--teal-light); }
    }
  }

  &__code {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--paper);
    line-height: 1;
  }

  &__label {
    font-size: 8px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    opacity: 0.5;
    margin-top: 2px;
  }

  &__connector {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 0 0 auto;
    padding: 0 var(--space-1);
  }

  &__line {
    display: block;
    width: 24px;
    height: 1px;
    background: rgba(255, 255, 255, 0.25);
  }

  &__plane {
    font-size: 1.1rem;
    color: var(--teal-light);
    flex-shrink: 0;
  }

  &__train-icon {
    font-size: 1.1rem;
    color: var(--teal-light);
    flex-shrink: 0;
  }
}

// Train variant: stacked (origin above, destination below) so long station names don't overlap
.bp-route-hero--train {
  flex-direction: column;
  gap: var(--space-1);

  .bp-route-hero__connector {
    width: 100%;
    padding: var(--space-1) 0;
    justify-content: center;
  }

  .bp-route-hero__side {
    width: 100%;
  }

  .bp-route-hero__code {
    font-size: 1.25rem;
    max-width: 100%;
    line-height: 1.3;
    overflow-wrap: break-word;
    word-break: break-word;
  }

  .bp-route-hero__label {
    margin-top: 0;
  }
}

.bp-header__meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  font-size: var(--fs-small);
  opacity: 0.7;
  flex-wrap: wrap;

  .bp-header__airline {
    font-weight: 600;
    color: var(--paper);
  }

  .bp-header__divider {
    opacity: 0.4;
  }

  .bp-header__flight,
  .bp-header__date {
    font-size: var(--fs-small);
  }
}

// --- Info grid ---
.bp-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3) var(--space-4);
  padding: var(--space-4) var(--space-5) var(--space-5);
  position: relative;
  z-index: 1;
}

.bp-info__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.bp-info__label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--navy-muted);
  font-weight: 500;
}
.bp-info__value {
  font-size: var(--fs-body);
  color: var(--navy);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bp-info__sub {
  font-size: var(--fs-small);
  color: var(--navy-soft);
  font-weight: 400;
}

// Pasajero ocupa fila completa y permite wrap (no trunca nombres largos)
.bp-info__cell--wide {
  grid-column: 1 / -1;
  .bp-info__value {
    white-space: normal;
    word-break: break-word;
    text-overflow: clip;
  }
}



// --- Accordion group styles (same as result page) ---
.bill-list {
  padding: var(--space-3) var(--space-1) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 720px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.person-group {
  background: var(--paper);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.person-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  cursor: pointer;
  user-select: none;
  background: var(--paper);
  transition: background 0.15s ease;

  &:hover {
    background: var(--paper-soft);
  }

  &__left {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-width: 0;
    flex: 1;
  }

  &__chevron {
    font-size: 1.5rem;
    color: var(--teal);
    flex-shrink: 0;
    transition: transform 0.2s ease;
  }

  &__name {
    font-size: var(--fs-h3, 1.1rem);
    font-weight: 600;
    color: var(--navy);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__right {
    flex-shrink: 0;
    margin-left: var(--space-3);
  }

  &__count {
    font-size: var(--fs-tiny);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--navy-muted);
    font-weight: 500;
  }
}

.person-passes {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 0 var(--space-3) var(--space-3);
}

// --- Static header (single passenger, no accordion) ---
.person-header--static {
  cursor: default;

  &:hover {
    background: var(--paper);
  }

  .person-header__chevron {
    display: none;
  }
}

// --- QR barcode enlargement overlay ---
.bp-barcode__img {
  cursor: pointer;
  transition: opacity 0.15s ease;

  &:active {
    opacity: 0.7;
  }
}

.qr-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  animation: qrFadeIn 0.2s ease;

  &__content {
    position: relative;
    max-width: 90vw;
    max-height: 90vh;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      max-width: 100%;
      max-height: 85vh;
      display: block;
      border-radius: var(--radius-sm);
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
    }
  }

  &__close {
    position: fixed;
    top: var(--space-4);
    right: var(--space-4);
    --color: var(--navy-muted);
    --background: rgba(255, 255, 255, 0.8);
    --border-radius: 50%;
    width: 44px;
    height: 44px;
    margin: 0;
    z-index: 10001;

    ion-icon {
      font-size: 2rem;
    }
  }
}

@keyframes qrFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

// --- Error actions row ---
.error-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

// --- Expand section button ---
.expand-section {
  text-align: center;
  padding: var(--space-4) 0;
}

.btn-expand {
  --border-color: var(--teal);
  --color: var(--teal);
  --border-radius: var(--radius);
  --border-width: 1.5px;
  font-weight: 600;
  font-size: var(--fs-small);
  max-width: 320px;
  margin: 0 auto;

  ion-icon { font-size: 1.1rem; }
}

.expand-error {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--fs-small);
  font-weight: 500;
}

// --- Botón crear itinerario ---
.btn-itinerary {
  --background: linear-gradient(135deg, var(--teal), var(--teal-dark, #0a7a7e));
  --color: white;
  --border-radius: 14px;
  --padding-top: 16px;
  --padding-bottom: 16px;
  font-weight: 600;
  font-size: 1.05rem;
  letter-spacing: 0.02em;
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
  box-shadow: 0 4px 16px rgba(13, 115, 119, 0.3);
  transition: transform 0.15s ease, box-shadow 0.15s ease;

  &:active {
    transform: scale(0.97);
    box-shadow: 0 2px 8px rgba(13, 115, 119, 0.2);
  }

  &[disabled] {
    opacity: 0.6;
    --background: var(--navy-muted);
    box-shadow: none;
  }
}
````

## File: boarding-pass/src/app/itinerary/itinerary.page.ts
````typescript
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

const SEGMENT_ICONS: Record<string, string> = {
  flight: 'airplane', train: 'train', hotel: 'bed',
  car: 'car', restaurant: 'restaurant', activity: 'football',
};
const SEGMENT_LABELS: Record<string, string> = {
  flight: 'Vuelo', train: 'Tren', hotel: 'Hotel',
  car: 'Coche', restaurant: 'Restaurante', activity: 'Actividad',
};

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
  activeTab: 'plan' | 'cards' | 'bookings' | 'eat' | 'sleep' | 'visit' | 'tips' = 'plan';

  enlargedBarcode: BarcodeImage | null = null;
  private previousBrightness: number | undefined;

  expanding: Record<string, boolean> = {};
  expandErrors: Record<string, string> = {};

  constructor(
    private router: Router,
    private itinerarySvc: ItineraryService,
    private bpSvc: BoardingPassService,
    private toastCtrl: ToastController,
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
        // Si hay itinerario, saltar al Plan automaticamente
        if (resp.itinerary?.daily_itinerary?.length) {
          this.activeTab = 'plan';
        }
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
    const map = new Map<string, Pass[]>();
    for (const p of passes) {
      const key = (p.name || 'Sin nombre').toUpperCase();
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    }
    const groups: { name: string; passes: Pass[] }[] = [];
    for (const [, list] of map) {
      list.sort((a, b) => {
        const dateCmp = this.compareFlightDates(a, b);
        if (dateCmp !== 0) return dateCmp;
        const ta = a.flight_time || '99:99';
        const tb = b.flight_time || '99:99';
        return ta < tb ? -1 : 1;
      });
      const originalName = list[0].name || 'Sin nombre';
      groups.push({ name: originalName, passes: list });
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

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
````

## File: boarding-pass/src/app/home/home.page.ts
````typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { ToastController } from '@ionic/angular';
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
  private cancelled = false;

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private toastCtrl: ToastController,
  ) {}

  cancel() {
    this.cancelled = true;
    this.busy = false;
    this.progress = '';
  }

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

    this.busy = true;

    const allPasses: Pass[] = [];
    const allImages: any[] = [];
    const filenames: string[] = [];
    let errors = 0;
    const errorMessages: string[] = [];

    for (let i = 0; i < picked.length; i++) {
      if (this.cancelled) break;
      const file = picked[i];
      const filename = file.name || `pdf_${i + 1}.pdf`;
      this.progress = `${i + 1}/${picked.length}`;

      try {
        const blob = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(blob, file.name));
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
      if (this.cancelled) break;
    }
    if (this.cancelled) {
      this.cancelled = false;
      this.busy = false;
      this.progress = '';
      return;
    }

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

    try {
      await firstValueFrom(this.svc.saveTrip(combinedName, allPasses, allImages));
      try { await Haptics.impact({ style: ImpactStyle.Medium }); } catch {}
    } catch (e: any) {
      console.error('Error guardando viaje:', e);
    }
    this.router.navigate(['/trips']);
  }

  private async toBlob(picked: any): Promise<Blob> {
    const name = picked.name ?? 'file';
    const mime = picked.mimeType || '';
    const b64 = picked.data || picked.blob;
    if (typeof b64 === 'string' && b64.length > 0) {
      let clean = b64.includes(',') ? b64.split(',')[1] : b64;
      try {
        const chars = atob(clean);
        const bytes = new Uint8Array(chars.length);
        for (let i = 0; i < chars.length; i++) bytes[i] = chars.charCodeAt(i);
        return new Blob([bytes], { type: mime });
      } catch (e: any) {
        throw new Error('Base64 decode failed: ' + e.message);
      }
    }
    if (picked.blob instanceof Blob) {
      return picked.blob;
    }
    const url = picked.path ?? picked.uri ?? '';
    if (url) {
      const resp = await fetch(url);
      return await resp.blob();
    }
    throw new Error('No file data available');
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 4000, color });
    await t.present();
  }
}
````

## File: boarding-pass/src/app/itinerary/itinerary.page.html
````html
<ion-header class="glass">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-button (click)="goBack()" fill="clear">
        <ion-icon name="arrow-back"></ion-icon>
      </ion-button>
    </ion-buttons>
    <ion-title class="mono">{{ tripName || 'itinerario' }}</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content>
  <ion-refresher slot="fixed" (ionRefresh)="onRefresh($event)">
    <ion-refresher-content></ion-refresher-content>
  </ion-refresher>

  <!-- Loading -->
  <div *ngIf="loading" class="state-container">
    <ion-spinner name="dots"></ion-spinner>
    <p>Cargando itinerario…</p>
  </div>

  <!-- No itinerary yet -->
  <div *ngIf="!loading && !itinerary && !error" class="state-container">
    <div class="empty-state__icon">
      <ion-icon name="compass-outline"></ion-icon>
    </div>
    <h2>Sin itinerario</h2>
    <p>Genera un plan de viaje personalizado con recomendaciones de restaurantes, hoteles y actividades.</p>
    <ion-button class="btn-itinerary" (click)="generateItinerary()" [disabled]="generating">
      <ion-icon name="sparkles-outline" slot="start"></ion-icon>
      {{ generating ? 'Creando…' : 'Crear itinerario' }}
    </ion-button>
  </div>

  <!-- Error -->
  <div *ngIf="!loading && error && !itinerary" class="state-container error">
    <ion-icon name="warning-outline" size="large" color="danger"></ion-icon>
    <h2>Error</h2>
    <p>{{ error }}</p>
    <div class="error-actions">
      <ion-button (click)="retryLoad()" fill="outline">
        <ion-icon name="refresh-outline" slot="start"></ion-icon>
        Reintentar
      </ion-button>
      <ion-button (click)="goBack()" fill="clear" color="medium">Volver</ion-button>
    </div>
  </div>

  <!-- Itinerary content -->
  <ng-container *ngIf="!loading && itinerary && !itinerary.parse_error && !itinerary.error">
    <div class="hero" *ngIf="itinerary.destination_overview">
      <div class="hero__destinations">
        <ion-chip *ngFor="let d of itinerary.meta?.destinations" color="primary" outline>
          <ion-icon name="location-outline"></ion-icon>
          <ion-label>{{ d }}</ion-label>
        </ion-chip>
      </div>
      <p class="hero__overview">{{ itinerary.destination_overview }}</p>
    </div>

    <div class="section" *ngIf="itinerary.weather?.length">
      <h2 class="section__title"><ion-icon name="partly-sunny-outline"></ion-icon> Clima</h2>
      <p class="section__weather-summary" *ngIf="itinerary.weather_summary">{{ itinerary.weather_summary }}</p>
      <div class="weather-grid">
        <div class="weather-card" *ngFor="let w of itinerary.weather">
          <div class="weather-card__date">{{ w.date | date:'EEE dd' }}</div>
          <div class="weather-card__icon">{{ w.condition }}</div>
          <div class="weather-card__temps">
            <span class="max">{{ w.temp_max }}°</span>
            <span class="min">{{ w.temp_min }}°</span>
          </div>
        </div>
      </div>
    </div>
  </ng-container>

  <!-- Tabs (always visible when trip has data) -->
  <ng-container *ngIf="!loading && (itinerary || passes.length || segments.length)">
    <ion-segment [(ngModel)]="activeTab" [value]="activeTab" scrollable="true" class="tabs">
      <ion-segment-button value="plan" *ngIf="itinerary">
        <ion-icon name="calendar-outline"></ion-icon>
        <ion-label>Plan</ion-label>
      </ion-segment-button>
      <ion-segment-button value="cards">
        <ion-icon name="ticket-outline"></ion-icon>
        <ion-label>Billetes</ion-label>
      </ion-segment-button>
      <!-- <ion-segment-button value="bookings">
        <ion-icon name="reader-outline"></ion-icon>
        <ion-label>Reservas</ion-label>
      </ion-segment-button> -->
      <ion-segment-button value="eat" *ngIf="itinerary">
        <ion-icon name="restaurant-outline"></ion-icon>
        <ion-label>Comer</ion-label>
      </ion-segment-button>
      <ion-segment-button value="sleep" *ngIf="itinerary">
        <ion-icon name="bed-outline"></ion-icon>
        <ion-label>Dormir</ion-label>
      </ion-segment-button>
      <ion-segment-button value="visit" *ngIf="itinerary">
        <ion-icon name="eye-outline"></ion-icon>
        <ion-label>Visitar</ion-label>
      </ion-segment-button>
      <ion-segment-button value="tips" *ngIf="itinerary">
        <ion-icon name="bulb-outline"></ion-icon>
        <ion-label>Tips</ion-label>
      </ion-segment-button>
    </ion-segment>

    <!-- BILLETES -->
    <div class="section" *ngIf="activeTab === 'cards'">
      <div *ngIf="groups.length === 0" class="empty-tab">
        <p>No hay billetes subidos.</p>
      </div>

      <div class="bill-list" *ngIf="groups.length">
        <ng-container *ngIf="groups.length === 1; else multiAccordion">
          <ng-container *ngTemplateOutlet="passCard; context: { $implicit: groups[0].passes }"></ng-container>
        </ng-container>
        <ng-template #multiAccordion>
          <div class="person-group" *ngFor="let grp of groups; let i = index">
            <div class="person-header" (click)="toggleGroup(grp.name)">
              <div class="person-header__left">
                <ion-icon [name]="isGroupExpanded(grp.name) ? 'chevron-down-circle' : 'chevron-forward-circle'"
                          class="person-header__chevron"></ion-icon>
                <span class="person-header__name">{{ grp.name }}</span>
              </div>
              <div class="person-header__right">
                <span class="person-header__count">{{ grp.passes.length }} billete{{ grp.passes.length > 1 ? 's' : '' }}</span>
              </div>
            </div>
            <div class="person-passes" *ngIf="isGroupExpanded(grp.name)">
              <ng-container *ngTemplateOutlet="passCard; context: { $implicit: grp.passes }"></ng-container>
            </div>
          </div>
        </ng-template>

        <!-- Pass card template (shared between single and multi) -->
        <ng-template #passCard let-passes>
          <article class="boarding-pass pass-stub" *ngFor="let pass of passes; let j = index">
            <header class="bp-header">
              <div class="bp-route-hero" [class.bp-route-hero--train]="pass.kind === 'train'">
                <div class="bp-route-hero__side">
                  <span class="bp-route-hero__code">{{ pass.from || '???' }}</span>
                  <span class="bp-route-hero__label" *ngIf="pass.from">ORIGEN</span>
                </div>
                <div class="bp-route-hero__connector">
                  <span class="bp-route-hero__line"></span>
                  <ion-icon *ngIf="pass.kind === 'train'" name="train" class="bp-route-hero__train-icon"></ion-icon>
                  <ion-icon *ngIf="pass.kind !== 'train'" name="airplane" class="bp-route-hero__plane"></ion-icon>
                  <span class="bp-route-hero__line"></span>
                </div>
                <div class="bp-route-hero__side bp-route-hero__side--dest">
                  <span class="bp-route-hero__code">{{ pass.to || '???' }}</span>
                  <span class="bp-route-hero__label" *ngIf="pass.to">DESTINO</span>
                </div>
              </div>
              <div class="bp-header__meta">
                <span class="bp-header__airline">{{ getAirlineName(pass.airline) || (pass.kind === 'train' ? 'Tren' : pass.format) }}</span>
                <span class="bp-header__divider"></span>
                <span class="mono bp-header__flight">{{ pass.kind === 'train' ? (pass.train || '') : (pass.airline || '') + (pass.flight || '') }}</span>
                <span class="bp-header__divider" *ngIf="pass.flight_date">·</span>
                <span class="mono bp-header__date" *ngIf="pass.flight_date">{{ formatDate(pass) }}</span>
              </div>
            </header>

            <div class="bp-info">
              <div class="bp-info__cell bp-info__cell--wide">
                <span class="bp-info__label">PASAJERO</span>
                <span class="bp-info__value">{{ pass.name || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">PNR</span>
                <span class="bp-info__value mono">{{ pass.pnr || '—' }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">{{ pass.kind === 'train' ? 'OPERADOR' : 'COMPAÑÍA' }}</span>
                <span class="bp-info__value">{{ getAirlineName(pass.airline) || (pass.kind === 'train' ? 'Renfe' : pass.format) }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">{{ pass.kind === 'train' ? 'TREN' : 'VUELO' }}</span>
                <span class="bp-info__value mono">{{ pass.kind === 'train' ? (pass.train || '—') : (pass.airline || '') + (pass.flight || '') }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">FECHA</span>
                <span class="bp-info__value mono">{{ formatDate(pass) }}</span>
              </div>
              <div class="bp-info__cell" *ngIf="pass.class">
                <span class="bp-info__label">CLASE</span>
                <span class="bp-info__value mono">{{ pass.class }}</span>
              </div>
              <div class="bp-info__cell">
                <span class="bp-info__label">HORA</span>
                <span class="bp-info__value mono">{{ pass.flight_time || '—' }}</span>
              </div>
              <div class="bp-info__cell" *ngIf="pass.gate_close_time">
                <span class="bp-info__label">CIERRE PUERTAS</span>
                <span class="bp-info__value mono">{{ pass.gate_close_time }}</span>
              </div>
              <div class="bp-info__cell" *ngIf="pass.seat">
                <span class="bp-info__label">ASIENTO</span>
                <span class="bp-info__value mono">{{ pass.seat }}</span>
              </div>
            </div>

            <div *ngIf="imageFor(pass) as img" class="bp-barcode">
              <img [src]="'data:image/png;base64,' + img.base64" [alt]="pass.format"
                   class="bp-barcode__img" (click)="openBarcode(img)" />
              <span class="bp-barcode__hint mono">{{ pass.format }} · p{{ pass.page }}</span>
            </div>
          </article>
        </ng-template>
      </div>
    </div>

    <!-- RESERVAS -->
    <!-- <div class="section" *ngIf="activeTab === 'bookings'">
      <div *ngIf="segments.length === 0" class="empty-tab">
        <p>No hay reservas añadidas.</p>
      </div>
      <div class="summary-list">
        <div class="summary-item" *ngFor="let seg of segments">
          <ion-icon [name]="segmentIcon(seg.type)" color="primary"></ion-icon>
          <span class="summary-label">{{ segmentSummary(seg) }}</span>
          <ion-badge color="medium">{{ segmentLabel(seg.type) }}</ion-badge>
        </div>
      </div>
      <ion-button expand="block" fill="outline" size="small" class="edit-segments-btn" (click)="editSegments()">
        <ion-icon name="create-outline" slot="start"></ion-icon>
        Editar reservas
      </ion-button>
    </div> -->

    <!-- PLAN DIARIO -->
    <div class="section" *ngIf="activeTab === 'plan' && itinerary?.daily_itinerary?.length">
      <ion-card class="day-card" *ngFor="let day of itinerary!.daily_itinerary">
        <ion-card-header>
          <ion-card-subtitle>Día {{ day.day_number }} — {{ day.date | date:'fullDate' }}</ion-card-subtitle>
          <ion-card-title *ngIf="day.theme">{{ day.theme }}</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <div class="day-card__slot">
            <ion-icon name="sunny-outline" color="warning"></ion-icon>
            <div>
              <strong>Mañana</strong>
              <p>{{ day.morning?.description }}</p>
              <div class="day-card__activities" *ngIf="day.morning?.activities?.length">
                <ion-chip *ngFor="let a of day.morning.activities" outline>{{ a }}</ion-chip>
              </div>
            </div>
          </div>
          <div class="day-card__slot">
            <ion-icon name="sunny-outline" color="primary"></ion-icon>
            <div>
              <strong>Tarde</strong>
              <p>{{ day.afternoon?.description }}</p>
              <div class="day-card__activities" *ngIf="day.afternoon?.activities?.length">
                <ion-chip *ngFor="let a of day.afternoon.activities" outline>{{ a }}</ion-chip>
              </div>
            </div>
          </div>
          <div class="day-card__slot">
            <ion-icon name="moon-outline" color="tertiary"></ion-icon>
            <div>
              <strong>Noche</strong>
              <p>{{ day.evening?.description }}</p>
              <div class="day-card__activities" *ngIf="day.evening?.activities?.length">
                <ion-chip *ngFor="let a of day.evening.activities" outline>{{ a }}</ion-chip>
              </div>
            </div>
          </div>
          <div class="day-card__meal" *ngIf="day.meal_suggestions">
            <ion-icon name="restaurant-outline" color="success"></ion-icon>
            <div>
              <span *ngIf="day.meal_suggestions.lunch"><strong>Almuerzo:</strong> {{ day.meal_suggestions.lunch }}</span>
              <span *ngIf="day.meal_suggestions.dinner"><strong>Cena:</strong> {{ day.meal_suggestions.dinner }}</span>
            </div>
          </div>
          <!-- Clima del dia -->
          <div class="day-card__weather" *ngIf="weatherForDate(day.date) as w">
            {{ w.condition }} · {{ w.temp_max }}° / {{ w.temp_min }}°
          </div>
        </ion-card-content>
      </ion-card>
    </div>

    <!-- RESTAURANTES -->
    <div class="section" *ngIf="activeTab === 'eat'">
      <ion-card class="rec-card" *ngFor="let r of itinerary?.restaurants">
        <ion-card-header>
          <ion-card-title>{{ r.name }}</ion-card-title>
          <ion-card-subtitle>{{ r.type }} · {{ r.price_range }}</ion-card-subtitle>
        </ion-card-header>
        <ion-card-content>
          <p>{{ r.description }}</p>
        </ion-card-content>
      </ion-card>
      <div class="empty-tab" *ngIf="!itinerary?.restaurants?.length">
        <p>Aún no hay recomendaciones de restaurantes.</p>
      </div>
      <div class="expand-section">
        <ion-button expand="block" fill="outline" class="btn-expand"
                    (click)="expandSection('restaurants')"
                    [disabled]="expanding['restaurants']">
          <ion-icon [name]="expanding['restaurants'] ? 'hourglass-outline' : 'search-outline'" slot="start"></ion-icon>
          {{ expanding['restaurants'] ? 'Buscando…' : 'Buscar más restaurantes' }}
        </ion-button>
        <ion-text color="danger" class="expand-error" *ngIf="expandErrors['restaurants']">
          {{ expandErrors['restaurants'] }}
        </ion-text>
      </div>
    </div>

    <!-- HOTELES -->
    <div class="section" *ngIf="activeTab === 'sleep'">
      <ion-card class="rec-card" *ngFor="let h of itinerary?.hotels">
        <ion-card-header>
          <ion-card-title>{{ h.name }}</ion-card-title>
          <ion-card-subtitle>{{ h.zone }} · {{ h.price_range }}</ion-card-subtitle>
        </ion-card-header>
        <ion-card-content>
          <p>{{ h.description }}</p>
          <div class="card-chips" *ngIf="h.highlights?.length">
            <ion-chip *ngFor="let hl of h.highlights">{{ hl }}</ion-chip>
          </div>
        </ion-card-content>
      </ion-card>
      <div class="empty-tab" *ngIf="!itinerary?.hotels?.length">
        <p>Aún no hay recomendaciones de alojamiento.</p>
      </div>
      <div class="expand-section">
        <ion-button expand="block" fill="outline" class="btn-expand"
                    (click)="expandSection('hotels')"
                    [disabled]="expanding['hotels']">
          <ion-icon [name]="expanding['hotels'] ? 'hourglass-outline' : 'search-outline'" slot="start"></ion-icon>
          {{ expanding['hotels'] ? 'Buscando…' : 'Buscar más alojamientos' }}
        </ion-button>
        <ion-text color="danger" class="expand-error" *ngIf="expandErrors['hotels']">
          {{ expandErrors['hotels'] }}
        </ion-text>
      </div>
    </div>

    <!-- LUGARES DE INTERÉS + SITIOS HISTÓRICOS -->
    <div class="section" *ngIf="activeTab === 'visit'">
      <h3 *ngIf="itinerary?.places_of_interest?.length">Lugares de interés</h3>
      <ion-card class="rec-card" *ngFor="let p of itinerary?.places_of_interest">
        <ion-card-header>
          <ion-card-title>{{ p.name }}</ion-card-title>
          <ion-card-subtitle>{{ p.type }}</ion-card-subtitle>
        </ion-card-header>
        <ion-card-content>
          <p>{{ p.description }}</p>
          <div class="card-chips" *ngIf="p.tips?.length">
            <ion-chip *ngFor="let t of p.tips">{{ t }}</ion-chip>
          </div>
        </ion-card-content>
      </ion-card>

      <h3 *ngIf="itinerary?.historical_sites?.length">Sitios históricos</h3>
      <ion-card class="rec-card historical" *ngFor="let h of itinerary?.historical_sites">
        <ion-card-header>
          <ion-card-title>{{ h.name }}</ion-card-title>
          <ion-card-subtitle>{{ h.period }}</ion-card-subtitle>
        </ion-card-header>
        <ion-card-content>
          <p>{{ h.description }}</p>
          <div class="curiosity">
            <ion-icon name="information-circle-outline"></ion-icon>
            <span>{{ h.curiosity }}</span>
          </div>
        </ion-card-content>
      </ion-card>

      <div class="empty-tab" *ngIf="!itinerary?.places_of_interest?.length && !itinerary?.historical_sites?.length">
        <p>Aún no hay lugares para visitar.</p>
      </div>

      <div class="expand-section">
        <ion-button expand="block" fill="outline" class="btn-expand"
                    (click)="expandSection('visit')"
                    [disabled]="expanding['visit']">
          <ion-icon [name]="expanding['visit'] ? 'hourglass-outline' : 'search-outline'" slot="start"></ion-icon>
          {{ expanding['visit'] ? 'Buscando…' : 'Buscar más lugares' }}
        </ion-button>
        <ion-text color="danger" class="expand-error" *ngIf="expandErrors['visit']">
          {{ expandErrors['visit'] }}
        </ion-text>
      </div>
    </div>

    <!-- TIPS -->
    <div class="section" *ngIf="activeTab === 'tips'">
      <ion-card class="tips-card" *ngIf="itinerary?.transport_tips?.length">
        <ion-card-header>
          <ion-card-title><ion-icon name="bus-outline"></ion-icon> Transporte</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ul class="tips-list">
            <li *ngFor="let t of itinerary?.transport_tips">{{ t }}</li>
          </ul>
        </ion-card-content>
      </ion-card>

      <ion-card class="tips-card" *ngIf="itinerary?.general_tips?.length">
        <ion-card-header>
          <ion-card-title><ion-icon name="bulb-outline"></ion-icon> Consejos generales</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ul class="tips-list">
            <li *ngFor="let t of itinerary?.general_tips">{{ t }}</li>
          </ul>
        </ion-card-content>
      </ion-card>

      <ion-card class="tips-card" *ngIf="itinerary?.cultural_notes?.length">
        <ion-card-header>
          <ion-card-title><ion-icon name="book-outline"></ion-icon> Notas culturales</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ul class="tips-list">
            <li *ngFor="let t of itinerary?.cultural_notes">{{ t }}</li>
          </ul>
        </ion-card-content>
      </ion-card>

      <div class="empty-tab" *ngIf="!itinerary?.transport_tips?.length && !itinerary?.general_tips?.length && !itinerary?.cultural_notes?.length">
        <p>Aún no hay consejos disponibles.</p>
      </div>

      <div class="expand-section">
        <ion-button expand="block" fill="outline" class="btn-expand"
                    (click)="expandSection('tips')"
                    [disabled]="expanding['tips']">
          <ion-icon [name]="expanding['tips'] ? 'hourglass-outline' : 'search-outline'" slot="start"></ion-icon>
          {{ expanding['tips'] ? 'Buscando…' : 'Buscar más tips' }}
        </ion-button>
        <ion-text color="danger" class="expand-error" *ngIf="expandErrors['tips']">
          {{ expandErrors['tips'] }}
        </ion-text>
      </div>
    </div>
  </ng-container>

  <!-- QR enlarger overlay -->
  <div class="qr-overlay" *ngIf="enlargedBarcode" (click)="closeBarcode()">
    <div class="qr-overlay__content" (click)="$event.stopPropagation()">
      <img [src]="'data:image/png;base64,' + enlargedBarcode.base64" alt="Código de barras ampliado" />
      <ion-button fill="clear" class="qr-overlay__close" (click)="closeBarcode()">
        <ion-icon name="close-circle" size="large"></ion-icon>
      </ion-button>
    </div>
  </div>
</ion-content>

<!-- Generating overlay -->
<div class="proc-overlay" *ngIf="generating">
  <div class="proc-card">
    <ion-spinner name="dots" color="primary"></ion-spinner>
    <p class="proc-card__title">Creando itinerario</p>
    <p class="proc-card__count">Buscando las mejores recomendaciones…</p>
  </div>
</div>
````

## File: backend/itinerary.py
````python
"""
Modulo de generacion de itinerarios de viaje usando DeepSeek LLM y Open-Meteo.

DeepSeek: recomendaciones personalizadas (restaurantes, hoteles, lugares, historia, tips).
Open-Meteo: prediccion meteorologica gratuita sin API key.
"""

import json
import sys
from datetime import datetime, date
from pathlib import Path

import httpx
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parser import infer_years

# --- Configuracion ---

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _format_short_date(date_str: str) -> str:
    """Convierte '2026-12-06' -> '06/12' para nombres de viaje compactos."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m")
    except (ValueError, TypeError):
        return date_str

# Coordenadas de aeropuertos/ciudades comunes para el clima
CITY_COORDS: dict[str, tuple[float, float]] = {
    "MAD": (40.4168, -3.7038), "BCN": (41.3874, 2.1686),
    "LHR": (51.4700, -0.4543), "ORY": (48.7239, 2.3795),
    "CDG": (49.0097, 2.5479), "AMS": (52.3105, 4.7683),
    "FCO": (41.8003, 12.2389), "PMI": (39.5517, 2.7382),
    "AGP": (36.6749, -4.4991), "SVQ": (37.3891, -5.9845),
    "BIO": (43.3011, -2.9103), "VLC": (39.4893, -0.4816),
    "ALC": (38.2824, -0.5582), "IBZ": (38.9067, 1.4206),
    "TFN": (28.4826, -16.3197), "LPA": (27.9388, -15.3866),
    "TFS": (28.0444, -16.5725), "EAS": (43.3566, -1.7906),
    "SCQ": (42.8984, -8.4153), "VGO": (42.2346, -8.6262),
    "SDR": (43.4271, -3.8206), "ZAZ": (41.6662, -1.0419),
    "GRX": (37.1887, -3.7767), "XRY": (36.7441, -6.0605),
    "LEI": (36.8438, -2.3671), "BRU": (50.9018, 4.4836),
    "FRA": (50.0392, 8.5592), "MUC": (48.3537, 11.7750),
    "BER": (52.5588, 13.2884), "MXP": (45.63, 8.7231),
    "LIN": (45.4495, 9.2774), "VCE": (45.5047, 12.3395),
    "NAP": (40.8845, 14.2907), "LIS": (38.7746, -9.1353),
    "OPO": (41.2372, -8.6708), "FAO": (37.0204, -7.9719),
    "ATH": (37.9363, 23.9474), "VIE": (48.1192, 16.5667),
    "PRG": (50.1061, 14.2667), "BUD": (47.4365, 19.2553),
    "WAW": (52.1699, 20.9728), "DUB": (53.4264, -6.2499),
    "CPH": (55.6176, 12.6498), "OSL": (60.1975, 11.1008),
    "ARN": (59.6491, 17.9306), "HEL": (60.3183, 24.9524),
    "IST": (41.2611, 28.7427), "DXB": (25.2487, 55.3653),
    "JFK": (40.6413, -73.7781), "EWR": (40.6895, -74.1745),
    "MIA": (25.7959, -80.2870), "LAX": (33.9416, -118.4085),
    "MEX": (19.4357, -99.0718), "BOG": (4.6996, -74.1466),
    "EZE": (-34.8124, -58.5396), "GRU": (-23.4254, -46.4819),
    "NRT": (35.7738, 140.3874), "HND": (35.5533, 139.7811),
    "SIN": (1.3592, 103.9900), "BKK": (13.6930, 100.7523),
    "DOH": (25.2686, 51.6100), "AUH": (24.4335, 54.6481),
}

AIRPORT_CITY_NAMES: dict[str, str] = {
    "MAD": "Madrid", "BCN": "Barcelona", "LHR": "Londres",
    "ORY": "París", "CDG": "París", "AMS": "Ámsterdam",
    "FCO": "Roma", "PMI": "Palma de Mallorca", "AGP": "Málaga",
    "SVQ": "Sevilla", "BIO": "Bilbao", "VLC": "Valencia",
    "ALC": "Alicante", "IBZ": "Ibiza", "TFN": "Tenerife",
    "LPA": "Gran Canaria", "TFS": "Tenerife Sur", "EAS": "San Sebastián",
    "SCQ": "Santiago", "VGO": "Vigo", "SDR": "Santander",
    "ZAZ": "Zaragoza", "GRX": "Granada", "XRY": "Jerez",
    "LEI": "Almería", "BRU": "Bruselas", "FRA": "Fráncfort",
    "MUC": "Múnich", "BER": "Berlín", "MXP": "Milán",
    "LIN": "Milán", "VCE": "Venecia", "NAP": "Nápoles",
    "LIS": "Lisboa", "OPO": "Oporto", "FAO": "Faro",
    "ATH": "Atenas", "VIE": "Viena", "PRG": "Praga",
    "BUD": "Budapest", "WAW": "Varsovia", "DUB": "Dublín",
    "CPH": "Copenhague", "OSL": "Oslo", "ARN": "Estocolmo",
    "HEL": "Helsinki", "IST": "Estambul", "DXB": "Dubái",
    "JFK": "Nueva York", "EWR": "Nueva York", "MIA": "Miami",
    "LAX": "Los Ángeles", "MEX": "Ciudad de México",
    "BOG": "Bogotá", "EZE": "Buenos Aires", "GRU": "São Paulo",
    "NRT": "Tokio", "HND": "Tokio", "SIN": "Singapur",
    "BKK": "Bangkok", "DOH": "Doha", "AUH": "Abu Dabi",
}

# Normalizacion de ciudades que aparecen escritas enteras en el billete
# (no como codigo IATA) en PDFs de Renfe/OUIGO
SPANISH_CITY_ALIASES: dict[str, str] = {
    "MADRID P.ATOCHA": "Madrid",
    "MADRID ATOCHA": "Madrid",
    "MADRID CHAMARTIN": "Madrid",
    "MADRID PUERTA DE ATOCHA": "Madrid",
    "BARCELONA SANTS": "Barcelona",
    "TOLEDO": "Toledo",
    "SEVILLA SANTA JUSTA": "Sevilla",
    "VALENCIA JOAQUIN SOROLLA": "Valencia",
    "MADRID": "Madrid",
    "BARCELONA": "Barcelona",
    "SEVILLA": "Sevilla",
    "VALENCIA": "Valencia",
    "MALAGA": "Málaga",
    "BILBAO": "Bilbao",
    "ZARAGOZA": "Zaragoza",
    "SANTIAGO": "Santiago de Compostela",
    "A CORUÑA": "A Coruña",
    "VIGO": "Vigo",
    "ALICANTE": "Alicante",
    "MURCIA": "Murcia",
}


def _sort_by_date(items: list[dict], date_key: str = "flight_date", time_key: str = "flight_time") -> list[dict]:
    """Ordena items por fecha y hora usando objetos date para orden correcto."""
    def sort_key(item):
        d_str = item.get(date_key, "")
        t_str = item.get(time_key, "") or ""
        try:
            d = date.fromisoformat(d_str) if d_str else date.min
            return (d, t_str)
        except (ValueError, TypeError):
            return (date.min, t_str)
    return sorted(items, key=sort_key)


def _get_city_name(code: str) -> str:
    """Convierte codigo de aeropuerto o nombre de estacion a ciudad.

    Maneja:
    - Codigos IATA: 'BCN' -> 'Barcelona'
    - Nombres de estacion: 'Sevilla - Santa Justa' -> 'Sevilla'
    - Ciudades en texto: 'MADRID P.ATOCHA' -> 'Madrid'
    """
    if not code:
        return ""
    code_upper = code.upper().strip()
    if code_upper in AIRPORT_CITY_NAMES:
        return AIRPORT_CITY_NAMES[code_upper]
    if code_upper in SPANISH_CITY_ALIASES:
        return SPANISH_CITY_ALIASES[code_upper]
    # Estacion: 'Sevilla - Santa Justa' -> 'Sevilla'
    if " - " in code:
        return code.split(" - ")[0].strip()
    return code


def _get_coords(code: str) -> tuple[float, float] | None:
    """Obtiene coordenadas para un codigo de aeropuerto."""
    return CITY_COORDS.get(code.upper())


# --- Clima (Open-Meteo, gratuito, sin API key) ---

async def fetch_weather(city_code: str, start_date: str, end_date: str) -> list[dict]:
    """Obtiene prediccion meteorologica para una ciudad en un rango de fechas.

    Devuelve lista de {date, temp_max, temp_min, precipitation, condition, wind_speed}.
    """
    coords = _get_coords(city_code)
    if not coords:
        return []

    lat, lon = coords
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[weather] Error: {e}")
        return []

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    weather_codes = daily.get("weather_code", [])
    wind = daily.get("wind_speed_10m_max", [])

    weather = []
    for i, d in enumerate(dates):
        weather.append({
            "date": d,
            "temp_max": temps_max[i] if i < len(temps_max) else None,
            "temp_min": temps_min[i] if i < len(temps_min) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "condition": _weather_emoji(weather_codes[i] if i < len(weather_codes) else 0),
            "wind_kmh": wind[i] if i < len(wind) else None,
        })
    return weather


def _weather_emoji(code: int) -> str:
    """Convierte codigo WMO a descripcion con emoji."""
    if code == 0:
        return "☀️ Despejado"
    if code in (1, 2, 3):
        return "🌤️ Parcialmente nublado"
    if code in (45, 48):
        return "🌫️ Niebla"
    if code in (51, 53, 55):
        return "🌧️ Llovizna"
    if code in (61, 63, 65, 80, 81, 82):
        return "🌧️ Lluvia"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄️ Nieve"
    if code in (95, 96, 99):
        return "⛈️ Tormenta"
    return "🌥️ Nublado"


# --- Calendario diario (extrae itinerario base de pases + segmentos) ---

_SPANISH_WEEKDAYS = [
    "Lunes", "Martes", "Miércoles", "Jueves",
    "Viernes", "Sábado", "Domingo",
]

def _spanish_weekday(date_str: str) -> str:
    """Convierte '2025-12-01' -> 'Lunes'."""
    try:
        d = date.fromisoformat(date_str)
        return _SPANISH_WEEKDAYS[d.weekday()]
    except (ValueError, TypeError):
        return ""


def _infer_city_per_day(
    passes: list[dict],
    segments: list[dict],
    all_dates: list[str],
) -> dict[str, str | None]:
    """Determina en qué ciudad está el viajero cada día del viaje.

    Algoritmo:
    1. Ciudad inicial = origen del primer vuelo.
    2. Hoteles: Si hay check-in en fecha D, la ciudad del hotel pisa la actual
       y se mantiene hasta el check-out (inclusive).
    3. Vuelos/trenes: al llegar a destino, se actualiza la ciudad actual
       para esa fecha y las siguientes.
    4. Actividades y restaurantes: refuerzan la ciudad para su fecha.

    Returns dict {fecha: ciudad | None}.
    """
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)

    trains = [p for p in passes if p.get("kind") == "train"]
    trains_sorted = _sort_by_date(trains, date_key="flight_date", time_key="flight_time")

    # Ciudad inicial: origen del primer vuelo o tren
    current_city: str | None = None
    if flights_sorted:
        current_city = _get_city_name(flights_sorted[0].get("from", ""))
    elif trains_sorted:
        current_city = _get_city_name(trains_sorted[0].get("from", ""))

    # Hoteles: rango de fechas -> ciudad (prioridad máxima)
    hotel_map: dict[str, str] = {}
    for s in segments:
        if s.get("type") != "hotel":
            continue
        city = _get_city_name(s.get("city", ""))
        if not city:
            continue
        ci = s.get("check_in", "")
        co = s.get("check_out", "")
        if not ci:
            continue
        # Aplicar a todas las fechas entre check_in y check_out (inclusive)
        for d in all_dates:
            if ci <= d <= (co or ci):
                hotel_map[d] = city

    # Vuelos y trenes: eventos que cambian la ciudad
    transport_events: list[dict] = []
    for f in flights_sorted:
        fd = f.get("flight_date", "")
        if not fd:
            continue
        transport_events.append({
            "date": fd,
            "time": f.get("flight_time", "") or "12:00",
            "to_city": _get_city_name(f.get("to", "")),
        })
    for t in trains_sorted:
        fd = t.get("flight_date", "")
        if not fd:
            continue
        transport_events.append({
            "date": fd,
            "time": t.get("flight_time", "") or "12:00",
            "to_city": _get_city_name(t.get("to", "")),
        })
    for s in segments:
        if s.get("type") == "train":
            transport_events.append({
                "date": s.get("date", ""),
                "time": s.get("time", "") or "12:00",
                "to_city": _get_city_name(s.get("to", "")),
            })
        elif s.get("type") == "flight":
            transport_events.append({
                "date": s.get("date", ""),
                "time": s.get("time", "") or "12:00",
                "to_city": _get_city_name(s.get("to_city", s.get("to", ""))),
            })
    transport_events.sort(key=lambda e: (e["date"], e["time"]))

    city_per_day: dict[str, str | None] = {}
    for date in all_dates:
        # 1. ¿Hay hotel que cubra esta fecha?
        if date in hotel_map:
            current_city = hotel_map[date]
            city_per_day[date] = current_city
            continue

        # 2. ¿Hay llegada de vuelo/tren en esta fecha?
        arrivals_today = [e for e in transport_events if e["date"] == date]
        if arrivals_today:
            # La última llegada del día fija la ciudad
            last = arrivals_today[-1]
            if last["to_city"]:
                current_city = last["to_city"]

        city_per_day[date] = current_city

    # 3. Refuerzo: actividades y restaurantes confirman ciudad para su fecha
    for s in segments:
        if s.get("type") in ("activity", "restaurant"):
            city = _get_city_name(s.get("city", ""))
            date = s.get("date", "")
            if city and date in city_per_day:
                if city_per_day[date] is None:
                    city_per_day[date] = city

    return city_per_day


def _build_daily_calendar(
    passes: list[dict],
    segments: list[dict],
    all_dates: list[str],
    *,
    origin_city: str | None = None,
) -> list[dict]:
    """Construye un calendario diario del viaje a partir de pases y segmentos.

    Cada día incluye:
    - date, day_number, weekday (español), city
    - events: lista de eventos fijos
    - free_blocks: franjas horarias libres para sugerir actividades
    - is_origin_day: True si la ciudad = ciudad de origen (sin sugerencias)

    Args:
        origin_city: ciudad de origen del viajero. Días en esta ciudad
                     se marcan como is_origin_day sin bloques libres.
    """
    flights = [p for p in passes if p.get("kind") == "flight"]
    trains = [p for p in passes if p.get("kind") == "train"]

    flights_sorted = _sort_by_date(flights)

    city_per_day = _infer_city_per_day(passes, segments, all_dates)

    # Construir eventos diarios
    days: dict[str, dict] = {
        d: {
            "date": d,
            "day_number": i + 1,
            "weekday": _spanish_weekday(d),
            "city": city_per_day.get(d),
            "is_origin_day": bool(origin_city and city_per_day.get(d) == origin_city),
            "events": [],
        }
        for i, d in enumerate(all_dates)
    }

    # --- Vuelos (PDF/imagen) ---
    for f in flights_sorted:
        fd = f.get("flight_date", "")
        if fd not in days:
            continue
        flight_time = f.get("flight_time", "") or ""
        gate_close = f.get("gate_close_time", "") or ""
        airline = f.get("airline", "")
        flight_no = f.get("flight", "")
        from_city = _get_city_name(f.get("from", ""))
        to_city = _get_city_name(f.get("to", ""))
        # Enriquecer descripcion con horas reales si existen
        time_extra = ""
        if flight_time:
            time_extra += f" (salida {flight_time})"
        if gate_close:
            time_extra += f" — cierre puertas {gate_close}"
        days[fd]["events"].append({
            "type": "flight_arrival",
            "time": flight_time,
            "gate_close": gate_close,
            "description": f"Llegada {airline}{flight_no} desde {from_city}{time_extra}",
            "city": to_city,
        })

    # --- Trenes (PDF) ---
    for t in trains:
        fd = t.get("flight_date", "")
        if fd not in days:
            continue
        time_str = t.get("flight_time", "") or ""
        train_no = t.get("train", "")
        from_raw = t.get("from", "")
        to_raw = t.get("to", "")
        from_city = _get_city_name(from_raw) or from_raw
        to_city = _get_city_name(to_raw) or to_raw
        days[fd]["events"].append({
            "type": "train_arrival",
            "time": time_str,
            "description": f"Llegada tren {train_no} desde {from_city}",
            "city": to_city,
        })

    # --- Vuelos manuales ---
    for s in segments:
        if s.get("type") != "flight":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        airline = s.get("airline", "")
        flight_no = s.get("flight_number", "")
        from_city = _get_city_name(s.get("from", "")) or s.get("from", "")
        to_city = _get_city_name(s.get("to_city", s.get("to", ""))) or s.get("to", "")
        days[fd]["events"].append({
            "type": "flight_arrival",
            "time": s.get("time", "") or "",
            "description": f"Llegada {airline}{flight_no} desde {from_city}",
            "city": to_city,
        })

    # --- Trenes manuales ---
    for s in segments:
        if s.get("type") != "train":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        op = s.get("operator", "")
        train_no = s.get("train_number", "")
        from_city = _get_city_name(s.get("from", "")) or s.get("from", "")
        to_city = _get_city_name(s.get("to", "")) or s.get("to", "")
        days[fd]["events"].append({
            "type": "train_arrival",
            "time": s.get("time", "") or "",
            "description": f"Llegada {op} {train_no} desde {from_city}",
            "city": to_city,
        })

    # --- Hoteles ---
    for s in segments:
        if s.get("type") != "hotel":
            continue
        hotel_city = _get_city_name(s.get("city", "")) or s.get("city", "")
        name = s.get("name", "")
        ci = s.get("check_in", "")
        co = s.get("check_out", "")
        if ci and ci in days:
            days[ci]["events"].append({
                "type": "hotel_checkin",
                "time": "",
                "description": f"Check-in {name}",
                "city": hotel_city,
            })
        if co and co in days:
            days[co]["events"].append({
                "type": "hotel_checkout",
                "time": "",
                "description": f"Check-out {name}",
                "city": hotel_city,
            })

    # --- Coches ---
    for s in segments:
        if s.get("type") != "car":
            continue
        company = s.get("company", "")
        city = _get_city_name(s.get("city", "")) or s.get("city", "")
        pickup_date = s.get("pickup_date", "")
        return_date = s.get("return_date", "")
        if pickup_date and pickup_date in days:
            days[pickup_date]["events"].append({
                "type": "car_pickup",
                "time": "",
                "description": f"Recogida coche {company}",
                "city": city,
            })
        if return_date and return_date in days:
            days[return_date]["events"].append({
                "type": "car_return",
                "time": "",
                "description": f"Devolución coche {company}",
                "city": city,
            })

    # --- Restaurantes ---
    for s in segments:
        if s.get("type") != "restaurant":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        name = s.get("name", "")
        time_str = s.get("time", "") or ""
        days[fd]["events"].append({
            "type": "restaurant",
            "time": time_str,
            "description": f"Cena: {name}",
            "city": _get_city_name(s.get("city", "")) or s.get("city", ""),
        })

    # --- Actividades ---
    for s in segments:
        if s.get("type") != "activity":
            continue
        fd = s.get("date", "")
        if fd not in days:
            continue
        name = s.get("name", "")
        time_str = s.get("time", "") or ""
        days[fd]["events"].append({
            "type": "activity",
            "time": time_str,
            "description": f"Reserva: {name}",
            "city": _get_city_name(s.get("city", "")) or s.get("city", ""),
        })

    # Ordenar eventos por hora dentro de cada día
    for d in days.values():
        d["events"].sort(key=lambda e: e["time"] or "23:59")

    # Calcular bloques libres aprovechando horas reales de vuelos/trenes
    for d in days.values():
        events_with_time = [e for e in d["events"] if e["time"]]
        occupied_slots: set[str] = set()
        earliest_event: int | None = None
        for e in events_with_time:
            h = int(e["time"].split(":")[0])
            if earliest_event is None or h < earliest_event:
                earliest_event = h
            if h < 12:
                occupied_slots.add("morning")
            elif h < 18:
                occupied_slots.add("afternoon")
            else:
                occupied_slots.add("evening")

        # Para días en ciudad de origen (vuelta a casa): sin sugerencias
        if d["is_origin_day"]:
            d["free_blocks"] = []
            d["has_fixed_events"] = len(d["events"]) > 0
            continue

        free_blocks = []
        # Si sabemos que el primer evento es tarde (ej: vuelo llega a las 09:15),
        # ajustamos las franjas para que el LLM sepa que la mañana está ocupada
        # solo hasta cierta hora y el resto del día queda libre
        if "morning" in occupied_slots and earliest_event is not None and earliest_event < 12:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Mañana ocupada hasta ~%d:00 (llegada de vuelo)" % earliest_event,
            })
        if "afternoon" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Tarde libre (12:00—18:00)",
            })
        if "evening" not in occupied_slots:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Noche libre (18:00—24:00)",
            })
        elif "afternoon" not in occupied_slots:
            # Si la tarde está libre, mencionamos la noche también aunque esté ocupada
            pass

        # Si no hay franjas ocupadas, día completamente libre
        if not occupied_slots:
            free_blocks = [
                {"start": None, "end": None, "label": "Mañana (06:00—12:00)"},
                {"start": None, "end": None, "label": "Tarde (12:00—18:00)"},
                {"start": None, "end": None, "label": "Noche (18:00—24:00)"},
            ]

        if not free_blocks:
            free_blocks.append({
                "start": None, "end": None,
                "label": "Día completo con eventos — tiempo libre entre medias",
            })

        d["free_blocks"] = free_blocks
        d["has_fixed_events"] = len(d["events"]) > 0

    return [days[d] for d in all_dates]


# --- DeepSeek LLM ---

def _build_itinerary_prompt(
    passes: list[dict],
    segments: list[dict],
    weather: list[dict],
    all_dates: list[str],
    num_days: int,
    *,
    trip_title: str | None = None,
) -> str:
    """Construye el prompt para DeepSeek a partir del calendario diario calculado."""

    # Determinar ciudad de origen desde el primer vuelo
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    calendar = _build_daily_calendar(passes, segments, all_dates, origin_city=origin_city)

    # Construir ciudades visitadas y nº de destinos únicos
    # Ciudades visitadas EXCLUYENDO ciudad de origen (no generar contenido sobre ella)
    all_cities = list(dict.fromkeys(
        d["city"] for d in calendar if d["city"]
    ))
    cities = [c for c in all_cities if c != origin_city] or all_cities[:1]
    dest_str = ", ".join(cities) if cities else "destino desconocido"
    unique_destinations = cities

    # --- Formatear CALENDARIO DIARIO como sección central del prompt ---
    calendar_lines = []
    for day in calendar:
        header = f"Día {day['day_number']} — {day['weekday']} {day['date']} — 📍 {day['city'] or '?'}"
        calendar_lines.append(header)

        if day["events"]:
            calendar_lines.append("  Eventos fijos (NO modificar):")
            for ev in day["events"]:
                time_part = f"  {ev['time']}" if ev["time"] else "     --"
                calendar_lines.append(f"  {time_part}  {ev['description']}")
        else:
            calendar_lines.append("  (sin eventos fijos — día libre)")

        if day["free_blocks"]:
            calendar_lines.append("  ⏳ Bloques libres para sugerir actividades:")
            for fb in day["free_blocks"]:
                calendar_lines.append(f"     • {fb['label']}")

        calendar_lines.append("")  # línea en blanco entre días

    calendar_text = "\n".join(calendar_lines)

    # --- Clima ---
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']}: {w['condition']}, max {w['temp_max']}°C, min {w['temp_min']}°C"
            for w in weather[:14]
        )

    # --- Construir el prompt ---
    prompt = f"""Eres un agente de viajes experto. Genera un itinerario enriquecido a partir del calendario base que te proporciono.

=== TÍTULO DEL VIAJE ===
{trip_title or dest_str}
Este es el nombre del viaje. El destino PRINCIPAL es {dest_str}.

=== DATOS DEL VIAJE ===
Destinos: {dest_str}
Días totales: {num_days}
Fechas: {all_dates[0]} → {all_dates[-1]}

=== CALENDARIO BASE (extraído de tus reservas reales) ===
Este es el esqueleto del viaje. Los eventos marcados como "fijos" son inamovibles
(vuelos, trenes, hoteles, restaurantes y actividades ya reservados).
Tu tarea es RELLENAR LOS HUECOS LIBRES con sugerencias.

{calendar_text}

=== CLIMA PREVISTO ===
{weather_str or "No disponible — usa clima histórico de la época."}

=== TU TAREA ===
A partir del calendario base, genera un JSON con:

1. daily_itinerary [{num_days} elementos]: Para cada día, respeta los eventos fijos tal cual aparecen en el calendario base. En los bloques libres, sugiere actividades realistas para esa ciudad, clima y franja horaria. No inventes eventos que contradigan los fijos. La ciudad de cada día ya viene determinada en el calendario base — úsala.
2. hotels: Si NO hay hoteles reservados en el calendario base, sugiere 2-3 hoteles reales en {" cada una de las ciudades: " + dest_str if len(unique_destinations) > 1 else " " + dest_str}. Si YA hay hoteles, NO sugieras otros, solo referencia los existentes.
3. restaurants: 3-4 restaurantes reales en {dest_str}. Si ya hay cenas reservadas, menciónalas en daily_itinerary y sugiere restaurantes para las comidas sin reserva.
4. places_of_interest: 3-5 lugares reales en {dest_str}.
5. historical_sites: 1-2 sitios históricos reales en {dest_str}.
6. transport_tips, general_tips, cultural_notes: tips breves y reales.

=== REGLAS ===
- SOLO nombres reales. PROHIBIDO inventar hoteles, restaurantes o museos.
- Nombres propios en idioma local. Descripciones en español.
- BREVEDAD: cada descripción ≤ 12 palabras. Tips ≤ 8 palabras.
- daily_itinerary usa EXACTAMENTE las fechas del calendario base (no inventes otras).
- Respeta check-in/check-out: el día de check-out NO sugieras actividades vinculadas a ese hotel.
- Si un día es de desplazamiento (tren/vuelo), sugiere actividades ligeras o cercanas a la estación/aeropuerto.
- Si hay "cierre puertas" en un vuelo, sugiere salir hacia el aeropuerto al menos 45 min antes de esa hora.
- Si la mañana está ocupada por un vuelo, NO sugieras actividades matutinas — empieza desde la tarde.
- Precios en €. Categorías: €, €€, €€€, €€€€.

=== FORMATO DE SALIDA ===
Responde ÚNICAMENTE con el JSON. Sin markdown, sin explicaciones.

{{
  "destination_overview": "1 frase descriptiva de {dest_str}",
  "weather_summary": "1 frase resumiendo el clima para las fechas del viaje",
  "hotels": [
    {{
      "name": "Nombre real del hotel",
      "zone": "Barrio o zona",
      "description": "1 frase breve (≤12 palabras)",
      "price_range": "€, €€, €€€ o €€€€",
      "highlights": ["Punto fuerte 1", "Punto fuerte 2"]
    }}
  ],
  "restaurants": [
    {{
      "name": "Nombre real",
      "type": "Tradicional / Fusión / Mercado / etc",
      "description": "Plato estrella (≤8 palabras)",
      "price_range": "€, €€, €€€ o €€€€"
    }}
  ],
  "places_of_interest": [
    {{
      "name": "Nombre real",
      "type": "Museo / Parque / Mirador / etc",
      "description": "1 frase (≤12 palabras)",
      "tips": ["Tip ≤8 palabras"]
    }}
  ],
  "historical_sites": [
    {{
      "name": "Nombre real",
      "period": "Siglo / época",
      "description": "1 frase (≤12 palabras)",
      "curiosity": "Dato curioso ≤10 palabras"
    }}
  ],
  "daily_itinerary": [
    {{
      "day_number": 1,
      "date": "{all_dates[0]}",
      "city": "{cities[0] if cities else '?'}",
      "theme": "Concepto del día (≤5 palabras)",
      "morning": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "afternoon": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "evening": {{ "activities": ["..."], "description": "≤12 palabras" }},
      "meal_suggestions": {{ "lunch": "Restaurante o zona (≤8 palabras)", "dinner": "Restaurante o zona (≤8 palabras)" }}
    }}
  ],
  "transport_tips": ["Tip ≤10 palabras"],
  "general_tips": ["Tip ≤10 palabras"],
  "cultural_notes": ["Nota cultural ≤10 palabras"]
}}"""

    return prompt


def _real_flight_destinations(flights: list[dict], seg_hotels: list[dict], origin: str) -> list[str]:
    """Retorna destinos reales de vuelos: excluye origen y conexiones
    (siguiente vuelo desde misma ciudad el mismo día)."""
    flights_sorted = _sort_by_date(flights)

    def es_real(idx: int) -> bool:
        f = flights_sorted[idx]
        to_city = _get_city_name(f.get("to", ""))
        if not to_city or to_city == origin:
            return False
        for sh in seg_hotels:
            if _get_city_name(sh.get("city", "")).lower() == to_city.lower():
                return True
        if idx == len(flights_sorted) - 1:
            return True
        for f2 in flights_sorted[idx + 1:]:
            if _get_city_name(f2.get("from", "")).lower() == to_city.lower():
                return f2.get("flight_date") != f.get("flight_date")
        return True

    dests = []
    for i, f in enumerate(flights_sorted):
        c = _get_city_name(f.get("to", ""))
        if c and es_real(i) and c not in dests:
            dests.append(c)
    return dests


def generate_trip_name(passes: list[dict], segments: list[dict] | None = None) -> str:
    """Genera un titulo basado en los destinos del viaje: 'Viaje a Sevilla'.
    Excluye origen y ciudades de conexión."""
    if segments is None:
        segments = []

    flights = [p for p in passes if p.get("kind") == "flight"]
    trains = [p for p in passes if p.get("kind") == "train"]
    seg_hotels = [s for s in segments if s.get("type") == "hotel"]

    origin = ""
    if flights:
        origin = _get_city_name(flights[0].get("from", ""))
    elif trains:
        # Ordenar trenes por fecha para detectar correctamente el origen
        sorted_trains = sorted(
            [t for t in trains if t.get("flight_date")],
            key=lambda t: t["flight_date"]
        )
        if sorted_trains:
            origin = _get_city_name(sorted_trains[0].get("from", ""))
        else:
            origin = _get_city_name(trains[0].get("from", ""))

    dests = _real_flight_destinations(flights, seg_hotels, origin)
    for t in trains:
        city = _get_city_name(t.get("to", ""))
        if city and city != origin and city not in dests:
            dests.append(city)
        elif not city:
            train = t.get("train", "")
            date = t.get("flight_date", "")
            label = f"Tren {train}" if train else "Tren"
            if date:
                label += f" {_format_short_date(date)}"
            if label not in dests:
                dests.append(label)
    for s in seg_hotels:
        city = s.get("city", "")
        if city and city != origin and city not in dests:
            dests.append(city)

    if dests:
        prefix = "Viaje en tren a " if (not flights and trains) else "Viaje a "
        return f"{prefix}{' y '.join(dests[:3])}"
    if flights:
        return f"Viaje a {_get_city_name(flights[0].get('to',''))}"
    if trains:
        to_city = _get_city_name(trains[0].get("to", ""))
        if to_city:
            return f"Viaje en tren a {to_city}"
        train_no = trains[0].get("train", "?")
        return f"Tren {train_no}"
    return "Viaje sin destino"


def _parse_json_response(content: str) -> dict:
    """Intenta parsear la respuesta del LLM como JSON usando multiples estrategias.

    Los LLMs a veces devuelven JSON con ruido: markdown fences, texto extra,
    comas finales, etc. Esta funcion prueba varias tecnicas de limpieza.
    """
    import re

    if not content or not content.strip():
        return {"raw_response": content, "parse_error": True}

    strategies: list[tuple[str, str]] = []

    # Estrategia 1: texto tal cual
    strategies.append(("raw", content.strip()))

    # Estrategia 2: quitar fences de markdown (```json ... ```)
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        strategies.append(("no-fences", cleaned.strip()))

    # Estrategia 3: extraer el primer objeto JSON valido con regex
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        strategies.append(("regex-extract", match.group(0)))

    # Estrategia 4: quitar comas finales antes de ] o }
    for name, text in list(strategies):
        fixed = re.sub(r",(\s*[}\]])", r"\1", text)
        if fixed != text:
            strategies.append((f"{name}-no-trailing-comma", fixed))

    # Estrategia 5: reparar JSON truncado (cerrar llaves/corchetes abiertos)
    for name, text in list(strategies):
        if text.endswith(","):
            text = text[:-1]
        # Contar aperturas y cierres, añadir los que faltan
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        if open_braces > 0 or open_brackets > 0:
            # Cerrar strings abiertos
            in_string = False
            fixed_text = list(text)
            for i, ch in enumerate(text):
                if ch == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
            if in_string:
                text += '"'
            text += "]" * max(0, open_brackets)
            text += "}" * max(0, open_braces)
            strategies.append((f"{name}-repaired-truncation", text))

    # Probar cada estrategia
    last_error = ""
    for strategy_name, text in strategies:
        try:
            result = json.loads(text)
            print(f"[parse_json] success with strategy: {strategy_name}")
            return result
        except json.JSONDecodeError as e:
            last_error = f"{strategy_name}: {e}"

    print(f"[parse_json] all strategies failed: {last_error}")
    return {
        "raw_response": content[:2000],
        "parse_error": True,
    }


def _build_basic_itinerary(
    passes: list[dict],
    segments: list[dict],
    weather: list[dict],
    all_dates: list[str],
    num_days: int,
) -> dict:
    """Devuelve un itinerario básico (sin LLM) a partir del calendario diario.

    Se usa como fallback cuando no hay DEEPSEEK_API_KEY configurada.
    Contiene solo los eventos fijos extraídos de pases y segmentos, sin
    sugerencias de restaurantes, lugares de interés ni notas culturales.
    """
    # Determinar origen desde el primer vuelo
    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    calendar = _build_daily_calendar(passes, segments, all_dates, origin_city=origin_city)

    cities = list(dict.fromkeys(
        d["city"] for d in calendar if d["city"]
    ))

    daily = []
    for day in calendar:
        entry: dict = {
            "day_number": day["day_number"],
            "date": day["date"],
            "city": day["city"],
            "theme": f"Día en {day['city']}" if day["city"] else "Día de viaje",
            "morning": {"activities": [], "description": ""},
            "afternoon": {"activities": [], "description": ""},
            "evening": {"activities": [], "description": ""},
            "meal_suggestions": {"lunch": "", "dinner": ""},
        }
        for ev in day["events"]:
            desc = ev["description"]
            if ev["type"] in ("flight_arrival", "train_arrival"):
                entry["morning"]["activities"].append(desc)
            elif ev["type"] in ("restaurant",):
                entry["evening"]["activities"].append(desc)
                entry["meal_suggestions"]["dinner"] = desc.replace("Cena: ", "")
            elif ev["type"] in ("activity",):
                entry["afternoon"]["activities"].append(desc)
            else:
                entry["morning"]["activities"].append(desc)

        if day["free_blocks"]:
            for fb in day["free_blocks"]:
                if "Mañana" in fb["label"]:
                    entry["morning"]["description"] = fb["label"]
                elif "Día completo" in fb["label"]:
                    entry["morning"]["description"] = "Día libre"
                elif "Noche" in fb["label"]:
                    entry["evening"]["description"] = fb["label"]
                else:
                    entry["afternoon"]["description"] = fb["label"]

        daily.append(entry)

    return {
        "destination_overview": f"Viaje a {', '.join(cities)}" if cities else "Viaje",
        "weather_summary": "",
        "hotels": [],
        "restaurants": [],
        "places_of_interest": [],
        "historical_sites": [],
        "daily_itinerary": daily,
        "transport_tips": [],
        "general_tips": [],
        "cultural_notes": [],
        "basic_mode": True,
    }


async def generate_itinerary(
    passes: list[dict],
    segments: list[dict] | None = None,
    session_id: str | None = None,
) -> dict:
    """Genera un itinerario completo usando DeepSeek LLM y Open-Meteo.

    Args:
        passes: Lista de pases extraidos de billetes.
        segments: Segmentos manuales (hoteles, vuelos, etc.).
        session_id: ID de sesion para tracking de tokens (opcional).
    """
    from datetime import timedelta

    if segments is None:
        segments = []

    # Re-ejecutar infer_years con TODOS los pases juntos:
    # en la API cada extract corre infer_years por separado y no detecta
    # rollover de año (DOY 365 -> 002). Aqui con todos los pases juntos
    # sí detecta el cruce y corrige las fechas.
    infer_years(passes)

    flights = [p for p in passes if p.get("kind") == "flight"]
    seg_flights = [s for s in segments if s.get("type") == "flight"]
    seg_hotels = [s for s in segments if s.get("type") == "hotel"]
    seg_activities = [s for s in segments if s.get("type") == "activity"]

    # 1. Calcular todas las fechas del viaje (de pases + segmentos manuales)
    all_dates_set: set[str] = set()

    # Fechas de vuelos extraidos
    for p in flights:
        fd = p.get("flight_date")
        if fd:
            all_dates_set.add(fd)

    # Fechas de trenes (pases)
    for p in passes:
        if p.get("kind") == "train":
            fd = p.get("flight_date")
            if fd:
                all_dates_set.add(fd)

    # Fechas de segmentos manuales
    for s in seg_flights + seg_activities:
        fd = s.get("date")
        if fd:
            all_dates_set.add(fd)
    for s in seg_hotels:
        for key in ("check_in", "check_out"):
            fd = s.get(key)
            if fd:
                all_dates_set.add(fd)
    # Fechas de coches
    for s in segments:
        if s.get("type") == "car":
            for key in ("pickup_date", "return_date"):
                fd = s.get(key)
                if fd:
                    all_dates_set.add(fd)

    all_dates: list[str] = sorted(all_dates_set) if all_dates_set else [date.today().isoformat()]

    # Expandir rango (si hay check_in y check_out, rellenar dias intermedios)
    if all_dates:
        try:
            start = date.fromisoformat(all_dates[0])
            end = date.fromisoformat(all_dates[-1])
            expanded = []
            current = start
            while current <= end:
                expanded.append(current.isoformat())
                current += timedelta(days=1)
            all_dates = expanded
        except ValueError:
            pass

    num_days = len(all_dates)

    # Safety: nunca tener más de 31 días (un mes máximo) — evita year-inference bugs
    if num_days > 31:
        print(f"[itinerary] WARNING: {num_days} días es sospechoso, limitando a 31")
        all_dates = all_dates[:31]
        num_days = 31

    # Calcular título del viaje para pasarlo al prompt
    trip_title = generate_trip_name(passes, segments)

    # 2. Guardrail: verificar que hay destinos identificables
    # antes de gastar tokens del LLM en datos inservibles.
    weather: list[dict] = []
    calendar_check = _build_daily_calendar(passes, segments, all_dates)
    identified_cities = [d["city"] for d in calendar_check if d["city"]]
    has_events = any(d["has_fixed_events"] for d in calendar_check)
    if not identified_cities:
        print("[itinerary] ERROR: no se pudo determinar ninguna ciudad de destino")
        return {
            "error": "No se pudo determinar el destino del viaje. Añade al menos un vuelo, tren, hotel o actividad con ciudad.",
            "weather": weather,
        }
    if not has_events and not DEEPSEEK_API_KEY:
        print("[itinerary] ERROR: sin eventos fijos ni API key — imposible generar")
        return {
            "error": "Sin reservas ni eventos. Añade vuelos, hoteles o actividades y configura DEEPSEEK_API_KEY.",
            "weather": weather,
        }

    # 3. Obtener clima para el primer destino con coordenadas
    weather = []
    for src_list in (flights, seg_flights):
        for item in src_list:
            code = item.get("to", item.get("to_city", ""))
            if code and _get_coords(code.upper()):
                weather = await fetch_weather(code.upper(), all_dates[0], all_dates[-1])
                break
        if weather:
            break

    # Si no hay vuelos, usar primera ciudad de hotel
    if not weather:
        for h in seg_hotels:
            city = h.get("city", "")
            # Buscar coordenadas por nombre de ciudad
            for code, name in AIRPORT_CITY_NAMES.items():
                if name.lower() == city.lower() and _get_coords(code):
                    weather = await fetch_weather(code, all_dates[0], all_dates[-1])
                    break
            if weather:
                break

    # 3. Generar recomendaciones con DeepSeek
    # Si no hay API key, devolvemos un itinerario basico (solo clima + estructura)
    if not DEEPSEEK_API_KEY:
        print("[itinerary] DEEPSEEK_API_KEY no configurada: devolviendo itinerario basico")
        basic = _build_basic_itinerary(passes, segments, weather, all_dates, num_days)
        return {
            "warning": "Itinerario basico: configura DEEPSEEK_API_KEY para recomendaciones personalizadas",
            "weather": weather,
            **basic,
        }

    prompt = _build_itinerary_prompt(passes, segments, weather, all_dates, num_days, trip_title=trip_title)

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Eres un asistente de viajes experto. Responde SIEMPRE solo con JSON valido, sin markdown ni texto adicional."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=16384,
        )
        content = response.choices[0].message.content or ""
        print(f"[deepseek] response length: {len(content)} chars")

        # Registrar consumo real de tokens de la API
        if session_id and response.usage:
            from token_tracker import record_usage
            token_stats = record_usage(
                session_id,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            print(f"[deepseek] tokens: {response.usage.prompt_tokens} in + "
                  f"{response.usage.completion_tokens} out = "
                  f"{response.usage.total_tokens} total "
                  f"(sesion: {token_stats['total_tokens_used']}/"
                  f"{token_stats['max_tokens']})")
    except Exception as e:
        print(f"[deepseek] Error: {e}")
        return {
            "error": f"Error al generar itinerario: {e}",
            "weather": weather,
        }

    # 3. Parsear JSON con limpieza robusta
    itinerary = _parse_json_response(content)

    # Añadir clima al resultado
    itinerary["weather"] = weather

    # Añadir metadatos del viaje
    destinations = list(set(
        _get_city_name(p.get("to", ""))
        for p in passes if p.get("kind") == "flight" and p.get("to")
    ))
    itinerary["meta"] = {
        "destinations": destinations,
        "pass_count": len(passes),
        "generated_at": datetime.now().isoformat(),
    }

    # Incluir estadisticas de tokens (app.py las extrae con pop)
    if session_id and response.usage:
        itinerary["_token_usage"] = token_stats

    return itinerary


def _serialize_for_prompt(items: list[dict], keys: list[str]) -> str:
    """Serializa items para incluir en el prompt."""
    lines = []
    for i, item in enumerate(items, 1):
        parts = [f"{i}. "]
        for k in keys:
            val = item.get(k)
            if val:
                if isinstance(val, list):
                    parts.append(f"{k}: {', '.join(val)}")
                else:
                    parts.append(f"{k}: {val}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if lines else "(ninguno)"


def expand_section(
    passes: list[dict],
    segments: list[dict],
    existing_itinerary: dict,
    section: str,
    session_id: str | None = None,
) -> dict:
    """Genera mas recomendaciones de una seccion concreta del itinerario.

    Returns dict with either:
      - {"items": [...], "section": str}
      - {"error": str}
      - For "visit": {"places_of_interest": [...], "historical_sites": [...], "section": "visit"}
      - For "tips": {"transport_tips": [...], "general_tips": [...], "cultural_notes": [...], "section": "tips"}
    """
    from datetime import timedelta

    if segments is None:
        segments = []

    flights = [p for p in passes if p.get("kind") == "flight"]
    flights_sorted = _sort_by_date(flights)
    origin_city = _get_city_name(flights_sorted[0].get("from", "")) if flights_sorted else None

    all_dates_set = set()
    for p in passes:
        fd = p.get("flight_date")
        if fd:
            all_dates_set.add(fd)
    for s in segments:
        fd = s.get("date") or s.get("check_in")
        if fd:
            all_dates_set.add(fd)

    all_dates = sorted(all_dates_set)
    dates_str = ", ".join(all_dates) if all_dates else "fechas no especificadas"

    all_cities = list(dict.fromkeys(
        d.get("city") for d in _build_daily_calendar(passes, segments, all_dates)
        if d.get("city")
    ))
    cities = [c for c in all_cities if c != origin_city] or all_cities[:1]
    dest_str = ", ".join(cities) if cities else "destino desconocido"

    passenger_names = list(dict.fromkeys(
        p.get("name", "") for p in passes if p.get("name")
    ))
    passengers_str = ", ".join(passenger_names) if passenger_names else "no especificado"

    overview = existing_itinerary.get("destination_overview", "")
    weather = existing_itinerary.get("weather", [])
    weather_str = ""
    if weather:
        weather_str = "\n".join(
            f"  {w['date']}: {w['condition']}, max {w['temp_max']}°C, min {w['temp_min']}°C"
            for w in weather[:7]
        )

    passes_str = ""
    for p in passes:
        route = f"{p.get('from', '?')} → {p.get('to', '?')}"
        d = p.get("flight_date", "")
        t = p.get("flight_time", "")
        carrier = p.get("train") or f"{p.get('airline', '')}{p.get('flight', '')}"
        passes_str += f"  - {route} | {d} {t} | {carrier} | {p.get('kind', 'flight')}\n"

    seg_str = ""
    for s in segments:
        stype = s.get("type", "")
        if stype == "flight":
            seg_str += f"  - Vuelo: {s.get('airline','')}{s.get('flight_number','')} {s.get('from','')}→{s.get('to','')} {s.get('date','')} {s.get('time','')}\n"
        elif stype == "train":
            seg_str += f"  - Tren: {s.get('operator','')} {s.get('train_number','')} {s.get('from','')}→{s.get('to','')} {s.get('date','')}\n"
        elif stype == "hotel":
            seg_str += f"  - Hotel: {s.get('name','')} {s.get('city','')} {s.get('check_in','')}→{s.get('check_out','')}\n"
        elif stype == "car":
            seg_str += f"  - Coche: {s.get('company','')} {s.get('city','')} {s.get('pickup_date','')}→{s.get('return_date','')}\n"
        elif stype == "restaurant":
            seg_str += f"  - Restaurante: {s.get('name','')} {s.get('city','')} {s.get('date','')}\n"
        elif stype == "activity":
            seg_str += f"  - Actividad: {s.get('name','')} {s.get('city','')} {s.get('date','')} - {s.get('description','')}\n"

    section_prompts = {
        "restaurants": {
            "section_name": "restaurantes",
            "existing": _serialize_for_prompt(existing_itinerary.get("restaurants", []), ["name", "type", "price_range"]),
            "instruction": "Devuelve un array JSON con 3-5 nuevos restaurantes que sean DIFERENTES a los ya listados.",
            "output_schema": '{"name": "Nombre restaurante", "type": "cocina catalana", "description": "2-3 frases llamativas", "price_range": "15-30€"}',
        },
        "hotels": {
            "section_name": "hospedaje",
            "existing": _serialize_for_prompt(existing_itinerary.get("hotels", []), ["name", "zone", "price_range"]),
            "instruction": "Devuelve un array JSON con 3-5 nuevos hoteles/alojamientos DIFERENTES a los ya listados.",
            "output_schema": '{"name": "Nombre hotel", "zone": "barrio o zona", "description": "2-3 frases", "price_range": "80-150€", "highlights": ["piscina", "vistas"]}',
        },
        "visit": {
            "section_name": "lugares que visitar",
            "existing": _serialize_for_prompt(
                existing_itinerary.get("places_of_interest", []) + existing_itinerary.get("historical_sites", []),
                ["name", "type", "period"],
            ),
            "instruction": "Devuelve un objeto JSON con dos arrays: 'places_of_interest' (no historicos) y 'historical_sites' (sitios historicos con 'period' y 'curiosity'). 2-3 por categoria. DIFERENTES a los ya listados.",
            "output_schema": '{"places_of_interest": [{"name": "...", "type": "museo", "description": "...", "tips": ["..."]}], "historical_sites": [{"name": "...", "period": "s.XIX", "description": "...", "curiosity": "... rumor curioso"}]}',
        },
        "tips": {
            "section_name": "consejos",
            "existing": _serialize_for_prompt(
                [{"tip": t} for t in existing_itinerary.get("transport_tips", [])]
                + [{"tip": t} for t in existing_itinerary.get("general_tips", [])]
                + [{"tip": t} for t in existing_itinerary.get("cultural_notes", [])],
                ["tip"],
            ),
            "instruction": "Devuelve un objeto JSON con 3 arrays: 'transport_tips', 'general_tips', 'cultural_notes'. 2-3 tips por categoria. DIFERENTES a los ya listados.",
            "output_schema": '{"transport_tips": ["tip transporte..."], "general_tips": ["tip general..."], "cultural_notes": ["nota cultural..."]}',
        },
    }

    sec = section_prompts.get(section)
    if not sec:
        return {"error": "Seccion desconocida"}

    prompt = f"""Eres un guia local experto. El usuario pide MAS recomendaciones para su viaje.

VIAJE: {dest_str}
FECHAS: {dates_str}
PASAJEROS: {passengers_str}
{chr(10) + "RESUMEN: " + overview[:500] if overview else ""}

CLIMA PREVISTO:
{weather_str or "(no disponible)"}

BILLETES:
{passes_str if passes_str else "(sin billetes)"}
RESERVAS MANUALES:
{seg_str if seg_str else "(ninguna)"}

YA RECOMENDADO ({sec['section_name']}):
{sec['existing']}

{sec['instruction']}

Estructura esperada del JSON:
{sec['output_schema']}

Responde SOLO el JSON, sin markdown ni texto alrededor."""

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Eres un guia de viajes experto. Responde solo JSON valido, sin markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=4096,
        )
        content = response.choices[0].message.content or "{}"

        if session_id and response.usage:
            from token_tracker import record_usage
            record_usage(session_id, response.usage.prompt_tokens, response.usage.completion_tokens)

    except Exception as e:
        print(f"[deepseek expand] Error: {e}")
        return {"error": f"Error al expandir {sec['section_name']}: {e}"}

    new_items = _parse_expand_response(content, section)

    if section == "visit":
        return {
            "places_of_interest": new_items.get("places_of_interest", []),
            "historical_sites": new_items.get("historical_sites", []),
            "section": section,
        }
    if section == "tips":
        return {
            "transport_tips": new_items.get("transport_tips", []),
            "general_tips": new_items.get("general_tips", []),
            "cultural_notes": new_items.get("cultural_notes", []),
            "section": section,
        }
    if isinstance(new_items, list):
        return {"items": new_items, "section": section}
    return {"items": [], "section": section}


def _parse_expand_response(content: str, section: str) -> dict | list:
    """Parsea la respuesta JSON del LLM con fallback robusto."""
    import re

    try:
        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return [] if section in ("restaurants", "hotels") else {}
````

## File: boarding-pass/src/app/trips/trips.page.ts
````typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { AlertController, ToastController } from '@ionic/angular';
import { FilePicker } from '@capawesome/capacitor-file-picker';
import { firstValueFrom } from 'rxjs';
import { BoardingPassService, Pass, Trip } from '../services/boarding-pass.service';

@Component({
  selector: 'app-trips',
  templateUrl: './trips.page.html',
  styleUrls: ['./trips.page.scss'],
  standalone: false,
})
export class TripsPage {
  trips: Trip[] = [];
  loading = true;

  busy = false;
  progress = '';
  private cancelled = false;

  constructor(
    private svc: BoardingPassService,
    private router: Router,
    private alertCtrl: AlertController,
    private toastCtrl: ToastController,
  ) {}

  cancel() {
    this.cancelled = true;
    this.busy = false;
    this.progress = '';
  }

  onRefresh(event: any) {
    this.loadTrips();
    event.target.complete();
  }

  /** Ionic lifecycle: se ejecuta cada vez que la pagina se muestra. */
  ionViewWillEnter() {
    this.loadTrips();
  }

  loadTrips() {
    this.loading = true;
    const sid = this.svc.getSessionId();
    console.debug('[TripsPage] loadTrips session:', sid);
    this.svc.getTrips().subscribe({
      next: (resp) => {
        console.debug('[TripsPage] trips recibidos:', resp.trips.length);
        this.trips = resp.trips;
        this.loading = false;
      },
      error: (err: any) => {
        console.error('[TripsPage] error:', err);
        this.loading = false;
        this.toast('Error al cargar viajes: ' + (err?.error?.detail ?? err?.message ?? err), 'danger');
      },
    });
  }

  viewTrip(trip: Trip) {
    this.router.navigate(['/itinerary'], {
      state: {
        tripId: trip.id,
        passes: trip.pass_data.passes,
        images: trip.pass_data.images,
        segments: trip.segments || [],
        tripName: trip.trip_name || trip.filename,
      },
    });
  }

  async deleteTrip(trip: Trip) {
    const alert = await this.alertCtrl.create({
      header: 'Eliminar viaje',
      message: `¿Borrar "${trip.filename}"?`,
      buttons: [
        { text: 'Cancelar', role: 'cancel' },
        {
          text: 'Eliminar',
          role: 'destructive',
          handler: () => {
            try { Haptics.impact({ style: ImpactStyle.Heavy }); } catch {}
            this.svc.deleteTrip(trip.id).subscribe({
              next: () => {
                this.trips = this.trips.filter((t) => t.id !== trip.id);
                this.toast('Viaje eliminado', 'success');
              },
              error: (err: any) =>
                this.toast('Error: ' + (err?.error?.detail ?? err?.message ?? err), 'danger'),
            });
          },
        },
      ],
    });
    await alert.present();
  }

  labelFor(pass: any): string {
    if (pass.kind === 'flight' || pass.airline) {
      const route = `${pass.from ?? '?'} → ${pass.to ?? '?'}`;
      const fl = pass.flight ? ` · ${pass.airline ?? ''}${pass.flight}` : '';
      return `${route}${fl}`;
    }
    if (pass.kind === 'train' || pass.train) {
      return `Tren ${pass.train ?? '?'}`;
    }
    return pass.format ?? 'Desconocido';
  }

  goHome() {
    this.router.navigate(['/home']);
  }

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

    this.busy = true;

    const allPasses: Pass[] = [];
    const allImages: any[] = [];
    const filenames: string[] = [];
    let errors = 0;
    const errorMessages: string[] = [];

    for (let i = 0; i < picked.length; i++) {
      if (this.cancelled) break;
      const file = picked[i];
      const filename = file.name || `pdf_${i + 1}.pdf`;
      this.progress = `${i + 1}/${picked.length}`;

      try {
        const blob = await this.toBlob(file);
        const resp = await firstValueFrom(this.svc.uploadPdf(blob, file.name));
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
      if (this.cancelled) break;
    }
    if (this.cancelled) {
      this.cancelled = false;
      this.busy = false;
      this.progress = '';
      return;
    }

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

    try {
      await firstValueFrom(this.svc.saveTrip(combinedName, allPasses, allImages));
    } catch (e: any) {
      console.error('Error guardando viaje:', e);
    }
    this.loadTrips();
  }

  private async toBlob(picked: any): Promise<Blob> {
    const name = picked.name ?? 'file';
    const mime = picked.mimeType || '';
    const b64 = picked.data || picked.blob;
    if (typeof b64 === 'string' && b64.length > 0) {
      let clean = b64.includes(',') ? b64.split(',')[1] : b64;
      try {
        const chars = atob(clean);
        const bytes = new Uint8Array(chars.length);
        for (let i = 0; i < chars.length; i++) bytes[i] = chars.charCodeAt(i);
        return new Blob([bytes], { type: mime });
      } catch (e: any) {
        throw new Error('Base64 decode failed: ' + e.message);
      }
    }
    if (picked.blob instanceof Blob) {
      return picked.blob;
    }
    const url = picked.path ?? picked.uri ?? '';
    if (url) {
      const resp = await fetch(url);
      const blob = await resp.blob();
      return blob;
    }
    throw new Error('No file data available');
  }


  goToItinerary(trip: Trip) {
    this.viewTrip(trip);
  }

  editTrip(trip: Trip) {
    this.router.navigate(['/trip-create'], {
      state: { editTripId: trip.id, tripName: trip.trip_name, segments: trip.segments },
    });
  }

  tripDateRange(trip: Trip): string {
    const dates = trip.pass_data.passes
      .map(p => p.flight_date)
      .filter((d): d is string => !!d)
      .sort();
    if (!dates.length) return '';
    if (dates.length === 1) return this.formatShortDate(dates[0]);
    const first = this.formatShortDate(dates[0]);
    const last = this.formatShortDate(dates[dates.length - 1]);
    return `${first} — ${last}`;
  }

  private formatShortDate(date: string): string {
    const parts = date.split('-');
    if (parts.length !== 3) return date;
    return `${parts[2]}/${parts[1]}`;
  }

  /** Determina el icono de modo de transporte para la tarjeta del viaje. */
  tripModeIcon(trip: Trip): string {
    const hasTrain = trip.pass_data.passes.some(p => p.kind === 'train');
    return hasTrain ? 'train-outline' : 'airplane-outline';
  }

  /** Extrae el código de origen del primer vuelo o tren. */
  getOriginCode(trip: Trip): string {
    const flight = trip.pass_data.passes.find(x => x.kind === 'flight');
    if (flight?.from) return flight.from as string;
    const train = trip.pass_data.passes.find(x => x.kind === 'train');
    if (train?.from) {
      const from = train.from as string;
      return from.includes(' - ') ? from.split(' - ')[0] : from;
    }
    return '—';
  }

  /** Extrae el destino del primer vuelo o tren (ida, no vuelta). */
  getDestCode(trip: Trip): string {
    const flights = trip.pass_data.passes.filter(x => x.kind === 'flight');
    if (flights.length) {
      return (flights[0]?.to as string) || '—';
    }
    const train = trip.pass_data.passes.find(x => x.kind === 'train');
    if (train?.to) {
      const to = train.to as string;
      return to.includes(' - ') ? to.split(' - ')[0] : to;
    }
    return '—';
  }

  private async toast(msg: string, color: string) {
    const t = await this.toastCtrl.create({ message: msg, duration: 3000, color });
    await t.present();
  }
}
````

## File: backend/app.py
````python
"""
API REST que envuelve el algoritmo de extraccion de QR/barcodes.

Endpoints:
  GET  /health              -> liveness check
  POST /api/extract         -> sube un PDF, devuelve codes + campos parseados
  GET  /api/trips           -> lista viajes de la sesion
  POST /api/trips           -> guarda un viaje (con deduplicacion)
  DELETE /api/trips/{id}    -> borra un viaje
"""

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from qr_client import extract_codes, extract_codes_from_image  # noqa: E402
from itinerary import expand_section, generate_itinerary, generate_trip_name  # noqa: E402
from parser import infer_years, parse_code  # noqa: E402
from token_tracker import check_limit, get_usage  # noqa: E402
from token_tracker import _ensure_table as _ensure_token_table  # noqa: E402
from admin import router as admin_router  # noqa: E402

DB_PATH = Path(__file__).resolve().parent / "trips.db"


def _get_db() -> sqlite3.Connection:
    """Crea o abre la base de datos SQLite y devuelve una conexion.
    Si la tabla trips no existe (BD borrada), la recrea automaticamente."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("SELECT 1 FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.close()
        _init_db()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Inicializa la tabla de viajes si no existe."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            pass_data TEXT NOT NULL,
            fingerprint TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trips_session
        ON trips(session_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trips_fingerprint
        ON trips(session_id, fingerprint)
    """)
    # Migracion: si la columna fingerprint no existe en una BD vieja, añadirla
    try:
        conn.execute("SELECT fingerprint FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''")
    try:
        conn.execute("SELECT updated_at FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN updated_at TEXT")
    try:
        conn.execute("SELECT itinerary_data FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN itinerary_data TEXT")
    try:
        conn.execute("SELECT trip_name FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN trip_name TEXT NOT NULL DEFAULT ''")
    try:
        conn.execute("SELECT segments FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE trips ADD COLUMN segments TEXT NOT NULL DEFAULT '[]'")
    conn.commit()
    conn.close()
    # Asegurar que la tabla de tracking de tokens tambien existe
    _ensure_token_table()


# Inicializar DB al arrancar
_init_db()

app = FastAPI(title="Boarding Pass Extractor", version="0.3.0")

# CORS permisivo para que la app Ionic pueda llamar en desarrollo
# (en produccion conviene restringir al dominio de la app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router de admin (dashboard de monitoreo de tokens)
app.include_router(admin_router)


# --- Session helper ---

def _get_session_id(request: Request) -> str:
    """Obtiene el session_id del header X-Session-Id, o crea uno nuevo."""
    sid = request.headers.get("X-Session-Id", "").strip()
    if not sid:
        sid = f"ses_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    return sid


# --- Fingerprint helpers ---

def _pass_fingerprint(p: dict) -> str:
    """Genera una huella unica para un pase basada en sus campos significativos.

    Vuelos:    kind + pnr + flight_date + flight + from + to
    Trenes:    kind + pnr + train + flight_date + flight_time + class
    Desconocido: kind + format + raw (truncado a 200 chars)
    Publicidad: se ignoran (no generan huella)
    """
    kind = (p.get("kind") or "").strip().lower()

    # Ignorar publicidad y URLs
    if kind == "advertising":
        return ""

    if kind == "flight":
        parts = [
            kind,
            (p.get("pnr") or "").strip().upper(),
            (p.get("flight_date") or "").strip(),
            (p.get("flight") or "").strip(),
            (p.get("from") or "").strip().upper(),
            (p.get("to") or "").strip().upper(),
        ]
    elif kind == "train":
        parts = [
            kind,
            (p.get("pnr") or "").strip().upper(),
            (p.get("train") or "").strip(),
            (p.get("flight_date") or "").strip(),
            (p.get("flight_time") or "").strip(),
            (p.get("class") or "").strip().upper(),
        ]
    else:
        raw = (p.get("raw") or "")[:200]
        parts = [
            kind or "unknown",
            (p.get("format") or "").strip(),
            raw,
        ]

    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _trip_fingerprint(passes: list[dict]) -> str:
    """Combina las huellas de todos los pases en una huella unica del viaje.

    Los pases se ordenan para que el orden de extraccion no afecte.
    Solo se consideran pases con huella no vacia (se ignoran ads).
    """
    fps = sorted(
        fp for p in passes if (fp := _pass_fingerprint(p))
    )
    if not fps:
        # Si no hay pases validos, usar hash del JSON completo
        raw = json.dumps(passes, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    return hashlib.sha256("|||".join(fps).encode()).hexdigest()[:16]


# --- Health ---

@app.get("/health")
def health():
    return {"status": "ok"}


# --- Validacion de pases ---

def _is_pass_complete(pass_data: dict) -> tuple[bool, str]:
    """Comprueba que un pase tiene todos los datos esenciales.
    Devuelve (ok, motivo) donde ok=True si es valido."""
    kind = pass_data.get("kind")
    if kind not in ("flight", "train"):
        return False, f"tipo desconocido {kind!r}"
    if not pass_data.get("flight_date"):
        return False, "falta fecha"
    if kind == "flight":
        if not pass_data.get("pnr"):
            return False, "vuelo sin localizador"
        if not pass_data.get("from") or not pass_data.get("to"):
            return False, "vuelo sin origen/destino"
        if not pass_data.get("name") or not pass_data.get("airline") or not pass_data.get("flight"):
            return False, "vuelo sin nombre/aerolinea/numero"
    if kind == "train":
        if not pass_data.get("train"):
            return False, "tren sin numero"
    return True, ""


# --- Extract ---

@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
    ALLOWED = {".pdf"} | IMG_EXTS

    if not file.filename:
        raise HTTPException(status_code=400, detail="Falta el nombre del archivo")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, PNG, JPG, WebP, BMP o TIFF")

    is_image = ext in IMG_EXTS

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = os.path.join(tmp, f"upload{ext}")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)

        try:
            if is_image:
                results, ocr_data = extract_codes_from_image(upload_path, out_dir)
                text_fields = {}
            else:
                # extract_codes ahora devuelve (codes, text_fields) para
                # evitar reabrir el PDF (fitz falla con rutas 8.3 / acentos).
                pdf_codes, text_fields = extract_codes(upload_path, out_dir)
                results = pdf_codes
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extrayendo: {e}")

    # results = [(page, fname, b64, text, format, origin), ...]
    # text_fields ya viene dentro del tuple de extract_codes para evitar
    # reabrir el PDF (fitz/PyMuPDF falla con rutas 8.3 / acentos en Windows).

    passes = []
    images = []
    descartados = 0
    for page, fname, b64, text, fmt, origin in results:
        parsed = parse_code(text)
        if parsed is None:
            descartados += 1
            print(f"[extract] p{page} descartado: {text[:60]!r}")
            continue
        # Mezclar campos del texto del PDF (solo si el barcode no los tiene)
        extras = text_fields.get(page, {})
        if extras:
            for key in ("from", "to", "seat", "name", "flight_time", "train", "coach", "pnr", "operator"):
                if key in extras and not parsed.get(key):
                    parsed[key] = extras[key]
            # Para trenes: sobreescribir train si el barcode empieza por 000 (invalido)
            if parsed.get("kind") == "train" and extras.get("train"):
                barcode_train = str(parsed.get("train", ""))
                if barcode_train.startswith("000") or barcode_train.lstrip("0") == "":
                    parsed["train"] = extras["train"]
            # Para trenes: usar el operador detectado como airline
            if parsed.get("kind") == "train" and parsed.get("operator") and not parsed.get("airline"):
                parsed["airline"] = parsed["operator"]
            # Si el código no tiene año (IATA BCBP) pero el PDF tiene fecha, usarla
            if not parsed.get("has_explicit_year") and extras.get("flight_date"):
                parsed["flight_date"] = extras["flight_date"]
                parsed["has_explicit_year"] = True
        # Mezclar hora de OCR (imagenes) si el barcode no la tiene
        if is_image and ocr_data:
            if ocr_data.get("flight_time") and not parsed.get("flight_time"):
                parsed["flight_time"] = ocr_data["flight_time"]
            if ocr_data.get("gate_close_time"):
                parsed["gate_close_time"] = ocr_data["gate_close_time"]
        # Validacion completa: descartar si faltan datos esenciales
        ok, motivo = _is_pass_complete(parsed)
        if not ok:
            descartados += 1
            raw_preview = parsed.get('raw', '')[:80] if parsed.get('raw') else text[:80]
            print(f"[extract] p{page} descartado ({motivo}): fmt={parsed.get('format','?')} raw={raw_preview!r}")
            continue
        passes.append({
            "page": page,
            "origin": origin,
            **parsed,
        })
        images.append({
            "page": page,
            "format": fmt,
            "filename": fname,
            "base64": b64,
        })
    if descartados:
        print(f"[extract] {descartados} pases descartados por datos incompletos")

    # Inferir años para vuelos sin año explícito (Ryanair, etc.)
    infer_years(passes)

    return {
        "filename": file.filename,
        "passes": passes,
        "images": images,
        "count": len(passes),
    }


# --- Trips CRUD ---

@app.get("/api/trips")
def list_trips(request: Request, x_session_id: str = Header(default="")):
    """Lista todos los viajes guardados para la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)
    print(f"[list_trips] session_id={sid} header={x_session_id!r}")
    if not sid:
        return {"trips": [], "session_id": ""}

    conn = _get_db()
    rows = conn.execute(
        "SELECT id, session_id, filename, pass_data, created_at, updated_at, trip_name, segments "
        "FROM trips WHERE session_id = ? ORDER BY created_at DESC",
        (sid,),
    ).fetchall()
    conn.close()

    print(f"[list_trips] found {len(rows)} trips for session {sid}")

    trips = []
    for r in rows:
        trips.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "filename": r["filename"],
            "trip_name": r["trip_name"] or "",
            "pass_data": json.loads(r["pass_data"]),
            "segments": json.loads(r["segments"] or "[]"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return {"trips": trips, "session_id": sid}


@app.post("/api/trips")
async def create_trip(request: Request, x_session_id: str = Header(default="")):
    """Guarda un viaje con deduplicacion.

    - Si el viaje no existe (misma huella) -> INSERT (status: created)
    - Si existe con mismos datos -> no hace nada (status: duplicate)
    - Si existe con datos distintos -> UPDATE (status: updated)

    Body: {filename, passes, images}
    """
    sid = _get_session_id_via_header(request, x_session_id)

    body = await request.json()
    filename = body.get("filename", "unknown.pdf")
    trip_name = body.get("trip_name", "").strip()
    passes = body.get("passes", body.get("pass_data", []))
    images = body.get("images", [])
    segments = body.get("segments", [])

    # Validar que todos los pases tengan datos completos
    for p in passes:
        ok, motivo = _is_pass_complete(p)
        if not ok:
            raise HTTPException(
                status_code=400,
                detail=f"Pase incompleto rechazado: {motivo}. Re-subir el archivo desde la home.",
            )

    # Auto-generar nombre si no se proporciono
    if not trip_name:
        try:
            trip_name = generate_trip_name(passes, segments)
        except Exception as e:
            print(f"[create_trip] Error generando nombre: {e}")
            trip_name = filename

    new_data = json.dumps({"passes": passes, "images": images}, ensure_ascii=False, sort_keys=True)
    fingerprint = _trip_fingerprint(passes)

    print(f"[create_trip] session_id={sid} fingerprint={fingerprint} passes={len(passes)} file={filename}")

    conn = _get_db()

    # Buscar viaje existente con la misma huella en esta sesion
    existing = conn.execute(
        "SELECT id, pass_data FROM trips "
        "WHERE session_id = ? AND fingerprint = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (sid, fingerprint),
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        existing_data = existing["pass_data"]

        # Comparar datos normalizados (ignorando whitespace en JSON)
        if json.loads(existing_data) == json.loads(new_data):
            conn.close()
            return {
                "status": "duplicate",
                "id": existing["id"],
                "session_id": sid,
                "filename": filename,
                "trip_name": trip_name,
                "message": "Este viaje ya estaba guardado, sin cambios",
            }

        # Datos distintos -> actualizar
        conn.execute(
            "UPDATE trips SET filename = ?, pass_data = ?, updated_at = ? WHERE id = ?",
            (filename, new_data, now, existing["id"]),
        )
        conn.commit()
        conn.close()
        return {
            "status": "updated",
            "id": existing["id"],
            "session_id": sid,
            "filename": filename,
            "message": "Viaje actualizado con nuevos datos",
        }

    # No existe -> insertar
    segments_json = json.dumps(segments, ensure_ascii=False)
    cursor = conn.execute(
        "INSERT INTO trips (session_id, filename, pass_data, fingerprint, trip_name, segments) VALUES (?, ?, ?, ?, ?, ?)",
        (sid, filename, new_data, fingerprint, trip_name, segments_json),
    )
    trip_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "created",
        "id": trip_id,
        "session_id": sid,
        "filename": filename,
        "trip_name": trip_name,
        "message": "Viaje guardado",
    }


@app.delete("/api/trips/{trip_id}")
def delete_trip(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Borra un viaje por ID, solo si pertenece a la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()

    return {"ok": True, "deleted": trip_id}


# --- Segments ---

@app.put("/api/trips/{trip_id}/segments")
async def update_segments(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Actualiza los segmentos manuales de un viaje.

    Body: { segments: [{type, ...}, ...] }
    Tipos soportados: flight, train, hotel, car, restaurant, activity
    """
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    body = await request.json()
    segments = body.get("segments", [])
    conn.execute(
        "UPDATE trips SET segments = ?, updated_at = ? WHERE id = ?",
        (json.dumps(segments, ensure_ascii=False), datetime.now(timezone.utc).isoformat(), trip_id),
    )
    conn.commit()
    conn.close()

    return {"ok": True, "trip_id": trip_id, "segments_count": len(segments)}


# --- Itinerary ---

@app.get("/api/itinerary/{trip_id}")
def get_trip_itinerary(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Obtiene el itinerario guardado de un viaje, si existe."""
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id, itinerary_data FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    itinerary_data = row["itinerary_data"]
    if not itinerary_data:
        raise HTTPException(status_code=404, detail="Itinerario no generado aun")

    return {
        "trip_id": trip_id,
        "cached": True,
        "itinerary": json.loads(itinerary_data),
    }


@app.post("/api/itinerary/{trip_id}")
async def generate_trip_itinerary(trip_id: int, request: Request, x_session_id: str = Header(default="")):
    """Genera (o devuelve cache) un itinerario para un viaje.

    Si el viaje ya tiene itinerario guardado, lo devuelve directamente.
    Si no, consulta clima y genera con DeepSeek, guardando el resultado.
    """
    sid = _get_session_id_via_header(request, x_session_id)

    conn = _get_db()
    row = conn.execute(
        "SELECT id, pass_data, itinerary_data, segments FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    # Devolver cache si ya existe (pero no si tiene error de parseo)
    cached = row["itinerary_data"]
    if cached:
        cached_it = json.loads(cached)
        if not cached_it.get("parse_error") and not cached_it.get("error"):
            conn.close()
            return {
                "trip_id": trip_id,
                "cached": True,
                "itinerary": cached_it,
            }

    pass_data = json.loads(row["pass_data"])
    passes = pass_data.get("passes", [])
    segments = json.loads(row["segments"] or "[]")
    conn.close()

    if not passes and not segments:
        raise HTTPException(status_code=400, detail="El viaje no tiene pases ni segmentos")

    # Verificar limite de tokens antes de llamar a DeepSeek
    allowed, usage_stats = check_limit(sid)
    if not allowed:
        if usage_stats.get("blocked"):
            error_msg = "Sesion bloqueada por el administrador"
        else:
            error_msg = "Limite de tokens excedido para esta sesion"
        raise HTTPException(
            status_code=429,
            detail={
                "error": error_msg,
                "blocked": usage_stats.get("blocked", False),
                "total_tokens_used": usage_stats["total_tokens_used"],
                "max_tokens": usage_stats["max_tokens"],
                "remaining": usage_stats["remaining"],
                "request_count": usage_stats["request_count"],
            },
        )

    # Generar nuevo itinerario
    try:
        itinerary = await generate_itinerary(passes, segments, session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando itinerario: {e}")

    # Guardar en BD (solo si no tiene errores)
    if not itinerary.get("parse_error") and not itinerary.get("error"):
        conn = _get_db()
        conn.execute(
            "UPDATE trips SET itinerary_data = ? WHERE id = ?",
            (json.dumps(itinerary, ensure_ascii=False), trip_id),
        )
        conn.commit()
        conn.close()

    # Incluir estadisticas de tokens en la respuesta
    token_info = itinerary.pop("_token_usage", None)
    response = {
        "trip_id": trip_id,
        "cached": False,
        "itinerary": itinerary,
    }
    if token_info:
        response["token_usage"] = token_info

    return response


# --- Expand section ---


@app.post("/api/itinerary/{trip_id}/expand")
async def expand_trip_section(
    trip_id: int,
    request: Request,
    x_session_id: str = Header(default=""),
):
    """Genera mas recomendaciones de una seccion concreta del itinerario.

    Body: { "section": "restaurants" | "hotels" | "visit" | "tips" }
    """
    sid = _get_session_id_via_header(request, x_session_id)
    body = await request.json()
    section = (body.get("section") or "").strip()

    if section not in ("restaurants", "hotels", "visit", "tips"):
        raise HTTPException(status_code=400, detail="Seccion no valida")

    conn = _get_db()
    row = conn.execute(
        "SELECT id, pass_data, itinerary_data, segments FROM trips WHERE id = ? AND session_id = ?",
        (trip_id, sid),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    pass_data = json.loads(row["pass_data"])
    passes = pass_data.get("passes", [])
    segments = json.loads(row["segments"] or "[]")
    itinerary_data = row["itinerary_data"]
    existing_itinerary = json.loads(itinerary_data) if itinerary_data else {}

    # Verificar limite de tokens
    allowed, usage_stats = check_limit(sid)
    if not allowed:
        if usage_stats.get("blocked"):
            error_msg = "Sesion bloqueada por el administrador"
        else:
            error_msg = "Limite de tokens excedido para esta sesion"
        raise HTTPException(
            status_code=429,
            detail={
                "error": error_msg,
                "blocked": usage_stats.get("blocked", False),
                "total_tokens_used": usage_stats["total_tokens_used"],
                "max_tokens": usage_stats["max_tokens"],
                "remaining": usage_stats["remaining"],
                "request_count": usage_stats["request_count"],
            },
        )

    try:
        result = expand_section(passes, segments, existing_itinerary, section, session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error expandiendo {section}: {e}")

    if result.get("error"):
        return result

    _merge_and_persist(trip_id, existing_itinerary, section, result)

    return result


def _merge_and_persist(trip_id: int, existing: dict, section: str, result: dict):
    merged = existing.copy()

    if section == "restaurants":
        merged["restaurants"] = existing.get("restaurants", []) + result.get("items", [])
    elif section == "hotels":
        merged["hotels"] = existing.get("hotels", []) + result.get("items", [])
    elif section == "visit":
        merged["places_of_interest"] = existing.get("places_of_interest", []) + result.get("places_of_interest", [])
        merged["historical_sites"] = existing.get("historical_sites", []) + result.get("historical_sites", [])
    elif section == "tips":
        merged["transport_tips"] = existing.get("transport_tips", []) + result.get("transport_tips", [])
        merged["general_tips"] = existing.get("general_tips", []) + result.get("general_tips", [])
        merged["cultural_notes"] = existing.get("cultural_notes", []) + result.get("cultural_notes", [])

    conn = _get_db()
    conn.execute(
        "UPDATE trips SET itinerary_data = ? WHERE id = ?",
        (json.dumps(merged, ensure_ascii=False), trip_id),
    )
    conn.commit()
    conn.close()


# --- Token Usage ---


@app.get("/api/token-usage")
def token_usage(request: Request, x_session_id: str = Header(default="")):
    """Devuelve las estadisticas de consumo de tokens de la sesion actual."""
    sid = _get_session_id_via_header(request, x_session_id)
    return get_usage(sid)


def _get_session_id_via_header(request: Request, header_value: str) -> str:
    """Combina header X-Session-Id con fallback a generacion automatica."""
    sid = (header_value or "").strip()
    if not sid:
        sid = request.headers.get("X-Session-Id", "").strip()
    if not sid:
        sid = f"ses_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    return sid
````
