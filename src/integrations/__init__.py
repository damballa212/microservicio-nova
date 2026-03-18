"""Módulo de integraciones externas."""

from src.integrations.openai_client import OpenAIClient, openai_client
from src.integrations.outbound_webhook import OutboundWebhookClient, outbound_webhook_client

__all__ = [
    "OutboundWebhookClient",
    "outbound_webhook_client",
    "OpenAIClient",
    "openai_client",
]
