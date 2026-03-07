import asyncio
import logging
import numpy as np
import sounddevice as sd
import io
import wave
import struct
import base64
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_INIT_SCRIPT = """
(function() {
    const FAKE_DEVICE_ID = 'bot-synthetic-audio-stream';

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

        // Nodo de silencio permanente — mantiene el MediaStream vivo en Jitsi
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
                console.log('[BotSala] Reproduciendo audio, duracion:', buf.duration.toFixed(2), 's');
                source.onended = function() {
                    window._isPlaying = false;
                    window._playNext();
                };
            } catch(e) {
                console.error('[BotSala] Error decodificando audio:', e);
                window._isPlaying = false;
                window._playNext();
            }
        };

        console.log('[BotSala] AudioContext creado (sampleRate=16000)');
        return { ctx: _ctx, dest: _dest };
    }

    // ── Inyectar nuestro dispositivo en la lista de Jitsi ────────────────────
    // Sin esto Jitsi elige "Mezcla estéreo" y nunca usa el stream del bot.
    const origEnumerate = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
    navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await origEnumerate();
        const fakeDevice = {
            deviceId : FAKE_DEVICE_ID,
            groupId  : 'bot-group',
            kind     : 'audioinput',
            label    : 'Bot Synthetic Microphone',
            toJSON   : () => ({
                deviceId : FAKE_DEVICE_ID,
                groupId  : 'bot-group',
                kind     : 'audioinput',
                label    : 'Bot Synthetic Microphone',
            }),
        };
        console.log('[BotSala] enumerateDevices — inyectando Bot Synthetic Microphone');
        // Poner el dispositivo falso primero para que Jitsi lo elija por defecto
        return [fakeDevice, ...devices.filter(d => d.kind !== 'audioinput')];
    };

    // ── Interceptar getUserMedia — siempre devolver stream sintético ─────────
    const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        if (!constraints || !constraints.audio) {
            return origGetUserMedia(constraints);
        }
        const { dest } = _getOrCreateContext();
        console.log('[BotSala] getUserMedia interceptado -> stream sintetico');
        return dest.stream;
    };

    // ── Forzar deviceId en localStorage antes de que Jitsi lo lea ───────────
    try {
        localStorage.setItem('audioDeviceId', FAKE_DEVICE_ID);
        localStorage.setItem('userSelectedAudioInput', JSON.stringify({
            deviceId : FAKE_DEVICE_ID,
            label    : 'Bot Synthetic Microphone',
        }));
    } catch(e) {}

    console.log('[BotSala] Interceptor instalado — FAKE_DEVICE_ID:', FAKE_DEVICE_ID);
})();
"""


