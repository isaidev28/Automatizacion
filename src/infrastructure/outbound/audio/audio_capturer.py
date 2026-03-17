# src/infrastructure/outbound/audio/AudioCapturer.py

import asyncio
import logging
import base64

logger = logging.getLogger(__name__)


class AudioCapturer:
    """Responsabilidad: capturar audio remoto del alumno desde Jitsi vía remoteDest."""

    async def capturar(self, page, segundos: float = 6.0) -> bytes:
        """
        Inicia MediaRecorder sobre _remoteDest, espera `segundos`
        y devuelve los bytes webm capturados.
        """
        await page.evaluate(f"""
            async () => {{
                if (!window._remoteDest) {{
                    console.warn('[AudioCapturer] remoteDest no disponible');
                    return;
                }}
                window._remoteChunks = [];
                const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus' : 'audio/webm';
                const recorder = new MediaRecorder(window._remoteDest.stream, {{ mimeType }});
                window._remoteRecorder = recorder;
                recorder.ondataavailable = e => {{
                    if (e.data.size > 0) window._remoteChunks.push(e.data);
                }};
                recorder.start(100);
                setTimeout(() => recorder.stop(), {int(segundos * 1000)});
                console.log('[AudioCapturer] Grabando audio remoto...');
            }}
        """)

        await asyncio.sleep(segundos + 0.8)

        b64 = await page.evaluate("""
            async () => {
                return new Promise(resolve => {
                    if (!window._remoteChunks || window._remoteChunks.length === 0) {
                        resolve(null); return;
                    }
                    const blob = new Blob(window._remoteChunks, { type: 'audio/webm' });
                    logger.log('[AudioCapturer] Blob grabado:', blob.size, 'bytes');
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(blob);
                });
            }
        """)

        if not b64:
            logger.warning("Sin audio remoto capturado")
            return b""

        audio = base64.b64decode(b64)
        logger.info(f"Audio remoto capturado: {len(audio)} bytes")
        return audio