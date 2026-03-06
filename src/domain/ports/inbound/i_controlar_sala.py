from abc import ABC, abstractmethod

class IControlarSala(ABC):

    @abstractmethod
    async def pausar_ia(self, clase_id: str) -> None:
        pass

    @abstractmethod
    async def reanudar_ia(self, clase_id: str) -> None:
        pass

    @abstractmethod
    async def finalizar_clase(self, clase_id: str) -> None:
        pass