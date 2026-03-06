from abc import ABC, abstractmethod

class ICrearClase(ABC):

    @abstractmethod
    async def ejecutar(self, dto) -> object:
        pass