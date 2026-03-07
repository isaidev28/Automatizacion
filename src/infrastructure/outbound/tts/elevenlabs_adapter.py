from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from src.domain.ports.outbound.i_tts_service import ITTSService
from src.domain.exceptions.ia_exception import TTSNoDisponibleException
from gtts import gTTS
import asyncio
import io
import wave
import logging

logger = logging.getLogger(__name__)

MAX_ELEVENLABS_CHARS = 400


class ElevenLabsAdapter(ITTSService):

    def __init__(self, api_key: str, voice_id: str):
        self._api_key  = api_key
        self._voice_id = voice_id

    def _get_client(self) -> ElevenLabs:
        return ElevenLabs(api_key=self._api_key)

    def _pcm_a_wav(self, pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)           # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        buf.seek(0)
        return buf.read()

    def _mp3_a_wav(self, mp3_bytes: bytes) -> bytes:
        try:
            from pydub import AudioSegment
            seg = (
                AudioSegment
                .from_mp3(io.BytesIO(mp3_bytes))
                .set_channels(1)
                .set_frame_rate(16000)
                .set_sample_width(2)
            )
            buf = io.BytesIO()
            seg.export(buf, format="wav")
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.warning(f"pydub no disponible, intentando miniaudio: {e}")
            import miniaudio
            decoded = miniaudio.decode(
                mp3_bytes,
                output_format = miniaudio.SampleFormat.SIGNED16,
                nchannels     = 1,
                sample_rate   = 16000,
            )
            return self._pcm_a_wav(decoded.samples, sample_rate=16000)

    def _sintetizar_elevenlabs(self, texto: str) -> bytes:
        client = self._get_client()
        chunks = []

        # Intentar PCM directo (más eficiente, sin conversión)
        try:
            for chunk in client.text_to_speech.convert(
                voice_id      = self._voice_id,
                text          = texto[:MAX_ELEVENLABS_CHARS],
                model_id      = "eleven_multilingual_v2",
                output_format = "pcm_16000",          # PCM crudo 16kHz mono
                voice_settings = VoiceSettings(
                    stability         = 0.5,
                    similarity_boost  = 0.8,
                    style             = 0.2,
                    use_speaker_boost = True,
                )
            ):
                chunks.append(chunk)
            pcm = b"".join(chunks)
            logger.info(f"ElevenLabs PCM OK ({len(pcm)} bytes)")
            return self._pcm_a_wav(pcm, sample_rate=16000)

        except Exception as e:
            if "output_format" in str(e).lower() or "invalid" in str(e).lower():
                # Plan gratuito no soporta PCM — fallback a MP3 y convertir
                logger.warning("PCM no soportado, usando MP3 → WAV")
                chunks.clear()
                for chunk in client.text_to_speech.convert(
                    voice_id      = self._voice_id,
                    text          = texto[:MAX_ELEVENLABS_CHARS],
                    model_id      = "eleven_multilingual_v2",
                    output_format = "mp3_44100_128",
                    voice_settings = VoiceSettings(
                        stability         = 0.5,
                        similarity_boost  = 0.8,
                        style             = 0.2,
                        use_speaker_boost = True,
                    )
                ):
                    chunks.append(chunk)
                mp3 = b"".join(chunks)
                return self._mp3_a_wav(mp3)
            raise

    def _sintetizar_gtts(self, texto: str) -> bytes:
        """Fallback: gTTS devuelve MP3, lo convertimos a WAV"""
        logger.info("gTTS fallback activado")
        tts    = gTTS(text=texto[:1000], lang="es", slow=False)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        mp3_bytes = buffer.read()
        # Convertir MP3 → WAV para que bot_sala pueda inyectarlo
        return self._mp3_a_wav(mp3_bytes)

    async def sintetizar(self, texto: str) -> bytes:
        try:
            audio = await asyncio.to_thread(self._sintetizar_elevenlabs, texto)
            logger.info(f"ElevenLabs OK → WAV ({min(len(texto), MAX_ELEVENLABS_CHARS)} chars)")
            return audio
        except Exception as e:
            err = str(e)
            if any(x in err for x in ["quota_exceeded", "401", "insufficient", "voice_not_found"]):
                logger.warning("ElevenLabs sin créditos — usando gTTS")
            else:
                logger.warning(f"ElevenLabs error — usando gTTS: {err[:80]}")
            try:
                return await asyncio.to_thread(self._sintetizar_gtts, texto)
            except Exception as e2:
                raise TTSNoDisponibleException(f"TTS no disponible: {str(e2)}")

    async def sintetizar_stream(self, texto: str):
        try:
            audio = await self.sintetizar(texto)
            for i in range(0, len(audio), 1024):
                yield audio[i:i+1024]
                await asyncio.sleep(0)
        except Exception as e:
            raise TTSNoDisponibleException(f"Error en stream TTS: {str(e)}")