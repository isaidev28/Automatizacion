import uuid
from src.domain.entities.clase import Clase, EstadoClase
from src.domain.value_objects.email import Email
from src.domain.value_objects.sala_id import SalaId
from src.domain.value_objects.url_pdf import UrlPdf
from src.domain.ports.outbound.i_llm_service import ILLMService
from src.domain.ports.outbound.i_tts_service import ITTSService
from src.domain.ports.outbound.i_sala_service import ISalaService
from src.domain.ports.outbound.i_pdf_service import IPDFService
from src.domain.ports.outbound.i_cache_service import ICacheService
from src.domain.ports.inbound.i_crear_clase import ICrearClase
from src.application.dtos.crear_clase_dto import CrearClaseDTO, RespuestaClaseDTO


class CrearClaseUseCase(ICrearClase):

    def __init__(
        self,
        llm_service:   ILLMService,
        tts_service:   ITTSService,
        sala_service:  ISalaService,
        pdf_service:   IPDFService,
        cache_service: ICacheService,
    ):
        self._llm   = llm_service
        self._tts   = tts_service
        self._sala  = sala_service
        self._pdf   = pdf_service
        self._cache = cache_service

    async def ejecutar(self, dto: CrearClaseDTO) -> RespuestaClaseDTO:

        # 1. Construir entidad con value objects validados
        clase = Clase(
            id               = str(uuid.uuid4()),
            nombre_profesor  = dto.nombre_profesor,
            nombre_alumno    = dto.nombre_alumno,
            correo_profesor  = Email(dto.correo_profesor),
            correo_alumno    = Email(dto.correo_alumno),
            url_pdf          = UrlPdf(dto.url_pdf),
            sala_id          = SalaId(f"clase_{uuid.uuid4().hex[:10]}"),
        )

        # 2. Extraer contenido del PDF desde S3
        clase.pdf_contenido = await self._pdf.extraer_contenido(str(clase.url_pdf))

        # 3. Crear sala Jitsi — alumno sin control de sala
        links = await self._sala.crear_sala(
            sala_id          = str(clase.sala_id),
            nombre_profesor  = clase.nombre_profesor,
            nombre_alumno    = clase.nombre_alumno,
            correo_alumno    = str(clase.correo_alumno),
        )
        clase.link_alumno     = links.alumno
        clase.link_supervisor = links.supervisor

        # 4. Iniciar entidad y crear sesión IA
        clase.iniciar()

        # 5. Generar introducción con el LLM
        introduccion = await self._llm.generar_explicacion(
            contenido_pdf   = clase.pdf_contenido.texto_completo,
            progreso        = 0.0,
            nombre_alumno   = clase.nombre_alumno,
            nombre_profesor = clase.nombre_profesor,
        )
        clase.sesion_ia.agregar_mensaje("assistant", introduccion)

        # 6. Convertir introducción a voz
        await self._tts.sintetizar(introduccion)

        # 7. Persistir sesión completa en Redis
        await self._cache.guardar_sesion(clase.id, {
            "clase_id":        clase.id,
            "nombre_profesor": clase.nombre_profesor,
            "nombre_alumno":   clase.nombre_alumno,
            "correo_alumno":   str(clase.correo_alumno),
            "correo_profesor": str(clase.correo_profesor),
            "sala_id":         str(clase.sala_id),
            "link_alumno":     clase.link_alumno,
            "link_supervisor": clase.link_supervisor,
            "estado":          clase.estado.value,
            "progreso":        clase.sesion_ia.progreso,
            "historial":       clase.sesion_ia.historial_chat,
            "pdf_texto":       clase.pdf_contenido.texto_completo,
            "pdf_temas":       clase.pdf_contenido.temas,
        })

        await self._cache.actualizar_estado(clase.id, EstadoClase.EN_CURSO.value)

        return RespuestaClaseDTO(
            clase_id        = clase.id,
            link_alumno     = clase.link_alumno,
            link_supervisor = clase.link_supervisor,
            estado          = clase.estado.value,
        )