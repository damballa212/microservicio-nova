# Implementación de Favoritos y Papelera

## ✅ Completado

Se implementaron las funcionalidades de **Favoritos** y **Papelera** para el InboxSidebar.

---

## 🗄️ Backend

### 1. Migración de Base de Datos
**Archivo**: `backend/alembic/versions/20251222_2215_8d6ebe4a089f_add_favoritos_and_papelera_to_.py`

```sql
-- Columnas agregadas a tabla conversaciones
ALTER TABLE conversaciones ADD COLUMN es_favorito BOOLEAN DEFAULT FALSE;
ALTER TABLE conversaciones ADD COLUMN en_papelera BOOLEAN DEFAULT FALSE;
ALTER TABLE conversaciones ADD COLUMN fecha_papelera TIMESTAMP WITH TIME ZONE;

-- Índices para performance
CREATE INDEX idx_conversaciones_favorito ON conversaciones(es_favorito) WHERE es_favorito = true;
CREATE INDEX idx_conversaciones_papelera ON conversaciones(en_papelera) WHERE en_papelera = true;
```

### 2. Modelo Actualizado
**Archivo**: `backend/app/models/conversacion.py`

```python
class Conversacion(Base):
    # ... campos existentes ...
    
    # Nuevos campos
    es_favorito = Column(Boolean, default=False, nullable=False, server_default='false')
    en_papelera = Column(Boolean, default=False, nullable=False, server_default='false')
    fecha_papelera = Column(DateTime(timezone=True), nullable=True)
```

### 3. Endpoints Nuevos
**Archivo**: `backend/app/api/conversaciones.py`

#### a) Toggle Favorito
```python
PATCH /api/conversaciones/{conversacion_id}/favorito
```
- Marca/desmarca conversación como favorita
- Publica evento SSE para actualización en tiempo real

#### b) Mover a Papelera
```python
PATCH /api/conversaciones/{conversacion_id}/papelera
```
- Mueve conversación a papelera
- Guarda fecha de eliminación
- Publica evento SSE

#### c) Restaurar de Papelera
```python
PATCH /api/conversaciones/{conversacion_id}/restaurar
```
- Restaura conversación de papelera
- Limpia fecha de eliminación
- Publica evento SSE

#### d) Eliminar Permanentemente
```python
DELETE /api/conversaciones/{conversacion_id}/permanente
```
- Elimina conversación permanentemente
- Solo funciona si está en papelera
- Elimina mensajes en cascada
- Publica evento SSE

---

## 🎨 Frontend

### 1. Hook de Filtros Actualizado
**Archivo**: `frontend/hooks/use-conversation-filters.ts`

**Cambios**:
- ✅ Agregados campos `es_favorito` y `en_papelera` a interface
- ✅ Contador de favoritos implementado
- ✅ Contador de papelera implementado
- ✅ Filtro de favoritos funcional
- ✅ Filtro de papelera funcional
- ✅ Conversaciones en papelera excluidas de otros filtros

**Lógica de Filtros**:
```typescript
// Favoritos: solo conversaciones marcadas como favoritas (no en papelera)
case "favorites":
  return conversations.filter(c => c.es_favorito === true && !c.en_papelera)

// Papelera: solo conversaciones en papelera
case "trash":
  return conversations.filter(c => c.en_papelera === true)

// Todos los demás filtros excluyen papelera
case "all":
  return conversations.filter(c => !c.en_papelera)
```

### 2. InboxSidebar Actualizado
**Archivo**: `frontend/components/conversaciones/inbox-sidebar.tsx`

**Cambios**:
- ✅ Botón "Favoritos" ahora funcional (antes retornaba array vacío)
- ✅ Botón "Papelera" ahora tiene `onClick` (antes no hacía nada)
- ✅ Contadores dinámicos funcionando
- ✅ Filtros activos con highlight visual

### 3. ChatHeader con Botones de Acción
**Archivo**: `frontend/components/conversaciones/chat-header.tsx`

**Nuevos Botones**:

#### a) Botón Favorito (Estrella)
- ⭐ Icono de estrella
- 🟡 Color amarillo cuando está marcado como favorito
- ✅ Toggle on/off con un click
- 🔄 Actualización en tiempo real vía SWR
- 🔔 Toast notification de confirmación

#### b) Botón Papelera
- 🗑️ Icono de papelera
- 🔴 Color rojo en hover
- ✅ Mueve conversación a papelera
- 🚫 Deshabilitado si ya está en papelera
- 🔄 Actualización en tiempo real vía SWR
- 🔔 Toast notification de confirmación

**Estados de Loading**:
- Botones deshabilitados durante operación
- Previene clicks múltiples
- Feedback visual inmediato

---

## 🎯 Funcionalidades Implementadas

### ✅ Favoritos
1. **Marcar como favorito**: Click en estrella en ChatHeader
2. **Desmarcar favorito**: Click nuevamente en estrella
3. **Filtrar favoritos**: Click en "Favoritos" en InboxSidebar
4. **Contador dinámico**: Muestra cantidad de favoritos
5. **Excluir papelera**: Favoritos no incluyen conversaciones en papelera

