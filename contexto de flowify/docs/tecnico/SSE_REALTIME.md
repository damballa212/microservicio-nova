# SSE - Tiempo Real con Server-Sent Events

## Descripción General

Sistema de eventos en tiempo real usando Server-Sent Events (SSE) para actualizar el frontend sin polling.

## Arquitectura

### Backend: Event Stream
```python
# backend/app/events/chat_stream.py

_streams: Dict[str, List[asyncio.Queue]] = {}  # Por tenant
_recent: Dict[str, List[dict]] = {}  # Últimos 100 eventos
_counts: Dict[str, int] = {}  # Contadores por tipo

async def publish(tenant_key: str, event: dict, ttl: int = 60):
    """Publica evento a todos los suscriptores del tenant"""
    
async def subscribe(tenant_key: str) -> asyncio.Queue:
    """Suscribe cliente y retorna cola de eventos"""
    
def unsubscribe(tenant_key: str, q: asyncio.Queue):
    """Desuscribe cliente"""
```

### Frontend: EventSource
```typescript
// frontend/hooks/use-conversation-sse.ts

const eventSource = new EventSource(
  `${API_URL}/api/conversaciones/stream?token=${token}`
)

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  handleEvent(data.event)
}
```

## Tipos de Eventos

### Conversaciones
```typescript
// Nuevo mensaje
{
  "type": "message",
  "conversation_id": 10,
  "message": {
    "id": 123,
    "content": "Hola",
    "sender_type": "Contact",
    "created_at": "2025-12-22T10:30:00Z"
  }
}

// Nueva conversación
{
  "type": "conversation_created",
  "conversation_id": 11,
  "conversation": {
    "id": 11,
    "contacto_id": 5,
    "estado": "nuevo",
    "canal": "whatsapp"
  }
}

// Cambio de estado
{
  "type": "status",
  "conversation_id": 10,
  "status": "abierto"
}
```

### Asignaciones
```typescript
// Asignación a usuario
{
  "type": "assignment",
  "conversation_id": 10,
  "assignee_id": 5,
  "assignee_nombre": "Juan Pérez"
}

// Asignación a team
{
  "type": "assignment",
  "conversation_id": 10,
  "team_id": 1,
  "team_nombre": "Ventas"
}
```

### Estado IA
```typescript
// Cambio de IA state
{
  "type": "ia_state",
  "conversation_id": 10,
  "ia_state": "off",
  "reason": "handoff_humano"
}
```

### Indicadores
```typescript
// Usuario escribiendo
{
  "type": "typing",
  "conversation_id": 10,
  "user_id": 5,
  "typing": true
}

// Mensaje leído
{
  "type": "read_receipt",
  "conversation_id": 10,
  "message_id": 123,
  "read_at": "2025-12-22T10:31:00Z"
}
```

### Sistema
```typescript
// Heartbeat (keep-alive)
{
  "type": "heartbeat",
  "timestamp": "2025-12-22T10:30:00Z"
}

// Estado de demo
{
  "type": "demo_status",
  "demo_active": true,
  "demo_ends_at": "2025-12-29T00:00:00Z",
  "days_remaining": 7
}
```

## Endpoint SSE

### Conexión
```http
GET /api/conversaciones/stream?token={jwt_token}
Accept: text/event-stream
```

**Headers**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### Autenticación
- Token JWT en query string
- Validación en cada conexión
- Multi-tenant por `empresa_id` del token

### Formato de Respuesta
```
data: {"event": {...}, "ttl": 60, "ts": 1703241000.123}

data: {"event": {...}, "ttl": 60, "ts": 1703241025.456}

data: {"event": {"type": "heartbeat"}, "ttl": 60, "ts": 1703241050.789}
```

## Implementación Backend

### Publicar Evento
```python
from app.events.chat_stream import publish

# En webhooks_chatwoot.py
await publish(
    tenant_key=f"empresa_{empresa_id}",
    event={
        "type": "message",
        "conversation_id": conversacion_id,
        "message": mensaje_data
    },
    ttl=60
)
```

### Endpoint Stream
```python
@router.get("/stream")
async def stream_events(
    request: Request,
    token: str = Query(...),
    current_user: Usuario = Depends(get_current_user_from_token)
):
    tenant_key = f"empresa_{current_user.empresa_id}"
    queue = subscribe(tenant_key)
    
    async def event_generator():
        try:
            while True:
                # Heartbeat cada 25 segundos
                try:
                    payload = await asyncio.wait_for(
                        queue.get(), 
                        timeout=25.0
                    )
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': {'type': 'heartbeat'}})}\n\n"
                    
                # Check si cliente desconectó
                if await request.is_disconnected():
                    break
        finally:
            unsubscribe(tenant_key, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

## Implementación Frontend

### Hook useConversationSSE
```typescript
export function useConversationSSE(selectedId?: number) {
  const { mutate } = useSWRConfig()
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  
  const handleMessage = useCallback(async (event: MessageEvent) => {
    const parsed = JSON.parse(event.data)
    const evt = parsed.event
    
    switch (evt.type) {
      case 'message':
        // Refresh mensajes
        await mutate(`/api/conversaciones/${evt.conversation_id}/mensajes`)
        await mutate('/api/conversaciones')
        break
        
      case 'conversation_created':
        // Refresh lista
        await mutate('/api/conversaciones')
        break
        
      case 'typing':
        setIsTyping(evt.typing)
        break
        
      case 'assignment':
        // Refresh conversación
        await mutate(`/api/conversaciones/${evt.conversation_id}`)
        await mutate('/api/conversaciones')
        break
        
      case 'ia_state':
        // Refresh IA state
        await mutate(`/api/conversaciones/${evt.conversation_id}/ia-state`)
        break
    }
  }, [mutate])
  
  const connect = useCallback(() => {
    const token = localStorage.getItem('token')
    const url = `${API_URL}/api/conversaciones/stream?token=${token}`
    const eventSource = new EventSource(url)
    
    eventSource.onopen = () => setIsConnected(true)
    eventSource.onmessage = handleMessage
    eventSource.onerror = () => {
      setIsConnected(false)
      eventSource.close()
      // Reconectar después de 2 segundos
      setTimeout(connect, 2000)
    }
    
    return eventSource
  }, [handleMessage])
  
  useEffect(() => {
    const eventSource = connect()
    return () => eventSource.close()
  }, [connect])
  
  return { isConnected, isTyping, connectionStatus }
}
```

### Uso en Componentes
```typescript
// En ConversationsPage
const { isConnected, isTyping } = useConversationSSE(selectedConversationId)

