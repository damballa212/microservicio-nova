# Pipeline de Ventas - Flowify CRM

## Descripción General

Sistema completo de gestión de oportunidades de venta (deals) con seguimiento de etapas, productos, forecast y métricas avanzadas.

## Modelos de Datos

### Deal (Oportunidad)
```python
{
  "id": 1,
  "empresa_id": 1,
  "contacto_id": 5,
  "usuario_asignado_id": 2,
  "pipeline_id": 1,
  "conversacion_id": 10,
  
  "titulo": "Venta Apartamento 2B - Juan Pérez",
  "descripcion": "Cliente interesado en apartamento...",
  
  "monto": 150000.00,
  "moneda": "USD",
  "probabilidad": 75,
  "monto_ponderado": 112500.00,  # monto * (probabilidad/100)
  
  "etapa": "propuesta",  # lead|calificado|propuesta|negociacion|ganado|perdido
  "origen": "conversacion",  # conversacion|manual|ia_automatico|importacion|web_form
  
  "fecha_cierre_estimada": "2025-12-30",
  "fecha_cierre_real": null,
  
  "datos_adicionales": {
    "fuente": "Facebook Ads",
    "campana": "Q4-2024",
    "historial_etapas": [...]
  }
}
```

### Pipeline Personalizado
```python
{
  "id": 1,
  "empresa_id": 1,
  "nombre": "Ventas Inmobiliarias",
  "descripcion": "Pipeline para venta de propiedades",
  "etapas": [
    {"orden": 1, "nombre": "Lead", "probabilidad": 10},
    {"orden": 2, "nombre": "Calificado", "probabilidad": 30},
    {"orden": 3, "nombre": "Propuesta", "probabilidad": 50},
    {"orden": 4, "nombre": "Negociación", "probabilidad": 75},
    {"orden": 5, "nombre": "Ganado", "probabilidad": 100}
  ],
  "activo": true,
  "es_predeterminado": true
}
```

### Producto
```python
{
  "id": 1,
  "empresa_id": 1,
  "nombre": "Apartamento 2 Habitaciones",
  "descripcion": "Apartamento moderno...",
  "sku": "APT-2B-001",
  "precio": 150000.00,
  "moneda": "USD",
  "categoria": "Inmuebles",
  "activo": true,
  "imagen_url": "https://...",
  "especificaciones": {
    "tamaño": "120m2",
    "habitaciones": 2,
    "baños": 2
  }
}
```

### DealProducto (Relación)
```python
{
  "id": 1,
  "deal_id": 1,
  "producto_id": 1,
  "cantidad": 1,
  "precio_unitario": 150000.00,
  "descuento": 5000.00,
  "total": 145000.00,
  "notas": "Descuento por pronto pago"
}
```

## Endpoints API

### CRUD de Deals

#### Crear Deal
```http
POST /api/deals
Authorization: Bearer {token}

{
  "contacto_id": 5,
  "titulo": "Venta Apartamento 2B",
  "monto": 150000,
  "moneda": "USD",
  "probabilidad": 50,
  "etapa": "lead",
  "origen": "conversacion",
  "conversacion_id": 10,
  "fecha_cierre_estimada": "2025-12-30"
}
```

#### Listar Deals
```http
GET /api/deals?skip=0&limit=100&etapa=propuesta&usuario_asignado_id=2
```

**Filtros disponibles**:
- `etapa`: lead, calificado, propuesta, negociacion, ganado, perdido
- `contacto_id`: Filtrar por contacto
- `usuario_asignado_id`: Filtrar por usuario
- `pipeline_id`: Filtrar por pipeline
- `team_id`: Filtrar por equipo
- `fecha_desde`, `fecha_hasta`: Rango de fechas

#### Obtener Deal
```http
GET /api/deals/{deal_id}
```

#### Actualizar Deal
```http
PATCH /api/deals/{deal_id}

{
  "monto": 145000,
  "probabilidad": 75,
  "descripcion": "Cliente muy interesado..."
}
```

#### Cambiar Etapa
```http
PATCH /api/deals/{deal_id}/etapa

{
  "etapa": "ganado",
  "notas": "Cliente firmó contrato"
}
```

**Comportamiento**:
- Si etapa = "ganado" → Registra `fecha_cierre_real`
- Guarda historial en `datos_adicionales.historial_etapas`

#### Eliminar Deal
```http
DELETE /api/deals/{deal_id}
```

### Productos en Deal

#### Agregar Producto
```http
POST /api/deals/{deal_id}/productos

{
  "producto_id": 1,
  "cantidad": 1,
  "precio_unitario": 150000,
  "descuento": 5000,
  "notas": "Descuento por pronto pago"
}
```

#### Quitar Producto
```http
DELETE /api/deals/{deal_id}/productos/{producto_id}
```

### Estadísticas

#### Resumen General
```http
GET /api/deals/stats/summary?usuario_asignado_id=2&fecha_desde=2025-01-01
```

