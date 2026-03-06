from dataclasses import dataclass, field
from typing import Optional

@dataclass 
class PdfContenido:
    url_origen: str
    texto_completo: str
    temas: list[str] = field(default_factory=list)
    total_paginas: int = 0
    resumen: Optional[str] = None


    def __post_init__(self):
        if not self.texto_completo or len(self.texto_completo.strip()) < 50:
            raise ValueError("EL contenido del PDF esta vacio o es demaciado corto")
        
    @property
    def texto_truncado(self, limite: int = 8000) -> str:
        """Devuelve el texto truncado para no exender el contexto del LLM"""
        return self.texto_completo[:limite]
    
    def contiene_tema(self, pregunta: str) -> bool:
        """Verificacion rapida en dominio - la validacion profunda la hace el LLM"""
        pregunta_lower = pregunta_lower()
        return any(tema.lower() in pregunta_lower for tema in self.temas)