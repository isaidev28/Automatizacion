from dataclasses import dataclass
from enum import Enum
from typing import Optional

class OrigenIntervencion(Enum):
    MICROFONO = "microfono"
    CHAT    = "chat"

@dataclass
class GestionarDudaDTO:
    clase_id: str
    pregunta: str
    origen: OrigenIntervencion

    def __post_init__(self):
        if not self.clase_id:
            raise ValueError("Clase_id es obligatorio")
        if not self.pregunta or not self.pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía")
        
@dataclass
class RespuestaDudaDTO:
    clase_id: str
    respuesta: str
    audio_url: Optional[str] = None #url temporal del audio generado
    dentro_del_tema: bool = True
    estado_clase: str = "en_curso"