class BotSala:

    def __init__(self, stt_service, tts_service, llm_service, cache_service,
                 sample_rate: int = 16000, chunk_duration: float = 3.0):
        self._stt         = stt_service
        self._tts         = tts_service
        self._llm         = llm_service
        self._cache       = cache_service
        self._sample_rate = sample_rate
        self._chunk_size  = int(sample_rate * chunk_duration)
        self._activo      = False
        self._page        = None

    # ──────────────────────────────────────────────────────────────────────────
    # Audio local (VB-Cable) — solo se usa si no hay página activa
    # ──────────────────────────────────────────────────────────────────────────

    def _obtener_dispositivos_cable(self):
        dispositivos = sd.query_devices()
        cable_input  = None
        cable_output = None
        for i, d in enumerate(dispositivos):
            nombre = d["name"]
            if "CABLE Input (VB-Audio Virtual Cable)" in nombre:
                if d["max_output_channels"] > 0 and cable_input is None:
                    cable_input = i
            if "CABLE Output (VB-Audio Virtual Cable)" in nombre:
                if d["max_input_channels"] > 0 and cable_output is None:
                    cable_output = i
        logger.info(f"CABLE Input  (reproducir): índice {cable_input}")
        logger.info(f"CABLE Output (capturar):   índice {cable_output}")
        return cable_input, cable_output

    def _bytes_a_numpy(self, audio_bytes: bytes) -> np.ndarray:
        try:
            import miniaudio
            decoded = miniaudio.decode(
                audio_bytes,
                output_format = miniaudio.SampleFormat.SIGNED16,
                nchannels     = 1,
                sample_rate   = self._sample_rate
            )
            samples = np.frombuffer(decoded.samples, dtype=np.int16)
            return samples.astype(np.float32) / 32768.0
        except Exception as e:
            logger.exception(f"Error convirtiendo audio: {e}")
            return np.zeros(1024, dtype=np.float32)

    def _reproducir_audio(self, audio_bytes: bytes):
        try:
            cable_input, _ = self._obtener_dispositivos_cable()
            if cable_input is None:
                logger.error("CABLE Input no encontrado")
                return
            audio_array = self._bytes_a_numpy(audio_bytes)
            sd.play(audio_array, samplerate=self._sample_rate, device=cable_input)
            sd.wait()
        except Exception as e:
            logger.exception(f"Error reproduciendo audio: {e}")

    def _capturar_audio(self) -> bytes:
        try:
            # CAMBIA ESTO: Usa CABLE Output, NO Mezcla estéreo
            _, cable_output = self._obtener_dispositivos_cable()
            
            if cable_output is None:
                logger.error("CABLE Output no encontrado")
                return b""
            
            logger.info(f"Capturando desde CABLE Output (índice {cable_output})...")
            audio = sd.rec(
                self._chunk_size,
                samplerate=self._sample_rate,
                channels=1,
                dtype=np.int16,
                device=cable_output,  # ← Cambiado de mezcla_index a cable_output
            )
            sd.wait()
            
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._sample_rate)
                wf.writeframes(audio.tobytes())
            return buffer.getvalue()
            
        except Exception as e:
            logger.exception(f"Error capturando audio: {e}")
            return b""
    # ──────────────────────────────────────────────────────────────────────────
    # Inyección de audio en página Jitsi
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _duracion_wav(audio_bytes: bytes) -> float:
        try:
            data_size = struct.unpack_from('<I', audio_bytes, 40)[0]
            byte_rate = struct.unpack_from('<I', audio_bytes, 28)[0]
            return data_size / byte_rate
        except Exception:
            return len(audio_bytes) / (16000 * 2)

    async def _inyectar_audio_en_pagina(self, page, audio_bytes: bytes):
        try:
            # 1. Inyectar en la página (para que otros participantes escuchen)
            b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await page.evaluate("""
                (b64) => {
                    window._audioQueue.push(b64);
                    if (window._playNext) window._playNext();
                }
            """, b64)
            
            # 2. REPRODUCIR LOCALMENTE (para que TÚ escuches)
            try:
                cable_input, _ = self._obtener_dispositivos_cable()
                if cable_input is not None:
                    audio_array = self._bytes_a_numpy(audio_bytes)
                    # Reproducir en paralelo sin esperar
                    sd.play(audio_array, samplerate=self._sample_rate, device=cable_input)
                    logger.info(f"🔊 Audio local reproduciendo en CABLE Input ({len(audio_bytes)} bytes)")
                else:
                    logger.warning("CABLE Input no encontrado, no se reproduce localmente")
            except Exception as e:
                logger.warning(f"Error reproduciendo audio local: {e}")
            
            duracion = self._duracion_wav(audio_bytes)
            logger.info(f"Audio inyectado en página ({len(audio_bytes)} bytes, {duracion:.1f}s)")
            await asyncio.sleep(duracion + 0.3)
            
        except Exception as e:
            logger.exception(f"Error inyectando audio: {e}")
    # ──────────────────────────────────────────────────────────────────────────
    # Loop principal de escucha
    # ──────────────────────────────────────────────────────────────────────────

    async def _loop_escucha(self, clase_id: str):
        logger.info(f"=== LOOP ESCUCHA INICIADO — clase {clase_id} ===")

        while self._activo:
            try:
                logger.info("Capturando audio del alumno...")
                audio_bytes = await asyncio.to_thread(self._capturar_audio)

                if not audio_bytes:
                    logger.warning("Audio vacío, reintentando...")
                    await asyncio.sleep(0.5)
                    continue

                logger.info(f"Audio capturado ({len(audio_bytes)} bytes), transcribiendo...")
                transcripcion = await self._stt.transcribir(audio_bytes)

                if not transcripcion or len(transcripcion.strip()) < 3:
                    logger.info("Sin voz detectada, continuando...")
                    continue

                logger.info(f"Alumno dijo: {transcripcion}")

                sesion = await self._cache.obtener_sesion(clase_id)
                if not sesion:
                    logger.warning("Sesión no encontrada en Redis")
                    continue

                respuesta = await self._llm.responder_duda(
                    pregunta      = transcripcion,
                    contenido_pdf = sesion.get("pdf_texto", ""),
                    historial     = sesion.get("historial", []),
                )
                logger.info(f"IA responde: {respuesta[:80]}...")

                audio_respuesta = await self._tts.sintetizar(respuesta[:400])

                if self._page:
                    await self._inyectar_audio_en_pagina(self._page, audio_respuesta)
                else:
                    await asyncio.to_thread(self._reproducir_audio, audio_respuesta)

                sesion["historial"].append({"role": "user",      "content": transcripcion})
                sesion["historial"].append({"role": "assistant",  "content": respuesta})
                await self._cache.guardar_sesion(clase_id, sesion)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error en loop: {e}")
                await asyncio.sleep(1)

        logger.info(f"Bot detenido — clase {clase_id}")

    # ──────────────────────────────────────────────────────────────────────────
    # Esperar alumno
    # ──────────────────────────────────────────────────────────────────────────

    async def _esperar_alumno(self, page, clase_id: str, timeout: int = 300) -> bool:
        logger.info("Esperando que el alumno entre a la sala...")
        inicio = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - inicio < timeout:
            try:
                participantes = await page.evaluate("""
                    () => {
                        const remote = document.querySelectorAll('[class*="remote"]').length;
                        const byId   = Array.from(document.querySelectorAll('*'))
                            .filter(el => el.id.match(/^participant_[a-f0-9]+$/))
                            .length;
                        return Math.max(remote, byId);
                    }
                """)
                if participantes > 0:
                    logger.info(f"¡Alumno detectado! ({participantes} participante(s))")
                    return True
            except Exception as e:
                logger.warning(f"Error verificando participantes: {e}")
            await asyncio.sleep(2)
        logger.warning(f"Timeout esperando alumno ({timeout}s)")
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # Entrar / salir sala
    # ──────────────────────────────────────────────────────────────────────────

    async def entrar_sala(self, link_supervisor: str, clase_id: str,
                          audio_introduccion: bytes = None):
        self._activo = True
        logger.info("=== BOT INICIANDO ===")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless = False,
                    args     = [
                        "--use-fake-ui-for-media-stream",
                        "--use-fake-device-for-media-stream",  # evita que Chromium use micros reales
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

                # Inyectar interceptor ANTES de cargar la página
                await page.add_init_script(_INIT_SCRIPT)

                logger.info("Navegando a sala...")
                await page.goto(link_supervisor, timeout=30000)
                await page.wait_for_timeout(3000)

                # Unirse a la reunión
                try:
                    join_btn = page.locator('button', has_text="Join meeting").first
                    await join_btn.wait_for(timeout=8000)
                    await join_btn.click()
                    logger.info("Bot entró a la sala")
                except Exception:
                    try:
                        await page.click('[data-testid="prejoin.joinMeeting"]', timeout=5000)
                        logger.info("Bot entró (selector 2)")
                    except Exception as e:
                        logger.warning(f"No pudo hacer clic en Join: {e}")

                await page.wait_for_timeout(5000)
                self._page = page
                logger.info("Bot en sala, esperando alumno...")

                alumno_entro = await self._esperar_alumno(page, clase_id)

                if alumno_entro:
                    sesion        = await self._cache.obtener_sesion(clase_id)
                    nombre_alumno = sesion.get("nombre_alumno", "estudiante") if sesion else "estudiante"

                    logger.info("Generando saludo de bienvenida...")
                    saludo = await self._llm.generar_saludo(
                        nombre_alumno   = nombre_alumno,
                        nombre_profesor = sesion.get("nombre_profesor", "Profesor"),
                        tema_pdf        = sesion.get("pdf_temas", ["el tema de hoy"])[0] if sesion else "el tema de hoy"
                    )
                    logger.info(f"Saludo: {saludo}")

                    try:
                        audio_saludo = await self._tts.sintetizar(saludo[:400])
                        await self._inyectar_audio_en_pagina(page, audio_saludo)
                    except Exception as e:
                        logger.warning(f"TTS saludo falló: {e}")

                    if sesion:
                        sesion.setdefault("historial", []).append(
                            {"role": "assistant", "content": saludo}
                        )
                        await self._cache.guardar_sesion(clase_id, sesion)

                logger.info("Iniciando loop de escucha...")
                await self._loop_escucha(clase_id)

        except Exception as e:
            logger.exception(f"=== ERROR EN BOT: {e} ===")
        finally:
            self._page = None

    async def salir_sala(self):
        self._activo = False
        self._page   = None
        logger.info("Bot saliendo de la sala")