from abc import ABC, abstractmethod
from src.domain.entities.pdf_contenido import PdfContenido

class IPDFService(ABC):

    @abstractmethod
    async def extraer_contenido(self, url_s3: str) -> PdfContenido:
        """Descarga PDF de S3 y extrae texto estructurado"""
        pass