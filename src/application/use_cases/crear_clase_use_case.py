import uuid
import asyncio
import threading
import logging
from src.domain.entities.clase import Clase, EstadoClase
from src.domain.value_objects.email import Email
from src.domain.value_objects.sala_id import SalaId
from src.domain.value_objects.url_pdf import UrlPdf
from src.domain.ports.outbound.i_llm_service import ILLMService
from src.domain.ports.outbound.i_tts_service import ITTSService
from src.domain.ports.outbound.i_sala_service import ISalaService
from src.domain.ports.outbound.i_pdf_service import IPDFService
from src.domain.ports.outbound.i_cache_service import ICacheService
from src.domain.ports.outbound.i_stt_service import ISTTService
from src.domain.ports.inbound.i_crear_clase import ICrearClase
from src.application.dtos.crear_clase_dto import CrearClaseDTO, RespuestaClaseDTO
from src.application.use_cases.ClaseOrquestador import ClaseOrquestador

logger = logging.getLogger(__name__)


class CrearClaseUseCase(ICrearClase):

    def __init__(
        self,
        llm_service:   ILLMService,
        tts_service:   ITTSService,
        sala_service:  ISalaService,
        pdf_service:   IPDFService,
        cache_service: ICacheService,
        stt_service:   ISTTService,
    ):
        self._llm   = llm_service
        self._tts   = tts_service
        self._sala  = sala_service
        self._pdf   = pdf_service
        self._cache = cache_service
        self._bot   = ClaseOrquestador(
            stt_service   = stt_service,
            tts_service   = tts_service,
            llm_service   = llm_service,
            cache_service = cache_service,
        )

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

        # 3. Crear sala Jitsi
        links = await self._sala.crear_sala(
            sala_id         = str(clase.sala_id),
            nombre_profesor = clase.nombre_profesor,
            nombre_alumno   = clase.nombre_alumno,
            correo_alumno   = str(clase.correo_alumno),
        )
        clase.link_alumno     = links.alumno
        clase.link_supervisor = links.supervisor

        # 4. Iniciar entidad y crear sesión IA
        clase.iniciar()

        # 5. Persistir sesión completa en Redis
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
            "historial":       [],
            "pdf_texto":       clase.pdf_contenido.texto_completo,
            "pdf_temas":       clase.pdf_contenido.temas,
        })

        await self._cache.actualizar_estado(clase.id, EstadoClase.EN_CURSO.value)

        # 6. Lanzar bot en hilo separado con su propio event loop
        link_supervisor    = clase.link_supervisor
        clase_id           = clase.id
        bot                = self._bot

        def _lanzar_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    bot.iniciar_clase(
                        link_supervisor    = link_supervisor,
                        clase_id           = clase_id,
                    )
                )
            except Exception as e:
                logger.exception(f"Error en hilo del bot: {e}")
            finally:
                loop.close()

        hilo = threading.Thread(
            target = _lanzar_bot,
            daemon = True,
            name   = f"bot-{clase_id}"
        )
        hilo.start()
        logger.info(f"Bot lanzado en hilo: bot-{clase_id}")

        return RespuestaClaseDTO(
            clase_id        = clase.id,
            link_alumno     = clase.link_alumno,
            link_supervisor = clase.link_supervisor,
            estado          = clase.estado.value,
        )