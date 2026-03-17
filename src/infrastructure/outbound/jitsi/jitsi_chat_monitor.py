# src/infrastructure/outbound/jitsi/JitsiChatMonitor.py

import logging

logger = logging.getLogger(__name__)


class JitsiChatMonitor:
    """Responsabilidad: leer mensajes nuevos del chat de Jitsi/JaaS."""

    # Selectores en orden de prioridad (distintas versiones de Jitsi/JaaS)
    _SELECTORES = [
        '[class*="chat-message"] [class*="message-text"]',
        '[class*="chatmessage"] [class*="text"]',
        '[class*="MessageContent"]',
        '[data-testid*="message"]',
        '.message-text',
        '[class*="chat"] [class*="message"]',
    ]

    async def leer_nuevo_mensaje(self, page) -> str | None:
        """
        Retorna el texto del último mensaje del chat si es nuevo,
        None si no hay mensajes o ya fue leído.
        """
        try:
            # DEBUG temporal — encontrar selectores reales de JaaS
            debug = await page.evaluate("""
                () => {
                    const todo = document.body.innerHTML;
                    const idx = todo.toLowerCase().indexOf('hola');
                    if (idx === -1) return 'NO ENCONTRADO EN DOM';
                    return todo.substring(Math.max(0, idx-300), idx+600);
                }
            """)
            logger.info(f"CHAT DEBUG: {debug[:800]}")

            return await page.evaluate(f"""
                () => {{
                    const selectores = {self._SELECTORES};
                    let ultimo = null;
                    for (const sel of selectores) {{
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {{ ultimo = els[els.length - 1]; break; }}
                    }}
                    if (!ultimo) return null;
                    const texto = ultimo.innerText?.trim();
                    if (!texto) return null;
                    const id = ultimo.dataset.msgId || texto.slice(0, 50);
                    if (window._ultimoMsgId === id) return null;
                    window._ultimoMsgId = id;
                    return texto;
                }}
            """)
        except Exception as e:
            logger.debug(f"JitsiChatMonitor: error leyendo chat — {e}")
            return None