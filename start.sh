#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
#  start.sh
#  Arranca los 3 servicios del Boarding Pass Extractor:
#    1. qr_service  (extracción QR/barcodes) → puerto 8766
#    2. backend     (API REST FastAPI)        → puerto 8765
#    3. frontend    (Angular + Ionic)         → puerto 4200
# ==============================================================================

ROOT="$(cd "$(dirname "$0")" && pwd)"
QR_SERVICE_DIR="$ROOT/qr_service"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/boarding-pass"

# ---- Colores ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }

# ---- Limpieza de puertos ----
clean_port() {
    local port=$1 name=$2
    local pid
    pid=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        warn "$name PID $pid usando puerto $port, liberando..."
        kill "$pid" 2>/dev/null || true
        sleep 1
    fi
}

clean_port 8766 "qr_service"
clean_port 8765 "backend"
clean_port 4200 "frontend"

# ---- 1) qr_service ----
info "Instalando dependencias de qr_service..."
cd "$QR_SERVICE_DIR"
pip install --break-system-packages -r requirements.txt -q

info "Arrancando qr_service en puerto 8766..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8766 > /tmp/qr_service.log 2>&1 &
QR_PID=$!

# ---- 2) backend ----
info "Instalando dependencias del backend..."
cd "$BACKEND_DIR"
pip install --break-system-packages -r requirements.txt -q

info "Arrancando backend en puerto 8765..."
python3 -m uvicorn app:app --host 0.0.0.0 --port 8765 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# ---- 3) frontend ----
info "Instalando dependencias del frontend..."
cd "$FRONTEND_DIR"
npm install --silent 2>/dev/null

info "Arrancando frontend (Angular) en puerto 4200..."
npx ng serve --host 0.0.0.0 --port 4200 --no-open > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# ---- Esperar a que respondan ----
echo ""
info "Esperando que los servicios respondan..."

wait_for() {
    local url=$1 label=$2 timeout=30
    for i in $(seq 1 $timeout); do
        if curl -sf "$url" >/dev/null 2>&1; then
            ok "$label responde en $url"
            return 0
        fi
        sleep 1
    done
    fail "$label no responde tras ${timeout}s (log: $3)"
    return 1
}

QR_OK=0; BK_OK=0; FE_OK=0

wait_for "http://127.0.0.1:8766/health" "qr_service"  "/tmp/qr_service.log"   && QR_OK=1
wait_for "http://127.0.0.1:8765/health" "backend"     "/tmp/backend.log"      && BK_OK=1
wait_for "http://127.0.0.1:4200"        "frontend"    "/tmp/frontend.log"     && FE_OK=1

# ---- Resumen ----
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  Boarding Pass Extractor — estado${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"

[ "$QR_OK"  -eq 1 ] && ok  "qr_service   http://localhost:8766" || fail "qr_service"
[ "$BK_OK"  -eq 1 ] && ok  "backend      http://localhost:8765" || fail "backend"
[ "$FE_OK"  -eq 1 ] && ok  "frontend     http://localhost:4200" || fail "frontend"

echo ""
echo -e "  PIDs:  qr_service=$QR_PID  backend=$BACKEND_PID  frontend=$FRONTEND_PID"
echo -e "  Logs:  /tmp/qr_service.log  /tmp/backend.log  /tmp/frontend.log"
echo ""

if [ "$QR_OK" -eq 1 ] && [ "$BK_OK" -eq 1 ] && [ "$FE_OK" -eq 1 ]; then
    echo -e "${GREEN}✅ Todo operativo. Abre http://localhost:4200${NC}"
else
    echo -e "${RED}⚠️  Algunos servicios no responden. Revisa los logs.${NC}"
    exit 1
fi
