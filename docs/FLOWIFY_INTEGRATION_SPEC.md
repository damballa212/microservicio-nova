# GUÍA DE INTEGRACIÓN FLOWIFY -> NOVA AI
**Versión de API:** 2.0 (Orquestación Dinámica)
**Fecha:** 26 Dic 2025

> [!NOTE]
> Para documentación técnica completa, consulte [PRD_NOVA_AI.md](./PRD_NOVA_AI.md).

Este documento define las especificaciones técnicas para que el equipo de Flowify CRM integre correctamente el microservicio NOVA AI con la nueva arquitectura de selección dinámica de prompts.

## 📌 Resumen del Cambio
Anteriormente, NOVA usaba un prompt estático. Ahora, **Flowify debe enviar el contexto del nicho (Vertical) y los datos operativos (Tenant Data)** en cada petición. NOVA usará esta info para ensamblar un cerebro a medida en tiempo real.

---

## 1. Nuevo Payload de Entrada (Request)
Cuando Flowify hace POST a `/webhook/inbound` o invoca al agente, debe asegurarse de incluir los siguientes campos en el objeto de estado o payload.

### Estructura del Objeto `state` esperado:

```json
{
  "chat_input": "Texto del usuario...",
  "phone_number": "54911...",
  "identifier": "unique_session_id",
  
  // --- NUEVOS CAMPOS REQUERIDOS ---
  "vertical_id": "string", // Ver catálogo abajo
  "tenant_data": {
     "nombre": "Nombre del Negocio",
     "giro": "Slogan o descripción corta",
     "ubicacion": "Dirección física (opcional)",
     "horarios": "Texto libre de horarios",
     "reglas_reserva": "Reglas específicas de reserva",
     "delivery_info": "Costos de envío, zonas, tiempos",
     "metodos_pago": "Lista de métodos aceptados",
     "reglas": "Reglas de negocio misceláneas",
     "tono": "Instrucciones de tono (ej: Formal, Amigable con emojis)",
     "oferta": "Resumen de productos/servicios clave"
  }
}
```

### Catálogo de `vertical_id` Soportados
| vertical_id | Descripción | Casos de Uso |
| :--- | :--- | :--- |
| `restaurante` | (Default) Comida y Bebida | Pizzerías, Sushi, Cafeterías. |
| `ecommerce` | Retail y Tiendas Online | Ropa, Zapatos, Tecnología. |
| `optica` | Salud Visual | Clínicas oftalmológicas, venta de lentes. |

> **Nota:** Si se envía un ID desconocido o nulo, el sistema hará fallback a `restaurante`.

---

## 2. Contrato de Salida (Response)
NOVA garantiza devolver **siempre** un JSON estructurado de tal forma que Flowify pueda tomar decisiones automatizadas.

### Estructura de Respuesta:
```json
{
  "response_text": "Texto final para enviar al usuario por WhatsApp.",
  
  "requires_human": boolean, // true = Escalar a agente humano inmediatamente
  
  "escalation_reason": "string", // null, "complexity", "user_request", "sentiment_negative"
  
  "nlu": {
    "intent": "string", // Identificador de intención (ver abajo)
    "confidence": 0.0-1.0, // Nivel de certeza
    "entities": {
      "clave": "valor", // Datos extraídos (ej: fecha, producto, talla)
      "cantidad": 1
    }
  },
  
  "suggested_actions": {
    "set_ia_state": "off" | null, // Si es "off", Flowify debe apagar la IA para este chat
    "apply_labels": ["label1", "label2"] // Etiquetas para clasificar el contacto/chat
  }
}
```

### Intents por Vertical (Referencia)

**Restaurante:**
*   `menu_consulta`, `reserva_intencion`, `pedido_intencion`, `reclamo_queja`, `alergias_info`.

**E-commerce:**
*   `catalogo_consulta`, `stock_consulta`, `pedido_estado` (WISMO), `garantia_devolucion`.

**Óptica:**
*   `examen_agendar`, `lentes_consulta`, `cristales_info`, `reparacion_ajuste`.

---

## 3. Lista de Tareas para Desarrollador Flowify

- [ ] **Actualizar Webhook/Llamada a NOVA**: Asegurar que al llamar al servicio, se inyecten `vertical_id` y el objeto `tenant_data` extraído de la configuración de la empresa en Flowify.
- [ ] **Manejo de Respuesta JSON**: Parsear el JSON de salida de NOVA.
    - Mostrar `response_text` en el chat.
    - Si `requires_human` es true -> Disparar alerta en dashboard / mover a inbox "Humanos".
    - Si `suggested_actions.set_ia_state` es "off" -> Cambiar estado de IA en DB local.
    - Si vienen `apply_labels` -> Aplicar etiquetas al contacto/conversación.
- [ ] **Validación de Datos**: Validar que `tenant_data` no vaya vacío o nulo para evitar respuestas genéricas del bot.

---

**Nota Final:** Esta integración permite que NOVA se comporte como un experto en cada nicho sin cambios de código en el microservicio, delegando la personalización a la configuración que vive en Flowify.
