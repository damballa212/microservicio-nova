# Análisis del InboxSidebar - Funcionalidad de Botones

## Estado Actual de Implementación

### ✅ FUNCIONALES (Implementados y Funcionando)

#### 1. **Sección Conversaciones**
- ✅ **Nuevos** - Filtra conversaciones con `estado === "nuevo"`
- ✅ **Todos** - Muestra todas las conversaciones
- ✅ **Asignados** - Filtra conversaciones con `estado === "abierto" || estado === "asignado"`
- ✅ **Urgentes** (en Negociaciones) - Filtra por etiquetas "urgente" o prioridad alta
- ✅ **Completadas** (en Negociaciones) - Filtra conversaciones cerradas/resueltas
- ✅ **Cerrados** - Filtra conversaciones con `estado === "cerrado" || estado === "resuelto"`

**Contadores**: Todos los contadores funcionan correctamente y se calculan dinámicamente.

---

### ⚠️ HARDCODEADOS / NO IMPLEMENTADOS

#### 2. **Botón "+" (Header)**
```tsx
<Button variant="ghost" size="icon" className="h-7 w-7 rounded-full hover:bg-gray-100">
    <Plus className="h-4 w-4 text-gray-600" />
</Button>
```
- ❌ **Sin funcionalidad** - No tiene `onClick`
- 📝 **Propósito sugerido**: Crear nueva conversación o acción rápida

#### 3. **Sección Principal (Top)**
- ❌ **Canales** - Sin funcionalidad (sin `onClick`)
- ❌ **Borradores** - Sin funcionalidad (sin `onClick`)
- ❌ **Menciones** - Sin funcionalidad (sin `onClick`)
- ❌ **Archivos** - Sin funcionalidad (sin `onClick`)

#### 4. **Favoritos**
```tsx
<NavItem
    icon={Star}
    label="Favoritos"
    count={counts.favorites || 0}
    active={activeFilter === "favorites"}
    onClick={() => onFilterChange?.("favorites")}
/>
```
- ⚠️ **Parcialmente implementado**:
  - ✅ Tiene `onClick` y cambia el filtro
  - ❌ El filtro retorna array vacío: `return []`
  - ❌ Contador siempre es 0: `favorites: 0`
  - ❌ No hay lógica para marcar conversaciones como favoritas

**En `use-conversation-filters.ts`:**
```typescript
case "favorites":
    // TODO: Implement favorites logic
    return []
```

#### 5. **Papelera**
```tsx
<NavItem icon={Trash2} label="Papelera" count={counts.trash || 0} />
```
- ⚠️ **Parcialmente implementado**:
  - ❌ Sin `onClick` - No filtra
  - ❌ Contador siempre es 0: `trash: 0`
  - ❌ No hay lógica para mover conversaciones a papelera

**En `use-conversation-filters.ts`:**
```typescript
case "trash":
    // TODO: Implement trash logic
    return []
```

#### 6. **Negociaciones - "Todas"**
```tsx
<NavItem label="Todas" count={counts.assigned || 0} onClick={() => onFilterChange?.("assigned")} />
```
- ⚠️ **Reutiliza el filtro "Asignados"**
  - Funciona pero usa el mismo filtro que "Asignados"
  - Debería tener su propia lógica si se quiere diferenciar

---

## Resumen de Funcionalidad

### Botones Funcionales: 6/13 (46%)
1. ✅ Nuevos
2. ✅ Todos
3. ✅ Asignados
4. ✅ Urgentes
5. ✅ Completadas
6. ✅ Cerrados

### Botones No Funcionales: 7/13 (54%)
1. ❌ Botón "+" (Header)
2. ❌ Canales
3. ❌ Borradores
4. ❌ Menciones
5. ❌ Archivos
6. ❌ Favoritos (parcial)
7. ❌ Papelera (parcial)

---

## Recomendaciones de Implementación

### Prioridad Alta 🔴

#### 1. **Favoritos**
**Backend necesario:**
- Agregar campo `es_favorito: boolean` a tabla `conversaciones`
- Endpoint: `PATCH /api/conversaciones/{id}/favorito`

**Frontend:**
```typescript
// En use-conversation-filters.ts
case "favorites":
    return conversations.filter(c => c.es_favorito === true)

// Contador
favorites: conversations.filter(c => c.es_favorito === true).length
```

**UI:**
- Agregar botón de estrella en ChatHeader o ConversationList
- Toggle favorito con click

#### 2. **Papelera**
**Backend necesario:**
- Agregar campo `en_papelera: boolean` a tabla `conversaciones`
- Endpoint: `PATCH /api/conversaciones/{id}/papelera`
- Endpoint: `DELETE /api/conversaciones/{id}` (eliminar permanentemente)

