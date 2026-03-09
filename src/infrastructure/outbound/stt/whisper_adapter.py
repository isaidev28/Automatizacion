from faster_whisper import WhisperModel
from src.domain.ports.outbound.i_stt_service import ISTTService
from src.domain.exceptions.ia_exception import STTNoDisponibleException
import io
import tempfile
import os
import wave
import time
import logging

logger = logging.getLogger(__name__)

class WhisperAdapter(ISTTService):

    def __init__(self, model_size: str = "small", device: str = "cpu"):
        """
        model_size: tiny | base | small | medium | large
        device:     cpu | cuda (si tienes GPU)
        """
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type="int8"  # Optimizado para CPU
        )
        logger.info(f" WhisperAdapter inicializado con modelo {model_size}")

    async def transcribir(self, audio_bytes: bytes, idioma: str = "es") -> str:
        """
        Transcribe audio con opción de depuración
        """
        tmp_path = None
        try:
            # 1. Verificar que el audio no esté vacío
            if len(audio_bytes) < 1000:  # Menos de 1KB probablemente es silencio
                logger.warning(" Audio demasiado corto, probable silencio")
                return ""

            # =========================================================
            #  DEPURACIÓN: Guardar audio para escucharlo manualmente
            # =========================================================
            debug_filename = f"debug_audio_{int(time.time())}.wav"
            with open(debug_filename, "wb") as f:
                f.write(audio_bytes)
            logger.info(f" Audio guardado para depuración: {debug_filename}")
            logger.info(f"   - Tamaño: {len(audio_bytes)} bytes")
            logger.info(f"   - Puedes reproducirlo con cualquier reproductor")
            # =========================================================

            # 2. Guardar como WAV para Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            logger.info(f" Procesando audio: {len(audio_bytes)} bytes")

            # 3. Transcribir SIN VAD (recomendado)
            segments, info = self._model.transcribe(
                tmp_path,
                language=idioma,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                vad_filter=False,  # ← Desactivado para evitar cortes
                condition_on_previous_text=False,
                without_timestamps=True,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.3,
            )

            # 4. Unir todos los segmentos
            transcripcion = " ".join(segment.text.strip() for segment in segments)
            
            # 5. Logging
            if transcripcion:
                logger.info(f" Transcripción exitosa: '{transcripcion[:100]}...'")
                logger.info(f"   - Idioma detectado: {info.language}")
                logger.info(f"   - Probabilidad: {info.language_probability:.2f}")
            else:
                logger.warning(" Transcripción vacía - ¿audio sin voz?")
            
            return transcripcion.strip()

        except Exception as e:
            logger.exception(f" Error en transcripción: {e}")
            raise STTNoDisponibleException(f"Error con Whisper local: {str(e)}")

        finally:
            # Limpiar archivo temporal
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
                logger.debug(f" Archivo temporal eliminado: {tmp_path}")