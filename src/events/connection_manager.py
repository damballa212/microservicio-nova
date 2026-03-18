"""
Connection Manager para WebSockets.

Maneja el ciclo de vida de conexiones WebSocket del dashboard.
Separado de EventEmitter para cumplir Single Responsibility Principle.
"""

from fastapi import WebSocket

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Gestiona conexiones WebSocket activas.
    
    Responsabilidades:
    - Mantener registro de conexiones activas
    - Enviar mensajes a todas las conexiones
    - Limpiar conexiones muertas
    """
    
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
    
    @property
    def connection_count(self) -> int:
        """Número de conexiones activas."""
        return len(self.active_connections)
    
    def add(self, websocket: WebSocket) -> None:
        """Agrega una conexión WebSocket."""
        self.active_connections.add(websocket)
        logger.info(f"WebSocket conectado. Total: {self.connection_count}")
    
    def remove(self, websocket: WebSocket) -> None:
        """Remueve una conexión WebSocket."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket desconectado. Total: {self.connection_count}")
    
    async def send_to_one(self, websocket: WebSocket, message: dict) -> bool:
        """
        Envía mensaje a una conexión específica.
        
        Returns:
            True si se envió exitosamente, False si falló
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False
    
    async def broadcast(self, message: dict) -> int:
        """
        Envía mensaje a todas las conexiones activas.
        
        Returns:
            Número de conexiones que recibieron el mensaje
        """
        if not self.active_connections:
            return 0
        
        sent_count = 0
        failed: set[WebSocket] = set()
        
        # Iterar sobre copia para evitar modificar durante iteración
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
                sent_count += 1
            except Exception:
                failed.add(ws)
        
        # Limpiar conexiones muertas
        if failed:
            self.active_connections -= failed
            logger.debug(f"Limpiadas {len(failed)} conexiones muertas")
        
        return sent_count
    
    async def broadcast_to_all_except(self, message: dict, exclude: WebSocket) -> int:
        """
        Envía mensaje a todas las conexiones excepto una.
        
        Útil para evitar eco cuando un cliente envía un mensaje.
        """
        sent_count = 0
        failed: set[WebSocket] = set()
        
        for ws in list(self.active_connections):
            if ws == exclude:
                continue
            try:
                await ws.send_json(message)
                sent_count += 1
            except Exception:
                failed.add(ws)
        
        if failed:
            self.active_connections -= failed
        
        return sent_count
    
    def is_connected(self, websocket: WebSocket) -> bool:
        """Verifica si un WebSocket está en la lista de activos."""
        return websocket in self.active_connections
    
    async def close_all(self) -> None:
        """Cierra todas las conexiones activas."""
        for ws in list(self.active_connections):
            try:
                await ws.close()
            except Exception:
                pass
        self.active_connections.clear()
        logger.info("Todas las conexiones WebSocket cerradas")


# Instancia global
connection_manager = ConnectionManager()