**Response**:
```json
{
  "total_deals": 50,
  "deals_activos": 30,
  "deals_ganados": 15,
  "deals_perdidos": 5,
  "revenue_total": 2500000.00,
  "revenue_ganado": 1200000.00,
  "revenue_ponderado": 800000.00,
  "ticket_promedio": 50000.00,
  "tasa_conversion": 30.0,
  "por_etapa": [
    {
      "etapa": "lead",
      "cantidad": 10,
      "monto_total": 500000.00,
      "monto_ponderado": 50000.00
    },
    ...
  ]
}
```

#### Forecast de Ventas
```http
GET /api/deals/stats/forecast?meses_adelante=3&incluir_cerrados=false
```

**Response**:
```json
[
  {
    "mes": "2025-12",
    "deals_a_cerrar": 8,
    "revenue_estimado": 400000.00,
    "revenue_ponderado": 300000.00,
    "por_etapa": [...]
  },
  {
    "mes": "2026-01",
    "deals_a_cerrar": 12,
    "revenue_estimado": 600000.00,
    "revenue_ponderado": 450000.00,
    "por_etapa": [...]
  },
  ...
]
```

#### Time-to-Win
```http
GET /api/deals/stats/time-to-win?window_days=90
```

**Response**:
```json
{
  "window_days": 90,
  "count": 15,
  "avg_days": 45.3,
  "median_days": 42.0
}
```

### Pipelines

#### Listar Pipelines
```http
GET /api/deals/pipelines
```

## Integración con Conversaciones

### Vinculación Automática
- Deals se pueden crear desde conversaciones
- Campo `conversacion_id` mantiene la relación
- Persistencia dual: conversación NO desaparece

### Políticas IA
```python
{
  "auto_create_deals": false,  # Por defecto manual
  "deal_confidence_threshold": 0.75,  # Umbral para sugerencias IA
  "deal_window_hours": 72  # Anti-duplicados
}
```

### Flujo con IA
1. Cliente muestra interés de compra en chat
2. NOVA detecta intent `deal_suggestion`
3. NOVA retorna:
```json
{
  "actions": {
    "deal_suggestion": {
      "titulo": "Venta Pizza Familiar",
      "monto": 25.00,
      "confidence": 0.85
    }
  }
}
```
4. Flowify muestra sugerencia en UI
5. Usuario acepta/rechaza manualmente
6. Si acepta → Crea deal vinculado a conversación

## UI Frontend

### Componentes Principales
- `DealsPage`: Lista de deals con filtros
- `DealCard`: Tarjeta de deal con info resumida
- `DealDetails`: Vista detallada con productos
- `DealForm`: Formulario crear/editar
- `DealStats`: Dashboard con métricas
- `DealForecast`: Gráfico de proyección

### Filtros Implementados
- Por etapa (tabs)
- Por usuario asignado
- Por equipo
- Por pipeline
- Por rango de fechas
- Por monto (min/max)

### Visualizaciones
- Kanban board por etapas
- Gráfico de embudo (funnel)
- Forecast por meses (línea)
- Revenue por etapa (barras)
- Time-to-win (histograma)

## Métricas Clave

### Revenue
- **Total**: Suma de todos los deals
- **Ganado**: Suma de deals en etapa "ganado"
- **Ponderado**: Suma de `monto × (probabilidad/100)` de deals activos

### Conversión
- **Tasa de conversión**: `(deals_ganados / total_deals) × 100`
- **Ticket promedio**: `revenue_total / total_deals`

### Velocidad
- **Time-to-win**: Días promedio desde creación hasta cierre
- **Mediana**: Valor medio de time-to-win (más robusto que promedio)

### Forecast
- **Revenue estimado**: Suma de montos de deals a cerrar en mes
- **Revenue ponderado**: Suma de montos ponderados (más realista)

## Reglas de Negocio

### Anti-Duplicados
- 1 deal por `conversacion_id` en ventana de 72h
- Override manual permitido
- Validación en backend

### Cambio de Etapa
- Historial completo en `datos_adicionales.historial_etapas`
- Registro de usuario y timestamp
- Notas opcionales por cambio

### Cierre de Deal
- Etapa "ganado" → Registra `fecha_cierre_real`
- Etapa "perdido" → Opcional: razón de pérdida
- Deals cerrados no se eliminan (auditoría)

### Productos
- Precio puede diferir del catálogo (negociación)
- Descuentos por línea de producto
- Total calculado automáticamente

## Permisos

### Por Rol
- **Admin**: CRUD completo, ver todos los deals
- **Manager**: CRUD completo, ver deals de su equipo
- **Agente**: CRUD en deals asignados, ver deals de su equipo
- **Viewer**: Solo lectura

### Filtros Automáticos
- Usuarios ven solo deals de su empresa (multi-tenant)
- Filtro por equipo si aplica
- Filtro por usuario si no es admin

## Próximos Pasos

### Corto Plazo
- [ ] Notificaciones de cambio de etapa
- [ ] Recordatorios de seguimiento
- [ ] Exportación a Excel/CSV

### Mediano Plazo
- [ ] Automatizaciones por etapa
- [ ] Plantillas de email por etapa
- [ ] Integración con calendarios

### Largo Plazo
- [ ] Predicción de cierre con ML
- [ ] Recomendaciones de acciones
- [ ] Análisis de pérdidas (why lost)

---

**El pipeline de ventas de Flowify es enterprise-grade y compite con Pipedrive y HubSpot en funcionalidad.**
