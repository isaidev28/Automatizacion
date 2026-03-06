from abc import ABC, abstractmethod

class ITTSService(ABC):
    @abstractmethod
    async def sintetizar(self, text: str) -> bytes:
        """Convierte el texto a audio(bytes MP3/WAV)"""
        pass

    @abstractmethod
    async def sintetizar_stream(self, texto: str):
        """Stream de audio para bajar la latencia"""
        pass