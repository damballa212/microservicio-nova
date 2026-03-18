# Registro de Cambios (Changelog)

## [2025-12-06] - Correcciones activación de demo, streaming y UX de suscripción

### Backend
- Suscripción: `POST /api/subscription/demo/activate` ahora sincroniza dos fuentes de verdad:
  - Actualiza `empresa.configuracion.subscription` con `plan=demo_pro`, `demo_active=true`, `demo_ends_at=+7d`, `entitlements`.
  - Sincroniza la tabla `suscripciones` creando/actualizando el registro de la empresa con `plan=DEMO_PRO`, `estado=ACTIVA`, `demo_active=true`, `demo_ends_at` y `entitlements`.
  - Referencias: `backend/app/api/subscription.py:117–154`.
- Lectura robusta: `GET /api/subscription/current` y `GET /api/subscription/usage` agregan fallback para leer desde la tabla `suscripciones` si el JSON indica `free` o está vacío, garantizando consistencia.
  - Referencias: `backend/app/api/subscription.py:70–89`, `backend/app/api/subscription.py:92–114`.
- Streaming en tiempo real: Reubicado `GET /api/conversaciones/stream` al inicio del router para evitar colisiones con rutas dinámicas y 403.
  - Valida JWT, extrae `empresa_id`, y usa un `tenant_key` consistente.
  - Referencia: `backend/app/api/conversaciones.py:36–70`.
- Publicación de eventos: Tras activar demo se publica `{"type":"demo_status","active":true}` al stream del tenant para refrescar el frontend.
  - Referencia: `backend/app/api/subscription.py:150–154`.
- CORS: Añadido `http://127.0.0.1:3000` a `allow_origins` para entornos locales.
  - Referencia: `backend/app/main.py:22`.

### Frontend
- Página de suscripción: Implementada completamente con estado actual, activación de demo y manejo de errores.
- SSE: Integrado para recibir eventos de demo en tiempo real.
- UX: Mejorada la experiencia de activación de demo con feedback inmediato.

## [2025-12-13] - Migración de n8n a NOVA Python/LangGraph

### Arquitectura
- **NOVA independiente**: Migrado de n8n a microservicio Python/LangGraph
- **Eliminación n8n**: Removidas todas las referencias y dependencias de n8n
- **Contratos actualizados**: Nuevos payloads Flowify ↔ NOVA

### Backend
- Webhooks: Actualizados para enviar a NOVA en lugar de n8n
- Configuración: Nuevas variables `NOVA_WEBHOOK_URL`
- Gating: Lógica de IA actualizada para NOVA

### Documentación
- **Limpieza masiva**: Eliminados archivos desactualizados
- **Nueva documentación**: README, ARQUITECTURA_ACTUAL, ESTADO_ACTUAL
- **Actualización**: Toda la documentación refleja el estado real del código

---

**Nota**: A partir de diciembre 2025, toda la documentación está actualizada y refleja el estado real del sistema.