from src.domain.ports.outbound.i_llm_service import ILLMService
from src.domain.ports.outbound.i_tts_service import ITTSService
from src.domain.ports.outbound.i_cache_service import ICacheService
from src.domain.ports.inbound.i_gestionar_duda import IGestionarDuda
from src.domain.exceptions.clase_exception import FueraDeTemaException
from src.application.dtos.gestionar_duda_dto import GestionarDudaDTO, RespuestaDudaDTO


RESPUESTA_FUERA_DE_TEMA = (
    "Esa pregunta está fuera del tema de esta clase. "
    "Enfoquémonos en el contenido del material que estamos revisando. "
    "¿Tienes alguna duda sobre lo que hemos visto hasta ahora?"
)


class GestionarDudaUseCase(IGestionarDuda):

    def __init__(
        self,
        llm_service:   ILLMService,
        tts_service:   ITTSService,
        cache_service: ICacheService,
    ):
        self._llm   = llm_service
        self._tts   = tts_service
        self._cache = cache_service

    async def ejecutar(
        self,
        clase_id: str,
        pregunta: str,
        origen: str
    ) -> RespuestaDudaDTO:

        #  Recuperar sesión desde Redis
        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            raise ValueError(f"No se encontró la clase {clase_id}")

        historial  = sesion.get("historial", [])
        pdf_texto  = sesion.get("pdf_texto", "")

        #  Pausar IA en Redis — alumno tiene el turno
        await self._cache.actualizar_estado(clase_id, "en_pausa_ia")

        #  Validar si la pregunta está dentro del tema
        dentro_del_tema = await self._llm.validar_tema(pregunta, pdf_texto)

        if not dentro_del_tema:
            respuesta = RESPUESTA_FUERA_DE_TEMA
        else:
            #  Generar respuesta con contexto del historial
            respuesta = await self._llm.responder_duda(
                pregunta      = pregunta,
                contenido_pdf = pdf_texto,
                historial     = historial[-10:],    # Últimos 10 mensajes
            )

        #  Guardar en historial
        await self._cache.guardar_historial_chat(clase_id, {
            "role": "user", "content": pregunta, "origen": origen
        })
        await self._cache.guardar_historial_chat(clase_id, {
            "role": "assistant", "content": respuesta
        })

        #  Sintetizar respuesta a voz
        await self._tts.sintetizar(respuesta)

        #  Reanudar IA
        await self._cache.actualizar_estado(clase_id, "en_curso")

        return RespuestaDudaDTO(
            clase_id        = clase_id,
            respuesta       = respuesta,
            dentro_del_tema = dentro_del_tema,
            estado_clase    = "en_curso",
        )