# Plan de Suscripciones, Billing y Control de IA

## Objetivo
- Definir control de acceso por planes y suscripciones con entitlements claros.
- Garantizar que el plan Gratuito opere siempre con intervención humana (IA desactivada).
- Habilitar NOVA en el plan Pro y preparar un modo "Demo Pro" con límites.
- Diseñar una arquitectura escalable hacia Stripe, con validación, idempotencia y buen UX.

## Estado Actual (Implementado)

### Modelo de Suscripción
- Tabla `suscripciones` completamente implementada con:
  - `plan`: enum (free, demo_pro, pro, enterprise)
  - `estado`: enum (activa, suspendida, vencida, cancelada)
  - `starts_at`, `ends_at`: Control de vigencia
  - `demo_active`, `demo_ends_at`, `demo_consumed`: Control de demo
  - `entitlements`: JSONB con permisos efectivos
  - `metadata_obj`: JSONB para datos adicionales

### Endpoints Implementados
- ✅ `GET /api/subscription/current` - Suscripción vigente
- ✅ `GET /api/subscription/entitlements` - Entitlements efectivos (source of truth)
- ✅ `POST /api/subscription/demo/activate` - Activar demo (un-click)
- ✅ Validación en webhooks Chatwoot por entitlements
- ✅ Gating de IA por `nova_enabled` en entitlements

### Gating Implementado
```python
# En webhooks_chatwoot.py
entitlements = get_entitlements(empresa_id)
if not entitlements.get("nova_enabled"):
    # Forzar ia_state='off', no enviar a NOVA
    return

# Validar demo expirada
if entitlements.get("demo_active") and demo_ends_at < now():
    # Cortar acceso IA inmediatamente
    return
```

## Alcance Actual (Solo NOVA)
- Agentes IA disponibles: solo `NOVA`. `PULSE` y `NEXUS` quedan fuera de alcance inicial y se desarrollarán más adelante.
- Acceso por plan: `Pro` no accesible por ahora. Se habilita exclusivamente `Demo Pro` como vía de acceso a IA.
- Objetivo de negocio: impulsar adquisición con "Obten tu demo gratis" y evaluar uso mediante límites de mensajes y tiempo.

## Demo Pro: Implementación Actual

### Características Implementadas
- **Entitlements**:
  - `nova_enabled=true` (IA completa)
  - `demo_active=true`
  - `demo_ends_at`: 7 días desde activación
  - `pulse_enabled=false`, `nexus_enabled=false`
  - Sin límite de mensajes durante vigencia
  
- **Reglas de negocio**:
  - ✅ Una sola demo por empresa (`demo_consumed=true` al activar)
  - ✅ Reactivación solo por superadmin
  - ✅ Corte inmediato al expirar `demo_ends_at`
  - ✅ Fuerza `ia_state='off'` al expirar
  - ✅ Bloquea `forward_to_nova` después de expiración

- **UI**:
  - ✅ Muestra días restantes en dashboard
  - ✅ Banner de expiración próxima
  - ✅ CTA "Upgrade to Pro" al expirar
  - ✅ Página `/dashboard/suscripcion` con estado completo

## Endpoints de Suscripción (Implementados)

### ✅ `POST /api/subscription/demo/activate`
- **Entrada**: `{}` (flujo un-click, usa current_user)
- **Validación**: 
  - Verifica que empresa no haya consumido demo (`demo_consumed=false`)
  - Si ya consumió, retorna 409 Conflict
- **Efecto**: 
  - Crea/actualiza suscripción con `plan=demo_pro`
  - Establece `demo_active=true`, `demo_ends_at=now()+7days`
  - Marca `demo_consumed=true`
  - Actualiza entitlements: `nova_enabled=true`
- **Salida**: 
```json
{
  "plan": "demo_pro",
  "demo_active": true,
  "demo_ends_at": "2025-12-29T00:00:00Z",
  "entitlements": {
    "nova_enabled": true,
    "pulse_enabled": false,
    "nexus_enabled": false
  }
}
```

