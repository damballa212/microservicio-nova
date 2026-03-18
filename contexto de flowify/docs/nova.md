ESTO ES UN CHAT QUE TUVE CON CHATGPT


## CHAT GPT:

Listo. Ya tengo el contexto completo del CRM Flowify que estás desarrollando (y cómo se conecta con tu chatbot NOVA).

Qué es Flowify (en 1 mapa mental)

Flowify es un CRM multi-tenant (una sola app, muchas empresas aisladas) con Chatwoot como hub de conversaciones, FastAPI + PostgreSQL como backend, Next.js como frontend, y NOVA (IA) orquestada vía n8n / microservicio LangGraph.  ￼  ￼

Flujo principal (end-to-end)
	1.	Chatwoot recibe el mensaje (WhatsApp vía Evolution API).
	2.	Webhook → Flowify: persiste contacto/conversación/mensajes y aplica etiquetas.
	3.	Si pasa el gating de IA, Flowify POSTea a n8n (Workflow NOVA), que hace RAG + LLM y devuelve respuesta.
	4.	Flowify publica la respuesta en Chatwoot para que llegue al cliente.  ￼

Piezas clave del CRM

1) Multi-tenant “de verdad”
	•	Aislamiento por empresa_id en todos los modelos y API key por empresa (para webhooks).  ￼
	•	El chatbot también va hacia prompt dinámico por tenant y parámetros LLM (system_prompt, temperatura, max_tokens).  ￼

2) Control IA↔Humano (Chatwoot-first) + anti-loop

Tu regla maestra: un solo “switch” en Chatwoot con ia_state: 'on' | 'off' + etiquetas:
	•	humano_activo cuando takeover humano
	•	asistencia_ia cuando IA activa  ￼

Y el webhook:
	•	Solo reenvía a n8n si ia_state == 'on'.  ￼
	•	Si detecta mensaje humano público saliente, fuerza IA off y etiqueta humano_activo.  ￼
	•	Anti-loop: mensajes IA se marcan (content_attributes.flowify_source == 'ai' y/o sender_id == nova.chatwoot_user_id) y no apagan IA ni se re-reenvían a n8n.  ￼

3) Suscripciones/entitlements (y demo) como “source of truth” del gating

Tienes planes (Free/Pro/Demo Pro/Enterprise) con entitlements; el backend decide siempre:
	•	Free: nova_enabled=false y además human_intervention='always_on' (o sea, IA no disponible).  ￼
	•	Pro / Demo Pro: nova_enabled=true (demo por tiempo con demo_ends_at).  ￼
	•	Servicio get_entitlements(empresa_id) combina plan + overrides y es el source of truth.  ￼
	•	El gating de NOVA se unificó: primero empresa.configuracion.subscription.entitlements.nova_enabled, fallback a tabla Suscripcion (incluye demo expirada).  ￼

En UI ya está contemplado:
	•	Pro/Demo ven el switch IA.
	•	Free oculta switch y muestra “IA no incluida” + botón Upgrade.  ￼

4) Conversaciones en tiempo real (SSE “event-first”)

Flowify usa SSE para que el inbox no haga re-fetch constante:
	•	Backend: publish() no bloqueante y subscribe() con cola más grande para ráfagas.  ￼
	•	Webhooks enriquecidos: emiten eventos tipo "message" y "conversation_created" con payload suficiente para actualizar UI al instante.  ￼
	•	Frontend: EventSource al stream y actualiza lista + timeline “en caliente”.  ￼
	•	El plan UI documenta también la parte de detalles (asignación, equipo, prioridad) ya implementada en ContactDetails.  ￼

5) Pipeline de ventas: Deals desde Conversaciones (con IA + n8n)

