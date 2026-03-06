from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LinksSala:
    alumno: str
    supervisor: str
    sala_id: str

class ISalaService(ABC):
    @abstractmethod
    async def crear_sala(
        self, 
        sala_id: str,
        nombre_profesor: str,
        nombre_alumno: str,
        correo_alumno: str
    ) -> LinksSala:
        """Crea sala en Jitsi y retorna los link con permisos correctos"""
        pass

    @abstractmethod
    async def cerrar_sala(self, sala_id: str) -> bool:
        pass

    @abstractmethod 
    def generar_token_alumno(self, sala_id: str, nombre: str, correo: str) -> str:
        """JWT sin permisos de moderacion"""
        pass

    @abstractmethod
    def generar_token_moderador(self, sala_id: str, nombre: str) -> str:
        """JWT con permisos completos"""
        pass