# Plan: Controles en "Detalles" de Conversaciones alineados a Chatwoot

## Resumen
- Integrar en la sección "Detalles" de la página de Conversaciones controles de: Agente asignado, Asignar a mi, Equipo asignado y Prioridad.
- Reutilizar endpoints ya existentes y respetar el estilo visual actual de Flowify.
- Extender el contrato de `ConversacionResponse` para exponer `usuario_asignado_id` y `team_id` y, opcionalmente, nombres derivados.

## Objetivos
- Mostrar el estado actual de asignación (usuario/equipo) y permitir cambios rápidos.
- Permitir "Asignar a mi" con un clic, vinculado a Chatwoot.
- Exponer y editar la prioridad de la conversación con badges coherentes con la UI.
- Mantener sincronización con Chatwoot (atributos y labels).

## Alcance y decisiones
- Colocar los controles dentro de "Configuración" del componente `ContactDetails`.
- No introducir nuevas dependencias; usar `Button`, `Badge`, `Switch`, `select` y hooks existentes.
- Valores de prioridad flowify: `alta | media | baja`. Nota: Chatwoot muestra opciones como "Urgente" y "Ninguna"; se documenta la compatibilidad más abajo.

## Inventario de APIs y modelos
- Listado y detalle de conversaciones:
  - `GET /api/conversaciones` y `GET /api/conversaciones/{id}` devuelven `ConversacionResponse`: `backend/app/api/conversaciones.py:77` y `backend/app/api/conversaciones.py:120` con schema en `backend/app/schemas/contacto.py:43-59`.
  - Decisión: extender `ConversacionResponse` para incluir `usuario_asignado_id` y `team_id` (y opcionalmente `usuario_asignado_nombre`, `team_nombre`).
- Asignación de conversación (usuario/equipo):
  - `POST /api/conversaciones/{id}/assign` con `assignee_id` (Chatwoot) y/o `team_id` (Chatwoot). Lógica y persistencia: `backend/app/api/conversaciones.py:566` y siguientes; mapeo a IDs locales tras éxito: `backend/app/api/conversaciones.py:595-616`.
- Prioridad de conversación:
  - `POST /api/conversaciones/{id}/prioridad` con `prioridad: 'alta'|'media'|'baja'`. Sincroniza atributo personalizado y labels en Chatwoot: `backend/app/api/conversaciones.py:707` y `backend/app/api/conversaciones.py:720-744`.
- Vincular usuario actual con Chatwoot (para "Asignar a mi"):
  - `POST /api/chatwoot/ensure/account-user` retorna/crea `chatwoot_user_id` para el usuario actual: `backend/app/api/chatwoot.py:649-704`.
- Listados auxiliares:
  - Agentes humanos: `GET /api/agentes-humanos` → `AgenteHumanoResponse` con `chatwoot_user_id`: `backend/app/api/agentes_humanos.py:45-48`, schema `backend/app/schemas/usuario.py:14-22`.

## Estado de Implementación
- ✅ **Backend**: Todos los endpoints necesarios están implementados
- ✅ **Frontend**: Componente `ContactDetails` con controles completos
- ✅ **Sincronización**: Chatwoot attributes y labels funcionando
- ✅ **SSE**: Eventos en tiempo real para cambios de estado

## Funcionalidades Disponibles
1. **Asignación de conversaciones** a usuarios/equipos
2. **Control de prioridad** con badges visuales
3. **Toggle IA state** (on/off)
4. **Handoff automático** IA→Humano
5. **Sincronización bidireccional** con Chatwoot

---

**Nota**: Esta funcionalidad está completamente implementada y operativa en el sistema actual.