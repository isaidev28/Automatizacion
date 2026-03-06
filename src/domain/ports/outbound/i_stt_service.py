from abc import ABC, abstractmethod

class ISTTService(ABC):
    @abstractmethod
    async def transcribir(self, audio_bytes: bytes, idioma: str = "es") -> str:
        """Convierte el audio a text"""
        pass