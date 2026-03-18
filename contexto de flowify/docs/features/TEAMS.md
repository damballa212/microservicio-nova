# Teams - Gestión de Equipos

## Descripción General

Sistema de equipos para organizar agentes humanos y asignar conversaciones de forma colaborativa.

## Modelo de Datos

### Team
```python
{
  "id": 1,
  "empresa_id": 1,
  "chatwoot_team_id": 123,
  "nombre": "Ventas",
  "descripcion": "Equipo de ventas y atención al cliente",
  "allow_auto_assign": true,
  "fecha_creacion": "2025-12-01T00:00:00Z",
  "fecha_actualizacion": "2025-12-22T00:00:00Z"
}
```

### TeamMember
```python
{
  "id": 1,
  "team_id": 1,
  "usuario_id": 5,
  "fecha_creacion": "2025-12-01T00:00:00Z"
}
```

## Endpoints API

### CRUD de Teams

#### Crear Team
```http
POST /api/teams
Authorization: Bearer {token}

{
  "nombre": "Ventas",
  "descripcion": "Equipo de ventas y atención al cliente",
  "allow_auto_assign": true
}
```

**Comportamiento**:
1. Crea team en Chatwoot (Platform API)
2. Guarda `chatwoot_team_id` en BD local
3. Sincronización bidireccional

#### Listar Teams
```http
GET /api/teams
```

**Response**:
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "chatwoot_team_id": 123,
    "nombre": "Ventas",
    "descripcion": "Equipo de ventas...",
    "allow_auto_assign": true,
    "fecha_creacion": "2025-12-01T00:00:00Z"
  },
  ...
]
```

#### Actualizar Team
```http
PATCH /api/teams/{team_id}

{
  "nombre": "Ventas y Soporte",
  "descripcion": "Equipo unificado",
  "allow_auto_assign": false
}
```

**Sincronización**: Actualiza también en Chatwoot

#### Eliminar Team
```http
DELETE /api/teams/{team_id}
```

**Comportamiento**:
1. Elimina team en Chatwoot
2. Elimina team en BD local
3. Elimina miembros asociados (cascade)

### Gestión de Miembros

#### Agregar Miembro
```http
POST /api/teams/{team_id}/members

{
  "usuario_id": 5
}
```

**Validaciones**:
- Usuario debe existir y pertenecer a la empresa
- Usuario debe tener `chatwoot_user_id`
- No duplicar membresía

**Sincronización**: Agrega miembro en Chatwoot

#### Listar Miembros
```http
GET /api/teams/{team_id}/members
```

**Response**:
```json
[
  {
    "usuario_id": 5,
    "nombre": "Juan Pérez",
    "email": "juan@empresa.com",
    "availability_status": "online"
  },
  ...
]
```

#### Remover Miembro
```http
DELETE /api/teams/{team_id}/members/{usuario_id}
```

**Sincronización**: Remueve miembro en Chatwoot

## Integración con Chatwoot

### Sincronización Bidireccional
- Crear team → Crea en Chatwoot
- Actualizar team → Actualiza en Chatwoot
- Eliminar team → Elimina en Chatwoot
- Agregar miembro → Agrega en Chatwoot
- Remover miembro → Remueve en Chatwoot

### Chatwoot Team ID
- Cada team local tiene `chatwoot_team_id`
- Permite sincronización y reconciliación
- Usado en asignación de conversaciones

## Asignación de Conversaciones

### Asignar a Team
```http
POST /api/conversaciones/{conversacion_id}/assign

{
  "team_id": 1
}
```

**Comportamiento**:
1. Asigna conversación a team en Chatwoot
2. Actualiza `team_id` en BD local
3. Emite evento SSE
4. Notifica a miembros del team

### Auto-Asignación
Si `allow_auto_assign=true`:
- Conversaciones nuevas se asignan automáticamente
- Round-robin entre miembros disponibles
- Considera `availability_status`

### Filtros por Team
```http
GET /api/conversaciones?team_id=1
GET /api/deals?team_id=1
```

## Estados de Disponibilidad

### Availability Status
- `online`: Disponible para asignación
- `busy`: Ocupado, no asignar
- `offline`: Fuera de línea

### Actualizar Disponibilidad
```http
PATCH /api/agentes-humanos/{usuario_id}/availability

{
  "availability_status": "online"
}
```

## UI Frontend

### Componentes
- `TeamsPage`: Lista de teams con CRUD
- `TeamCard`: Tarjeta de team con miembros
- `TeamForm`: Formulario crear/editar
- `TeamMembersList`: Lista de miembros con acciones
- `TeamAssignment`: Selector de team en conversaciones

### Funcionalidades
- Crear/editar/eliminar teams
- Agregar/remover miembros
- Ver estadísticas por team
- Filtrar conversaciones/deals por team

## Métricas por Team

### Estadísticas
```http
GET /api/teams/{team_id}/stats
```

**Response**:
```json
{
  "team_id": 1,
  "nombre": "Ventas",
  "miembros_count": 5,
  "conversaciones_activas": 25,
  "conversaciones_cerradas_mes": 120,
  "deals_activos": 15,
  "deals_ganados_mes": 8,
  "revenue_mes": 450000.00,
  "tiempo_respuesta_promedio": 180,  // segundos
  "satisfaccion_promedio": 4.5  // 1-5
}
```

## Permisos

### Por Rol
- **Admin**: CRUD completo de teams
- **Manager**: CRUD de su team, ver otros teams
- **Agente**: Ver su team, no editar
- **Viewer**: Solo lectura

### Validaciones
- Solo admin puede crear teams
- Solo admin/manager pueden agregar/remover miembros
- Usuarios solo ven teams de su empresa (multi-tenant)

## Reglas de Negocio

### Membresía
- Un usuario puede pertenecer a múltiples teams
- Un team puede tener múltiples usuarios
- Relación many-to-many

### Asignación
- Una conversación puede estar asignada a:
  - Un usuario específico
  - Un team (sin usuario específico)
  - Un usuario Y un team
- Prioridad: usuario > team

### Auto-Asignación
- Solo si `allow_auto_assign=true`
- Solo a miembros con `availability_status=online`
- Round-robin o por carga (configurable)

## Integración con Deals

### Filtros
```http
GET /api/deals?team_id=1
```

### Estadísticas
```http
GET /api/deals/stats/summary?team_id=1
```

### Forecast
```http
GET /api/deals/stats/forecast?team_id=1
```

## Notificaciones

### Eventos SSE
```typescript
{
  "type": "assignment",
  "conversation_id": 10,
  "team_id": 1,
  "team_nombre": "Ventas"
}
```

### Notificaciones Push (Futuro)
- Asignación de conversación a team
- Nuevo miembro agregado
- Conversación urgente en team

## Próximos Pasos

### Corto Plazo
- [ ] Estadísticas en tiempo real por team
- [ ] Dashboard de performance por team
- [ ] Notificaciones de asignación

### Mediano Plazo
- [ ] Horarios de trabajo por team
- [ ] Capacidad máxima por team
- [ ] SLA por team

### Largo Plazo
- [ ] Gamificación (leaderboards)
- [ ] Análisis de performance
- [ ] Recomendaciones de asignación con ML

---

**El sistema de teams permite organización eficiente y colaboración entre agentes humanos.**
