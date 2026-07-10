# AGENT.md — Boarding Pass Extractor

## ¿Qué es esto?

App Ionic + Angular que extrae datos de tarjetas de embarque (vuelos y trenes) desde PDFs o imágenes, los parsea, los guarda en SQLite y genera itinerarios de viaje enriquecidos con LLM (DeepSeek).

---

## Arquitectura — 3 servicios

```
[qr_service :8766]        [backend :8765]         [frontend :4200]
 FastAPI                    FastAPI                 Angular 20 + Ionic 8
 Detecta QR/PDF417/Aztec   API REST + parser        UI móvil/web
 Recorta códigos en PNG    IATA BCBP / Renfe        File picker nativo
 ↓                          LLM DeepSeek itinerario   Sube PDFs/imágenes
 ↑                          SQLite trips.db          Muestra tarjetas + plan
 POST /extract             GET/POST /api/*           http://localhost:4200
```

### Flujo de datos

```
Imagen/PDF → frontend sube → backend /api/extract
  → qr_service decodifica QR/Aztec → texto crudo
  → parser.py trocea IATA BCBP o Renfe
  → OCR Tesseract extrae flight_time + gate_close_time (imágenes)
  → text_fields PDF para origen/destino Renfe
  → frontend guarda viaje → /api/trips → SQLite
  → usuario pide itinerario → backend llama DeepSeek con clima + datos reales
```

---

## Cómo arrancar (Windows)

### Requisitos previos
- Python 3.13+ (`python`, NO `python3` — `python3` es de Windows Store y no tiene los paquetes)
- Node 24+ / npm 11+
- Angular CLI 20 (`npx ng`)
- Tesseract OCR instalado en `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 1. qr_service (puerto 8766)
```bash
cd qr_service
python -m uvicorn main:app --host 0.0.0.0 --port 8766
```

### 2. backend (puerto 8765)
**IMPORTANTE**: ejecutar desde la raíz del proyecto, NO desde `backend/`. Los imports relativos necesitan que `backend` sea un paquete (`__init__.py`).
```bash
cd C:\Users\Rubén\Desktop\qr_extractor          # ← desde la raíz
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8765
```

### 3. frontend (puerto 4200)
```bash
cd boarding-pass
npx ng serve --host 0.0.0.0 --port 4200 --no-open
```

### Arranque combinado (un solo comando)
```bash
# Terminal 1
cd qr_service && python -m uvicorn main:app --host 0.0.0.0 --port 8766

# Terminal 2
cd C:\Users\Rubén\Desktop\qr_extractor && python -m uvicorn backend.app:app --host 0.0.0.0 --port 8765

