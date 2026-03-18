# Integración Chatwoot + Evolution API

**Estado:** ✅ Implementado y Funcional  
**Última actualización:** Diciembre 2024

## Índice
- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Arquitectura Multi-Tenant](#arquitectura-multi-tenant)
- [Flujo de Onboarding](#flujo-de-onboarding)
- [Webhooks y Sincronización](#webhooks-y-sincronización)
- [Endpoints API](#endpoints-api)
- [Configuración](#configuración)
- [Troubleshooting](#troubleshooting)

---

## Resumen Ejecutivo

Flowify integra **Chatwoot** (plataforma de mensajería) con **Evolution API** (gateway WhatsApp) en una arquitectura multi-tenant donde cada empresa tiene:

- **Account dedicado en Chatwoot** con su propio token
- **Instancia Evolution** para conexión WhatsApp
- **Inbox automático** que sincroniza mensajes bidireccionales
- **Importación automática** de contactos y mensajes históricos

### Características Clave

✅ **Auto-creación de Inbox** al conectar WhatsApp  
✅ **Importación automática** de contactos y últimos 7 días de mensajes  
✅ **Sincronización bidireccional** en tiempo real  
✅ **Sin spam de QR** - integración se activa solo al conectar  
✅ **Multi-tenant** - aislamiento completo entre empresas  

---

## Arquitectura Multi-Tenant

### Modelo de Datos

Cada empresa (`empresas` table) tiene:

```python
chatwoot_account_id: int          # ID del Account en Chatwoot
chatwoot_api_key: str             # Token del usuario admin (NO del account)
chatwoot_webhook_id: str          # ID del webhook configurado
evolution_instance_id: str        # Nombre de instancia (slug de empresa)
configuracion: JSONB              # Estado de integraciones
```

### Estado de Integraciones (`configuracion` JSONB)

```json
{
  "chatwoot_integration": {
    "status": "ok",                    // ok | failed
    "inbox_name": "WhatsApp Empresa",
    "verified_by": "channel",          // name | channel
    "verified_at": "2024-12-22T...",
    "attempts": 0,
    "last_success_at": "2024-12-22T..."
  },
  "evolution_connection_state": "open",  // open | connecting | close
  "last_evolution_state_at": "2024-12-22T...",
  "last_evolution_error": null
}
```

---

## Flujo de Onboarding

### 1. Creación de Empresa (Super Admin)

**Endpoint:** `POST /admin/empresas`

```bash
curl -X POST http://localhost:8000/admin/empresas \
  -H "Authorization: Bearer {super_admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Pizzería Lalo",
    "email": "admin@pizzerialalo.com",
    "admin_email": "gerente@pizzerialalo.com",
    "admin_nombre": "Juan Pérez",
    "admin_password": "secure123"
  }'
```

**Backend ejecuta:**

1. ✅ Crea Account "Pizzería Lalo" en Chatwoot (Platform API)
2. ✅ Crea usuario "Juan Pérez" como admin del Account
3. ✅ Obtiene `access_token` del usuario (NO del account)
4. ✅ Configura webhook usando token de usuario
5. ✅ Guarda `chatwoot_account_id`, `chatwoot_api_key`, `chatwoot_webhook_id`
6. ✅ Crea empresa en BD
7. ✅ Crea usuario admin
8. ✅ Crea agentes (NOVA, PULSE, NEXUS)

**Archivos:**
- `backend/app/api/admin.py:22-165`
- `backend/app/integrations/chatwoot_platform.py`

---

### 2. Conexión WhatsApp (Usuario)

**Endpoint:** `POST /whatsapp/connect`

```bash
curl -X POST http://localhost:8000/whatsapp/connect \
  -H "Authorization: Bearer {user_token}"
```

**Backend ejecuta:**

1. ✅ Valida que empresa tenga Account Chatwoot
2. ✅ Crea instancia Evolution con nombre `{empresa.slug}`
3. ✅ Configura webhook Evolution → `/webhooks/evolution`
4. ✅ Configura integración Chatwoot **DESACTIVADA** (`enabled=False`)
   - Evita spam de QR en Chatwoot mientras está en `connecting`
5. ✅ Retorna QR code (base64)

**Response:**

```json
{
  "qr_code": "data:image/png;base64,iVBOR...",
  "instance_name": "pizzeria-lalo",
  "status": "waiting",
  "message": "Escanea el código QR con WhatsApp..."
}
```

**Archivos:**
- `backend/app/api/whatsapp.py:141-155`
- `backend/app/integrations/evolution_client.py:172-225`

---

### 3. Activación al Conectar

Cuando el usuario escanea el QR, Evolution envía webhook:

```json
{
  "event": "CONNECTION_UPDATE",
  "instance": "pizzeria-lalo",
  "data": {
    "state": "open"
  }
}
```

**Backend ejecuta** (`/webhooks/evolution`):

1. ✅ Detecta `state=open`
2. ✅ **Activa integración Chatwoot** con:
   - `enabled=True`
   - `auto_create=True` - Evolution crea Inbox automáticamente
   - `import_contacts=True`
   - `import_messages=True`
   - `days_limit_import_messages=7`
3. ✅ Verifica que Inbox existe en Chatwoot (con reintentos)
4. ✅ Actualiza estado en `configuracion.chatwoot_integration`

**Archivos:**
- `backend/app/api/webhooks_evolution.py:80-205`

---

## Webhooks y Sincronización

### Webhook Chatwoot → Flowify

**Endpoint:** `POST /webhooks/chatwoot`

**Eventos manejados:**
- `message_created` - Nuevo mensaje en conversación
- `conversation_created` - Nueva conversación
- `conversation_status_changed` - Cambio de estado

**Multi-tenant:**
```python
# Busca empresa por chatwoot_account_id del webhook
result = await db.execute(
    select(Empresa).where(Empresa.chatwoot_account_id == account_id)
)
```

**Archivos:**
- `backend/app/api/webhooks_chatwoot.py:68-76`

---

### Webhook Evolution → Flowify

**Endpoint:** `POST /webhooks/evolution`

**Eventos manejados:**

| Evento | Descripción | Acción |
|--------|-------------|--------|
| `QRCODE_UPDATED` | QR actualizado (~60s) | Almacenar para frontend |
| `CONNECTION_UPDATE` | Estado cambió | Activar integración si `open` |
| `MESSAGES_UPSERT` | Mensaje recibido | Informativo (ya en Chatwoot) |

**Resolución de empresa:**
```python
# 1. Por slug (nombre de instancia)
empresa = await db.execute(
    select(Empresa).where(Empresa.slug == instance_name)
)

# 2. Fallback por evolution_instance_id
if not empresa:
    empresa = await db.execute(
        select(Empresa).where(Empresa.evolution_instance_id == instance_name)
    )
```

**Archivos:**
- `backend/app/api/webhooks_evolution.py:94-99`

---

## Endpoints API

### WhatsApp

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/whatsapp/connect` | Conectar WhatsApp (retorna QR) |
| `GET` | `/whatsapp/status` | Estado de conexión actual |
| `POST` | `/whatsapp/disconnect` | Desconectar (logout) |
| `DELETE` | `/whatsapp/delete` | Eliminar instancia completamente |

### Admin - Gestión de Empresas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/admin/empresas` | Crear empresa con Chatwoot |
| `GET` | `/admin/empresas/{id}/integracion` | Estado de integraciones |
| `GET` | `/admin/empresas/by-slug/{slug}/integracion` | Estado por slug |
| `DELETE` | `/admin/empresas/by-slug/{slug}` | Eliminar empresa |
| `DELETE` | `/admin/empresas/by-chatwoot/{account_id}` | Borrado integral |

---

### Borrado Integral

**Endpoint:** `DELETE /admin/empresas/by-chatwoot/{account_id}`

Elimina **todos** los recursos asociados:

1. ✅ Desasocia y elimina usuarios del Account Chatwoot
2. ✅ Elimina Account en Chatwoot
3. ✅ Elimina instancia Evolution
4. ✅ Elimina empresa en Flowify (cascada)

**Response:**
```json
{
  "chatwoot": {
    "account_id": 18,
    "deleted": true,
    "users_deleted": 2,
    "users_errors": []
  },
  "evolution": {
    "instance_id": "pizzeria-lalo",
    "deleted": true
  },
  "empresa": {
    "id": 5,
    "slug": "pizzeria-lalo",
    "deleted": true
  }
}
```

**Archivos:**
- `backend/app/api/admin.py:365-460`
- `backend/app/integrations/chatwoot_platform.py:308-362`

---

## Configuración

### Variables de Entorno (`.env`)

```bash
# Chatwoot
CHATWOOT_URL=https://chatwoot.tu-dominio.com
CHATWOOT_PLATFORM_TOKEN=tu-platform-token-aqui

# Evolution API
EVOLUTION_API_URL=https://evolution.tu-dominio.com
EVOLUTION_API_KEY=tu-api-key-aqui

# Backend
BACKEND_URL=https://tu-ngrok.ngrok.io  # desarrollo
# BACKEND_URL=https://api.flowify.com  # producción

# Observabilidad (opcional)
N8N_WEBHOOK_BASE_URL=https://n8n.tu-dominio.com
SLACK_ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

---

## Troubleshooting

### Problema: Webhook no se crea en Chatwoot

**Causa:** API de webhooks requiere token de **usuario**, no de account.

**Solución:** 
- Usar `access_token` del usuario admin
- Obtener con `get_user_details` si no viene en `create_user`
- Persistir en `chatwoot_api_key`

**Referencias:**
- `backend/app/api/auth.py:160-184`
- `backend/app/integrations/chatwoot_platform.py:239`

---

### Problema: Spam de QR en Chatwoot

**Causa:** Integración activada antes de escanear QR.

**Solución:** 
- Configurar integración con `enabled=False` al conectar
- Activar solo cuando `state=open`

**Referencias:**
- `backend/app/api/whatsapp.py:154`
- `backend/app/api/webhooks_evolution.py:110`

---

### Problema: Inbox no se verifica

**Causa:** Nombre o canal no coincide.

**Solución:**
- Verificación por nombre normalizado: `WhatsApp {empresa.nombre}`
- Fallback por canal: acepta `whatsapp` o `api` con nombre que contenga `whatsapp`
- Reintentos con backoff exponencial (5 intentos)

**Estado en BD:**
```json
{
  "chatwoot_integration": {
    "status": "failed",
    "error": "Inbox not found after 5 attempts",
    "attempts": 5,
    "last_attempt_at": "2024-12-22T..."
  }
}
```

**Referencias:**
- `backend/app/api/webhooks_evolution.py:172-205`

---

### Problema: Empresa no se encuentra en webhook

**Causa:** Instancia Evolution usa nombre diferente al slug.

**Solución:**
- Búsqueda por `slug` primero
- Fallback por `evolution_instance_id`

**Referencias:**
- `backend/app/api/webhooks_evolution.py:94-99`

---

## Testing

### Test 1: Crear Empresa

```bash
POST http://localhost:8000/admin/empresas
Authorization: Bearer {super_admin_token}

# Verificar en Chatwoot Super Admin
# Debe aparecer nuevo Account "Test Empresa"
```

### Test 2: Conectar WhatsApp

```bash
# 1. Login como usuario de empresa
POST http://localhost:8000/auth/login
{ "email": "user@empresa.com", "password": "..." }

# 2. Conectar WhatsApp
POST http://localhost:8000/whatsapp/connect
Authorization: Bearer {user_token}

# 3. Escanear QR mostrado
# 4. Verificar en Evolution Manager: estado "Connected"
# 5. Verificar en Chatwoot: nuevo Inbox "WhatsApp Test"
```

### Test 3: Enviar Mensaje

```bash
# 1. Enviar mensaje de WhatsApp del cliente → número de empresa
# 2. Verificar que llega a Chatwoot Inbox
# 3. Verificar que se guarda en BD local
# 4. Verificar que agente NOVA responde (si está activo)
```

---

## Documentación de Referencia

- **Chatwoot Platform API:** https://www.chatwoot.com/developers/api/platform
- **Evolution API Docs:** https://doc.evolution-api.com/
- **Arquitectura Multi-Tenant:** `docs/ARQUITECTURA_MULTI_TENANT_CHATWOOT.md`

---

## Archivos Clave

### Nuevos
- `backend/app/integrations/chatwoot_platform.py` (241 líneas)
- `backend/app/integrations/evolution_client.py` (310 líneas)
- `backend/app/api/whatsapp.py` (298 líneas)
- `backend/app/api/webhooks_evolution.py` (94 líneas)
- `backend/alembic/versions/003_chatwoot_multi_tenant.py`

### Modificados
- `backend/app/models/empresa.py` (+2 campos)
- `backend/app/config.py` (+2 variables)
- `backend/app/api/admin.py` (+40 líneas)
- `backend/app/main.py` (+2 routers)

---

**Estado:** ✅ Backend 100% funcional - Listo para producción
