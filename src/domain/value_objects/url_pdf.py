from dataclasses import dataclass
from urllib.parse import unquote

@dataclass(frozen=True)
class UrlPdf:
    valor: str

    def __post_init__(self):
        if not self.valor.startswith("https://"):
            raise ValueError("La url del PDF tiene que ser https")
        
        # Decodificar URL para validar la extensión
        url_decoded = unquote(self.valor).lower()
        
        if not (url_decoded.endswith(".pdf") or "s3.amazonaws.com" in self.valor):
            raise ValueError("La URL no parece ser un PDF de S3 válido")

    def __str__(self):
        return self.valor