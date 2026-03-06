from google import genai
from src.domain.ports.outbound.i_llm_service import ILLMService
from src.domain.exceptions.ia_exception import LLMNoDisponibleException
from typing import AsyncGenerator
import asyncio

SYSTEM_PROMPT_TEMPLATE = """
Eres {nombre_profesor}, un profesor virtual experto dando clase a {nombre_alumno}.

CONTENIDO DEL CURSO (estrictamente basado en este material):
{contenido_pdf}

REGLAS ABSOLUTAS — NUNCA las rompas:
1. SOLO puedes hablar sobre temas presentes en el PDF.
   Si te preguntan algo externo responde EXACTAMENTE:
   "Ese tema no forma parte de esta clase. Retomemos [tema actual]."
2. Cada vez que el progreso llegue a un checkpoint pregunta:
   "¿Tienes alguna duda sobre lo que acabamos de ver?"
3. Cuando el alumno intervenga: DETENTE, escucha, responde con claridad y retoma.
4. Estructura la clase: introducción → desarrollo → ejemplos → cierre.
5. Habla siempre en español, de forma clara y didáctica.
6. Progreso actual de la clase: {progreso}%
"""

PROMPT_VALIDAR_TEMA = """
Tienes el siguiente contenido de un PDF educativo:
{contenido_pdf}

¿La siguiente pregunta está relacionada con ese contenido?
PREGUNTA: {pregunta}

Responde ÚNICAMENTE con: SI o NO
"""


class GeminiAdapter(ILLMService):

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-preview-04-17"):
        self._api_key    = api_key
        self._model_name = model

    def _get_client(self) -> genai.Client:
        """Cliente síncrono nuevo por cada llamada — evita conflictos de event loop"""
        return genai.Client(api_key=self._api_key)

    def _generar_sincrono(self, prompt: str) -> str:
        client   = self._get_client()
        response = client.models.generate_content(
            model    = self._model_name,
            contents = prompt
        )
        return response.text

    async def generar_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> str:
        try:
            prompt = SYSTEM_PROMPT_TEMPLATE.format(
                nombre_profesor = nombre_profesor,
                nombre_alumno   = nombre_alumno,
                contenido_pdf   = contenido_pdf[:8000],
                progreso        = progreso
            ) + "\n\nContinúa con la clase desde donde quedamos."

            return await asyncio.to_thread(self._generar_sincrono, prompt)

        except Exception as e:
            raise LLMNoDisponibleException(f"Error con Gemini: {str(e)}")

    async def responder_duda(
        self,
        pregunta: str,
        contenido_pdf: str,
        historial: list[dict]
    ) -> str:
        try:
            historial_texto = "\n".join([
                f"{m['role'].upper()}: {m['content']}"
                for m in historial[-10:]
            ])
            prompt = (
                f"Responde SOLO basándote en este contenido:\n{contenido_pdf[:8000]}\n\n"
                f"Historial:\n{historial_texto}\n\n"
                f"ALUMNO: {pregunta}"
            )
            return await asyncio.to_thread(self._generar_sincrono, prompt)

        except Exception as e:
            raise LLMNoDisponibleException(f"Error respondiendo duda: {str(e)}")

    async def validar_tema(self, pregunta: str, contenido_pdf: str) -> bool:
        try:
            prompt = PROMPT_VALIDAR_TEMA.format(
                contenido_pdf = contenido_pdf[:3000],
                pregunta      = pregunta
            )
            respuesta = await asyncio.to_thread(self._generar_sincrono, prompt)
            return "SI" in respuesta.strip().upper()

        except Exception as e:
            raise LLMNoDisponibleException(f"Error validando tema: {str(e)}")

    async def stream_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> AsyncGenerator[str, None]:
        # Para stream usamos síncrono también
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            nombre_profesor = nombre_profesor,
            nombre_alumno   = nombre_alumno,
            contenido_pdf   = contenido_pdf[:8000],
            progreso        = progreso
        ) + "\n\nContinúa con la clase."

        try:
            texto = await asyncio.to_thread(self._generar_sincrono, prompt)
            # Simular stream por chunks de palabras
            for palabra in texto.split(" "):
                yield palabra + " "
                await asyncio.sleep(0.05)
        except Exception as e:
            raise LLMNoDisponibleException(f"Error en stream Gemini: {str(e)}")