from faster_whisper import WhisperModel
from src.domain.ports.outbound.i_stt_service import ISTTService
from src.domain.exceptions.ia_exception import STTNoDisponibleException
import io
import tempfile
import os


class WhisperAdapter(ISTTService):

    def __init__(self, model_size: str = "small", device: str = "cpu"):
        """
        model_size: tiny | base | small | medium | large
        device:     cpu | cuda (si tienes GPU)
        """
        self._model = WhisperModel(
            model_size,
            device          = device,
            compute_type    = "int8"    # Optimizado para CPU
        )

    async def transcribir(self, audio_bytes: bytes, idioma: str = "es") -> str:
        try:
            # Faster-Whisper necesita un archivo temporal
            with tempfile.NamedTemporaryFile(
                suffix  = ".mp3",
                delete  = False
            ) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            segments, info = self._model.transcribe(
                tmp_path,
                language             = idioma,
                beam_size            = 5,
                vad_filter           = True,    # Filtra silencios
                vad_parameters       = dict(min_silence_duration_ms=500)
            )

            # Unir todos los segmentos transcritos
            transcripcion = " ".join(
                segment.text.strip() for segment in segments
            )

            return transcripcion.strip()

        except Exception as e:
            raise STTNoDisponibleException(f"Error con Whisper local: {str(e)}")

        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)