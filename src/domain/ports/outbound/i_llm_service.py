from abc import ABC, abstractmethod
from typing import AsyncGenerator

class ILLMService(ABC):

    @abstractmethod
    async def generar_explication(
        self, 
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> str:
        """Genera el siguiente bloqueo de clase basado en el PDF"""
        pass

    @abstractmethod
    async def responder_duda(
        self,
        preguntar: str,
        contenido_pdf: str,
        historial: list[dict]
    ) -> str:
        """Responde duda del alumno, estrictamente basado en el pdf"""
        pass

    @abstractmethod
    async def validar_tema(
        self,
        preguntar: str,
        contenido_pdf: str
    ) -> bool:
        """True si la pregunta esta dentro del tema del PDF"""
        pass

    @abstractmethod
    async def stream_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str,
    ) -> AsyncGenerator[str, None]:
        """Stream para respuestas en tiempo real"""
        pass