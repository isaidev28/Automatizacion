import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.llm.deepseek_adapter import DeepSeekAdapter

load_dotenv()

PDF_EJEMPLO = """
Introducción a Python:
Python es un lenguaje de programación de alto nivel, interpretado y de propósito general.
Fue creado por Guido van Rossum en 1991.
Sus características principales son: sintaxis simple, tipado dinámico y gran ecosistema de librerías.
Los tipos de datos básicos son: int, float, str, bool, list, dict, tuple y set.
"""

@pytest.fixture
def adapter():
    return DeepSeekAdapter(
        api_key  = os.getenv("DEEPSEEK_API_KEY"),
        base_url = os.getenv("DEEPSEEK_BASE_URL"),
        model    = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    )


@pytest.mark.asyncio
async def test_generar_explicacion(adapter):
    respuesta = await adapter.generar_explicacion(
        contenido_pdf   = PDF_EJEMPLO,
        progreso        = 0.0,
        nombre_alumno   = "Juan",
        nombre_profesor = "Dr. García"
    )
    print(f"\n Explicación generada:\n{respuesta}")
    assert respuesta is not None
    assert len(respuesta) > 50


@pytest.mark.asyncio
async def test_validar_tema_dentro(adapter):
    resultado = await adapter.validar_tema(
        pregunta      = "¿Qué es el tipado dinámico en Python?",
        contenido_pdf = PDF_EJEMPLO
    )
    print(f"\n Pregunta dentro del tema: {resultado}")
    assert resultado is True


@pytest.mark.asyncio
async def test_validar_tema_fuera(adapter):
    resultado = await adapter.validar_tema(
        pregunta      = "¿Cuál es la receta de la paella?",
        contenido_pdf = PDF_EJEMPLO
    )
    print(f"\n Pregunta fuera del tema: {resultado}")
    assert resultado is False


@pytest.mark.asyncio
async def test_responder_duda(adapter):
    respuesta = await adapter.responder_duda(
        pregunta      = "¿Quién creó Python?",
        contenido_pdf = PDF_EJEMPLO,
        historial     = []
    )
    print(f"\n Respuesta a duda:\n{respuesta}")
    assert respuesta is not None
    assert len(respuesta) > 10