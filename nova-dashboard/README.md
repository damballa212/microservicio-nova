# 🧠 Nova Dashboard - Visualizador Neural del Pipeline NOVA AI

Dashboard de debugging y observabilidad en tiempo real para el microservicio NOVA AI. Visualiza la ejecución del grafo LangGraph nodo por nodo mediante WebSocket.

## ✨ Características

- **NeuralGraph**: Visualización del pipeline de 15 nodos organizados en 5 fases
- **Chat Sidebar**: Interface de pruebas para enviar mensajes al pipeline
- **Log Timeline**: Logs en tiempo real con filtros por nivel
- **Metrics Cards**: Métricas de ejecución (tokens, latencia, costos)
- **WebSocket**: Conexión en vivo con el backend NOVA

## 🏗️ Arquitectura

```
src/
├── app/
│   ├── page.tsx           # Layout principal 3 columnas
│   ├── layout.tsx
│   └── globals.css
└── components/
    ├── neural/
    │   ├── NeuralGraph.tsx      # Pipeline visual
    │   ├── ChatSidebar.tsx      # Chat de pruebas
    │   ├── LogSidebar.tsx       # Panel de logs
    │   ├── LogTimeline.tsx      # Timeline de eventos
    │   ├── MetricCard.tsx       # Tarjetas de métricas
    │   └── TestSettings.tsx     # Configuración
    └── providers/
        └── DashboardProvider.tsx  # Context + WebSocket
```

## 🚀 Quick Start

### Requisitos
- Node.js 18+
- Backend NOVA corriendo en puerto 8000

### Instalación

```bash
# Instalar dependencias
npm install

# Desarrollo
npm run dev
```

Abrir [http://localhost:3000](http://localhost:3000)

### Variables de Entorno

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/dashboard
```

## 🎨 Fases del Pipeline

El NeuralGraph muestra los nodos organizados en 5 fases:

| Fase | Color | Nodos |
|------|-------|-------|
| **VALIDATION** | Cyan | validate_event, validate_sender, check_bot_state, extract_data |
| **BUFFER** | Yellow | add_to_buffer, check_buffer_status |
| **PROCESS** | Violet | process_multimodal, classify_intent, score_lead |
| **AI** | Emerald | generate_response, format_response |
| **OUTPUT** | Rose | classify_escalation, post_to_outbound |

## 🔌 WebSocket Events

El dashboard escucha los siguientes eventos del backend:

| Evento | Descripción |
|--------|-------------|
| `execution_started` | Nueva ejecución iniciada |
| `node_started` | Nodo comenzando procesamiento |
| `node_completed` | Nodo completado con métricas |
| `node_error` | Error en un nodo |
| `execution_completed` | Pipeline finalizado |
| `log` | Entrada de log del sistema |

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| Next.js | 16.1.1 | Framework |
| React | 19.2.3 | UI |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| Lucide React | 0.562 | Iconos |

## 📚 Documentación

Para documentación completa del sistema NOVA AI, consulta:
- [PRD_NOVA_AI.md](../docs/PRD_NOVA_AI.md) - Sección 11: Dashboard Neural

---

© 2025 Flowify AI
