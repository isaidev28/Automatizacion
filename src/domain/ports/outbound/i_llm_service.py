from abc import ABC, abstractmethod
from typing import AsyncGenerator

class ILLMService(ABC):

    @abstractmethod
    async def generar_explicacion(          # ← explication → explicacion
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> str:
        """Genera el siguiente bloque de clase basado en el PDF"""
        pass

    @abstractmethod
    async def responder_duda(
        self,
        pregunta: str,                      # ← preguntar → pregunta
        contenido_pdf: str,
        historial: list[dict]
    ) -> str:
        """Responde duda del alumno, estrictamente basado en el PDF"""
        pass

    @abstractmethod
    async def validar_tema(
        self,
        pregunta: str,                      # ← preguntar → pregunta
        contenido_pdf: str
    ) -> bool:
        """True si la pregunta está dentro del tema del PDF"""
        pass

    @abstractmethod
    async def stream_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> AsyncGenerator[str, None]:
        """Stream para respuestas en tiempo real"""
        pass

    @abstractmethod 
    async def generar_saludo(
        self,
        nombre_alumno: str,
        nombre_profesor: str,
        tema_pdf:str
    ) -> str: 
        """Generar saludo al inicio de la plataforma """
        pass