import asyncio
import argparse
import struct
import math
import wave
import io
import base64
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─── Init script: AudioContext único + deshabilitar lobby ─────────────────────
INIT_SCRIPT = """
(function() {
    let _ctx  = null;
    let _dest = null;

    window._audioQueue = [];
    window._isPlaying  = false;

    function _getOrCreateContext() {
        if (_ctx) return { ctx: _ctx, dest: _dest };

        _ctx  = new AudioContext({ sampleRate: 16000 });
        _dest = _ctx.createMediaStreamDestination();
        window._audioContext = _ctx;
        window._audioDest    = _dest;

        const silBuf  = _ctx.createBuffer(1, _ctx.sampleRate, _ctx.sampleRate);
        const silNode = _ctx.createBufferSource();
        silNode.buffer = silBuf;
        silNode.loop   = true;
        silNode.connect(_dest);
        silNode.start();

        window._playNext = async function() {
            if (window._isPlaying || window._audioQueue.length === 0) return;
            window._isPlaying = true;
            if (_ctx.state === 'suspended') await _ctx.resume();

            const b64    = window._audioQueue.shift();
            const binary = atob(b64);
            const bytes  = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

            try {
                const buf    = await _ctx.decodeAudioData(bytes.buffer);
                const source = _ctx.createBufferSource();
                source.buffer = buf;
                source.connect(_dest);
                source.start();
                console.log('[BOT] Reproduciendo audio, duracion:', buf.duration.toFixed(2), 's');
                source.onended = function() {
                    window._isPlaying = false;
                    window._playNext();
                };
            } catch(e) {
                console.error('[BOT] Error decoding audio:', e);
                window._isPlaying = false;
                window._playNext();
            }
        };

        console.log('[BOT] AudioContext creado OK');
        return { ctx: _ctx, dest: _dest };
    }

    // Interceptar getUserMedia — devolver siempre el mismo stream sintético
    const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        if (!constraints || !constraints.audio) return origGetUserMedia(constraints);
        const { dest } = _getOrCreateContext();
        console.log('[BOT] getUserMedia interceptado');
        return dest.stream;
    };

    // ── Deshabilitar lobby automáticamente cuando Jitsi esté listo ──────────
    // Jitsi expone APP.conference y APP.store en window cuando está inicializado
    window._lobbyDisabled = false;
    const _lobbyInterval = setInterval(() => {
        try {
            // Método 1: IFrame API / APP store
            if (window.APP && window.APP.store) {
                const state = window.APP.store.getState();
                // Dispatchar acción para deshabilitar lobby
                window.APP.store.dispatch({
                    type: 'TOGGLE_LOBBY_MODE',
                    enabled: false
                });
                console.log('[BOT] Lobby deshabilitado via APP.store');
                window._lobbyDisabled = true;
                clearInterval(_lobbyInterval);
                return;
            }
            // Método 2: API directa de la conferencia
            if (window.APP && window.APP.conference && window.APP.conference._room) {
                window.APP.conference._room.setLobbyEnabled(false);
                console.log('[BOT] Lobby deshabilitado via conference._room');
                window._lobbyDisabled = true;
                clearInterval(_lobbyInterval);
                return;
            }
        } catch(e) {
            // Aún no está listo, seguir esperando
        }
    }, 500);

    // Parar después de 15s si no se pudo
    setTimeout(() => {
        clearInterval(_lobbyInterval);
        if (!window._lobbyDisabled) {
            console.warn('[BOT] No se pudo deshabilitar lobby automaticamente');
        }
    }, 15000);
})();
"""


# ─── Generadores de audio ─────────────────────────────────────────────────────

