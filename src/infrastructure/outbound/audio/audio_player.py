# src/infrastructure/outbound/audio/AudioPlayer.py

import asyncio
import logging
import struct
import base64
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Responsabilidad: reproducir audio tanto en Jitsi (Web Audio API) como localmente (VB-Cable)."""

    def __init__(self, sample_rate: int = 16000):
        self._sample_rate = sample_rate

    # ──────────────────────────────────────────────────────────────────────────
    # Dispositivos
    # ──────────────────────────────────────────────────────────────────────────

    def _obtener_cable_input(self) -> int | None:
        for i, d in enumerate(sd.query_devices()):
            if "CABLE Input (VB-Audio Virtual Cable)" in d["name"] and d["max_output_channels"] > 0:
                return i
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Conversión
    # ──────────────────────────────────────────────────────────────────────────

    def _bytes_a_numpy(self, audio_bytes: bytes) -> np.ndarray:
        try:
            import miniaudio
            decoded = miniaudio.decode(
                audio_bytes,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=self._sample_rate,
            )
            return np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.exception(f"Error convirtiendo audio: {e}")
            return np.zeros(1024, dtype=np.float32)

    @staticmethod
    def _duracion_wav(audio_bytes: bytes) -> float:
        try:
            data_size = struct.unpack_from('<I', audio_bytes, 40)[0]
            byte_rate = struct.unpack_from('<I', audio_bytes, 28)[0]
            return data_size / byte_rate
        except Exception:
            return len(audio_bytes) / (16000 * 2)

    # ──────────────────────────────────────────────────────────────────────────
    # Reproducción
    # ──────────────────────────────────────────────────────────────────────────

    def _reproducir_local(self, audio_bytes: bytes):
        """Reproduce en CABLE Input para monitoreo local."""
        cable_input = self._obtener_cable_input()
        if cable_input is None:
            logger.warning("CABLE Input no encontrado — sin reproducción local")
            return
        try:
            sd.play(self._bytes_a_numpy(audio_bytes), samplerate=self._sample_rate, device=cable_input)
            logger.info(f"Audio local reproduciendo en CABLE Input ({len(audio_bytes)} bytes)")
        except Exception as e:
            logger.warning(f"Error reproduciendo audio local: {e}")

    async def reproducir(self, page, audio_bytes: bytes, stop_event: asyncio.Event = None):
        """
        Inyecta el audio en Jitsi y lo reproduce localmente.
        Si stop_event se activa antes de que termine, detiene ambos.
        """
        # 1. Inyectar en página
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await page.evaluate("""
            (b64) => {
                window._audioQueue.push(b64);
                if (window._playNext) window._playNext();
            }
        """, b64)

        # 2. Reproducir localmente (no bloqueante)
        self._reproducir_local(audio_bytes)

        # 3. Esperar duración con polling de interrupción
        duracion = self._duracion_wav(audio_bytes)
        logger.info(f"Audio inyectado en página ({len(audio_bytes)} bytes, {duracion:.1f}s)")

        elapsed, interval, total = 0.0, 0.2, duracion + 0.3
        while elapsed < total:
            if stop_event is not None and stop_event.is_set():
                logger.info("Audio interrumpido por el alumno")
                await page.evaluate("() => { if (window._stopAudio) window._stopAudio(); }")
                sd.stop()
                return
            await asyncio.sleep(interval)
            elapsed += interval

    async def detener(self, page):
        """Detiene reproducción en Jitsi y localmente."""
        await page.evaluate("() => { if (window._stopAudio) window._stopAudio(); }")
        sd.stop()
        logger.info("Reproducción detenida")