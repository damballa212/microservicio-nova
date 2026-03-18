import re
from typing import Any


def _split_path(path: str) -> list[str]:
    p = path.replace("[", ".").replace("]", "")
    return [s for s in p.split(".") if s != ""]


def _get_value(data: Any, path: str) -> Any:
    current = data
    for part in _split_path(path):
        if isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        elif isinstance(current, dict):
            if part not in current:
                return None
            current = current.get(part)
        else:
            return None
    return current


def _ensure_path(target: dict[str, Any], parts: list[str]) -> tuple[dict[str, Any], str]:
    current: Any = target
    for i, part in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        is_next_index = False
        try:
            int(nxt)
            is_next_index = True
        except ValueError:
            is_next_index = False

        if isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                raise KeyError("Invalid list index")
            while len(current) <= idx:
                current.append({} if not is_next_index else [])
            current = current[idx]
        else:
            if part not in current:
                current[part] = [] if is_next_index else {}
            current = current[part]
    last = parts[-1]
    if isinstance(current, list):
        try:
            idx = int(last)
        except ValueError:
            raise KeyError("Invalid list index")
        while len(current) <= idx:
            current.append(None)
        return target, last
    return current, last


def _set_value(target: dict[str, Any], path: str, value: Any) -> None:
    parts = _split_path(path)
    if not parts:
        return
    parent, key = _ensure_path(target, parts)
    if isinstance(parent, list):
        idx = int(key)
        parent[idx] = value
    else:
        parent[key] = value


class DynamicAdapter:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping or {}

    def transform(self, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for canonical_path, source_path in self.mapping.items():
            val = _get_value(payload, source_path)
            if val is not None:
                _set_value(result, canonical_path, val)
        return result

    def validate(self, payload: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for canonical_path, source_path in self.mapping.items():
            if _get_value(payload, source_path) is None:
                missing.append(canonical_path)
        return missing

    @staticmethod
    def apply_defaults(result: dict[str, Any]) -> dict[str, Any]:
        body = result.get("body") or {}
        if "event" not in body:
            _set_value(result, "body.event", "message_created")
        msg_path = "body.conversation.messages[0]"
        if _get_value(result, f"{msg_path}.sender_type") is None:
            _set_value(result, f"{msg_path}.sender_type", "Contact")
        if _get_value(result, f"{msg_path}.content_type") is None:
            _set_value(result, f"{msg_path}.content_type", "text")
        if _get_value(result, f"{msg_path}.attachments") is None:
            _set_value(result, f"{msg_path}.attachments", [])
        if _get_value(result, f"{msg_path}.account_id") is None:
            _set_value(result, f"{msg_path}.account_id", 0)
        if _get_value(result, f"{msg_path}.conversation_id") is None:
            _set_value(result, f"{msg_path}.conversation_id", 0)
        if _get_value(result, "body.conversation.contact_inbox.contact_id") is None:
            _set_value(result, "body.conversation.contact_inbox.contact_id", 0)
        ident = _get_value(result, f"{msg_path}.sender.identifier")
        if ident is None or (isinstance(ident, str) and ident.strip() == ""):
            phone = _get_value(result, f"{msg_path}.sender.phone_number")
            if isinstance(phone, str) and phone.strip():
                sanitized = re.sub(r"[\s\-\(\)]", "", phone.strip())
                _set_value(result, f"{msg_path}.sender.identifier", f"whatsapp:{sanitized}")
        return result
