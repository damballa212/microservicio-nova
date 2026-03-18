📡 API Endpoints: NOVA Google Sheets
Backend preparado: ✅ Completado
Archivo: 
backend/app/api/agentes.py

📋 ENDPOINTS DISPONIBLES (3 nuevos)
1. POST /api/agentes/nova/configure-sheet
Descripción: Configura el Google Sheet de inventario para NOVA

Autenticación: JWT (usuario autenticado)

Request Body:

{
  "google_sheet_url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
}
Validaciones:

URL debe ser válida de Google Sheets
Pattern: https://docs.google.com/spreadsheets/d/[SHEET_ID]
Se extrae automáticamente el Sheet ID
Response 200 OK:

{
  "success": true,
  "message": "Google Sheet configurado exitosamente para NOVA. Sheet ID: 1BxiMVs0XRA5...",
  "google_sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "empresa_id": 5
}
Errores:

400 Bad Request: URL inválida o Sheet ID no extraíble
404 Not Found: Empresa no encontrada
401 Unauthorized: Usuario no autenticado
2. GET /api/agentes/nova/status
Descripción: Obtiene el estado completo de configuración de NOVA

Autenticación: JWT (usuario autenticado)

Response 200 OK:

{
  "nova_activo": true,
  "google_sheet_configurado": true,
  "google_sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "base_conocimiento_archivos": 3,
  "system_prompt_configurado": true
}
Campos:

nova_activo: Si el agente NOVA está activado (switch ON)
google_sheet_configurado: Si tiene Sheet ID guardado
google_sheet_id: El Sheet ID configurado (null si no hay)
base_conocimiento_archivos: Número de PDFs/docs subidos para RAG
system_prompt_configurado: Si tiene system prompt personalizado
Uso: Ideal para mostrar en frontend el estado de configuración de NOVA

3. DELETE /api/agentes/nova/remove-sheet
Descripción: Elimina la configuración del Google Sheet de NOVA

Autenticación: JWT (usuario autenticado)

Response 200 OK:

{
  "success": true,
  "message": "Google Sheet removido exitosamente de NOVA"
}
Efecto:

Establece empresa.google_sheet_id = NULL
NOVA dejará de consultar inventario en tiempo real
El RAG (base de conocimiento) se mantiene intacto
🎯 FLUJO DE TRABAJO COMPLETO
Paso 1: Usuario comparte su Sheet
El usuario (empresa "Baku Burgers"):

Abre su Google Sheet de inventario
Click en "Compartir"
Agrega email: nova-bot@tu-proyecto.iam.gserviceaccount.com
Le da permisos de "Viewer" o "Editor"
Paso 2: Usuario configura en CRM
Request desde Frontend:

const response = await fetch('/api/agentes/nova/configure-sheet', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    google_sheet_url: 'https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit'
  })
});
const data = await response.json();
console.log(data.google_sheet_id); // "1BxiMVs0XRA5..."
Paso 3: Backend procesa automáticamente
Validación: URL válida de Google Sheets
Extracción: Extrae Sheet ID con regex
Guardado: UPDATE empresas SET google_sheet_id = '1BxiMVs0...' WHERE id = 5
Respuesta: Confirma con Sheet ID extraído
Paso 4: n8n consume el Sheet ID
Cuando un cliente pregunta: "¿Tienen pizza hawaiana disponible?"

Workflow NOVA en n8n:

Webhook recibe: {
  "empresa_id": 5,
  "mensaje": "¿Tienen pizza hawaiana disponible?"
}
  ↓
Lookup en CRM: empresa_id → google_sheet_id
  ↓
Google Sheets Tool consulta: Sheet ID "1BxiMVs0..."
  ↓
Encuentra: {"pizza_hawaiana": {"stock": 5, "disponible": true}}
  ↓
NOVA responde: "¡Sí! Tenemos 5 pizzas hawaianas disponibles"
🧪 TESTING DE ENDPOINTS
Test 1: Configurar Sheet válido
curl -X POST http://localhost:8000/api/agentes/nova/configure-sheet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "google_sheet_url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
  }'
Esperado: Status 200, Sheet ID extraído

Test 2: URL inválida
curl -X POST http://localhost:8000/api/agentes/nova/configure-sheet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "google_sheet_url": "https://www.google.com"
  }'
Esperado: Status 400, mensaje de error

Test 3: Obtener status
curl -X GET http://localhost:8000/api/agentes/nova/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
Esperado: Status 200, objetocon configuración actual

Test 4: Remover Sheet
curl -X DELETE http://localhost:8000/api/agentes/nova/remove-sheet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
Esperado: Status 200, Sheet ID eliminado de la BD

📊 UTILIDADES CREADAS
Archivo: 
app/utils/nova.py
Función 1: 
extract_sheet_id(url)

>>> from app.utils.nova import extract_sheet_id
>>> extract_sheet_id("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5/edit")
'1BxiMVs0XRA5'
Función 2: 
validate_sheet_id_format(sheet_id)

>>> from app.utils.nova import validate_sheet_id_format
>>> validate_sheet_id_format("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
True
>>> validate_sheet_id_format("invalid!")
False
🔐 SCHEMAS PYDANTIC
Archivo: 
app/schemas/nova.py
1. NovaGoogleSheetConfig (Input)

Valida URL de Google Sheets
Extrae Sheet ID automáticamente
2. NovaGoogleSheetResponse (Output)

Confirma éxito de configuración
Devuelve Sheet ID extraído
3. NovaConfigStatus (Output)

Estado completo de NOVA
Usado por GET /status
✅ BACKEND LISTO
Archivos creados/modificados:

✅ 
backend/app/schemas/nova.py
 (3 schemas)
✅ 
backend/app/utils/nova.py
 (2 utilidades)
✅ 
backend/app/api/agentes.py
 (3 endpoints nuevos)
✅ 
backend/app/models/empresa.py
 (campo google_sheet_id)
✅ 
backend/alembic/versions/002_nova_google_sheets.py
 (migración)
Base de datos: ✅ Migración aplicada

Próximos pasos:

 Crear Service Account en Google Cloud
 Configurar credenciales en n8n
 Workflow Maestro NOVA en n8n
 Frontend para onboarding