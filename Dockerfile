# Usar una imagen base ligera de Python
FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y asegurar que el log se imprima en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias de sistema necesarias para procesamiento de documentos (PDF, Docs)
# curl se necesita para el HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del microservicio
COPY . .

# Crear directorio para logs y uploads si no existen
RUN mkdir -p logs data/rag/uploads

# Exponer el puerto que usará FastAPI
EXPOSE 8000

# Healthcheck para que Dokploy sepa cuándo el servicio está listo
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto para arrancar la API primaria
# (Para el worker se sobreescribirá este comando en el docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
