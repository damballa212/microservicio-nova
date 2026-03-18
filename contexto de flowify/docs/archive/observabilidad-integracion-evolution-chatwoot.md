# Observabilidad y Automatización: Evolution API ↔ Chatwoot en Flowify

## Resumen
- Se habilitó la auto-creación de Inbox en Chatwoot durante el onboarding de WhatsApp para nuevas instancias Evolution.
- Se robusteció la resolución de empresa en webhooks de Evolution usando `slug` y fallback por `evolution_instance_id`.
- Se implementó y documentó el endpoint de administración que elimina integralmente recursos por `chatwoot_account_id` (Chatwoot Account, usuarios asociados, instancia Evolution y Empresa Flowify).
- Se validaron cambios y se ejecutaron pruebas operativas con autenticación de super admin.

## Onboarding de WhatsApp
- Integración Chatwoot con auto-creación de Inbox:
  - Código: `backend/app/api/whatsapp.py:141-155`
  - Parámetros clave: `auto_create=True`, `enabled=True`, `import_contacts=True`, `import_messages=True`, `days_limit_import_messages=7`.
  - Efecto: Evolution crea automáticamente un Inbox en Chatwoot con nombre `WhatsApp {empresa.nombre}`, importa contactos y mensajes recientes.

## Webhooks de Evolution
- Fallback de resolución de empresa por instancia:
  - Código: `backend/app/api/webhooks_evolution.py:94-99`
  - Lógica: Primero busca por `Empresa.slug == instance_name`, si no existe, intenta `Empresa.evolution_instance_id == instance_name`.
- Verificación/activación de integración Chatwoot al estado `open`:
  - Código: `backend/app/api/webhooks_evolution.py:103-111` y `172-205`.
  - Comportamiento: Reintentos exponenciales para garantizar que el Inbox exista y actualizar estado en `empresa.configuracion.chatwoot_integration`.

## Endpoint de Borrado Integral (Admin)
- Ruta: `DELETE /admin/empresas/by-chatwoot/{account_id}`
- Código: `backend/app/api/admin.py:365-460`
- Alcance de borrado:
  - Chatwoot: desasocia y elimina usuarios del Account, luego elimina el Account.
  - Evolution: elimina la instancia vinculada (`empresa.evolution_instance_id`).
  - Flowify: elimina la `Empresa` y todos los recursos relacionados por cascada.
- Respuesta JSON:
  - `chatwoot.deleted`, `chatwoot.users_deleted`, `chatwoot.users_errors`, `evolution.deleted`, `empresa.deleted`.

### Cliente Chatwoot Platform – Métodos usados
- `delete_account(account_id)`: `backend/app/integrations/chatwoot_platform.py:308-320`
- `list_account_users(account_id)`: `backend/app/integrations/chatwoot_platform.py:322-334`
- `remove_account_user(account_id, user_id)`: `backend/app/integrations/chatwoot_platform.py:336-348`
- `delete_user(user_id)`: `backend/app/integrations/chatwoot_platform.py:350-362`

## Ejemplos de Uso

### Autenticación (Super Admin)
- Login (alternativa directa vía API):
  - `POST http://localhost:8000/auth/login`
  - Body JSON: `{ "email": "<super-admin-email>", "password": "<password>" }`
  - Respuesta incluye `access_token` para usar como `Bearer`.

### Borrado Integral por Account ID
- `curl -X DELETE http://localhost:8000/admin/empresas/by-chatwoot/18 -H "Authorization: Bearer <TOKEN>"`
- Respuesta exitosa típica:
  - `{ "chatwoot": { "account_id": 18, "deleted": true }, "evolution": { "instance_id": "<nombre>", "deleted": true }, "empresa": { "id": <id>, "slug": "<slug>", "deleted": true } }`

## Observabilidad y Estados
- Evolución de conexión:
  - Estado actualizado en `empresa.configuracion.evolution_connection_state` y último error en `empresa.configuracion.last_evolution_error`.
  - Código: `backend/app/api/webhooks_evolution.py:113-171`.
- Integración Chatwoot:
  - Estado y verificación registrados en `empresa.configuracion.chatwoot_integration`.
  - Código: `backend/app/api/webhooks_evolution.py:172-205`.

## Seguridad
- Acceso al endpoint admin restringido a `super admin` vía JWT:
  - Dependencia: `backend/app/dependencies.py:86-119`.
- Evitar exposición de tokens y secretos en logs y documentación.

## Validación
- Compilación de módulos modificados para asegurar integridad:
  - `python3 -m py_compile backend/app/api/whatsapp.py backend/app/api/webhooks_evolution.py backend/app/api/admin.py backend/app/integrations/chatwoot_platform.py`
- Ejecuciones de prueba con `DELETE /admin/empresas/by-chatwoot/{account_id}` confirmaron borrados de Chatwoot, Evolution y Empresa.

