# Implementación de Fotos de Perfil de WhatsApp

## Resumen

Se implementó la carga automática de fotos de perfil tanto para **contactos** como para el **dueño de la cuenta de WhatsApp** (usuario de la empresa).

---

## 1. Fotos de Perfil de Contactos

### Implementación
- **Backend**: Se agregó `fetch_profile_picture_url()` en `evolution_client.py`
- **Webhook**: Se modificó `webhooks_chatwoot.py` para cargar foto automáticamente al crear contacto
- **Storage**: URL guardada en `contacto.datos_extra["profile_picture_url"]`
- **Frontend**: Actualizado `contact-details.tsx`, `conversation-list.tsx` y `chat-header.tsx`

### Flujo Automático
1. Llega mensaje de nuevo contacto vía Chatwoot webhook
2. Se crea el contacto en la base de datos
3. Se llama a Evolution API para obtener foto de perfil
4. Se guarda URL en `datos_extra`
5. Frontend muestra la foto en todos los componentes

### Migración
Script `migrate_profile_pictures.py` para cargar fotos de contactos existentes.

---

## 2. Foto de Perfil del Dueño de WhatsApp

### Problema Inicial
El evento `CONNECTION_UPDATE` de Evolution API **NO** incluye información del dueño de la cuenta.

### Solución Implementada
Se descubrió el endpoint `/instance/fetchInstances` que retorna información completa:
```json
{
  "ownerJid": "584126560695@s.whatsapp.net",
  "profileName": "CANI",
  "profilePicUrl": "https://pps.whatsapp.net/...",
  "connectionStatus": "open"
}
```

### Implementación

#### Backend - Evolution Client (`evolution_client.py`)
```python
async def get_instance_info(self, instance_name: str) -> Optional[Dict]:
    """
    Obtiene información completa de una instancia específica.
    Incluye: ownerJid, profileName, profilePicUrl, connectionStatus
    """
```

#### Backend - Webhook (`webhooks_evolution.py`)
```python
async def _fetch_and_store_user_profile_picture(instance_name, empresa, data, db):
    """
    1. Llama a get_instance_info() para obtener datos completos
    2. Extrae ownerJid, profileName, profilePicUrl
    3. Guarda en empresa.configuracion:
       - whatsapp_phone_number
       - whatsapp_profile_name
       - whatsapp_profile_picture_url
       - whatsapp_profile_picture_fetched_at
    """
```

#### Frontend - InboxSidebar (`inbox-sidebar.tsx`)
```typescript
// Prioridad: WhatsApp > avatar_url > dicebear
const whatsappProfilePicture = user?.empresa?.configuracion?.whatsapp_profile_picture_url;
const avatarUrl = whatsappProfilePicture || user?.avatar_url;
```

#### Schema - Auth (`auth.py`)
```python
class EmpresaBasicResponse(BaseModel):
    configuracion: Optional[dict] = None  # Incluye whatsapp_profile_picture_url
```

### Flujo Automático para Nuevas Empresas
1. ✅ Usuario se registra en Flowify
2. ✅ Usuario escanea QR de WhatsApp
3. ✅ Evolution API envía webhook `CONNECTION_UPDATE` con `state: "open"`
4. ✅ Backend llama a `get_instance_info(instance_name)`
5. ✅ Backend extrae `ownerJid`, `profileName`, `profilePicUrl`
6. ✅ Backend guarda información en `empresa.configuracion`
7. ✅ Frontend muestra foto en InboxSidebar automáticamente

### Migración
Script `migrate_user_profile_picture_auto.py` para cargar fotos de empresas existentes.

---

## Archivos Modificados

### Backend
- `backend/app/integrations/evolution_client.py` - Agregado `get_instance_info()`
- `backend/app/api/webhooks_evolution.py` - Actualizado `_fetch_and_store_user_profile_picture()`
- `backend/app/api/webhooks_chatwoot.py` - Agregado `_fetch_and_store_profile_picture()`
- `backend/app/schemas/auth.py` - Agregado `configuracion` a `EmpresaBasicResponse`

### Frontend
- `frontend/components/conversaciones/inbox-sidebar.tsx` - Muestra foto de WhatsApp
- `frontend/components/conversaciones/contact-details.tsx` - Muestra foto de contacto
- `frontend/components/conversaciones/conversation-list.tsx` - Muestra foto de contacto
- `frontend/components/conversaciones/chat-header.tsx` - Muestra foto de contacto

### Scripts de Migración
- `backend/migrate_profile_pictures.py` - Migración de fotos de contactos
- `backend/migrate_user_profile_picture_auto.py` - Migración de fotos de usuarios

---

## Testing

### Scripts de Prueba Creados
- `backend/test_connection_state.py` - Prueba endpoints de Evolution API
- `backend/test_new_profile_method.py` - Prueba `get_instance_info()`
- `backend/test_webhook_connection.py` - Simula webhook CONNECTION_UPDATE
- `backend/clear_profile_picture.py` - Limpia configuración para testing

### Resultados
✅ Todas las pruebas pasaron exitosamente
✅ Foto de perfil se carga automáticamente al conectar WhatsApp
✅ Frontend muestra foto correctamente en InboxSidebar

---

## Ventajas de la Solución

1. **Automático**: No requiere intervención manual
2. **Completo**: Obtiene número, nombre y foto en una sola llamada
3. **Eficiente**: Usa endpoint nativo de Evolution API
4. **Robusto**: Maneja errores sin bloquear el flujo principal
5. **Escalable**: Funciona para todas las empresas que se registren

---

## Próximos Pasos

- [ ] Implementar actualización periódica de fotos de perfil
- [ ] Agregar caché de fotos de perfil
- [ ] Implementar fallback si Evolution API falla
- [ ] Agregar logs de auditoría para cambios de foto

---

## Notas Técnicas

### Evolution API Endpoints Usados
- `POST /chat/fetchProfilePictureUrl/{instance}` - Para fotos de contactos
- `GET /instance/fetchInstances` - Para información completa de instancias (incluye foto del dueño)

### Estructura de Datos

#### Contacto
```json
{
  "datos_extra": {
    "profile_picture_url": "https://pps.whatsapp.net/..."
  }
}
```

#### Empresa
```json
{
  "configuracion": {
    "whatsapp_phone_number": "584126560695",
    "whatsapp_profile_name": "CANI",
    "whatsapp_profile_picture_url": "https://pps.whatsapp.net/...",
    "whatsapp_profile_picture_fetched_at": "2025-12-22T22:10:28.123Z"
  }
}
```
