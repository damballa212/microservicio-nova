"""
Modelos Pydantic para payloads de entrada (webhooks) hacia el microservicio.

Estos modelos representan un esquema canónico de evento que puede ser producido
por distintos orígenes (CRM, canal, adaptadores).
"""

from pydantic import BaseModel, ConfigDict, Field


class WebhookAttachment(BaseModel):
    file_type: str = Field(default="", description="Tipo de archivo")
    data_url: str = Field(default="", description="URL del archivo")
    thumb_url: str | None = Field(default=None, description="URL de miniatura")

    model_config = ConfigDict(extra="allow")


class WebhookCustomAttributes(BaseModel):
    estado: str = Field(default="ON", description="Estado del bot")

    model_config = ConfigDict(extra="allow")


class WebhookSender(BaseModel):
    phone_number: str | None = Field(default=None, description="Número de teléfono")
    name: str = Field(default="", description="Nombre")
    identifier: str | None = Field(default=None, description="Identificador")
    custom_attributes: WebhookCustomAttributes = Field(
        default_factory=WebhookCustomAttributes,
        description="Atributos personalizados",
    )

    model_config = ConfigDict(extra="allow")


class WebhookMessage(BaseModel):
    content: str | None = Field(default="", description="Contenido del mensaje")
    account_id: int = Field(description="ID de la cuenta")
    conversation_id: int = Field(description="ID de la conversación")
    sender: WebhookSender = Field(description="Información del remitente")
    source_id: str | None = Field(default="", description="ID único del mensaje")
    content_type: str = Field(default="text", description="Tipo de contenido")
    attachments: list[WebhookAttachment] = Field(
        default_factory=list,
        description="Lista de adjuntos",
    )
    created_at: str | None = Field(default=None, description="Timestamp de creación")
    sender_type: str = Field(default="Contact", description="Tipo de remitente")

    model_config = ConfigDict(extra="allow")


class WebhookContactInbox(BaseModel):
    contact_id: int = Field(description="ID del contacto")

    model_config = ConfigDict(extra="allow")


class WebhookConversation(BaseModel):
    messages: list[WebhookMessage] = Field(default_factory=list, description="Lista de mensajes")
    contact_inbox: WebhookContactInbox | None = Field(
        default=None, description="Inbox del contacto"
    )
    timestamp: int | None = Field(default=None, description="Timestamp Unix")

    model_config = ConfigDict(extra="allow")


class WebhookBody(BaseModel):
    event: str = Field(description="Tipo de evento")
    conversation: WebhookConversation = Field(description="Datos de la conversación")

    model_config = ConfigDict(extra="allow")


class InboundWebhookPayload(BaseModel):
    body: WebhookBody = Field(description="Cuerpo del webhook")

    model_config = ConfigDict(extra="allow")

    @property
    def event(self) -> str:
        return self.body.event

    @property
    def first_message(self) -> WebhookMessage | None:
        messages = self.body.conversation.messages
        return messages[0] if messages else None

    @property
    def is_message_created(self) -> bool:
        return self.event == "message_created"

    @property
    def is_from_contact(self) -> bool:
        msg = self.first_message
        return msg.sender_type == "Contact" if msg else False
