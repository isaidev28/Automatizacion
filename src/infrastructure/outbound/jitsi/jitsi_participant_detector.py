# src/infrastructure/outbound/jitsi/JitsiParticipantDetector.py

import asyncio
import logging

logger = logging.getLogger(__name__)


class JitsiParticipantDetector:
    """Responsabilidad: detectar la presencia de participantes remotos en la sala."""

    async def hay_participantes(self, page) -> bool:
        """Retorna True si hay al menos un participante remoto en sala."""
        try:
            count = await page.evaluate("""
                () => {
                    const porClase = document.querySelectorAll('[class*="remote"]').length;
                    const porId    = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.id.match(/^participant_[a-f0-9]+$/))
                        .length;
                    return Math.max(porClase, porId);
                }
            """)
            return count > 0
        except Exception as e:
            logger.debug(f"JitsiParticipantDetector: error — {e}")
            return False

    async def esperar_alumno(self, page, timeout: int = 300) -> bool:
        """
        Polling hasta que entre al menos un participante o se agote el timeout.
        Retorna True si el alumno entró a tiempo.
        """
        logger.info("Esperando que el alumno entre a la sala...")
        inicio = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - inicio < timeout:
            if await self.hay_participantes(page):
                logger.info("¡Alumno detectado!")
                return True
            await asyncio.sleep(2)

        logger.warning(f"Timeout esperando alumno ({timeout}s)")
        return False