Puntos de diseño clave:
	•	Persistencia dual: la conversación NO desaparece; el Deal vive en “Negociaciones” y se vincula por conversacion_id.  ￼
	•	Política IA:
	•	auto_create_deals=false por defecto
	•	deal_confidence_threshold=0.75
	•	override manual desde UI ante propuestas IA  ￼
	•	Reenvío a n8n siempre como evento de conversación, condicionado por IA activa y sin takeover + corte por demo/entitlements.  ￼
	•	Priorización unificada alta|media|baja, reflejada en Chatwoot (custom_attributes.prioridad) y en datos del contacto, con badges/filtros en UI.  ￼
	•	Anti-duplicados: 1 Deal por conversacion_id en ventana (72h configurable) con override manual.  ￼

6) Observabilidad (tokens, latencia, errores por nodo)

Tu stack de chatbot tiene un plan de observabilidad serio:
	•	Métricas por nodo: tokens/costo, latencia, errores, modelo/proveedor.  ￼
	•	Persistencia en Redis con TTL (ej. 7 días) y endpoints /metrics/*.  ￼
	•	Dashboard: pintar tokens/costo/errores sobre el grafo.  ￼

Estado del proyecto (según tu propio “Resumen Completo”)

Completitud general ~92%, con Pipeline de Ventas y Productos marcados como “recién implementado”.  ￼

Y tus “pendientes críticos/importantes” más relevantes:
	•	Firma HMAC de webhooks Chatwoot: el código existe pero estaba desactivado en doc (riesgo spoofing).  ￼
	•	Conocimiento: PDFs suben pero falta notificar a n8n para que el RAG se actualice.  ￼
	•	Suscripción UI: se propone página /dashboard/suscripcion (parte ya existe en flujos/CTAs).  ￼

⸻

Si me dices qué vas a construir ahora mismo (por ejemplo: “panel Propuestas IA”, “activar HMAC en prod”, “página de Suscripción”, o “workflow n8n para deal_suggestion”), te lo bajo a pasos concretos + contratos JSON + endpoints exactos para que lo implementes sin fricción.



## YO:

Si entiendes que para el chatbot, como mi crm sera multi tenant, o sea cada empresa es de un nicho diferente, como una clinica, un restaurante, debemos armar un systemprompt para cada nicho, y quiero que planeemos primero el de restaurante, entremos en modo planeamiento profesional y critico


## CHATGPT:

Sí, lo entiendo perfecto: multi-tenant = un system prompt por empresa, y como cada empresa vive en un nicho distinto, el prompt tiene que ser especializado por vertical (restaurante ≠ clínica), pero manteniendo un “núcleo” común (seguridad, anti-alucinación, formato de outputs, escalamiento a humano, logging/metadata).

Entremos en modo planeamiento profesional y crítico para el prompt de Restaurante.

1) Decisión de arquitectura de prompts (para que esto escale)

Vamos a diseñar así:
	•	Prompt Núcleo (global, igual para todos los tenants)
Reglas duras: no inventar, cómo pedir datos faltantes, cómo escalar a humano, formato de respuesta, políticas de privacidad, estilo, etc.
	•	Prompt Vertical: Restaurante (igual para todos los restaurantes)
Intenciones + flujos típicos de restaurante: menú, reservas, delivery, horarios, ubicación, alergias, eventos, grupos grandes, reclamos.
	•	Prompt Empresa (tenant-specific)
Datos concretos: nombre, tono, menú real, horarios, links, políticas, zonas de delivery, métodos de pago, promos, reglas de reservas.

En runtime, el system_prompt final suele ser:
CORE + VERTICAL_RESTAURANTE + TENANT_RESTAURANTE_X

Esto evita que “cada restaurante sea un mundo” y te permite versionar y testear.

⸻

2) Qué debe lograr el prompt de Restaurante (objetivos medibles)

El asistente debe optimizar estas 5 métricas:
	1.	Resolver en 1–2 turnos (máxima tasa de “respuesta útil” con mínima fricción).
	2.	Cero alucinaciones (si no está en Conocimiento/Sheets/config, no inventa).
	3.	Convertir a acción (reserva / pedido / dirección / pago / delivery).
	4.	Escalamiento limpio cuando toque (humano, casos sensibles, ambigüedad alta).
	5.	Datos estructurados para el CRM (intent, datos extraídos, señales de compra).

⸻

3) “Capacidades” permitidas vs prohibidas (crítico para no romper confianza)

Permitidas (siempre que haya datos)
	•	Informar horarios, ubicación, menú, precios, promos, medios de pago, políticas (propinas, mascotas, etc.)
	•	Guiar reservas (tomar datos y crear “solicitud” si existe integración; si no, derivar)
	•	Guiar pedido (armar carrito o “resumen de pedido” y confirmar)
	•	Manejar reclamos con empatía + captura de datos + escalamiento

Prohibidas (aunque el usuario insista)
	•	Confirmar una reserva como “hecha” si no hay integración real para crearla
	•	Inventar platos, precios, tiempos exactos de entrega, disponibilidad
	•	Dar consejos médicos sobre alergias (“esto es seguro”) — solo advertir y sugerir confirmar con el local

⸻

4) Intenciones del vertical Restaurante (la columna vertebral)

Estas intents deben estar explícitas en el prompt:
	•	menu_consulta (qué recomiendas / tienen vegan / sin gluten)
	•	precio_consulta
	•	horario_ubicacion
	•	reserva (mesa / cumpleaños / grupo)
	•	pedido_delivery / pedido_pickup
	•	estado_pedido (si aplica)
	•	eventos_catering (grupos grandes = lead caliente)
	•	reclamo / postventa
	•	hablar_humano
	•	otro

Y para cada intent definimos:
	•	Datos mínimos a recolectar
	•	Preguntas cerradas (para no alargar)
	•	Cuándo escalar
	•	Qué loggear al CRM

⸻

5) Plantilla de System Prompt — Restaurante (versión 0.1)

Aquí va el “molde” profesional que vamos a iterar. Está escrito para que lo puedas guardar en agente_config.system_prompt por tenant, con placeholders.

SYSTEM PROMPT (VERTICAL + TENANT RESTAURANTE)

Rol
Eres el asistente oficial de atención al cliente de {RESTAURANT_NAME}. Atiendes consultas, reservas y pedidos con tono {BRAND_TONE} (ej: cálido, directo, premium, juvenil).

Objetivo
Resolver rápido y con precisión. Convertir conversaciones en:
	•	Reserva solicitada/confirmable
	•	Pedido confirmado
	•	Visita al local
	•	Escalamiento a humano cuando corresponda

Fuentes de verdad (anti-alucinación)
Solo puedes afirmar datos (menú, precios, horarios, zonas, promos, políticas) si están en:
	•	Config del tenant (empresa_config)
	•	Conocimiento/RAG (docs del restaurante)
	•	Sheets/menú (si existe)
Si falta info, di “No lo tengo confirmado” y ofrece: (a) pedir un dato, (b) pasar con humano.

Estilo
	•	Respuestas cortas y accionables, máximo 6–8 líneas.
	•	Usa bullets para menú/opciones.
	•	Si el usuario escribe en otro idioma, responde en ese idioma.
	•	Nunca inventes.

Flujos
	1.	Reservas
Si piden reserva, recolecta mínimo:

	•	fecha, hora, cantidad de personas, nombre, teléfono
Luego:
	•	Si {RESERVATION_MODE} = “integrated”: confirma creación según integración.
	•	Si {RESERVATION_MODE} = “manual”: di que “lo gestionará el equipo” y escala a humano/crea ticket.
Si grupo ≥ {LARGE_PARTY_THRESHOLD}, tratar como lead prioritario.

	2.	Pedidos (delivery/pickup)
Si piden pedir:

	•	confirma si es delivery o pick-up
	•	recolecta: items + cantidades, dirección (si delivery), método de pago, nombre/teléfono
	•	si hay dudas: ofrece 2–3 recomendaciones populares (solo si existen en datos)
Antes de cerrar: manda resumen de pedido y pregunta “¿Confirmas?”

	3.	Alergias / restricciones
Si mencionan alergia, responde:

	•	advertencia + sugerir confirmación con cocina
	•	ofrece opciones si están documentadas (sin gluten/vegano/etc.)
Nunca garantices 100% seguridad.

	4.	Reclamos
Empatía breve + recolecta:

	•	qué pasó, número de pedido (si aplica), fecha/hora, canal, teléfono
Escala a humano.

	5.	Humano
Si el usuario pide “humano”, “asesor”, “llamar”, o está molesto/amenaza denuncia:

	•	escalar inmediatamente según el mecanismo definido (sin debatir).

Salida estructurada interna (para CRM)
Además de tu respuesta al cliente, genera un bloque interno (no visible al cliente) con:
	•	intent principal
	•	datos extraídos (fecha/hora/personas/dirección/items/teléfono)
	•	prioridad (alta si reserva o pedido o reclamo fuerte)
	•	requiere_humano (bool)
	•	resumen corto

(Esto puede ir como JSON en metadata si tu pipeline lo soporta.)

Límites
Si no hay información suficiente para responder con certeza, haz 1 pregunta clave y ofrece pasar a humano.

⸻

6) Lo crítico ahora: qué definimos antes de escribir el prompt final por “Restaurante X”

Para que el prompt sea realmente “de restaurante” y no genérico, necesitamos fijar los parámetros del tenant (en config o Sheets). Te dejo la lista mínima que deberías tener por restaurante:
	•	Nombre, tono, idioma default
	•	Dirección + link mapa + zona
	•	Horarios (por día) + feriados
	•	Menú estructurado: categorías → items → precio → alérgenos → disponibilidad
	•	Reservas: ¿se hacen por WhatsApp? ¿por link? ¿por teléfono? ¿o no hay?
	•	Delivery: zonas, costo, partners (PedidosYa, etc.), tiempos (si existen)
	•	Métodos de pago
	•	Políticas: mascotas, propina, cumpleaños, eventos, estacionamiento

Con eso, el prompt queda cortito y hace el trabajo. Sin eso, el prompt termina “hablando lindo” pero no vende.

⸻

Si quieres, en el siguiente paso te dejo 2 versiones del prompt de restaurante:
	1.	v0 enfocada a “conversión rápida” (venta/reserva).
	2.	v0-safe súper conservadora (cero riesgo de inventar, ideal para arrancar).

Y además te propongo un set de tests (20 mensajes reales) para validar que el prompt no se descarrile.


## yo:

Por si te sirve o te parece bien, aqui esta el payload enviado desde flowify a nova y luego de nova hacia flowify "Webhook recibido
{"body": {"event": "message_created", "conversation": {"messages": [{"content": "Tienen pizzas?", "account_id": 21, "conversation_id": 2, "source_id": 5172, "content_type": "text", "created_at": "2025-12-13T01:31:46.790Z", "sender_type": "Contact", "sender": {"identifier": "584122236071@s.whatsapp.net", "phone_number": "+584122236071", "name": "Marlon Pernia", "custom_attributes": {"estado": "ON"}}, "attachments": []}], "contact_inbox": {"contact_id": null}, "custom_attributes": {"bot_status": "
Payload Flowify
{"empresa_id": 1, "agente": "NOVA", "evento": "message_processed", "contacto": {"nombre": "Marlon Pernia", "telefono": "+584122236071", "email": null}, "conversacion_id": 2, "mensaje": {"texto": "Tienen pizzas?"}, "respuesta_agente": {"texto": "Hola Marlon, ¡sí! Tenemos una variedad de pizzas disponibles. ¿Te gustaría que te envíe el menú con los tipos de pizza y sus precios?"}, "etiquetas_aplicadas": [], "lead_calificado": false, "metadata": {"source": "nova", "execution_id": "bda80591-9786-446" si es de añadir mas campos pues me dices si no pues bien




## chatgpt:

Sí, ese payload ya está bien encaminado para un flujo multi-tenant y te sirve perfecto como “mínimo viable”. Ahora, si quieres que esto escale fino (reservas, pedidos, menús por nicho, deals, QA, métricas, dedupe), te recomiendo añadir campos opcionales en 2 capas:
	1.	Capa “transporte/infra” (versionado, idempotencia, trazas, seguridad)
	2.	Capa “semántica/CRM” (intent, entidades, confianza, acciones sugeridas)

Abajo te dejo exactamente qué agregaría y por qué, con un ejemplo JSON listo.

⸻

1) Flowify → NOVA: qué agregaría (sin romper lo que ya tienes)

Campos infra (clave)
	•	schema_version: para evolucionar sin romper n8n/NOVA.
	•	trace_id (o reutilizar execution_id): para correlación E2E.
	•	idempotency_key: evita respuestas duplicadas (Chatwoot a veces reintenta webhooks).
	•	timestamp_received: debug/latencias.
	•	auth: si vas a firmar HMAC.

Contexto multi-tenant / runtime
	•	empresa_slug (humano) además de empresa_id.
	•	timezone, locale (p/ horas de reservas y lenguaje).
	•	canales: channel: "whatsapp" | "instagram" | ...
	•	ia_state: si Flowify decide gating, pásalo para que NOVA no “decida a ciegas”.

Mensaje (mínimo “operable”)
	•	message_id (source_id de Chatwoot)
	•	direction (incoming|outgoing)
	•	content_type + attachments_meta (aunque venga vacío)
	•	contact.identifier (whatsapp jid) además de teléfono

Config del agente (lo que hace el prompt “por restaurante”)
	•	agente_config: system_prompt_id, system_prompt_version, temperature, max_tokens
	•	knowledge_refs: ids de docs / sheet id / menú version

⸻

2) NOVA → Flowify: qué agregaría para que el CRM “mande” (no solo muestre texto)

Tu respuesta actual está ok (respuesta_agente.texto). Lo potente es sumar:

Semántica
	•	intent (ej. menu_consulta, reserva, pedido_delivery, etc.)
	•	entities (p. ej. categoria: "pizzas", cantidad, direccion, hora, etc.)
	•	confidence (0–1)
	•	language

Acciones sugeridas (para automatizar)
	•	actions.apply_labels: etiquetas a aplicar en Chatwoot/Flowify
	•	actions.set_ia_state: apagar IA si el caso lo requiere
	•	actions.create_task: crear tarea/nota para humano
	•	actions.deal_suggestion: si detecta negociación

Observabilidad
	•	llm: modelo, tokens, costo estimado, latencia
	•	safety: si hubo “no inventar / faltan datos / escalado”

⸻

3) Ejemplo recomendado (compacto, extensible)

Flowify → NOVA

{
  "schema_version": "1.0",
  "trace_id": "bda80591-9786-446",
  "idempotency_key": "chatwoot:account:21:conv:2:msg:5172",
  "timestamp_received": "2025-12-13T01:31:47.120Z",

  "empresa_id": 1,
  "empresa_slug": "pizzeria-la-roma",
  "timezone": "America/Caracas",
  "locale": "es-VE",

  "channel": "whatsapp",
  "ia_state": "on",

  "contacto": {
    "nombre": "Marlon Pernia",
    "telefono": "+584122236071",
    "identifier": "584122236071@s.whatsapp.net"
  },

  "conversacion": {
    "chatwoot_account_id": 21,
    "chatwoot_conversation_id": 2
  },

  "mensaje": {
    "message_id": 5172,
    "direction": "incoming",
    "content_type": "text",
    "texto": "Tienen pizzas?",
    "attachments_meta": []
  },

  "agente": {
    "name": "NOVA",
    "agente_config": {
      "system_prompt_id": "restaurant_v1",
      "system_prompt_version": "1.2.0",
      "temperature": 0.3,
      "max_tokens": 350
    },
    "knowledge_refs": {
      "sheet_menu_id": "1Abc...",
      "menu_version": "2025-12-10"
    }
  }
}




NOVA → Flowify

{
  "schema_version": "1.0",
  "trace_id": "bda80591-9786-446",

  "empresa_id": 1,
  "conversacion_id": 2,

  "respuesta_agente": {
    "texto": "Hola Marlon, ¡sí! 🍕 Tenemos pizzas. ¿Quieres que te pase el menú con precios o me dices si la prefieres clásica, pepperoni o 4 quesos?"
  },

  "nlu": {
    "intent": "menu_consulta",
    "confidence": 0.86,
    "language": "es",
    "entities": {
      "categoria": "pizzas"
    }
  },

  "actions": {
    "apply_labels": ["consulta_menu"],
    "set_ia_state": null,
    "create_task": null,
    "deal_suggestion": null
  },

  "lead_calificado": false,
  "etiquetas_aplicadas": [],

  "observability": {
    "model": "gpt-4.1-mini",
    "tokens_in": 210,
    "tokens_out": 55,
    "latency_ms": 820
  }
}{
  "schema_version": "1.0",
  "trace_id": "bda80591-9786-446",

  "empresa_id": 1,
  "conversacion_id": 2,

  "respuesta_agente": {
    "texto": "Hola Marlon, ¡sí! 🍕 Tenemos pizzas. ¿Quieres que te pase el menú con precios o me dices si la prefieres clásica, pepperoni o 4 quesos?"
  },

  "nlu": {
    "intent": "menu_consulta",
    "confidence": 0.86,
    "language": "es",
    "entities": {
      "categoria": "pizzas"
    }
  },

  "actions": {
    "apply_labels": ["consulta_menu"],
    "set_ia_state": null,
    "create_task": null,
    "deal_suggestion": null
  },

  "lead_calificado": false,
  "etiquetas_aplicadas": [],

  "observability": {
    "model": "gpt-4.1-mini",
    "tokens_in": 210,
    "tokens_out": 55,
    "latency_ms": 820
  }
}


4) Cómo esto ayuda directamente al system prompt de Restaurante

Con esos campos, el prompt puede ser estricto y operativo, porque NOVA:
	•	sabe qué restaurante es (empresa_id/slug)
	•	sabe qué knowledge usar (sheet_menu_id/menu_version)
	•	devuelve intent + entidades + acciones, no solo texto
	•	Flowify puede automatizar: etiquetas, tareas, deals, “IA off”, etc.

⸻

Recomendación final (crítica)

Si quieres elegir “lo mínimo que realmente vale la pena”, yo haría solo 5 añadidos obligatorios ya:
	1.	schema_version
	2.	trace_id + idempotency_key
	3.	agente_config.system_prompt_id + version
	4.	nlu.intent + confidence en la vuelta
	5.	actions.apply_labels en la vuelta

Con eso, ya puedes iterar prompts de restaurante con control y sin caos.

Si te parece, el siguiente paso lo hago yo aquí: te propongo el system prompt Restaurante v1 ya escrito para producción, alineado a estos campos (intents, entidades, acciones y “no inventar”).



## YO:

La data no viene de chatwoot, el flujo es asi: whatsapp -- > evolutio api -- > chatwoot -- > flowify crm (se encarga de armar el payload) -- > nova, luego nova -- > flowify crm -- > chatwoot -- > evolution api -- > whatsapp, por lo que flowify se encarga de que si el payload viene con escalacion a humano pues flowify dispara el toggle de apagar ia y asi


## CHATGPT:

Perfecto, así queda mucho más claro: Flowify es el “cerebro orquestador” y Chatwoot/Evolution/WhatsApp son solo canales. Entonces el contrato NOVA↔Flowify debe asumir que:
	•	NOVA NO toca Chatwoot (ni “apaga IA” directamente).
	•	NOVA solo devuelve decisiones/acciones sugeridas.
	•	Flowify aplica esas acciones (toggle IA, etiquetas, asignación, etc.) y recién ahí publica al canal.

Eso es exactamente lo correcto para multi-tenant + control.

Implicación clave: el “switch IA” vive en Flowify

Tu regla queda así:
	1.	Flowify recibe evento (desde Chatwoot), normaliza y decide si llama NOVA (gating).
	2.	NOVA responde con:
	•	respuesta_agente.texto
	•	requires_human / escalation_reason
	•	actions sugeridas (por ejemplo set_ia_state: "off")
	3.	Flowify ejecuta:
	•	Si requires_human=true → apaga IA en Flowify + etiqueta humano_activo + asigna/crea tarea + (opcional) manda mensaje de “te atiende un humano”.

✅ Esto te permite que el comportamiento sea consistente aunque cambies de proveedor de canal.

⸻

Cómo ajustaría el payload (para reflejar tu flujo real)

Flowify → NOVA (sin “dependencia” de Chatwoot)

Puedes seguir mandando ids del canal si te sirven para correlación, pero NOVA debe tratarlos como metadata, no como “fuente”.

Recomendado:
	•	event_id (Flowify) + idempotency_key (Flowify) ✅
	•	channel_provider (chatwoot) + channel_conversation_id (opcional)
	•	tenant (empresa_id/slug)
	•	ia_state actual (según Flowify)
	•	context (memoria, últimos N mensajes, perfil del contacto)

NOVA → Flowify (lo importante)

NOVA debe devolver, además del texto:
	•	requires_human: true|false
	•	escalation_reason (enum)
	•	actions.set_ia_state: "off"|"on"|null
	•	actions.apply_labels: []
	•	nlu.intent/confidence/entities (para que Flowify automatice CRM/deals)

Ejemplo mínimo en tu estilo:

{
  "empresa_id": 1,
  "agente": "NOVA",
  "evento": "message_processed",
  "trace_id": "bda80591-9786-446",
  "conversacion_id": 2,

  "respuesta_agente": { "texto": "Sí tenemos pizzas 🍕. ¿Quieres que te pase el menú con precios?" },

  "nlu": {
    "intent": "menu_consulta",
    "confidence": 0.86,
    "entities": { "categoria": "pizzas" }
  },

  "requires_human": false,
  "escalation_reason": null,

  "actions": {
    "set_ia_state": null,
    "apply_labels": ["consulta_menu"]
  }
}

Y si toca humano:

{
  "requires_human": true,
  "escalation_reason": "customer_requests_human",
  "actions": {
    "set_ia_state": "off",
    "apply_labels": ["humano_activo", "requiere_atencion"]
  }
}

Qué significa esto para el System Prompt de “Restaurante”

Como Flowify ejecuta el toggle, el prompt debe obligar a NOVA a decidir y devolver flags con disciplina:
	•	“Si el usuario pide humano / está molesto / tema sensible / falta info crítica para cerrar pedido/reserva → requires_human=true”
	•	“Si falta menú real/precios/horario y no hay fuente → NO inventar; pedir 1 dato o escalar”
	•	“Siempre devolver intent + entities para que Flowify automatice”

👉 O sea: el prompt ya no es solo “responde bonito”, sino “responde + clasifica + sugiere acciones”.

⸻

Reglas duras que yo pondría (críticas)
	1.	NOVA nunca afirma “reserva confirmada” si no recibió explícitamente capabilities.reservas.integrated=true en el payload.
	2.	Si el usuario dice “quiero hablar con un humano” → requires_human=true inmediato.
	3.	Si hay reclamo fuerte / amenaza / chargeback → humano inmediato.
	4.	Si hay alergia → NO garantizar; sugerir confirmación con cocina y, si el usuario insiste, humano.

⸻

Si estás de acuerdo, el siguiente paso lo hago ya: te escribo el System Prompt Restaurante v1 (vertical) en formato listo para agente_config.system_prompt, incluyendo el bloque de salida estructurada (intent/entities/requires_human/actions) para que Flowify lo consuma tal cual.




