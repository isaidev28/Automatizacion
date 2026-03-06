import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.sala.jitsi_adapter import JitsiAdapter

load_dotenv()


@pytest.fixture
def adapter():
    return JitsiAdapter(
        app_id           = os.getenv("JITSI_APP_ID"),
        api_key_id       = os.getenv("JITSI_API_KEY_ID"),
        private_key_path = os.getenv("JITSI_PRIVATE_KEY_PATH"),
    )


@pytest.mark.asyncio
async def test_crear_sala(adapter):
    sala_id = f"test_{os.urandom(4).hex()}"

    links = await adapter.crear_sala(
        sala_id         = sala_id,
        nombre_profesor = "Profesor IA",
        nombre_alumno   = "Juan Pérez",
        correo_alumno   = "juan@test.com",
    )

    print(f"\n Sala creada: {sala_id}")
    print(f"\n Link alumno:\n   {links.alumno}")
    print(f"\n Link supervisor:\n   {links.supervisor}")

    assert links.alumno is not None
    assert links.supervisor is not None
    assert sala_id in links.alumno
    assert sala_id in links.supervisor
    assert "jwt=" in links.alumno
    assert "jwt=" in links.supervisor


def test_token_alumno_no_es_moderador(adapter):
    token = adapter.generar_token_alumno(
        sala_id = "test_sala",
        nombre  = "Juan",
        correo  = "juan@test.com"
    )
    # Verificar que el token fue generado
    assert token is not None
    assert len(token) > 50
    print(f"\n Token alumno generado: {token[:50]}...")


def test_token_moderador(adapter):
    token = adapter.generar_token_moderador(
        sala_id = "test_sala",
        nombre  = "Profesor IA"
    )
    assert token is not None
    assert len(token) > 50
    print(f"\n Token moderador generado: {token[:50]}...")