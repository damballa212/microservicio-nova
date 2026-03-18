# Flowify + Chatwoot + Evolution API — Contexto y Cambios (Caso "Demi")

## Objetivos
- Limpieza de datos de prueba en Chatwoot y Flowify.
- Diagnóstico y corrección de la creación de webhooks en Chatwoot.
- Integración WhatsApp vía Evolution API, evitando spam de QR en Chatwoot.
- Asegurar flujos estables y con permisos correctos entre Flowify, Chatwoot y Evolution.

## Limpieza Inicial
- Eliminación de cuentas y usuarios en Chatwoot (multi-tenant) y sus empresas asociadas en Flowify.
- Endpoint de administración para eliminar empresa por `slug`:
  - `backend/app/api/admin.py:290` — `DELETE /admin/empresas/by-slug/{slug}`

## Webhook de Chatwoot — Causa y Solución
- Hallazgo: la API de webhooks de Chatwoot requiere `api_access_token` de **usuario**, no del **account**. El `GET /platform/api/v1/accounts/{id}` devuelve solo `id` y `name`, y no incluye `access_token` útil para webhooks.
- Ajustes implementados:
  - Registro (autenticación):
    - Crear usuario vía Platform API y asociarlo al Account.
    - Obtener `access_token` del usuario. Si no llega en `create_user`, recuperarlo con `get_user_details`.
    - Crear webhook usando el token del usuario (no el del account) y persistir `chatwoot_api_key` con ese token.
    - Referencias:
      - `backend/app/api/auth.py:160` — creación del webhook con token de usuario
      - `backend/app/api/auth.py:184` — persistencia de `chatwoot_api_key` (token de usuario)
      - `backend/app/integrations/chatwoot_platform.py:239` — `get_user_details`
      - `backend/app/integrations/chatwoot_platform.py:157` — `create_webhook`
  - Creación de empresa por Super Admin:
    - Mismo patrón: usar el `access_token` del usuario para crear el webhook y persistir `chatwoot_api_key`.
    - Referencias:
      - `backend/app/api/admin.py:108` — creación del webhook con token de usuario
      - `backend/app/api/admin.py:134` — persistencia de `chatwoot_api_key`

## Caso "Demi" — Spam de QR en Chatwoot
- Observación: Evolution API enviaba QR actualizado cada ~40s al inbox de Chatwoot mientras la instancia estaba en `connecting`.
- Causa raíz: la integración de Chatwoot estaba **habilitada** (y en algunos casos `autoCreate=true`) antes de escanear el QR. Evolution publica estado/QR al inbox cuando la integración está activa.

### Decisión Arquitectónica
- Diferir la activación de la integración de Chatwoot (y autoCreate/importaciones) hasta que WhatsApp esté **conectado** (`CONNECTION_UPDATE=open`).

### Cambios Aplicados
- Cliente de Evolution: aceptar `enabled` en `set_chatwoot_integration`.
  - `backend/app/integrations/evolution_client.py:172` — firma actualizada con `enabled`
  - `backend/app/integrations/evolution_client.py:225` — payload con `"enabled": enabled`
- Conectar WhatsApp (fase inicial): configurar integración desactivada y sin auto-importaciones.
  - `backend/app/api/whatsapp.py:141` — llamada a `set_chatwoot_integration`
  - `backend/app/api/whatsapp.py:154` — `enabled=False` y `autoCreate=False`, `importContacts=False`, `importMessages=False`
- Webhook de Evolution: habilitar integración solo al conectar.
  - `backend/app/api/webhooks_evolution.py:80` — `handle_connection_update(..., db)`
  - `backend/app/api/webhooks_evolution.py:110` — habilita `enabled=True` y activa importaciones cuando `state == "open"`

## Flujo Operativo Resultante
1. Usuario inicia “Conectar WhatsApp” desde Flowify.
2. Se crea/asegura instancia en Evolution (`connecting`), se configura integración de Chatwoot **desactivada**.
3. Evolution emite QR al backend (solo se muestra en Flowify), sin publicar en Chatwoot.
4. Al escanear el QR y pasar a `open`, el webhook activa la integración:
   - `enabled=true`, `importContacts=true`, `importMessages=true`, `autoCreate` condicionado a si falta inbox.
   - A partir de aquí, los mensajes se sincronizan a Chatwoot como corresponde.

## Consideraciones de Seguridad y Permisos
- Webhooks y API de Chatwoot operan con token de **usuario** para endpoints del Account (webhooks, inbox), garantizando permisos adecuados por rol.
- `chatwoot_api_key` en `Empresa` almacena el token del usuario administrador asociado al Account.
- Mantener al menos un usuario “service” con rol `administrator` por tenant para asegurar continuidad de permisos.

## Validación
- Compilación de Python de los archivos modificados sin errores.
- Servidor de desarrollo corre con `--reload`; cambios aplicados en caliente.

## Riesgos y Mitigaciones
- Si el token del usuario se revoca o el usuario pierde permisos, la integración puede fallar. Acciones: regenerar token y actualizar `chatwoot_api_key`.
- Inbox ya existente con integraciones previas puede seguir recibiendo QR si fue activado externamente; al reconectar desde Flowify, la integración queda deshabilitada hasta `open`.

## Siguientes Pasos sugeridos
- Añadir en UI un selector avanzado: “Activar integración de Chatwoot solo al conectar” para control explícito.
- Auditoría periódica de permisos del usuario de servicio por tenant.

## Referencias de Código
- Webhook Evolution: `backend/app/api/webhooks_evolution.py:80`, `backend/app/api/webhooks_evolution.py:110`
- WhatsApp Connect: `backend/app/api/whatsapp.py:141`, `backend/app/api/whatsapp.py:154`
- Evolution Client: `backend/app/integrations/evolution_client.py:172`, `backend/app/integrations/evolution_client.py:225`
- Chatwoot Platform Client: `backend/app/integrations/chatwoot_platform.py:157`, `backend/app/integrations/chatwoot_platform.py:239`
- Auth (Registro): `backend/app/api/auth.py:160`, `backend/app/api/auth.py:184`
- Admin (Crear Empresa): `backend/app/api/admin.py:108`, `backend/app/api/admin.py:134`
- Admin (Eliminar Empresa por slug): `backend/app/api/admin.py:290`

