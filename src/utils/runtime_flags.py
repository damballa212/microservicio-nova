sandbox_mode = False


def set_sandbox_mode(enabled: bool) -> None:
    global sandbox_mode
    sandbox_mode = bool(enabled)


def is_sandbox_mode() -> bool:
    return sandbox_mode
