import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.llm.gemini_adapter import GeminiAdapter

load_dotenv()

PDF_EJEMPLO = """
Introducción a Python:
Python es un lenguaje de programación de alto nivel, interpretado y de propósito general.
Fue creado por Guido van Rossum en 1991.
Sus características principales son: sintaxis simple, tipado dinámico y gran ecosistema de librerías.
"""

@pytest.fixture
def adapter():
    return GeminiAdapter(
        api_key = os.getenv("GEMINI_API_KEY"),
        model   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )

@pytest.mark.asyncio
async def test_generar_explicacion(adapter):
    respuesta = await adapter.generar_explicacion(
        contenido_pdf   = PDF_EJEMPLO,
        progreso        = 0.0,
        nombre_alumno   = "Juan",
        nombre_profesor = "Dr. García"
    )
    print(f"\n Explicación:\n{respuesta}")
    assert respuesta is not None
    assert len(respuesta) > 50

@pytest.mark.asyncio
async def test_validar_tema_dentro(adapter):
    resultado = await adapter.validar_tema(
        pregunta      = "¿Qué es el tipado dinámico en Python?",
        contenido_pdf = PDF_EJEMPLO
    )
    print(f"\n Dentro del tema: {resultado}")
    assert resultado is True

@pytest.mark.asyncio
async def test_validar_tema_fuera(adapter):
    resultado = await adapter.validar_tema(
        pregunta      = "¿Cuál es la receta de la paella?",
        contenido_pdf = PDF_EJEMPLO
    )
    print(f"\n Fuera del tema: {resultado}")
    assert resultado is False