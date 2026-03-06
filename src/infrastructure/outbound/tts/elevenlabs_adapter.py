from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from src.domain.ports.outbound.i_tts_service import ITTSService
from src.domain.exceptions.ia_exception import TTSNoDisponibleException
import asyncio


class ElevenLabsAdapter(ITTSService):

    def __init__(self, api_key: str, voice_id: str):
        self._api_key  = api_key
        self._voice_id = voice_id

    def _get_client(self) -> ElevenLabs:
        return ElevenLabs(api_key=self._api_key)

    def _sintetizar_sincrono(self, texto: str) -> bytes:
        client = self._get_client()
        chunks = []
        for chunk in client.text_to_speech.convert(
            voice_id = self._voice_id,
            text     = texto,
            model_id = "eleven_multilingual_v2",
            voice_settings = VoiceSettings(
                stability        = 0.5,
                similarity_boost = 0.8,
                style            = 0.2,
                use_speaker_boost = True
            )
        ):
            chunks.append(chunk)
        return b"".join(chunks)

    async def sintetizar(self, texto: str) -> bytes:
        try:
            return await asyncio.to_thread(self._sintetizar_sincrono, texto)
        except Exception as e:
            raise TTSNoDisponibleException(f"Error con ElevenLabs: {str(e)}")

    async def sintetizar_stream(self, texto: str):
        try:
            audio = await asyncio.to_thread(self._sintetizar_sincrono, texto)
            # Simular stream por chunks de 1024 bytes
            for i in range(0, len(audio), 1024):
                yield audio[i:i+1024]
                await asyncio.sleep(0)
        except Exception as e:
            raise TTSNoDisponibleException(f"Error en stream TTS: {str(e)}")