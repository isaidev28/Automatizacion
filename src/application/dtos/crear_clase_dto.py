from dataclasses import dataclass
from typing import Optional

@dataclass 
class CrearClaseDTO:
    nombre_profesor: str
    nombre_alumno: str
    correo_profesor: str
    correo_alumno: str
    url_pdf: str

    def __post_init__(self):
        campos = [
            ("nombre_profesor", self.nombre_profesor),
            ("nombre_alumno", self.nombre_alumno),
            ("correo_profesor", self.correo_profesor),
            ("correo_alumno", self.correo_alumno),
            ("url_pdf", self.url_pdf),
        ]
        for nombre, valor in campos:
            if not valor or not str(valor).strip():
                raise ValueError(f"El campo '{nombre}' es obligatorio")
            
@dataclass
class RespuestaClaseDTO:
    clase_id: str
    link_alumno: str
    link_supervisor: str
    estado: str
    mensaje: str = "clase iniciada correctamente"