## Notas Operativas
- En entornos sin `super admin` existente, provisionar temporalmente uno para auditar y ejecutar operaciones administrativas, y revocar privilegios luego.
- Mantener `CHATWOOT_URL`, `CHATWOOT_PLATFORM_TOKEN`, `EVOLUTION_API_URL`, `EVOLUTION_API_KEY` y `DATABASE_URL` correctamente configurados en `.env`.

## Objetivo
- Activación automática de la integración Chatwoot cuando WhatsApp (Evolution) está conectado.
- Verificación robusta del Inbox en Chatwoot con reintentos y backoff.
- Observabilidad backend-only: persistencia de estado y errores, sin UI para clientes.
- Endpoints de administración para diagnóstico y soporte.

## Flujo de Arquitectura
- Webhook Evolution `CONNECTION_UPDATE` → backend `webhooks_evolution.py`.
- Si `state=open`:
  - Llama `set_chatwoot_integration` con `auto_create=true` (Evolution crea Inbox y configura importaciones).
  - Verifica Inbox en Chatwoot:
    - Primero por nombre normalizado: `WhatsApp {empresa.nombre}`.
    - Luego por canal: acepta inbox con `channel`/`channel_type` que contenga `whatsapp`, o `api` con nombre que contenga `whatsapp`.
  - Reintenta con backoff exponencial si no se verifica.
  - Actualiza estado en BD y opcionalmente alerta vía n8n o Slack.
- Siempre persiste el último `state` y posibles errores de Evolution.

## Persistencia (empresas.configuracion)
- `chatwoot_integration`:
  - `status`: `ok` | `failed`
  - `error`: último error de integración (o `null` si exitoso)
  - `inbox_name`: nombre esperado del inbox
  - `verified_by`: `name` | `channel` (criterio usado para verificar)
  - `verified_at`: ISO timestamp de verificación
  - `attempts`: contador de intentos de verificación/activación
  - `last_attempt_at`: ISO timestamp del último intento
  - `last_success_at`: ISO timestamp del último éxito (cuando `status=ok`) y `attempts` se reinicia a `0`
- `evolution_connection_state`: `open` | `connecting` | `close`
- `last_evolution_state_at`: ISO timestamp del último estado
- `last_evolution_error`: último error extraído del payload Evolution; se limpia cuando `state=open`

## Endpoints de Administración
- `GET /admin/empresas/{empresa_id}/integracion`
- `GET /admin/empresas/by-slug/{slug}/integracion`
- Respuesta incluye:
  - `empresa_id`, `slug`
  - `chatwoot`: `account_id`, `webhook_id`, `integration` (objeto completo arriba)
  - `evolution`: `instance_id`, `connection_state`, `last_state_at`, `last_error`

## Variables de Entorno
- Requeridas del sistema:
  - `BACKEND_URL`
  - `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`
  - `CHATWOOT_URL`
- Opcionales de observabilidad:
  - `N8N_WEBHOOK_BASE_URL` → envia alertas a `.../webhook/flowify-alerts`
  - `SLACK_ALERT_WEBHOOK_URL` → alerta a Slack; si no existe, se ignora

## Validaciones y Reintentos
- Backoff: inicia en ~0.75s y multiplica por 1.6 entre intentos (máx 5 intentos).
- Idempotencia: `auto_create=true` evita duplicados; verificación por canal tolera variaciones de nombre.
- Limpieza de errores: al `open`, se limpia `last_evolution_error`.
- Contador de intentos: incrementa en cada intento; se reinicia a `0` en éxito.

## Pruebas Operativas
- Conectar WhatsApp en Evolution y confirmar `state=open`.
- Verificar en admin:
  - `GET /admin/empresas/{id}/integracion` o `GET /admin/empresas/by-slug/{slug}/integracion`.
  - Confirmar `chatwoot.integration.status=ok`, `verified_by`, `last_success_at` y `attempts=0`.
  - Confirmar `evolution.connection_state=open` y `last_evolution_error=null`.
- Forzar fallo (simulación) y verificar que `status=failed`, `error`, `attempts>0` y persistencia de `last_evolution_error` si `state!=open`.

## Consideraciones de Seguridad
- Sin exposición al cliente del CRM: todo backend-only.
- No se almacenan secretos en logs; se usan tokens ya configurados en `.env`.
- Alertas opcionales; si no hay n8n/Slack, el sistema funciona con persistencia y logs.

## Archivos y Ubicaciones Clave
- `backend/app/api/webhooks_evolution.py`
  - Handler conexión: persistencia de `state` y verificación/alertas.
  - Reintentos y backoff: activación + verificación Inbox.
  - Persistencia de intentos y errores.
- `backend/app/api/admin.py`
  - Endpoints para inspección de integración por ID o `slug`.

## Mantenimiento y Soporte
- Si `status=failed` recurrente:
  - Validar `chatwoot_account_id` y `chatwoot_api_key` en la empresa.
  - Validar que `CHATWOOT_URL` y `EVOLUTION_API_URL` sean correctos.
  - Revisar `last_evolution_error` y el `state` actual.
  - Activar alertas con `N8N_WEBHOOK_BASE_URL` o `SLACK_ALERT_WEBHOOK_URL` si se requiere.
