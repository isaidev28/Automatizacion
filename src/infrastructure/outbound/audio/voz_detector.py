# src/infrastructure/outbound/audio/VozDetector.py

import asyncio
import logging
import base64

logger = logging.getLogger(__name__)


class VozDetector:
    """
    Responsabilidad: detectar actividad de voz del alumno y capturar
    el audio en cuanto se detecta, sin esperar confirmación externa.
    """

    def __init__(self, capturer, stt_service, segundos_grabacion: float = 6.0):
        self._capturer          = capturer   # AudioCapturer
        self._stt               = stt_service
        self._segundos          = segundos_grabacion

    # ──────────────────────────────────────────────────────────────────────────
    # Detección puntual
    # ──────────────────────────────────────────────────────────────────────────

    async def mic_activo(self, page) -> bool:
        """Retorna True si el AnalyserNode detecta voz remota en este instante."""
        try:
            resultado = await page.evaluate("""
                () => ({
                    activo:           window._remoteActivo === true,
                    detectorIniciado: window._detectorIniciado === true,
                    tieneRemoteDest:  !!window._remoteDest,
                })
            """)
            logger.debug(f"Mic check: {resultado}")
            return bool(resultado.get("activo"))
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Captura + transcripción
    # ──────────────────────────────────────────────────────────────────────────

    async def capturar_y_transcribir(self, page) -> str | None:
        """
        Inicia grabación inmediatamente, espera `segundos_grabacion`
        y devuelve la transcripción o None si no hubo audio/voz relevante.
        """
        logger.info(" Micrófono detectado — grabando desde ahora...")

        # Iniciar MediaRecorder sin esperar (fire & forget en JS)
        await page.evaluate(f"""
            async () => {{
                if (!window._remoteDest) return;
                window._remoteChunks = [];
                const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus' : 'audio/webm';
                const recorder = new MediaRecorder(window._remoteDest.stream, {{ mimeType }});
                window._remoteRecorder = recorder;
                recorder.ondataavailable = e => {{
                    if (e.data.size > 0) window._remoteChunks.push(e.data);
                }};
                recorder.start(100);
                setTimeout(() => recorder.stop(), {int(self._segundos * 1000)});
                console.log('[VozDetector] Grabando...');
            }}
        """)

        await asyncio.sleep(self._segundos + 0.8)

        # Recuperar audio grabado
        b64 = await page.evaluate("""
            async () => {
                return new Promise(resolve => {
                    if (!window._remoteChunks || window._remoteChunks.length === 0) {
                        resolve(null); return;
                    }
                    const blob = new Blob(window._remoteChunks, { type: 'audio/webm' });
                    console.log('[VozDetector] Blob:', blob.size, 'bytes');
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(blob);
                });
            }
        """)

        if not b64:
            logger.debug("VozDetector: sin chunks grabados")
            return None

        audio = base64.b64decode(b64)
        if len(audio) < 500:
            logger.debug(f"VozDetector: audio demasiado corto ({len(audio)} bytes)")
            return None

        transcripcion = await self._stt.transcribir(audio)
        if not transcripcion or len(transcripcion.strip()) < 3:
            logger.debug("VozDetector: transcripción vacía o muy corta")
            return None

        logger.info(f" Alumno dijo: {transcripcion}")
        return transcripcion.strip()

    # ──────────────────────────────────────────────────────────────────────────
    # Monitor continuo (corre en paralelo con la explicación)
    # ──────────────────────────────────────────────────────────────────────────

    async def monitorear(
        self,
        page,
        stop_event: asyncio.Event,
        resultado: list,
        espera_inicial: float = 2.0,
    ):
        """
        Polling de actividad de voz. En cuanto detecta mic activo,
        captura, transcribe y setea stop_event.
        Diseñado para correr con asyncio.gather junto a explicar().
        """
        await asyncio.sleep(espera_inicial)

        while not stop_event.is_set():
            if await self.mic_activo(page):
                transcripcion = await self.capturar_y_transcribir(page)
                if transcripcion:
                    resultado.append(("voz", transcripcion))
                    stop_event.set()
                    return
            await asyncio.sleep(0.5)