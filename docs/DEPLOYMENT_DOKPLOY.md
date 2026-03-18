# 🚀 Guía de Despliegue: NOVA AI en Dokploy

> Guía paso a paso para desplegar el stack completo de NOVA AI en cualquier VPS con Dokploy instalado.

---

## ✅ Pre-requisitos

| Requisito | Detalle |
|---|---|
| VPS | Mínimo 2 vCPU / 4 GB RAM recomendado |
| Dokploy | Instalado y accesible en el VPS |
| GitHub | Repositorio `NOVA-AI` conectado a Dokploy |
| Supabase | PostgreSQL con extensión `pgvector` habilitada |
| API Keys | Google Gemini y OpenAI |

---

## Paso 1 — Crear el Proyecto en Dokploy

1. En el panel de Dokploy, haz clic en **"New Project"** y nómbralo `NOVA-AI`.
2. Dentro del proyecto, haz clic en **"+ Service"** → selecciona **"Compose"**.

---

## Paso 2 — Configurar la Fuente (GitHub)

1. En la pestaña **"General"**, conecta tu cuenta de GitHub.
2. Selecciona el repositorio `NOVA-AI` y la rama `main`.
3. En **Build Method** selecciona **"Docker Compose"**.
4. Activa **"Auto Deploy"** si quieres deploys automáticos al hacer push.

---

## Paso 3 — Variables de Entorno

1. Ve a la pestaña **"Environment"** del Compose.
2. Copia y pega el siguiente bloque (**reemplaza los valores `***`**):

```env
# Redis interno (coincide con el servicio 'redis' del docker-compose.yml)
REDIS_URL=redis://default:TU_PASSWORD_REDIS@redis:6379
REDIS_PASSWORD=TU_PASSWORD_REDIS

# LLMs (OBLIGATORIOS)
GOOGLE_API_KEY=AIza...
OPENAI_API_KEY=sk-...

# Chatwoot
CHATWOOT_BASE_URL=https://tu-chatwoot.dominio.com
CHATWOOT_API_TOKEN=tu-token
CHATWOOT_ACCOUNT_ID=1

# Flowify / Webhook
FLOWIFY_BASE_URL=https://tu-flowify.dominio.com
N8N_WEBHOOK_SECRET=tu-secreto

# Dashboard URL (la asignas en el paso 4)
NEXT_PUBLIC_API_URL=https://nova-api.tu-dominio.com

# PostgreSQL/Supabase
POSTGRES_URL=postgresql://user:pass@host:5432/db?sslmode=require
PG_SCHEMA=rag

# Servidor
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production
LOG_LEVEL=INFO

# Seguridad
ENCRYPTION_KEY=TU_FERNET_KEY

# Memoria
MEMORY_WINDOW_SIZE=4
BUFFER_WAIT_SECONDS=10

# CORS (dominios permitidos)
CORS_ALLOWED_ORIGINS=https://nova-dashboard.tu-dominio.com

# Observabilidad (opcional, desactivar si no tienes Phoenix)
PHOENIX_ENABLED=false
```

> **Generar ENCRYPTION_KEY:**
> ```bash
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

---

## Paso 4 — Configurar Dominios

Dokploy expone cada servicio a través de **Traefik**. Para cada servicio que necesite URL pública:

### `nova-api` → Puerto 8000
1. En el Compose, busca el servicio `nova-api`.
2. Ve a **"Domains"** del servicio.
3. Agrega: `nova-api.tu-dominio.com` → Puerto `8000`.
4. Dokploy generará SSL automáticamente con Let's Encrypt.

### `nova-dashboard` → Puerto 3000
1. En el servicio `nova-dashboard`.
2. Ve a **"Domains"**.
3. Agrega: `nova-dashboard.tu-dominio.com` → Puerto `3000`.

> ⚠️ **Importante:** El `docker-compose.yml` usa `expose` (no `ports`) para que Dokploy gestione el routing via Traefik. No cambies esto.

> ⚠️ **Importante:** `NEXT_PUBLIC_API_URL` que configuraste en el paso 3 debe coincidir exactamente con la URL pública del servicio `nova-api`.

---

## Paso 5 — Hacer el Deploy

1. En la pestaña **"Deployments"**, haz clic en **"Deploy"**.
2. Observa los logs en tiempo real — el build tomará ~3-5 minutos la primera vez.
3. El orden de inicio es: `redis` → `nova-api` → `nova-worker` + `nova-episodes-worker` + `nova-dashboard`.

---

## Paso 6 — Verificar

| Endpoint | Esperado |
|---|---|
| `https://nova-api.tu-dominio.com/health` | `{"status": "ok"}` - 200 OK |
| `https://nova-api.tu-dominio.com/docs` | Swagger UI de FastAPI |
| `https://nova-dashboard.tu-dominio.com` | Dashboard Neural |

Desde los **Logs** de Dokploy verifica:
- `nova-api`: debe mostrar `"Iniciando Chatbot WhatsApp"` y `"Conexión Redis establecida"`
- `nova-worker`: debe mostrar `"Iniciando Worker de RAG persistente"`
- `nova-episodes-worker`: debe mostrar `"Iniciando Worker de Episodios Semánticos"`

---

## 🗂️ Volúmenes y Persistencia

El `docker-compose.yml` usa **named volumes** (administrados por Docker/Dokploy):

| Volumen | Contenido |
|---|---|
| `nova-redis-data` | Datos persistentes de Redis |
| `nova-data` | Uploads de documentos RAG |
| `nova-logs` | Archivos de log |

Puedes configurar backups automáticos de estos volúmenes desde **Dokploy → Volume Backups**.

---

## 🔌 Chatwoot / Webhook de Entrada

El webhook de entrada de NOVA AI es:
```
POST https://nova-api.tu-dominio.com/webhook/inbound
```

Configura esta URL en Chatwoot como **outgoing webhook** para que los mensajes lleguen al agente.

---

## ❓ Troubleshooting

| Problema | Solución |
|---|---|
| `nova-api` no inicia | Revisa que `GOOGLE_API_KEY` esté configurada |
| `Bad Gateway` en el dominio | Verifica que el puerto en Dokploy sea `8000` para `nova-api` y `3000` para `nova-dashboard` |
| Redis no conecta | Verifica que `REDIS_URL` use `redis:6379` (nombre del servicio) y no `localhost` |
| Dashboard no conecta a la API | Verifica que `NEXT_PUBLIC_API_URL` coincida exactamente con la URL pública de `nova-api` |
| Worker no procesa documentos | Verifica `PG_SCHEMA=rag` y que `POSTGRES_URL` tenga extensión `pgvector` habilitada |

---

© 2025 Flowify AI — NOVA AI Deployment Guide
