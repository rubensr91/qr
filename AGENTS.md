## Constraints
- **Backend restart**: cambio `backend/` → reiniciar `uvicorn app:app --port 8765`. Pasos: `ps aux | grep uvicorn`, `kill <PID>`, `cd backend && nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8765 > /tmp/backend-api.log 2>&1 &`
