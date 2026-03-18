# 🧠 NOVA AI - Microservicio de IA Conversacional Empresarial

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

**NOVA (Neural Omnichannel Virtual Assistant)** es el cerebro conversacional del ecosistema **Flowify CRM**. Transforma conversaciones en oportunidades de venta, resuelve consultas 24/7 y califica leads automáticamente.

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Multi-tenant** | Aislamiento estricto por empresa con prompts personalizados |
| **Multimodal** | Procesa texto, audio (Whisper) e imágenes (GPT-4 Vision) |
| **Memoria Híbrida** | Redis (velocidad) + PostgreSQL (persistencia) + Episodios Semánticos |
| **RAG Empresarial** | Base de conocimiento vectorial con pgvector + Cohere reranking |
| **NLU Avanzado** | Clasificación de intents y scoring automático de leads |
| **Dashboard Neural** | Visualización en tiempo real del flujo de ejecución |

## 🚀 Quick Start

### Requisitos
- Python 3.10+
- PostgreSQL con extensión `pgvector`
- Redis

### Instalación

```bash
# Clonar y configurar
git clone <repo-url>
cd MICROSERVICIO\ CHATBOT

# Entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: .\venv\Scripts\activate  # Windows

# Dependencias
pip install -r requirements.txt

# Configuración
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar
uvicorn src.main:app --reload
```

### Docker

```bash
docker-compose up --build
```

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [**PRD_NOVA_AI.md**](./docs/PRD_NOVA_AI.md) | 📋 **Documento maestro** - Arquitectura, APIs, Prompts, Memoria, RAG, y más |
| [FLOWIFY_INTEGRATION_SPEC.md](./docs/FLOWIFY_INTEGRATION_SPEC.md) | 🔗 Guía de integración para el equipo Flowify |
| [DEPLOYMENT_EASYPANEL.md](./docs/DEPLOYMENT_EASYPANEL.md) | 🚀 Guía de despliegue en Easypanel |

> [!TIP]
> El PRD contiene toda la documentación técnica del proyecto. Consulta las secciones específicas según lo que necesites.

## 🏗️ Estructura del Proyecto

```
src/
├── api/              # Routers (main, test, rag, metrics)
├── graph/            # LangGraph DAG builder
├── nodes/            # 15 nodos del pipeline
├── prompts/          # Sistema modular (Core/Vertical/Tenant)
├── memory/           # Redis + PostgreSQL + Episodios
├── rag/              # Base de conocimiento vectorial
├── events/           # WebSocket EventEmitter
└── processors/       # Multimodal (text, audio, image)

nova-dashboard/       # Dashboard Neural (Next.js)
```

## 🔌 API Endpoints

| Router | Base | Descripción |
|--------|------|-------------|
| Main | `/` | Webhooks, health, WebSocket |
| Test | `/test` | Endpoints de prueba y debugging |
| RAG | `/rag` | Ingesta y búsqueda de documentos |
| Metrics | `/metrics` | Métricas y observabilidad |

## 🧪 Tests

```bash
# Todos los tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=src --cov-report=html
```

---

© 2025 Flowify AI - Todos los derechos reservados.