# Terminal 3
cd boarding-pass && npx ng serve --host 0.0.0.0 --port 4200 --no-open
```

### Verificar
```bash
curl http://127.0.0.1:8766/health   # → {"status":"ok"}
curl http://127.0.0.1:8765/health   # → {"status":"ok"}
curl http://127.0.0.1:4200          # → HTTP 200
```

---

## Estructura de archivos clave

```
qr_extractor/
├── qr_service/               # ⚠️ INTOCABLE (ver qr_service/README.md)
│   ├── main.py               # FastAPI: POST /extract, GET /health
│   ├── client.py             # CLI de test
│   └── requirements.txt
│
├── backend/                  # API principal
│   ├── __init__.py           # Necesario para imports relativos
│   ├── app.py                # FastAPI: /api/extract, /api/trips, /api/itinerary
│   ├── parser.py             # IATA BCBP parser (posiciones fijas) + Renfe
│   ├── qr_client.py          # Cliente HTTP → qr_service + OCR Tesseract
│   ├── itinerary.py          # Generación de itinerario (calendario + prompt DeepSeek)
│   ├── trips.db              # SQLite (se recrea automáticamente si no existe)
│   └── requirements.txt      # fastapi, uvicorn, pymupdf, pillow, pytesseract, requests
│
├── boarding-pass/            # Frontend Angular + Ionic
│   └── src/app/
│       ├── home/             # Selector de archivos, upload, saveTrip
│       ├── result/           # Vista de billetes extraídos (legacy, casi no se usa)
│       ├── itinerary/        # Vista principal: pestañas Plan/Billetes/Reservas/...
│       ├── trips/            # Lista de viajes guardados
│       └── services/         # boarding-pass.service.ts, itinerary.service.ts
│
├── extraer_qr_pdfs.py        # Algoritmo legacy: extrae QR de PDFs + text_fields
├── boarding-pass-debug.apk   # APK compilada (production, apunta a Cloudflare Tunnel)
├── start.sh                  # Script bash de arranque (Linux/Mac, no usar en Windows)
├── AGENT.md                  # Este archivo
└── README.md                 # Documentación original
```

---

## OCR — Tesseract (NO easyocr)

- **easyocr fue reemplazado** por Tesseract. easyocr pesa ~2GB en modelos. Tesseract ~30MB.
- El OCR se usa **solo para imágenes** (capturas de pantalla de tarjetas de embarque).
- Extrae: `flight_time` y `gate_close_time` del texto visible.
- **NO extrae nombres**. El nombre viene del código QR (formato IATA BCBP).
- Tesseract instalado vía `winget install UB-Mannheim.TesseractOCR`
- Path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Python: `pytesseract` (wrapper)
- Función: `backend/qr_client.py → _ocr_flight_time()`
- Config OCR: `--psm 6 --oem 1`, idioma `spa+eng`

### Cómo funciona el OCR
1. Escala la imagen x2 si es pequeña (<1200px)
2. `pytesseract.image_to_string()` con PSM 6 (bloque uniforme de texto)
3. Busca línea con "Salida" y/o "puerta"
4. En la siguiente línea extrae HH:MM → `flight_time` y `gate_close_time`

---

## Parser — IATA BCBP

El código QR/Aztec contiene datos estructurados en formato IATA BCBP (Resolution 792).

### Campos extraídos (posiciones fijas):
| Posición | Campo | Ejemplo |
|---|---|---|
| 0-1 | Formato | M1 |
| 2-21 | Nombre (truncado 20 chars, APELLIDO/NOMBRE) | SERENAROAS/RUBEN |
| 23-29 | PNR | K9CBYG |
| 30-32 | Origen | SVQ |
| 33-35 | Destino | BCN |
| 36-38 | Aerolínea | FR |
| 39-43 | Vuelo | 6397 |
| 44-46 | Día del año (DOY) | 002 |
| 47 | Clase | Y |
| 48-51 | Asiento | 006C |
| 52-55 | Check-in seq | 0051 |
| 56+ | Datos variables | (flight_time NO incluido en Ryanair) |

### ⚠️ Ryanair NO incluye flight_time en el código
Por eso necesitamos OCR para leer la hora de la imagen. Otras aerolíneas (Vueling) SÍ lo incluyen y se extrae del campo variable "14" en posición 56+.

---

## Reglas de trabajo

### 🚫 NO HACER
- **NO instalar easyocr** ni librerías pesadas sin preguntar
- **NO tocar `qr_service/`** (es INTOCABLE salvo autorización)
- **NO usar `python3`** en Windows (es el Python de Windows Store, no tiene los paquetes). Usar `python`
- **NO ejecutar el backend desde `backend/`**. Hacerlo desde la raíz con `python -m uvicorn backend.app:app`
- **NO modificar `parser.py` sin entender el estándar IATA BCBP** (layout de posiciones fijas)
- **NO borrar `backend/__init__.py`** (necesario para imports relativos)

### ✅ BUENAS PRÁCTICAS
- **Probar con archivos reales** del proyecto: `.jpg`, `.pdf` en la raíz
- **Limpiar BBDD** entre tests: `rm backend/trips.db*`
- **Matar puertos ocupados** antes de reiniciar:
  ```bash
  netstat -ano | grep ":8765" | awk '{print $5}' | xargs taskkill //F //PID
  ```
- **Verificar que los 3 servicios responden** después de cambios
- **Commits atómicos** con mensajes descriptivos en español
- **Tags semánticos**: `v1.2.0`, `v1.3.0`, etc.

---

## Endpoints principales

### Backend (:8765)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/extract` | Subir PDF/imagen → devuelve passes + images |
| GET | `/api/trips` | Lista viajes de la sesión |
| POST | `/api/trips` | Guarda viaje (con deduplicación) |
| DELETE | `/api/trips/{id}` | Borra viaje |
| PUT | `/api/trips/{id}/segments` | Actualiza segmentos manuales |
| GET | `/api/itinerary/{id}` | Obtiene itinerario cacheado |
| POST | `/api/itinerary/{id}` | Genera itinerario nuevo (DeepSeek) |