def generar_tono_wav(frecuencia=440, duracion=2.0, sample_rate=16000, amplitud=0.6):
    n = int(sample_rate * duracion)
    samples = [int(amplitud * math.sin(2 * math.pi * frecuencia * i / sample_rate) * 32767)
               for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{n}h', *samples))
    buf.seek(0)
    return buf.read()


def generar_voz_gtts(texto):
    try:
        from gtts import gTTS
        from pydub import AudioSegment
        tts = gTTS(text=texto, lang="es", slow=False)
        mp3 = io.BytesIO()
        tts.write_to_fp(mp3)
        mp3.seek(0)
        seg = AudioSegment.from_mp3(mp3).set_channels(1).set_frame_rate(16000).set_sample_width(2)
        wav = io.BytesIO()
        seg.export(wav, format="wav")
        wav.seek(0)
        return wav.read()
    except Exception as e:
        logger.warning(f"gTTS no disponible: {e}")
        return None


def duracion_wav(b):
    try:
        return struct.unpack_from('<I', b, 40)[0] / struct.unpack_from('<I', b, 28)[0]
    except Exception:
        return len(b) / (16000 * 2)


# ─── Test principal ───────────────────────────────────────────────────────────

async def test_audio_en_jitsi(url: str, usar_voz: bool = True):
    from playwright.async_api import async_playwright

    logger.info("=" * 60)
    logger.info("TEST DE AUDIO BOT EN JITSI  v3")
    logger.info("=" * 60)
    logger.info(f"URL: {url}")
    logger.info("")
    logger.info(">>> ABRE ESTA URL EN TU MOVIL O EN OTRO NAVEGADOR:")
    logger.info(f">>> {url}")
    logger.info("")

    audios = [
        ("Tono 440Hz 2s", generar_tono_wav(440, 2.0)),
        ("Tono 880Hz 2s", generar_tono_wav(880, 2.0)),
    ]
    if usar_voz:
        voz = generar_voz_gtts("Hola, esto es una prueba. Me escuchas bien?")
        if voz:
            audios.append(("Voz gTTS", voz))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless = False,
            args     = [
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=WebRtcVadSuppression",
            ]
        )
        context = await browser.new_context(
            permissions         = ["microphone", "camera"],
            ignore_https_errors = True,
        )
        page = await context.new_page()
        page.on("console", lambda m: logger.info(f"[BROWSER] {m.text}"))

        await page.add_init_script(INIT_SCRIPT)

        logger.info("Navegando a sala...")
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)

        # Entrar
        for selector, desc in [
            ('[data-testid="prejoin.joinMeeting"]', "prejoin testid"),
            ('button:has-text("Join meeting")',      "Join meeting"),
            ('button:has-text("Unirse")',             "Unirse"),
        ]:
            try:
                await page.click(selector, timeout=5000)
                logger.info(f"Clic en: {desc}")
                break
            except Exception:
                continue

        # ── Esperar hasta que el bot esté EN la conferencia ───────────────────
        # Detectar si sigue en lobby (knocking) o ya está dentro
        logger.info("Esperando que el bot entre a la conferencia...")
        en_conferencia = False
        for _ in range(20):  # hasta 20s
            await asyncio.sleep(1)
            try:
                # Si hay toolbar visible → estamos dentro de la conferencia
                toolbar_visible = await page.evaluate("""
                    () => {
                        // Toolbar principal de Jitsi (solo aparece cuando estás dentro)
                        const toolbar = document.querySelector(
                            '#new-toolbox, .new-toolbox, [data-testid="toolbar.hangup"]'
                        );
                        if (toolbar) return true;

                        // Verificar que NO estamos en pantalla de lobby/knocking
                        const knockingText = document.body.innerText;
                        const enLobby = knockingText.includes('asking to join') ||
                                        knockingText.includes('waiting') ||
                                        knockingText.includes('Waiting') ||
                                        knockingText.includes('knocking');
                        return !enLobby && document.querySelector('.filmstrip') !== null;
                    }
                """)
                if toolbar_visible:
                    logger.info("Bot confirmado DENTRO de la conferencia")
                    en_conferencia = True
                    break

                # Intentar deshabilitar lobby si aún está bloqueado
                await page.evaluate("""
                    () => {
                        if (window.APP && window.APP.conference) {
                            try {
                                // Intentar entrar directamente ignorando lobby
                                if (window.APP.conference._room) {
                                    window.APP.conference._room.setLobbyEnabled(false);
                                }
                            } catch(e) {}
                        }
                    }
                """)
            except Exception:
                pass

        if not en_conferencia:
            logger.warning("=" * 60)
            logger.warning("El bot no pudo entrar a la conferencia.")
            logger.warning("meet.jit.si tiene lobby forzado en este servidor.")
            logger.warning("")
            logger.warning("OPCIONES:")
            logger.warning("  1. Usa tu propio servidor Jitsi (sin lobby)")
            logger.warning("     O usa 8x8.vc que permite deshabilitar lobby:")
            logger.warning("     https://8x8.vc/vpaas-magic-cookie-xxx/tu-sala")
            logger.warning("")
            logger.warning("  2. Abre la sala TU PRIMERO en el navegador normal,")
            logger.warning("     desactiva el lobby en Seguridad, y luego")
            logger.warning("     corre este test con la misma URL.")
            logger.warning("")
            logger.warning("  3. Para el bot REAL en producción usa JaaS (8x8.vc)")
            logger.warning("     que es lo que ya tienes configurado con JWT.")
            logger.warning("=" * 60)
            await asyncio.sleep(5)
            await browser.close()
            return

        # ── Verificar AudioContext ────────────────────────────────────────────
        ctx_state = await page.evaluate(
            "() => window._audioContext ? window._audioContext.state : 'no-creado'"
        )
        logger.info(f"AudioContext state: {ctx_state}")

        if ctx_state == "suspended":
            await page.evaluate("() => window._audioContext.resume()")
            await asyncio.sleep(0.5)

        # Esperar que ICE/DTLS termine de negociar
        logger.info("Esperando 6s para que ICE se estabilice...")
        await asyncio.sleep(6)

        # ── Inyectar audios ───────────────────────────────────────────────────
        logger.info("")
        logger.info("Inyectando audios de prueba...")
        logger.info("")

        for nombre, audio_bytes in audios:
            dur = duracion_wav(audio_bytes)
            logger.info(f"▶  {nombre}  ({dur:.1f}s)")
            b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await page.evaluate("(b64) => { window._audioQueue.push(b64); window._playNext(); }", b64)
            await asyncio.sleep(dur + 0.8)
            cola    = await page.evaluate("() => window._audioQueue.length")
            playing = await page.evaluate("() => window._isPlaying")
            logger.info(f"   cola: {cola} | reproduciendo: {playing}")

        logger.info("")
        logger.info("Manteniendo sala abierta 20s...")
        await asyncio.sleep(20)
        await browser.close()

    logger.info("=" * 60)
    logger.info("Si escuchaste audio → bot_sala.py funciona correctamente")
    logger.info("Si no escuchaste   → usa JaaS/8x8.vc en lugar de meet.jit.si")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default = f"https://meet.jit.si/bot-test-{int(time.time())}",
        help    = "URL de la sala Jitsi"
    )
    parser.add_argument("--sin-voz", action="store_true")
    args = parser.parse_args()
    asyncio.run(test_audio_en_jitsi(args.url, usar_voz=not args.sin_voz))