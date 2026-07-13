Boarding Pass Extractor — Project Overview
Mobile app that extracts data from boarding passes (flights/trains) from PDFs or images, parses barcodes (PDF417/Aztec/QR/IATA BCBP), and generates AI-powered travel itineraries.
Architecture
extraer_qr_pdfs.py   → Legacy monolithic extraction algorithm
qr_service/          → Isolated extraction microservice
backend/             → Orchestrator REST API (FastAPI)
boarding-pass/       → Mobile app (Ionic + Angular + Capacitor)
dashboard/           → Admin web (vanilla HTML/CSS)
Services
qr_service/ — Barcode extraction (DO NOT MODIFY)
FastAPI microservice. POST /extract: receives PDF/image, detects QR/PDF417/Aztec via zxing-cpp, crops each barcode as PNG base64. No parsing, no persistence, no external calls. Dockerized.
backend/ — Orchestrator API (FastAPI, port 8765)
Endpoints:
- POST /api/extract: upload PDF → calls qr_service → parses via parser.py (IATA BCBP / Renfe format) → returns structured passes (flight/train with normalized fields)
- CRUD /api/trips: save/load trips in SQLite with dedup by fingerprint
- POST /api/itinerary/{trip_id}: generate itinerary via DeepSeek + Open-Meteo (weather), caches result
- POST /api/itinerary/{trip_id}/expand: expand sections (restaurants, hotels, sightseeing, tips)
- POST /api/quiz/{trip_id}: generate interactive travel quiz
- GET /api/token-usage: DeepSeek token tracking per session
- GET /api/admin/*: admin endpoints (grant tokens, block/unblock sessions)
Modules:
- parser.py — IATA BCBP (M1/M2) and Renfe proprietary format parser. Extracts PNR, passenger name, airline, flight number, date, seat, class
- itinerary.py — LLM orchestration: weather fetch → DeepSeek prompt → structured itinerary JSON
- token_tracker.py — SQLite-backed per-session token usage with configurable caps and manual block/grant
- admin.py — FastAPI admin router for dashboard
- qr_client.py — HTTP client for qr_service with fallback and OCR for image-only flows
boarding-pass/ — Mobile app (Ionic 8 + Angular 20 + Capacitor 8)
Pages:
- home: PDF file picker (native Capacitor File Picker)
- result: displays extracted barcode images + parsed fields
- trip-create: save trip with manual/auto naming
- trips: list saved trips by session
- itinerary: rich itinerary view with expandable sections + quiz
Services: BoardingPassService (HTTP client), ItineraryService, QuizService, LocaltunnelInterceptor (LAN testing).
dashboard/ — Admin panel (vanilla HTML/CSS)
Monitors token usage per session. Lists sessions with progress bars, block/unblock, grant tokens. Calls GET /api/admin/sessions.
Database
SQLite (backend/trips.db). No ORM, raw SQL. Tables:
- trips: id, session_id, filename, pass_data (JSON), fingerprint (SHA-256 dedup), trip_name, segments (JSON), itinerary_data (JSON), timestamps
- token_tracking: session_id, total_tokens, request_count, max_tokens, blocked, timestamps
Session-based (no auth). Identified by X-Session-Id header, auto-generated if missing.
Supported carriers
Carrier	Barcode format
Vueling, Iberia, Ryanair, AA, Lufthansa, BA, etc.	PDF417 / Aztec / QR (IATA BCBP)
Renfe, Iryo, OUIGO	Renfe proprietary
Stack
- Python: FastAPI, PyMuPDF, Pillow, zxing-cpp, httpx, openai (DeepSeek client)
- Frontend: Ionic 8, Angular 20, Capacitor 8
- Android: JDK 21+, Android SDK, Gradle (cap sync android + assembleDebug)
- DB: SQLite (WAL, raw queries)
- LLM: DeepSeek API (itineraries, quiz, expand), Open-Meteo (free weather API)
- Limitations: no auth, CORS open, EasyJet unsupported, OUIGO locator extraction buggy, passenger name missing for Renfe/OUIGO (OCR pending)