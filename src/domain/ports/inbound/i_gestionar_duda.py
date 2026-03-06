from abc import ABC, abstractmethod

class IGestionarDuda(ABC):

    @abstractmethod
    async def ejecutar(self, clase_id: str, pregunta: str, origen: str) -> object:
        """origen: 'microfono' | 'chat'"""
        pass