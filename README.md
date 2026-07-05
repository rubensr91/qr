# Boarding Pass Extractor

Extrae datos de tarjetas de embarque (vuelos y trenes) y los muestra en una app móvil.

## Estructura

```
.
├── extraer_qr_pdfs.py      # Algoritmo: extrae QR / PDF417 / Aztec de PDFs
├── backend/                # API REST (FastAPI) que envuelve el algoritmo
│   ├── app.py              # POST /api/extract, GET /health
│   ├── parser.py           # Parser de IATA BCBP (M1) y Renfe
│   └── requirements.txt
└── boarding-pass/          # App Ionic + Capacitor (Angular)
    ├── src/app/
    │   ├── home/           # Selector de PDF
    │   ├── result/         # Vista de tarjetas parseadas + códigos
    │   └── services/       # Cliente HTTP del backend
    └── android/            # Proyecto Android nativo
```

## Uso local

### 1. Backend
```bash
pip install -r backend/requirements.txt
cd backend
uvicorn app:app --host 0.0.0.0 --port 8765
```

### 2. App (web, en el navegador)
```bash
cd boarding-pass
npm install
npx ng serve --host 0.0.0.0 --port 4200
```
Abre http://localhost:4200

### 3. App (APK Android)
```bash
cd boarding-pass
npx cap sync android
cd android
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

> El `environment.ts` apunta a `http://localhost:8765` por defecto.
> Para emulador Android: cambiar a `http://10.0.2.2:8765`.
> Para dispositivo físico en LAN: cambiar a `http://<IP_LAN>:8765`.

## Aerolíneas / operadores soportados

| Operador | Formato barcode | Parser |
|---|---|---|
| Vueling, Iberia, Ryanair, AA, Lufthansa, BA, etc. | PDF417 / Aztec / QR (IATA BCBP) | ✅ IATA BCBP |
| Renfe, Iryo, OUIGO | Código propietario Renfe | ✅ Renfe (parcial) |

EasyJet no usa el estándar IATA BCBP, **no funciona** con este script.

## Limitaciones conocidas

- **OUIGO**: el localizador se extrae mal (formato propietario distinto). Fecha, hora, tren y clase sí.
- **Nombre del pasajero en Renfe/OUIGO**: no viene en el código de barras, habría que leerlo del PDF renderizado (OCR pendiente).
- **CORS abierto en backend**: en producción restringir al dominio de la app.
- **Sin autenticación**: cualquiera con la URL del backend puede subir PDFs.

## Dependencias

- **Python**: PyMuPDF, Pillow, zxing-cpp, fastapi, uvicorn
- **Node**: Ionic 8, Angular 20, Capacitor 8, @capawesome/capacitor-file-picker
- **Android**: JDK 17+, Android SDK, Gradle
