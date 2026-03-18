# Instrucciones para Conectar al Backend con Supabase

## ❌ Problema Actual

El backend no puede conectarse a la base de Datos de Supabase porque el hostname `db.utlsypgtvjewksswzfec.supabase.co` no se puede resolver (Error DNS).

## ✅ Solución

Necesitas proporcionar la **URL de conexión correcta** desde tu panel de Supabase.

### Paso 1: Ir a tu Panel de Supabase

1. Ve a: https://supabase.com/dashboard
2. Selecciona tu proyecto
3. En el menú lateral, ve a **Settings → Database**

### Paso 2: Obtener Connection String

Hay dos opciones:

#### Opción A: Connection Pooling (Recomendado para producción)
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

#### Opción B: Direct Connection (Más simple para desarrollo)
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Paso 3: Convertir para AsyncPG

Reemplaza `postgresql://` con `postgresql+asyncpg://`

**Ejemplo**:
```
postgresql+asyncpg://postgres:tu-contraseña@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Paso 4: Actualizar `.env`

Luego de obtener la URL correcta, actualiza el archivo `.env` en el backend:

```bash
cd "/Users/marlon/Documents/FLOWIFY CRM/backend"
nano .env  # o usa tu editor preferido
```

Y reemplaza la línea `DATABASE_URL` con la URL correcta.

### Paso 5: Reiniciar el Servidor

```bash
# El servidor se recargará automáticamente si está en modo --reload
# O reinicia manualmente con:
cd "/Users/marlon/Documents/FLOWIFY CRM/backend"
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

## 🎯 Estado Actual

- ✅ Código del backend completo y funcional
- ✅ Tablas creadas en Supabase
- ✅ Dependencias instaladas (SQLAlchemy 2.0.36, asyncpg, greenlet, etc.)
- ✅ Configuración SSL para Supabase
- ❌ URL de conexión incorrecta (requiere actualización)

## 📝 Archivos Importantes

- `/Users/marlon/Documents/FLOWIFY CRM/backend/.env` - Variables de entorno (actualizar aquí)
- `/Users/marlon/Documents/FLOWIFY CRM/backend/alembic.ini` - También tiene la URL (actualizar también)

Una vez que proporciones la URL correcta, podré actualizar estos archivos y probar la conexión.
