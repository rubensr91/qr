FROM python:3.11-slim

WORKDIR /app

# PyMuPDF necesita libs del sistema para algunas imagenes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8766

# Configuracion: el servicio es INTOCABLE. No anadir flags raros.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8766"]
