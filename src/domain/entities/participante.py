from dataclasses import dataclass
from enum import Enum
from src.domain.value_objects.email import Email

class RolParticipante(Enum):
    PROFESOR_IA = "profesor_ia"
    ALUMNO = "alumno"
    SUPERVISOR = "supervisor" #puede ser el profesor o dueño de la app

@dataclass
class Participante:
    nomnbre: str
    email: Email
    rol: RolParticipante
    microfono_activo: bool = False
    camara_activa: bool = False
    es_moderador: bool = False

    def __post_init__(self):
        if self.rol == RolParticipante.ALUMNO:
            self.es_moderador = False # alumno nunca sera moderador
        elif self.rol in (RolParticipante.PROFESOR_IA, RolParticipante.SUPERVISOR):
            self.es_moderador = True


    def activar_microfono(self):
        self.microfono_activo = True

    def desactivar_microfono(self):
        self.microfono_activo = False