### ✅ `GET /api/subscription/current`
- **Retorna**: Suscripción vigente con plan, estado, vigencia, demo status
- **Ejemplo**:
```json
{
  "id": 1,
  "empresa_id": 1,
  "plan": "demo_pro",
  "estado": "activa",
  "starts_at": "2025-12-22T00:00:00Z",
  "ends_at": null,
  "demo_active": true,
  "demo_ends_at": "2025-12-29T00:00:00Z",
  "demo_consumed": true,
  "entitlements": {...}
}
```

### ✅ `GET /api/subscription/entitlements`
- **Retorna**: Entitlements efectivos (source of truth para gating)
- **Lógica**: Combina plan base + overrides + validación de expiración
- **Ejemplo**:
```json
{
  "nova_enabled": true,
  "pulse_enabled": false,
  "nexus_enabled": false,
  "max_conversations": 1000,
  "advanced_analytics": false,
  "demo_active": true,
  "demo_ends_at": "2025-12-29T00:00:00Z",
  "days_remaining": 7
}
```

### 🔜 `POST /api/subscription/demo/claim` (Pendiente)
- **Entrada**: `{ token: string }` (flujo token-based para campañas)
- **Validación**: Token firmado/hasheado, vigente, single-use
- **Efecto**: Igual a `activate` pero con validación de token
- **Uso**: Campañas de marketing con códigos únicos

## Modelo de Datos – Suscripcion (detallado)
- Tabla `suscripciones`
  - `id` PK
  - `empresa_id` FK → `empresas.id` (índice)
  - `plan` enum: `free | demo_pro | pro | enterprise`
  - `estado` enum: `activa | suspendida | vencida | cancelada` (índice por empresa+estado)
  - `starts_at` timestamptz, `ends_at` timestamptz (índice en `ends_at`)
  - `demo_active` boolean, `demo_ends_at` timestamptz
  - `entitlements` jsonb, `metadata` jsonb
  - Regla: una suscripción `activa` vigente por empresa; historial permitido para auditoría.
  - Nota: para `demo_pro` no se usan contadores de mensajes; el gating es exclusivamente por tiempo.

## Reglas de Negocio (Planes)
- Free
  - `nova_enabled=false`, `pulse_enabled=false`, `nexus_enabled=false`.
  - `human_intervention='always_on'`.
  - Límite base de contactos/conversaciones; `ai_messages_limit=0`.
- Pro
  - `nova_enabled=true` (IA disponible); PULSE/NEXUS opcionales.
  - `human_intervention='policy'` (usuario puede encender/apagar IA).
  - Límite de uso superior o ilimitado según pricing.
- Demo Pro
  - `nova_enabled=true`.
  - Sin contadores de mensajes; solo tiempo (`demo_ends_at`).
- Enterprise
  - Entitlements ampliados, SLA y límites altos.

## Puntos de Gating (Backend/UI)
- Webhooks Chatwoot
  - Mantener bloqueo por `estado` y `fecha_vencimiento` (`webhooks_chatwoot.py:89–97`).
  - Añadir gating por entitlements:
    - Si `nova_enabled=false`, forzar `ia_state='off'`, evitar `forward_to_nova`.
    - Si `demo_active=true`, decrementar `demo_ai_messages_quota` y cortar al agotarse.
- Endpoints IA (NOVA/PULSE/NEXUS)
  - No permitir activar/configurar NOVA si `nova_enabled=false` (403).
  - Envío de mensajes IA solo si entitlements habilitan IA.
- UI (Frontend)
  - Conversaciones: toggle IA deshabilitado en Free con CTA de upgrade.
  - Página "Suscripción": plan actual, vencimiento, estado demo, botón "Upgrade" (sin pasarela de pago por ahora).

---

**Nota**: Este documento define el marco para monetización y control de IA. Se establece como base una tabla `Suscripcion` dedicada, sin Stripe por ahora, manteniendo el backend como autoridad del gating y proporcionando una UX clara de suscripción en el frontend.