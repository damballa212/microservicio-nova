# Guía de Despliegue: NOVA AI en Easypanel

Easypanel es ideal para este microservicio porque permite gestionar contenedores Docker persistentes (necesarios para el Worker de RAG) de forma sencilla.

## 1. Requisitos Previos
- VPS con Easypanel instalado.
- Repositorio de GitHub de NOVA-AI actualizado con el `Dockerfile` y `docker-compose.yml`.

## 2. Pasos en el Panel de Easypanel

### Paso A: Crear el Proyecto
1. Haz clic en **"New Project"** y nómbralo `NOVA-AI`.
2. Dentro del proyecto, haz clic en **"+ Service"** y selecciona **"App"**.

### Paso B: Configurar la Fuente (GitHub)
1. En la pestaña **"Source"**, conecta tu cuenta de GitHub.
2. Selecciona el repositorio `NOVA-AI` y la rama `main`.

### Paso C: Configurar el Build
1. Ve a la pestaña **"Build"**.
2. Selecciona **"Docker Compose"** como método.
3. Easypanel detectará automáticamente tu archivo `docker-compose.yml`.

### Paso D: Variables de Entorno
1. Ve a la pestaña **"Environment"**.
2. Copia y pega el contenido de tu archivo `.env`. 
   > [!IMPORTANT]
   > Asegúrate de que las URLs de `POSTGRES_URL` y `REDIS_URL` sean accesibles desde el VPS (pueden ser servicios internos en Easypanel también).

### Paso E: Dominios y URL Pública
1. En el servicio `nova-api`, ve a la pestaña **"Domains"**.
2. Añade tu subdominio (ej: `nova.tuempresa.com`).
3. Easypanel generará automáticamente el certificado **SSL (HTTPS)** vía Let's Encrypt.
4. Asegúrate de apuntar el puerto interno al **8000**.

## 3. Verificación
Una vez desplegado, puedes verificar la salud del sistema:
- **API**: `https://tu-url.com/health` (debería responder 200 OK).
- **Worker**: Revisa los **Logs** en Easypanel para el servicio `nova-worker` para confirmar que se conectó a Redis.

---
© 2025 Flowify AI Deployment Guide
