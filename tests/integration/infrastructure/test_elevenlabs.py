import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.tts.elevenlabs_adapter import ElevenLabsAdapter

load_dotenv()


@pytest.fixture
def adapter():
    return ElevenLabsAdapter(
        api_key  = os.getenv("ELEVENLABS_API_KEY"),
        voice_id = os.getenv("ELEVENLABS_VOICE_ID"),
    )


@pytest.mark.asyncio
async def test_sintetizar_audio(adapter):
    texto = "Hola, soy tu profesor virtual. Bienvenido a la clase de hoy."

    audio_bytes = await adapter.sintetizar(texto)

    print(f"\n Audio generado: {len(audio_bytes)} bytes")
    assert audio_bytes is not None
    assert len(audio_bytes) > 0

    # Guardar el audio para escucharlo
    with open("tests/test_audio_output.mp3", "wb") as f:
        f.write(audio_bytes)
    print(" Audio guardado en: tests/test_audio_output.mp3")


@pytest.mark.asyncio
async def test_sintetizar_texto_largo(adapter):
    texto = """
    Bienvenido a la clase de Python. Hoy vamos a aprender sobre los tipos de datos básicos.
    Python es un lenguaje de programación de alto nivel, interpretado y de propósito general.
    Fue creado por Guido van Rossum en 1991 y se ha convertido en uno de los lenguajes
    más populares del mundo gracias a su sintaxis simple y su gran ecosistema de librerías.
    """

    audio_bytes = await adapter.sintetizar(texto)

    print(f"\n Audio largo generado: {len(audio_bytes)} bytes")
    assert len(audio_bytes) > 1000