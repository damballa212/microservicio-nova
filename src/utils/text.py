"""
Utilidades de texto.

Funciones comunes para manipulación de strings
utilizadas a lo largo del código.
"""


def escape_curly(text: str) -> str:
    """
    Escapa llaves para uso en LangChain prompts.
    
    LangChain interpreta {variable} como placeholder.
    Esta función las convierte a {{ y }} para que se
    rendericen literalmente.
    
    Args:
        text: Texto a escapar
        
    Returns:
        Texto con llaves escapadas
    """
    return text.replace("{", "{{").replace("}", "}}")


def unescape_curly(text: str) -> str:
    """
    Revierte el escape de llaves.
    
    Args:
        text: Texto con llaves escapadas
        
    Returns:
        Texto con llaves normales
    """
    return text.replace("{{", "{").replace("}}", "}")


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Trunca texto a una longitud máxima.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        suffix: Sufijo a agregar si se trunca
        
    Returns:
        Texto truncado
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_for_logging(text: str, max_length: int = 200) -> str:
    """
    Limpia texto para logging seguro.
    
    Trunca y remueve caracteres problemáticos.
    """
    if not text:
        return ""
    # Remover newlines para logging en una línea
    clean = text.replace("\n", " ").replace("\r", "")
    return truncate(clean, max_length)