### qr_service (:8766)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/extract` | Subir archivo → detecta y recorta códigos QR/PDF417/Aztec |

---

## Base de datos

SQLite en `backend/trips.db`. Se recrea automáticamente si no existe.

Tabla `trips`:
- `id`, `session_id`, `filename`, `pass_data` (JSON), `fingerprint` (SHA256)
- `trip_name`, `segments`, `itinerary_data` (JSON cache)
- Deduplicación por `session_id + fingerprint`
- Si mismo fingerprint + mismos datos → `duplicate`
- Si mismo fingerprint + datos distintos → `update`

---

---

## Despliegue remoto — Cloudflare Tunnel

Cloudflare Tunnel expone el backend local a internet sin abrir puertos en el router. Perfecto para probar la app desde el móvil con la APK.

### Cómo funciona

```
Móvil (APK) → Cloudflare Edge → cloudflared (tu PC) → localhost:8765 → backend
```

### Instalación de cloudflared

```bash
winget install cloudflare.cloudflared --accept-package-agreements --silent
```

Se instala en `C:\Program Files (x86)\cloudflared\cloudflared.exe`.

### Arrancar túnel rápido (gratis, sin cuenta)

```bash
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8765
```

Esto da una URL tipo: `https://palabras-aleatorias.trycloudflare.com`

### ⚠️ Limitaciones del túnel rápido

| Aspecto | Detalle |
|---|---|
| URL | **Cambia cada vez** que reinicias el túnel. Es aleatoria. |
| PC requerido | Tu PC debe estar **encendido** y el proceso de cloudflared corriendo. |
| Sin SLA | Sin garantía de uptime. Para uso en pruebas. |
| Actualizar APK | Si la URL cambia, hay que recompilar la APK con la nueva URL. |

### Para URL fija (named tunnel)

1. Crear cuenta gratuita en Cloudflare
2. Añadir un dominio (o usar uno existente)
3. Configurar un named tunnel:
   ```bash
   cloudflared tunnel create boarding-pass-tunnel
   cloudflared tunnel route dns boarding-pass-tunnel api.midominio.com
   cloudflared tunnel run boarding-pass-tunnel
   ```
4. La URL `https://api.midominio.com` es permanente → no requiere recompilar la APK cada vez.

### Flujo completo para desplegar con túnel

```bash
# 1. Arrancar los 3 servicios locales (ver "Cómo arrancar")
# 2. Arrancar el túnel
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8765
# 3. Copiar la URL que aparece (ej: https://xxx.trycloudflare.com)
# 4. Actualizar environment.prod.ts
# 5. Compilar APK (ver "Build de APK Android")
# 6. Instalar APK en el móvil
```

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Angular 20, Ionic 8, Capacitor 8, TypeScript 5.9 |
| Backend | Python 3.13, FastAPI, Uvicorn |
| QR decoder | zxing-cpp + PyMuPDF (qr_service) |
| Parser | IATA BCBP posiciones fijas + regex Renfe |
| OCR | Tesseract 5.4 + pytesseract |
| LLM | DeepSeek (itinerarios) |
| BD | SQLite |
| Android | Capacitor + Gradle |

---

## Build de APK Android (Capacitor)

### Requisitos previos

| Herramienta | Versión mínima | Cómo verificar |
|---|---|---|
| JDK | **21** (¡NO 17! Capacitor requiere 21) | `java -version` |
| Android SDK | platforms 34+, build-tools 34+ | `ls "$ANDROID_HOME/platforms"` |
| Gradle | 8.14+ (wrapper incluido) | `./gradlew --version` |

### ⚠️ JDK: problema común

El `JAVA_HOME` del sistema suele apuntar a JDK 17, pero Capacitor Android requiere JDK 21.
Para evitarlo, se fija el JDK en `boarding-pass/android/gradle.properties`:

```properties
org.gradle.java.home=C\:\\Program Files\\Microsoft\\jdk-21.0.11.10-hotspot
```

Esto sobreescribe `JAVA_HOME` solo para el build de Gradle.

### Android SDK

El SDK se instaló en `C:\Users\Rubén\AppData\Local\Android\Sdk`. Si falta `local.properties`, créalo:

```properties
sdk.dir=C\:\\Users\\Rubén\\AppData\\Local\\Android\\Sdk
```

### Build completo paso a paso

