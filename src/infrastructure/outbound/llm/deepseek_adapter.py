from openai import AsyncOpenAI
from src.domain.ports.outbound.i_llm_service import ILLMService
from src.domain.exceptions.ia_exception import LLMNoDisponibleException
from typing import AsyncGenerator

SYSTEM_PROMPT_TEMPLATE = """
Eres {nombre_profesor}, un profesor virtual experto dando clase a {nombre_alumno}.

CONTENIDO DEL CURSO (extrictamente basado en este material):
{contenido_pdf}

REGLAS ABSOLUTAS — NUNCA las rompas:
1. SOLO puedes hablar sobre temas presentes en el PDF.
   Si te preguntan algo externo responde EXACTAMENTE:
   "Ese tema no forma parte de esta clase. Retomemos [tema actual]."
2. Cada vez que el progreso llegue a un checkpoint (20%, 40%, 60%, 80%) pregunta:
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


class DeepSeekAdapter(ILLMService):

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model  = model

    async def generar_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model    = self._model,
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_TEMPLATE.format(
                            nombre_profesor = nombre_profesor,
                            nombre_alumno   = nombre_alumno,
                            contenido_pdf   = contenido_pdf[:8000],
                            progreso        = progreso
                        )
                    },
                    {
                        "role": "user",
                        "content": "Continúa con la clase desde donde quedamos."
                    }
                ],
                max_tokens  = 500,
                temperature = 0.7
            )
            return response.choices[0].message.content

        except Exception as e:
            raise LLMNoDisponibleException(f"Error con DeepSeek: {str(e)}")

    async def responder_duda(
        self,
        pregunta: str,
        contenido_pdf: str,
        historial: list[dict]
    ) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"Responde SOLO basándote en este contenido:\n{contenido_pdf[:8000]}\n"
                               f"Si la pregunta está fuera del tema responde que no es parte de la clase."
                },
                *historial,
                {"role": "user", "content": pregunta}
            ]
            response = await self._client.chat.completions.create(
                model       = self._model,
                messages    = messages,
                max_tokens  = 400,
                temperature = 0.5
            )
            return response.choices[0].message.content

        except Exception as e:
            raise LLMNoDisponibleException(f"Error respondiendo duda: {str(e)}")

    async def validar_tema(self, pregunta: str, contenido_pdf: str) -> bool:
        try:
            response = await self._client.chat.completions.create(
                model    = self._model,
                messages = [{
                    "role": "user",
                    "content": PROMPT_VALIDAR_TEMA.format(
                        contenido_pdf = contenido_pdf[:3000],
                        pregunta      = pregunta
                    )
                }],
                max_tokens  = 5,
                temperature = 0.0     # Sin creatividad para validaciones
            )
            resultado = response.choices[0].message.content.strip().upper()
            return "SI" in resultado

        except Exception as e:
            raise LLMNoDisponibleException(f"Error validando tema: {str(e)}")

    async def stream_explicacion(
        self,
        contenido_pdf: str,
        progreso: float,
        nombre_alumno: str,
        nombre_profesor: str
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(
                model    = self._model,
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_TEMPLATE.format(
                            nombre_profesor = nombre_profesor,
                            nombre_alumno   = nombre_alumno,
                            contenido_pdf   = contenido_pdf[:8000],
                            progreso        = progreso
                        )
                    },
                    {"role": "user", "content": "Continúa con la clase."}
                ],
                max_tokens = 500,
                stream     = True
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except Exception as e:
            raise LLMNoDisponibleException(f"Error en stream: {str(e)}")