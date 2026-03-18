# 🚀 Flowify AI CRM

**CRM Multi-tenant con Agentes IA para automatización de conversaciones**

## 📋 Descripción

Flowify es un CRM completo que permite a empresas gestionar conversaciones automatizadas con IA a través de múltiples canales (WhatsApp, Instagram, Facebook, Web). Cada empresa es un tenant completamente aislado con su propia configuración de agentes IA.

## 🏗️ Arquitectura

```
WhatsApp ↔ Evolution API ↔ Chatwoot ↔ Flowify CRM ↔ NOVA (Python/LangGraph)
```

### Componentes

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy (Multi-tenant)
- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS
- **IA**: NOVA (Microservicio Python/LangGraph independiente)
- **Canales**: Chatwoot + Evolution API para WhatsApp
- **Base de Datos**: PostgreSQL (Supabase)

## ✅ Funcionalidades Implementadas

### 🔐 Autenticación y Multi-tenancy
- [x] Login con JWT
- [x] Registro automático con creación de cuenta Chatwoot
- [x] Multi-tenant estricto (aislamiento completo por empresa)
- [x] Sistema de suscripciones con entitlements

### 👑 Administración (Super Admin)
- [x] CRUD completo de empresas
- [x] Suspender/Reactivar empresas
- [x] Gestión avanzada de suscripciones (FREE, DEMO_PRO, PRO, ENTERPRISE)
- [x] Reconciliación de Chatwoot

### 🤖 Agentes IA
- [x] Gestión de agentes (NOVA activo, PULSE/NEXUS preparados)
- [x] Activar/Desactivar agentes
- [x] Configuración de system prompts
- [x] Integración con Google Sheets para inventario
- [x] Status de configuración

### 👥 Gestión de Contactos
- [x] CRUD de contactos
- [x] Filtros por estado y fuente
- [x] Sistema de notas con historial
- [x] Sincronización con Chatwoot

### 💬 Conversaciones (Tiempo Real)
- [x] Inbox con SSE (Server-Sent Events)
- [x] Envío de mensajes (texto y multimedia)
- [x] Upload de adjuntos
- [x] Control de IA State (on/off)
- [x] Asignación a usuarios/equipos
- [x] Handoff IA→Humano
- [x] Sistema de prioridades
- [x] Sincronización bidireccional con Chatwoot

### 💰 Pipeline de Ventas (Deals)
- [x] CRUD completo de deals
- [x] Productos en deals
- [x] Estadísticas avanzadas con filtros
- [x] Forecast por meses
- [x] Métricas time-to-win
- [x] Cambio de etapas con historial
- [x] Vinculación con conversaciones

### 📚 Base de Conocimiento
- [x] Upload de archivos (PDF, TXT, DOC, DOCX, CSV)
- [x] Organización por agente
- [x] Gestión de archivos

### 🔗 Integraciones
- [x] Chatwoot Platform API (completa)
- [x] Chatwoot Account API (completa)
- [x] Evolution API para WhatsApp
- [x] Webhooks con validación HMAC
- [x] SSE para tiempo real

### 👨‍💼 Teams y Agentes Humanos
- [x] Gestión de equipos
- [x] Agentes humanos (usuarios)
- [x] Asignación de conversaciones

### 📊 Reportes y Analytics
- [x] Dashboard con métricas
- [x] Estadísticas de deals
- [x] Forecast de ventas
- [x] Reportes por etapa/usuario/equipo

## 🚀 Inicio Rápido

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# Configurar variables en .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📁 Estructura del Proyecto

```
flowify-crm/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # Endpoints REST
│   │   ├── models/         # Modelos SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── integrations/   # Clientes APIs externas
│   │   └── utils/          # Utilidades
│   ├── alembic/            # Migraciones BD
│   └── requirements.txt
├── frontend/               # Next.js Frontend
│   ├── app/               # App Router
│   ├── components/        # Componentes React
│   ├── hooks/            # Custom Hooks
│   └── lib/              # Utilidades
└── docs/                 # Documentación
```

## 🔧 Variables de Entorno Principales

```env
# Base de datos
DATABASE_URL=postgresql://...

# Seguridad
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Chatwoot
CHATWOOT_URL=https://your-chatwoot.com
CHATWOOT_PLATFORM_TOKEN=your-platform-token

# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://your-evolution.com
EVOLUTION_API_KEY=your-evolution-key

# NOVA (IA)
NOVA_WEBHOOK_URL=https://your-nova-service.com

# Backend
BACKEND_URL=https://your-backend.com
FRONTEND_URL=https://your-frontend.com
```

## 🔄 Flujo de Conversación

1. **Cliente** envía mensaje por WhatsApp
2. **Evolution API** recibe y envía a Chatwoot
3. **Chatwoot** dispara webhook a Flowify
4. **Flowify** valida empresa/suscripción y rutea a NOVA
5. **NOVA** (Python/LangGraph) procesa con IA y responde
6. **Flowify** recibe respuesta y actualiza BD
7. **Flowify** envía respuesta a Chatwoot
8. **Chatwoot** → Evolution API → WhatsApp → Cliente

## 📊 Modelos de Datos Principales

- **Empresa**: Tenants del sistema
- **Usuario**: Empleados de cada empresa
- **Agente**: Configuración de agentes IA
- **Contacto**: Clientes finales
- **Conversacion**: Chats agrupados
- **Mensaje**: Mensajes individuales
- **Deal**: Oportunidades de venta
- **Team**: Equipos de trabajo

## 🛡️ Seguridad

- Autenticación JWT
- Multi-tenancy estricto
- Validación HMAC en webhooks
- Passwords hasheados con bcrypt
- CORS configurado

## 📈 Estado del Proyecto

**Completitud: ~95%**

### ✅ Completamente Funcional
- Autenticación y multi-tenancy
- Gestión de conversaciones
- Pipeline de ventas
- Integraciones con Chatwoot/Evolution
- Dashboard y reportes

### ⚠️ Pendientes Menores
- Notificación a NOVA para procesamiento RAG
- Activar validación HMAC en producción
- Tests automatizados

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y propietario.

---

**Desarrollado con ❤️ para automatizar conversaciones con IA**