**Frontend:**
```typescript
// En use-conversation-filters.ts
case "trash":
    return conversations.filter(c => c.en_papelera === true)

// Contador
trash: conversations.filter(c => c.en_papelera === true).length
```

**UI:**
- Agregar opción "Mover a papelera" en menú contextual
- Agregar opción "Eliminar permanentemente" en vista de papelera

### Prioridad Media 🟡

#### 3. **Botón "+" (Crear Nueva Conversación)**
**Opciones:**
- Abrir modal para iniciar conversación con contacto existente
- Abrir modal para crear nuevo contacto y conversación
- Menú desplegable con acciones rápidas

#### 4. **Canales**
**Implementación sugerida:**
- Filtrar por `canal` (whatsapp, email, etc.)
- Mostrar lista de canales disponibles
- Contador por canal

### Prioridad Baja 🟢

#### 5. **Borradores**
**Backend necesario:**
- Tabla `borradores_mensajes` con:
  - `conversacion_id`
  - `contenido`
  - `fecha_creacion`

**Frontend:**
- Guardar borradores automáticamente
- Mostrar conversaciones con borradores pendientes

#### 6. **Menciones**
**Backend necesario:**
- Detectar menciones (@usuario) en mensajes
- Tabla `menciones` o campo en mensajes

**Frontend:**
- Filtrar conversaciones donde el usuario fue mencionado
- Notificaciones de menciones

#### 7. **Archivos**
**Backend necesario:**
- Filtrar mensajes con archivos adjuntos
- Endpoint: `/api/conversaciones/con-archivos`

**Frontend:**
- Mostrar conversaciones que tienen archivos
- Vista de galería de archivos

---

## Código de Ejemplo para Implementaciones

### 1. Favoritos (Frontend)

```typescript
// hooks/use-conversation-filters.ts
const counts = useMemo((): ConversationCounts => {
  // ... código existente ...
  
  const favoriteConversations = conversations.filter(c => c.es_favorito === true)
  
  return {
    // ... otros contadores ...
    favorites: favoriteConversations.length,
  }
}, [conversations])

// En filteredConversations
case "favorites":
  return conversations.filter(c => c.es_favorito === true)
```

### 2. Papelera (Frontend)

```typescript
// hooks/use-conversation-filters.ts
const counts = useMemo((): ConversationCounts => {
  // ... código existente ...
  
  const trashedConversations = conversations.filter(c => c.en_papelera === true)
  
  return {
    // ... otros contadores ...
    trash: trashedConversations.length,
  }
}, [conversations])

// En filteredConversations
case "trash":
  return conversations.filter(c => c.en_papelera === true)
```

### 3. Botón "+" (Frontend)

```tsx
// components/conversaciones/inbox-sidebar.tsx
<Button 
  variant="ghost" 
  size="icon" 
  className="h-7 w-7 rounded-full hover:bg-gray-100"
  onClick={() => {
    // Opción 1: Abrir modal
    setIsNewConversationModalOpen(true)
    
    // Opción 2: Navegar a página
    router.push('/dashboard/conversaciones/nueva')
  }}
>
  <Plus className="h-4 w-4 text-gray-600" />
</Button>
```

---

## Migraciones de Base de Datos Necesarias

### Para Favoritos
```sql
ALTER TABLE conversaciones 
ADD COLUMN es_favorito BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_conversaciones_favorito 
ON conversaciones(es_favorito) 
WHERE es_favorito = TRUE;
```

### Para Papelera
```sql
ALTER TABLE conversaciones 
ADD COLUMN en_papelera BOOLEAN DEFAULT FALSE,
ADD COLUMN fecha_papelera TIMESTAMP;

CREATE INDEX idx_conversaciones_papelera 
ON conversaciones(en_papelera) 
WHERE en_papelera = TRUE;
```

---

## Endpoints de Backend Necesarios

### Favoritos
```python
@router.patch("/conversaciones/{conversacion_id}/favorito")
async def toggle_favorito(
    conversacion_id: int,
    es_favorito: bool,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Actualizar es_favorito
    pass
```

### Papelera
```python
@router.patch("/conversaciones/{conversacion_id}/papelera")
async def mover_a_papelera(
    conversacion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Actualizar en_papelera = True
    pass

@router.delete("/conversaciones/{conversacion_id}")
async def eliminar_permanentemente(
    conversacion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Solo si en_papelera = True
    # Eliminar conversación y mensajes
    pass
```

---

## Conclusión

El InboxSidebar tiene una **base sólida** con los filtros principales funcionando correctamente. Sin embargo, hay **7 botones/funciones** que están hardcodeados o sin implementar.

**Recomendación**: Priorizar la implementación de **Favoritos** y **Papelera** ya que son funcionalidades estándar en cualquier CRM y mejoran significativamente la experiencia del usuario.
