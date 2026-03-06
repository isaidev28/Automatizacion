from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime

from src.domain.entities.participante import Participante, RolParticipante
from src.domain.entities.pdf_contenido import PdfContenido
from src.domain.entities.sesion_ia import SesionIA
from src.domain.value_objects.email import Email
from src.domain.value_objects.sala_id import SalaId
from src.domain.value_objects.url_pdf import UrlPdf
from src.domain.exceptions.clase_exception import (
    ClaseYaFinalizadaException,
    AlumnoNoAutorizadoException)

class EstadoClase(Enum):
    INICIANDO   =   "iniciando"
    EN_CURSO    =   "en_curso"
    EN_PAUSA_IA =   "en_pausa_ia" #intervalo de escucha de IA al alumno
    RESPONDIENTO    =   "respondiendo"
    FINALIZADA  =   "finalizada"

@dataclass
class Clase:
    id:str
    nombre_profesor: str
    nombre_alumno: str
    correo_profesor: str
    correo_alumno: str
    url_pdf: UrlPdf
    sala_id: SalaId
    estado: EstadoClase = EstadoClase.INICIANDO
    pdf_contenido: Optional[PdfContenido] = None
    sesion_ia: Optional[SesionIA] = None
    creada_en: datetime = field(default_factory=datetime.utcnow)
    finalizada_en: Optional[datetime] = None

    #Links generados por Jitsi
    link_alumno: Optional[str] = None
    link_supervisor: Optional[str] = None


    def iniciar(self):
        if self.estado != EstadoClase.INICIANDO:
            raise ClaseYaFinalizadaException("La clase ya fue iniciada")
        self.sesion_ia = SesionIA(clase_id=self.id)
        self.estado = EstadoClase.EN_CURSO

    def pausar_ia(self):
        """Alumno intervino - IA debe callarse y escuchar"""
        if self.estado == EstadoClase.FINALIZADA:
            raise ClaseYaFinalizadaException("No se puede pausar una clase finalizada")
        self.estado = EstadoClase.EN_PAUSA_IA
        if self.sesion_ia:
            self.sesion_ia.esperando_respuesta_alumno = True

    def reanudar_ia(self):
        """Alumno termino - IA retoma la clase"""
        self.estado = EstadoClase.EN_CURSO
        if self.sesion_ia:
            self.sesion_ia.esperando_respuesta_alumno = False

    def finalizar(self):
        self.estado = EstadoClase.FINALIZADA
        self.finalizada_en = datetime.utcnow()

    def alumno_puede_controlar_sala(self) -> bool:
        """Regla de negocio: el alumno NUNCA puede controlar la sala"""
        return False
    
    def validar_permiso_moderacion(self,rol: RolParticipante):
        if rol == RolParticipante.ALUMNO:
            raise AlumnoNoAutorizadoException(
                "El alumno no tiene permisos de moderacion sobre la sala"
            )
    @property
    def esta_activa(self) -> bool:
        return self.estado not in (EstadoClase.FINALIZADA, EstadoClase.INICIANDO)

