# QR Extraction Service

## ⚠️ INTOCABLE ⚠️

Este servicio **NO SE TOCA** salvo autorización explícita del propietario.

Si necesitas un cambio:
1. Abre un issue describiendo qué necesitas
2. Espera revisión y aprobación por escrito
3. NO abras un PR directo

## Qué hace

Recibe un PDF o imagen, detecta códigos QR / PDF417 / Aztec, **recorta cada código como imagen PNG**, y lo devuelve en base64.

**No hace** (deliberadamente):
- No parsea los datos del código
- No guarda nada en base de datos
- No llama a ninguna API externa (sin DeepSeek, sin OpenAI)
- No genera itinerarios

## API

### `POST /extract`

```bash
curl -F "file=@boarding_pass.pdf" http://host:8766/extract
```

**Respuesta 200:**
```json
{
  "filename": "boarding_pass.pdf",
  "count": 2,
  "items": [
    {
      "page": 1,
      "format": "PDF417",
      "text": "M1SERENAROAS/RUBEN SNT99R...",
      "origin": "embedded",
      "base64": "iVBORw0KGgo..."
    }
  ]
}
```

**Códigos de error:**
- `400`: formato no soportado o archivo >50MB
- `500`: error interno

### `GET /health`

```json
{ "status": "ok" }
```

## Formatos soportados

PDF, PNG, JPG, JPEG, WebP, BMP, TIFF

## Ejecutar

### Local
```bash
pip install -r requirements.txt
python main.py
# o
uvicorn main:app --host 0.0.0.0 --port 8766
```

### Docker
```bash
docker build -t qr-service .
docker run -p 8766:8766 qr-service
```

## Cliente CLI (solo para tests)
```bash
python client.py archivo.pdf
```

## Dependencias

- `fastapi` + `uvicorn`: API
- `pymupdf`: renderizado de PDFs
- `pillow`: manipulación de imágenes
- `zxing-cpp`: detección de códigos

## Por qué está aislado

Este servicio es consumido por el backend principal de la app
(`backend/app.py`). Aislar la detección de QR en un servicio aparte:

1. **Estabilidad**: los cambios en el backend/app principal no rompen la detección
2. **Escalabilidad**: se puede desplegar y escalar independientemente
3. **Testing**: se puede testear de forma aislada con PDFs reales
4. **Versionado**: la API es estable; cualquier cambio de comportamiento rompe clientes

## Cambios recientes

- **v1.0.0** (2026-07-07): extracción inicial de PDF + imagen, recortado con padding
