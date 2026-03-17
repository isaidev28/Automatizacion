# src/application/use_cases/ClaseOrquestador.py

import asyncio
import logging

from src.infrastructure.outbound.browser.playwright_controller import PlaywrightController
from src.infrastructure.outbound.audio.audio_player import AudioPlayer
from src.infrastructure.outbound.audio.audio_capturer import AudioCapturer
from src.infrastructure.outbound.audio.voz_detector import VozDetector
from src.infrastructure.outbound.jitsi.jitsi_chat_monitor import JitsiChatMonitor
from src.infrastructure.outbound.jitsi.jitsi_participant_detector import JitsiParticipantDetector

logger = logging.getLogger(__name__)


class ClaseOrquestador:
    """
    Responsabilidad: coordinar el flujo completo de una clase virtual.
    No contiene lógica de audio, navegador ni Jitsi — solo orquesta.
    """

    def __init__(
        self,
        llm_service,
        tts_service,
        stt_service,
        cache_service,
    ):
        self._llm   = llm_service
        self._tts   = tts_service
        self._cache = cache_service

        # Infraestructura
        self._browser     = PlaywrightController()
        self._player      = AudioPlayer()
        self._capturer    = AudioCapturer()
        self._voz         = VozDetector(self._capturer, stt_service)
        self._chat        = JitsiChatMonitor()
        self._participantes = JitsiParticipantDetector()

        self._activo = False

    # ──────────────────────────────────────────────────────────────────────────
    # Entrada / salida
    # ──────────────────────────────────────────────────────────────────────────

    async def iniciar_clase(self, link_supervisor: str, clase_id: str):
        self._activo = True
        logger.info("=== CLASE INICIANDO ===")

        try:
            page = await self._browser.iniciar(link_supervisor)
            await self._browser.unirse_a_sala()
            await page.wait_for_timeout(5000)

            alumno_entro = await self._participantes.esperar_alumno(page)
            if not alumno_entro:
                logger.warning("Alumno no entró — finalizando")
                return

            await self._saludar(page, clase_id)

            await asyncio.sleep(3.0)
            await self._browser.iniciar_detector_voz()

            logger.info("Iniciando loop de clase...")
            await self._loop_clase(page, clase_id)

        except Exception as e:
            logger.exception(f"=== ERROR EN CLASE: {e} ===")
        finally:
            await self._browser.cerrar()
            self._activo = False

    async def detener(self):
        self._activo = False
        await self._browser.cerrar()
        logger.info("Clase detenida")

    # ──────────────────────────────────────────────────────────────────────────
    # Saludo inicial
    # ──────────────────────────────────────────────────────────────────────────

    async def _saludar(self, page, clase_id: str):
        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            return

        saludo = await self._llm.generar_saludo(
            nombre_alumno   = sesion.get("nombre_alumno", "estudiante"),
            nombre_profesor = sesion.get("nombre_profesor", "Profesor"),
            tema_pdf        = sesion.get("pdf_temas", ["el tema de hoy"])[0],
        )
        logger.info(f"Saludo: {saludo}")

        try:
            audio = await self._tts.sintetizar(saludo[:400])
            await self._player.reproducir(page, audio)
        except Exception as e:
            logger.warning(f"TTS saludo falló: {e}")

        sesion.setdefault("historial", []).append({"role": "assistant", "content": saludo})
        await self._cache.guardar_sesion(clase_id, sesion)

    # ──────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ──────────────────────────────────────────────────────────────────────────

    async def _loop_clase(self, page, clase_id: str):
        logger.info(f"=== LOOP CLASE INICIADO — {clase_id} ===")

        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            logger.error("Sesión no encontrada")
            return

        pdf_texto = sesion.get("pdf_texto", "")

        logger.info("Generando plan de clase...")
        secciones = await self._llm.generar_secciones(pdf_texto)
        logger.info(f"Plan generado: {len(secciones)} secciones")

        sesion["secciones"]      = secciones
        sesion["seccion_actual"] = 0
        await self._cache.guardar_sesion(clase_id, sesion)

        while self._activo and sesion["seccion_actual"] < len(secciones):
            idx     = sesion["seccion_actual"]
            seccion = secciones[idx]
            logger.info(f"Sección {idx+1}/{len(secciones)}: {seccion['titulo']}")

            interrupcion = await self._explicar_seccion(page, clase_id, idx, seccion, pdf_texto)

            if interrupcion:
                tipo, contenido = interrupcion
                es_pregunta = await self._llm.validar_tema(contenido, pdf_texto)
                if not es_pregunta:
                    logger.info("No era pregunta relevante — avanzando sección...")
                    sesion["seccion_actual"] = idx + 1
                    await self._cache.guardar_sesion(clase_id, sesion)
                    continue
                await self._responder_duda(page, clase_id, contenido, pdf_texto)
                logger.info(f"Retomando sección {idx+1}...")
                continue

            # Sin interrupción → siguiente sección
            sesion["seccion_actual"] = idx + 1
            await self._cache.guardar_sesion(clase_id, sesion)

        await self._cerrar_clase(page, clase_id, pdf_texto)

    # ──────────────────────────────────────────────────────────────────────────
    # Explicar sección con monitoreo en paralelo
    # ──────────────────────────────────────────────────────────────────────────

    async def _explicar_seccion(self, page, clase_id, idx, seccion, pdf_texto) -> tuple | None:
        texto      = f"Sección {idx+1}: {seccion['titulo']}. {seccion['explicacion']}"
        stop_event = asyncio.Event()
        resultado  = []

        async def explicar(t=texto, ev=stop_event):
            try:
                audio = await self._tts.sintetizar(t[:400])
                if not ev.is_set():
                    await self._player.reproducir(page, audio, stop_event=ev)
            except Exception as e:
                logger.warning(f"TTS falló: {e}")
            finally:
                ev.set()

        async def monitorear(ev=stop_event):
            await asyncio.sleep(2.0)
            while not ev.is_set():
                msg = await self._chat.leer_nuevo_mensaje(page)
                if msg:
                    logger.info(f"Chat detectado: {msg}")
                    resultado.append(("chat", msg))
                    ev.set()
                    return
                await asyncio.sleep(0.5)
                if await self._voz.mic_activo(page):
                    ev.set()  # ← se calla YA
                    transcripcion = await self._voz.capturar_y_transcribir(page)
                    if transcripcion:
                        resultado.append(("voz", transcripcion))
                    return

        # ← AQUÍ, fuera de las dos funciones internas
        await asyncio.gather(explicar(), monitorear())
        return resultado[0] if resultado else None

    # ──────────────────────────────────────────────────────────────────────────
    # Responder duda
    # ──────────────────────────────────────────────────────────────────────────

    async def _responder_duda(self, page, clase_id: str, pregunta: str, pdf_texto: str):
        sesion    = await self._cache.obtener_sesion(clase_id)
        respuesta = await self._llm.responder_duda(
            pregunta      = pregunta,
            contenido_pdf = pdf_texto,
            historial     = sesion.get("historial", []),
        )
        logger.info(f"IA responde: {respuesta[:80]}...")

        try:
            audio = await self._tts.sintetizar(respuesta[:400])
            await self._player.reproducir(page, audio)
        except Exception as e:
            logger.warning(f"TTS respuesta falló: {e}")

        sesion["historial"].append({"role": "user",      "content": pregunta})
        sesion["historial"].append({"role": "assistant", "content": respuesta})
        await self._cache.guardar_sesion(clase_id, sesion)

    # ──────────────────────────────────────────────────────────────────────────
    # Cierre de clase
    # ──────────────────────────────────────────────────────────────────────────

    async def _cerrar_clase(self, page, clase_id: str, pdf_texto: str):
        logger.info("Clase completada")
        try:
            audio_fin = await self._tts.sintetizar(
                "Hemos terminado el tema de hoy. ¿Tienes alguna pregunta final?"
            )
            await self._player.reproducir(page, audio_fin)
        except Exception:
            pass

        # Esperar preguntas finales 30s
        stop_event = asyncio.Event()
        resultado  = []
        await asyncio.gather(
            asyncio.sleep(30),
            self._voz.monitorear(page, stop_event, resultado),
        )

        if resultado:
            _, pregunta_final = resultado[0]
            await self._responder_duda(page, clase_id, pregunta_final, pdf_texto)

        logger.info(f"Bot detenido — clase {clase_id}")
