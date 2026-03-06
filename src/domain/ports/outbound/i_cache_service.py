from abc import ABC, abstractmethod
from typing import Optional

class ICacheService(ABC):
    @abstractmethod
    async def guardar_sesion(self, clase_id: str, datos: dict, ttl: int = 7200) -> None:
        pass
    @abstractmethod
    async def obtener_sesion(self, clase_id: str) -> Optional[dict]:
        pass
    @abstractmethod
    async def actualizar_estado(self, clase_id:str, estado:str) -> None:
        pass
    @abstractmethod
    async def obtener_historial_chat(self, clase_id:str) -> list[dict]:
        pass
    @abstractmethod
    async def publicar_evento(self, canal: str, evento: dict) -> None:
        """Pub/Sub redis para comunicacion entre servicios"""
        pass

    @abstractmethod
    async def suscribir_canal(self, canal: str):
        pass
    @abstractmethod
    async def eliminar_sesion(self, clase_id: str) -> None:
        pass