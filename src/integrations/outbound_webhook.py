import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutboundWebhookClient:
    def __init__(
        self,
        base_url: str | None = None,
        path: str | None = None,
        secret: str | None = None,
    ):
        self.base_url = (base_url or settings.outbound_webhook_base_url or "").rstrip("/")
        self.path = path or settings.outbound_webhook_path
        self.secret = secret if secret is not None else (settings.outbound_webhook_secret or "")

    def _endpoint(self) -> str:
        base = self.base_url
        p = self.path.strip() if isinstance(self.path, str) else ""
        if not p:
            return base
        if not p.startswith("/"):
            p = "/" + p
        return f"{base}{p}" if base else p

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _signature(self, body_bytes: bytes) -> str | None:
        if not self.secret:
            return None
        return hmac.new(self.secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    async def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = self._serialize(payload)
        sig = self._signature(body)
        headers = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "1",
        }
        if sig:
            headers["X-Webhook-Signature"] = sig
        try:
            headers["X-Webhook-Timestamp"] = str(int(time.time()))
        except Exception:
            pass

        url = self._endpoint()
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body, headers=headers, timeout=10.0)
            status = resp.status_code
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text[:200]}
            logger.info("Outbound webhook enviado", url=url, status_code=status)
            return {"status_code": status, "data": data}


outbound_webhook_client = OutboundWebhookClient()
