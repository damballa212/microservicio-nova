# 🚀 Guía de Instalación - Flowify CRM

**Última actualización:** Diciembre 22, 2024

Esta guía te ayudará a configurar el entorno de desarrollo completo de Flowify CRM (Backend + Frontend).

---

## 📋 Requisitos Previos

### Software Requerido
- **Python 3.11+**
- **Node.js 18+** y npm/yarn
- **PostgreSQL 14+** (o cuenta de Supabase)
- **Git**

### Cuentas Externas Necesarias
- **Chatwoot** (Platform API Token)
- **Evolution API** (API Key)
- **Supabase** (opcional, para storage)
- **n8n** (para workflows de IA)

---

## 🔧 Instalación del Backend

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd "FLOWIFY CRM/backend"
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv

# Activar en Mac/Linux
source venv/bin/activate

# Activar en Windows
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```bash
# Base de Datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/flowify

# JWT
SECRET_KEY=tu-clave-secreta-muy-segura-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Chatwoot
CHATWOOT_URL=https://chatwoot.tu-dominio.com
CHATWOOT_PLATFORM_TOKEN=tu-platform-token-aqui

# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://evolution.tu-dominio.com
EVOLUTION_API_KEY=tu-api-key-aqui

# Backend URL (para webhooks)
BACKEND_URL=http://localhost:8000

# NOVA (Microservicio IA)
NOVA_WEBHOOK_URL=https://n8n.tu-dominio.com/webhook/nova

# Supabase (opcional, para storage)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key-aqui

# CORS
FRONTEND_URL=http://localhost:3000
```

### 5. Configurar Base de Datos

#### Opción A: PostgreSQL Local

```bash
# Crear base de datos
createdb flowify

# Ejecutar migraciones
alembic upgrade head
```

#### Opción B: Supabase

1. Ve a https://supabase.com/dashboard
2. Crea un nuevo proyecto
3. Ve a **Settings → Database**
4. Copia la **Connection String** (Connection Pooling recomendado)
5. Convierte a AsyncPG:

```bash
# De:
postgresql://postgres:password@aws-0-region.pooler.supabase.com:6543/postgres

# A:
postgresql+asyncpg://postgres:password@aws-0-region.pooler.supabase.com:6543/postgres
```

6. Actualiza `DATABASE_URL` en `.env`
7. Ejecuta migraciones:

```bash
alembic upgrade head
```

### 6. Ejecutar Servidor de Desarrollo

```bash
uvicorn app.main:app --reload --port 8000
```

El backend estará disponible en:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

---

## 🎨 Instalación del Frontend

### 1. Navegar al Directorio

```bash
cd "../frontend"
```

### 2. Instalar Dependencias

```bash
npm install
# o
yarn install
```

### 3. Configurar Variables de Entorno

Crea `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Ejecutar Servidor de Desarrollo

```bash
npm run dev
# o
yarn dev
```

El frontend estará disponible en:
- **App:** http://localhost:3000

---

## 🧪 Verificar Instalación

### Backend

```bash
# Health check
curl http://localhost:8000/health

# Debería retornar:
# {"status": "healthy", "database": "connected"}
```

### Frontend

1. Abre http://localhost:3000
2. Deberías ver la página de login
3. Intenta hacer login (si ya tienes usuario)

---

## 🔑 Crear Super Admin (Primera vez)

```bash
cd backend
python -c "
from app.database import SessionLocal
from app.models import Usuario
from app.utils.security import get_password_hash
import asyncio

async def create_super_admin():
    async with SessionLocal() as db:
        admin = Usuario(
            email='admin@flowify.com',
            nombre='Super Admin',
            password_hash=get_password_hash('admin123'),
            es_super_admin=True,
            empresa_id=None
        )
        db.add(admin)
        await db.commit()
        print('✅ Super admin creado')

asyncio.run(create_super_admin())
"
```

---

## 🛠️ Comandos Útiles

### Backend

```bash
# Ejecutar servidor
uvicorn app.main:app --reload --port 8000

# Ver logs detallados
uvicorn app.main:app --reload --log-level debug

# Crear migración
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Rollback última migración
alembic downgrade -1

# Verificar dependencias
pip list

# Actualizar dependencias
pip install -r requirements.txt --upgrade
```

### Frontend

```bash
# Ejecutar desarrollo
npm run dev

# Build para producción
npm run build

# Ejecutar producción
npm start

# Linting
npm run lint

# Type checking
npx tsc --noEmit
```

---

## 🐛 Troubleshooting

### Error: "Cannot connect to database"

**Causa:** URL de conexión incorrecta o base de datos no accesible.

**Solución:**
1. Verifica `DATABASE_URL` en `.env`
2. Si usas Supabase, asegúrate de usar Connection Pooling
3. Verifica que PostgreSQL esté corriendo (local)
4. Prueba conexión manual:

```bash
psql "postgresql://user:password@host:port/database"
```

### Error: "CORS policy blocked"

**Causa:** Frontend no está en la lista de orígenes permitidos.

**Solución:**
1. Verifica `FRONTEND_URL` en backend `.env`
2. Reinicia el servidor backend
3. Verifica que `NEXT_PUBLIC_API_URL` apunte al backend correcto

### Error: "Module not found" (Frontend)

**Causa:** Dependencias no instaladas o desactualizadas.

**Solución:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Error: "JWT token invalid"

**Causa:** Token expirado o `SECRET_KEY` cambió.

**Solución:**
1. Haz logout y login nuevamente
2. Verifica que `SECRET_KEY` sea consistente
3. Limpia localStorage del navegador

---

## 📚 Próximos Pasos

Una vez instalado:

1. **Crear primera empresa** (como super admin)
2. **Configurar Chatwoot** (crear Account)
3. **Conectar WhatsApp** (Evolution API)
4. **Configurar agente NOVA** (system prompt)
5. **Subir base de conocimiento** (PDFs)

Ver documentación completa en:
- **Arquitectura:** `docs/ARQUITECTURA_ACTUAL.md`
- **Integraciones:** `docs/integraciones/CHATWOOT_EVOLUTION.md`
- **Estado:** `docs/ESTADO_PROYECTO.md`

---

## 🚀 Deploy a Producción

### Backend

**Opciones recomendadas:**
- **Railway** (más fácil)
- **Render** (free tier disponible)
- **DigitalOcean App Platform**
- **AWS ECS/Fargate**

**Pasos generales:**
1. Configurar variables de entorno
2. Usar PostgreSQL managed (no SQLite)
3. Configurar `BACKEND_URL` con dominio real
4. Habilitar HTTPS
5. Configurar CORS con dominio frontend
6. Activar validación HMAC en webhooks

### Frontend

**Opciones recomendadas:**
- **Vercel** (recomendado, creadores de Next.js)
- **Netlify**
- **Cloudflare Pages**

**Pasos generales:**
1. Conectar repositorio Git
2. Configurar `NEXT_PUBLIC_API_URL` con backend real
3. Build automático en cada push
4. Configurar dominio custom

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs del backend/frontend
2. Consulta la documentación en `docs/`
3. Verifica las variables de entorno
4. Asegúrate de tener las versiones correctas de Python/Node

---

**¡Listo! Ahora tienes Flowify CRM corriendo localmente. 🎉**