```bash
# 1. Actualizar la URL del backend en environment.prod.ts
#    (si cambió el túnel de Cloudflare)
code boarding-pass/src/environments/environment.prod.ts

# 2. Compilar Angular con configuración production
#    (reemplaza environment.ts → environment.prod.ts)
cd boarding-pass
npx ng build --configuration production

# 3. Sincronizar web assets con Android
npx cap sync android

# 4. Compilar APK
cd android
./gradlew assembleDebug

# 5. El APK se genera en:
#    boarding-pass/android/app/build/outputs/apk/debug/app-debug.apk
```

### Output esperado

```
app/build/outputs/apk/debug/app-debug.apk   # ~5.4 MB
```

Se copia a la raíz del proyecto como `boarding-pass-debug.apk` para acceso rápido.

### Instalación en el móvil

1. Transferir `boarding-pass-debug.apk` al móvil (USB, Google Drive, Telegram, etc.)
2. En Android: abrir el archivo → permitir "Instalar desde orígenes desconocidos"
3. La app apunta a la URL configurada en `environment.prod.ts`

---

## Archivos de test en el proyecto

```
1229827802-IMG-20201231-WA0006.jpg   # Ryanair SVQ→BCN (screenshot)
275632110-IMG-20201228-WA0002.jpg    # Ryanair BCN→SVQ (screenshot)
Vueling_BoardingPass.pdf             # Vueling BCN→SVQ
IBERIA_KV4SS.pdf                     # Iberia SVQ→MAD→CAI (escala)
sevilla-madrid.pdf                   # Renfe Sevilla→Madrid
madrid-toledo.pdf                    # Renfe Madrid→Toledo
billetes.madrid.pdf                  # OUIGO Madrid
```

---

## Troubleshooting común

| Problema | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Backend ejecutado desde `backend/` | Ejecutar desde la raíz: `python -m uvicorn backend.app:app` |
| `Port 8765 already in use` | Proceso anterior no murió | `taskkill //F //PID <pid>` |
| `python3` no encuentra pytesseract | `python3` es Windows Store | Usar `python` a secas |
| OCR no encuentra horas | Imagen sin etiquetas "Salida"/"puerta" | Probar con `--psm 6` en el OCR |
| `flight_time: null` en PDFs | El código IATA de Ryanair no incluye hora | Normal — usar OCR en imagen o aceptar null |
| Tesseract `spa` no disponible | Falta `spa.traineddata` | Usar `spa+eng` o descargar modelo español |
| `gate_close_time` missing en JSON | OCR no lo encontró | Campo opcional — normal si no hay "cierre puertas" en la imagen |
| `boarding-pass-debug.apk` no se encuentra | No se ha hecho el build aún | Seguir pasos en "Build de APK Android" |
| `invalid source release: 21` al buildear APK | JAVA_HOME apunta a JDK 17, pero Capacitor requiere JDK 21 | Añadir `org.gradle.java.home=ruta_al_jdk21` en `gradle.properties` |
| `SDK location not found` al buildear APK | Falta `local.properties` en `boarding-pass/android/` | Crear `local.properties` con `sdk.dir=C\\:\\\\Users\\\\Rubén\\\\AppData\\\\Local\\\\Android\\\\Sdk` |
| `cloudflared: command not found` | cloudflared instalado pero no en PATH de Git Bash | Usar ruta completa: `"C:\Program Files (x86)\cloudflared\cloudflared.exe"` |
| El túnel de Cloudflare no responde | El backend local (puerto 8765) no está corriendo | Verificar con `curl http://127.0.0.1:8765/health` |
| La APK desde el móvil no conecta | URL del túnel ha cambiado (quick tunnel) | Recompilar APK con la nueva URL del túnel |
| La APK desde el móvil no conecta | El túnel no está corriendo | Arrancar cloudflared tunnel --url http://localhost:8765 |

---

## Historial de cambios relevantes

| Fecha | Tag | Cambios |
|---|---|---|
| 2026-07-10 | v1.2.0 | OCR Tesseract (reemplazo de easyocr), UI itinerario rediseñada |
| 2026-07-10 | — | **Cloudflare Tunnel**: instalado cloudflared, creado túnel a localhost:8765. **APK Android**: compilada con production config apuntando al túnel. Fijado JDK 21 para Gradle, creado `local.properties`. Documentado en AGENT.md. |
