import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.stt.whisper_adapter import WhisperAdapter
from src.infrastructure.outbound.tts.elevenlabs_adapter import ElevenLabsAdapter

load_dotenv()


@pytest.fixture(scope="module")
def stt_adapter():
    # scope="module" para cargar el modelo solo una vez
    print("\n Cargando modelo Whisper (primera vez descarga ~500MB)...")
    return WhisperAdapter(model_size="small", device="cpu")


@pytest.fixture
def tts_adapter():
    return ElevenLabsAdapter(
        api_key  = os.getenv("ELEVENLABS_API_KEY"),
        voice_id = os.getenv("ELEVENLABS_VOICE_ID"),
    )


@pytest.mark.asyncio
async def test_transcribir_audio(stt_adapter, tts_adapter):
    # 1. Generar audio con ElevenLabs
    texto_original = "Hola profesor, tengo una duda sobre Python."
    audio_bytes    = await tts_adapter.sintetizar(texto_original)

    print(f"\n Audio generado: {len(audio_bytes)} bytes")

    # 2. Transcribir con Whisper local
    transcripcion = await stt_adapter.transcribir(audio_bytes)

    print(f" Transcripción: {transcripcion}")

    assert transcripcion is not None
    assert len(transcripcion) > 5


@pytest.mark.asyncio
async def test_transcribir_pregunta_alumno(stt_adapter, tts_adapter):
    texto_original = "¿Cuáles son los tipos de datos en Python?"
    audio_bytes    = await tts_adapter.sintetizar(texto_original)

    transcripcion = await stt_adapter.transcribir(audio_bytes)

    print(f"\n Pregunta transcrita: {transcripcion}")

    assert transcripcion is not None
    assert len(transcripcion) > 5