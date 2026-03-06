from dataclasses import dataclass

@dataclass(frozen=True)
class UrlPdf:
    valor: str

    def __post_init__(self):
        if not self.valor.startswith("https//"):
            raise ValueError("La url del PDF tiene que ser https")
        if not (self.valor.endswith(".pdf") or "s3.amazon.com" in self.valor):
            raise ValueError("La URL no parece ser de un PDF de s3 valido")
        
    def __str__(self):
        return self.valor