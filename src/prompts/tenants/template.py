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
    Valores por defecto indican 'Información no disponible'.
    """
    return TENANT_TEMPLATE.format(
        empresa_nombre=data.get("nombre", "Empresa Sin Nombre"),
        empresa_giro=data.get("giro", "Servicios Varios"),
        empresa_tono=data.get("tono", "Profesional y servicial"),
        empresa_ubicacion=data.get("ubicacion", "Consultar dirección exacta"),
        empresa_horarios=data.get("horarios", "Consultar horarios de atención"),
        empresa_reglas_reserva=data.get("reglas_reserva", "Sujeto a disponibilidad"),
        empresa_delivery_info=data.get("delivery_info", "Consultar cobertura de entrega"),
        empresa_pagos=data.get("metodos_pago", "Consultar métodos de pago"),
        empresa_oferta=data.get("oferta", "Consultar catálogo disponible"),
        empresa_reglas=data.get("reglas", "Sin restricciones adicionales")
    )
