"""
Tenant Template Prompt.
Define la data específica del cliente que llena los huecos de conocimiento.
"""

TENANT_TEMPLATE = """
# TENANT CONFIGURATION: {empresa_nombre}

## IDENTITY & TONE
- **Giro**: {empresa_giro}
- **Tono de Voz**: {empresa_tono}

## OPERATIONAL DATA (Facts)
- **Ubicación**: {empresa_ubicacion}
- **Horarios**: {empresa_horarios}
- **Reglas de Reserva**: {empresa_reglas_reserva} (Ej: "Solo por link", "Mínimo 2 personas")
- **Delivery**: {empresa_delivery_info} (Ej: "Radio 5km", "Costo $3", "PedidosYa")
- **Pagos Aceptados**: {empresa_pagos} (Ej: "Efectivo, Zelle, Pago Móvil")

## MENU / OFFER HIGHLIGHTS
{empresa_oferta}

## SPECIFIC RESTRICTIONS
{empresa_reglas}
"""

def build_tenant_prompt(data: dict) -> str:
    """
    Construye el prompt del tenant con data segura.
    Usa "NO CONFIGURADO" cuando falta un dato para que el LLM
    sepa que NO debe inventar — debe usar rag_search o decirlo.
    """
    _nc = "NO CONFIGURADO — no inventes este dato, usa rag_search o informa que no está disponible."
    return TENANT_TEMPLATE.format(
        empresa_nombre=data.get("nombre") or "Empresa (nombre no configurado)",
        empresa_giro=data.get("giro") or _nc,
        empresa_tono=data.get("tono") or "Profesional y servicial",
        empresa_ubicacion=data.get("ubicacion") or _nc,
        empresa_horarios=data.get("horarios") or _nc,
        empresa_reglas_reserva=data.get("reglas_reserva") or _nc,
        empresa_delivery_info=data.get("delivery_info") or _nc,
        empresa_pagos=data.get("metodos_pago") or _nc,
        empresa_oferta=data.get("oferta") or _nc,
        empresa_reglas=data.get("reglas") or "Sin restricciones adicionales configuradas.",
    )