// Mostrar indicador de conexión
{isConnected ? (
  <Badge variant="success">Conectado</Badge>
) : (
  <Badge variant="warning">Reconectando...</Badge>
)}

// Mostrar indicador de escritura
{isTyping && (
  <div className="text-sm text-gray-500">
    El contacto está escribiendo...
  </div>
)}
```

## Características Avanzadas

### Eventos Recientes
- Últimos 100 eventos se guardan en memoria
- Nuevos suscriptores reciben eventos recientes (TTL válido)
- Evita pérdida de eventos durante reconexión

### Heartbeat
- Cada 25 segundos
- Mantiene conexión viva
- Detecta desconexiones

### Auto-Reconexión
- Frontend reconecta automáticamente
- Backoff exponencial (2s, 4s, 8s, ...)
- Máximo 5 intentos

### Multi-Tenant
- Eventos aislados por `empresa_id`
- Un tenant no ve eventos de otro
- Validación en cada conexión

## Optimizaciones

### Backend
```python
# Cola con tamaño máximo
queue = asyncio.Queue(maxsize=100)

# Publicación no bloqueante
try:
    queue.put_nowait(payload)
except asyncio.QueueFull:
    # Descartar evento más antiguo
    pass

# Limpieza de eventos antiguos
if len(_recent[tenant_key]) > 100:
    del _recent[tenant_key][:len(_recent[tenant_key]) - 100]
```

### Frontend
```typescript
// Debounce de mutate
const debouncedMutate = useMemo(
  () => debounce((key: string) => mutate(key), 500),
  [mutate]
)

// Batch updates
const pendingUpdates = useRef<Set<string>>(new Set())

useEffect(() => {
  const interval = setInterval(() => {
    pendingUpdates.current.forEach(key => mutate(key))
    pendingUpdates.current.clear()
  }, 1000)
  
  return () => clearInterval(interval)
}, [mutate])
```

## Monitoreo

### Métricas
```python
# Contadores por tipo de evento
_counts = {
  "message": 1523,
  "conversation_created": 45,
  "assignment": 89,
  "ia_state": 23,
  "heartbeat": 5420
}

# Endpoint de métricas
@router.get("/stream/metrics")
async def get_stream_metrics():
    return {
        "active_connections": len(_streams),
        "event_counts": _counts,
        "recent_events_size": sum(len(v) for v in _recent.values())
    }
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Log conexiones
logger.info(f"SSE: Nueva conexión - empresa_id={empresa_id}")

# Log desconexiones
logger.info(f"SSE: Desconexión - empresa_id={empresa_id}, duration={duration}s")

# Log errores
logger.error(f"SSE: Error publicando evento - {error}")
```

## Troubleshooting

### Cliente no recibe eventos
1. Verificar token JWT válido
2. Verificar `empresa_id` correcto
3. Verificar eventos se publican con tenant_key correcto
4. Verificar firewall/proxy no bloquea SSE

### Conexión se cae constantemente
1. Verificar heartbeat funciona
2. Verificar timeout de proxy/load balancer
3. Aumentar timeout de EventSource
4. Verificar logs de errores

### Eventos duplicados
1. Verificar no hay múltiples conexiones
2. Verificar mutate no se llama múltiples veces
3. Usar debounce en mutate

### Alto uso de memoria
1. Verificar limpieza de eventos antiguos
2. Verificar desuscripción al desmontar
3. Reducir tamaño de cola
4. Reducir TTL de eventos

## Comparación con Alternativas

### SSE vs WebSocket
| Característica | SSE | WebSocket |
|----------------|-----|-----------|
| Dirección | Servidor → Cliente | Bidireccional |
| Protocolo | HTTP | WS |
| Reconexión | Automática | Manual |
| Complejidad | Baja | Media |
| Uso | Notificaciones | Chat en tiempo real |

**Por qué SSE para Flowify**:
- Solo necesitamos servidor → cliente
- Reconexión automática
- Más simple que WebSocket
- Compatible con HTTP/2

### SSE vs Polling
| Característica | SSE | Polling |
|----------------|-----|---------|
| Latencia | Baja (~0ms) | Alta (1-5s) |
| Carga servidor | Baja | Alta |
| Carga red | Baja | Alta |
| Complejidad | Media | Baja |

**Por qué SSE sobre Polling**:
- Latencia casi cero
- Menos carga en servidor
- Menos tráfico de red
- Mejor UX

## Próximos Pasos

### Corto Plazo
- [ ] Métricas en dashboard
- [ ] Alertas de desconexión
- [ ] Logs estructurados

### Mediano Plazo
- [ ] Redis para eventos (escalabilidad)
- [ ] Compresión de eventos
- [ ] Rate limiting por tenant

### Largo Plazo
- [ ] WebSocket para chat en vivo
- [ ] Push notifications como fallback
- [ ] Eventos históricos (replay)

---

**SSE proporciona actualizaciones en tiempo real con baja latencia y alta confiabilidad.**
