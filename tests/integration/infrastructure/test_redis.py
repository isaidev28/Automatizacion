import pytest
import asyncio
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.cache.redis_adapter import RedisAdapter

load_dotenv()


@pytest.fixture
def adapter():
    return RedisAdapter(url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))


@pytest.mark.asyncio
async def test_ping(adapter):
    resultado = await adapter.ping()
    print(f"\n Redis conectado: {resultado}")
    assert resultado is True


@pytest.mark.asyncio
async def test_guardar_y_obtener_sesion(adapter):
    clase_id = "test_clase_001"
    datos    = {
        "nombre_profesor": "Dr. García",
        "nombre_alumno":   "Juan Pérez",
        "estado":          "en_curso",
        "progreso":        0.0
    }

    await adapter.guardar_sesion(clase_id, datos, ttl=60)
    sesion = await adapter.obtener_sesion(clase_id)

    print(f"\n Sesión guardada y recuperada: {sesion}")
    assert sesion["nombre_profesor"] == "Dr. García"
    assert sesion["estado"]          == "en_curso"


@pytest.mark.asyncio
async def test_actualizar_estado(adapter):
    clase_id = "test_clase_001"

    await adapter.actualizar_estado(clase_id, "en_pausa_ia")
    estado = await adapter._redis.hget(f"clase:{clase_id}:estado", "ia_estado")

    print(f"\n Estado actualizado: {estado}")
    assert estado == "en_pausa_ia"


@pytest.mark.asyncio
async def test_historial_chat(adapter):
    clase_id = "test_clase_001"

    await adapter.guardar_historial_chat(clase_id, {
        "role": "user", "content": "¿Qué es Python?"
    })
    await adapter.guardar_historial_chat(clase_id, {
        "role": "assistant", "content": "Python es un lenguaje de programación."
    })

    historial = await adapter.obtener_historial_chat(clase_id)

    print(f"\n Historial: {historial}")
    assert len(historial) >= 2


@pytest.mark.asyncio
async def test_eliminar_sesion(adapter):
    clase_id = "test_clase_001"

    await adapter.eliminar_sesion(clase_id)
    sesion = await adapter.obtener_sesion(clase_id)

    print(f"\n Sesión eliminada: {sesion}")
    assert sesion is None