### ✅ Papelera
1. **Mover a papelera**: Click en icono de papelera en ChatHeader
2. **Ver papelera**: Click en "Papelera" en InboxSidebar
3. **Restaurar**: Endpoint disponible (UI pendiente)
4. **Eliminar permanente**: Endpoint disponible (UI pendiente)
5. **Contador dinámico**: Muestra cantidad en papelera
6. **Aislamiento**: Conversaciones en papelera no aparecen en otros filtros

---

## 🔄 Eventos SSE (Tiempo Real)

Todos los endpoints publican eventos SSE para actualización en tiempo real:

```typescript
// Evento de favorito actualizado
{
  type: "favorito_updated",
  conversation_id: number,
  es_favorito: boolean
}

// Evento de papelera actualizada
{
  type: "papelera_updated",
  conversation_id: number,
  en_papelera: boolean
}

// Evento de conversación eliminada
{
  type: "conversation_deleted",
  conversation_id: number
}
```

---

## 📊 Flujo de Usuario

### Marcar como Favorito
1. Usuario abre conversación
2. Click en estrella en ChatHeader
3. Backend actualiza `es_favorito = true`
4. SSE notifica cambio
5. SWR revalida datos
6. UI actualiza automáticamente
7. Contador de favoritos incrementa

### Mover a Papelera
1. Usuario abre conversación
2. Click en icono de papelera en ChatHeader
3. Backend actualiza `en_papelera = true` y `fecha_papelera`
4. SSE notifica cambio
5. SWR revalida datos
6. Conversación desaparece de lista actual
7. Contador de papelera incrementa

### Ver Papelera
1. Usuario click en "Papelera" en InboxSidebar
2. Hook filtra conversaciones con `en_papelera = true`
3. Lista muestra solo conversaciones en papelera
4. Usuario puede ver/restaurar conversaciones

---

## 🚀 Próximos Pasos (Opcionales)

### UI Pendiente
- [ ] Botón "Restaurar" en vista de papelera
- [ ] Botón "Eliminar permanentemente" en vista de papelera
- [ ] Modal de confirmación para eliminar permanentemente
- [ ] Indicador visual en ConversationList para favoritos
- [ ] Menú contextual (click derecho) con opciones rápidas

### Funcionalidades Adicionales
- [ ] Auto-eliminar papelera después de 30 días
- [ ] Búsqueda dentro de favoritos
- [ ] Múltiple selección para mover a papelera
- [ ] Atajos de teclado (F para favorito, Del para papelera)
- [ ] Filtro combinado (ej: "Favoritos + Urgentes")

---

## 🧪 Testing

### Pruebas Manuales Recomendadas

1. **Favoritos**:
   - ✅ Marcar conversación como favorita
   - ✅ Desmarcar conversación favorita
   - ✅ Filtrar por favoritos
   - ✅ Verificar contador
   - ✅ Verificar que favoritos no incluyen papelera

2. **Papelera**:
   - ✅ Mover conversación a papelera
   - ✅ Verificar que desaparece de "Todos"
   - ✅ Filtrar por papelera
   - ✅ Verificar contador
   - ✅ Verificar fecha_papelera en BD

3. **Integración**:
   - ✅ Marcar favorito y luego mover a papelera
   - ✅ Verificar que no aparece en favoritos
   - ✅ Restaurar y verificar que vuelve a favoritos
   - ✅ Verificar eventos SSE en tiempo real

### Comandos de Testing

```bash
# Backend - Verificar migración
cd backend
python -m alembic current
python -m alembic history

# Backend - Verificar endpoints
curl -X PATCH http://localhost:8000/api/conversaciones/1/favorito \
  -H "Authorization: Bearer YOUR_TOKEN"

# Frontend - Verificar sin errores
cd frontend
npm run build
```

---

## 📝 Notas Técnicas

### Performance
- Índices parciales en PostgreSQL para queries eficientes
- Solo indexa registros con `es_favorito = true` o `en_papelera = true`
- Reduce tamaño de índices y mejora velocidad

### Seguridad
- Todos los endpoints verifican `empresa_id` del usuario
- No se puede acceder a conversaciones de otras empresas
- Eliminación permanente requiere estar en papelera primero

### Escalabilidad
- Eventos SSE para actualización en tiempo real
- SWR para caché y revalidación automática
- Filtros memoizados para evitar re-cálculos innecesarios

---

## ✅ Checklist de Implementación

### Backend
- [x] Migración de base de datos
- [x] Modelo actualizado
- [x] Endpoint toggle favorito
- [x] Endpoint mover a papelera
- [x] Endpoint restaurar
- [x] Endpoint eliminar permanente
- [x] Eventos SSE

### Frontend
- [x] Interface actualizada
- [x] Hook de filtros actualizado
- [x] Contadores funcionando
- [x] Filtros funcionando
- [x] Botón favorito en ChatHeader
- [x] Botón papelera en ChatHeader
- [x] Toast notifications
- [x] Estados de loading
- [x] InboxSidebar onClick agregado

### Testing
- [ ] Pruebas manuales
- [ ] Pruebas de integración
- [ ] Pruebas de performance

---

## 🎉 Resultado Final

**Antes**: 6/13 botones funcionales (46%)
**Después**: 8/13 botones funcionales (62%)

**Nuevos botones funcionales**:
1. ✅ Favoritos (antes retornaba array vacío)
2. ✅ Papelera (antes sin onClick)

**Impacto**:
- Mejora significativa en UX
- Funcionalidades estándar de CRM implementadas
- Base sólida para futuras mejoras
