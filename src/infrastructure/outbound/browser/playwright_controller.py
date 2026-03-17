import asyncio
import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

_INIT_SCRIPT = """
(function() {
    const FAKE_DEVICE_ID = 'bot-synthetic-audio-stream';
    let _ctx  = null;
    let _dest = null;

    window._audioQueue     = [];
    window._isPlaying      = false;
    window._remoteChunks   = [];
    window._remoteRecorder = null;

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

        window._remoteDest = _ctx.createMediaStreamDestination();

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
                source.onended = function() {
                    window._isPlaying = false;
                    window._playNext();
                };
            } catch(e) {
                window._isPlaying = false;
                window._playNext();
            }
        };

        window._stopAudio = function() {
            window._audioQueue = [];
            window._isPlaying  = false;
            try {
                if (_ctx) {
                    _ctx.suspend();
                    setTimeout(() => _ctx.resume(), 100);
                }
            } catch(e) {}
            console.log('[BotSala] Audio detenido');
        };

        window._remoteActivo = false;
        window._iniciarDetectorVoz = function() {
            if (!window._audioContext) return;
            const ctx = window._audioContext;
            const conectarAudios = () => {
                const audios = Array.from(document.querySelectorAll('audio'));
                audios.forEach(audio => {
                    if (audio._botConectado) return;
                    if (!audio.srcObject) return;
                    const tracks = Array.from(audio.srcObject.getAudioTracks());
                    const esRemoto = tracks.some(t => t.label !== 'Bot Synthetic Microphone');
                    if (!esRemoto) return;
                    try {
                        const src      = ctx.createMediaStreamSource(audio.srcObject);
                        const analyser = ctx.createAnalyser();
                        analyser.fftSize = 512;
                        src.connect(analyser);
                        const data = new Uint8Array(analyser.frequencyBinCount);
                        setInterval(() => {
                            analyser.getByteFrequencyData(data);
                            const avg = data.reduce((a, b) => a + b, 0) / data.length;
                            if (avg > 8) window._remoteActivo = true;
                        }, 100);
                        audio._botConectado = true;
                        console.log('[BotSala] Audio DOM conectado al detector');
                    } catch(e) {
                        console.error('[BotSala] Error conectando audio DOM:', e);
                    }
                });
            };
            conectarAudios();
            setInterval(conectarAudios, 2000);
            setInterval(() => { window._remoteActivo = false; }, 300);
            console.log('[BotSala] Detector de voz DOM iniciado');
        };

        console.log('[BotSala] AudioContext creado');
        return { ctx: _ctx, dest: _dest };
    }

    const origEnumerate = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
    navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await origEnumerate();
        const fakeDevice = {
            deviceId: FAKE_DEVICE_ID, groupId: 'bot-group',
            kind: 'audioinput', label: 'Bot Synthetic Microphone',
            toJSON: () => ({ deviceId: FAKE_DEVICE_ID, groupId: 'bot-group', kind: 'audioinput', label: 'Bot Synthetic Microphone' }),
        };
        return [fakeDevice, ...devices.filter(d => d.kind !== 'audioinput')];
    };

    const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        if (!constraints || !constraints.audio) return origGetUserMedia(constraints);
        const { dest } = _getOrCreateContext();
        console.log('[BotSala] getUserMedia -> stream sintetico');
        return dest.stream;
    };

    const OrigRTC = window.RTCPeerConnection;
    window.RTCPeerConnection = function(...args) {
        const pc = new OrigRTC(...args);
        pc.addEventListener('track', (event) => {
            if (event.track.kind !== 'audio') return;
            const { ctx } = _getOrCreateContext();
            const stream = event.streams[0] || new MediaStream([event.track]);
            try {
                const src = ctx.createMediaStreamSource(stream);
                src.connect(window._remoteDest);
                console.log('[BotSala] Track remoto conectado a remoteDest');
                if (!window._detectorIniciado) {
                    window._detectorIniciado = true;
                    setTimeout(() => window._iniciarDetectorVoz(), 1000);
                }
            } catch(e) {
                console.error('[BotSala] Error conectando track remoto:', e);
            }
        });
        return pc;
    };
    Object.assign(window.RTCPeerConnection, OrigRTC);
    window.RTCPeerConnection.prototype = OrigRTC.prototype;

    try { localStorage.setItem('audioDeviceId', FAKE_DEVICE_ID); } catch(e) {}
    console.log('[BotSala] Interceptor RTCPeerConnection instalado');
})();
"""


class PlaywrightController:
    """Responsabilidad: gestionar el ciclo de vida del navegador y la página Jitsi."""

    BROWSER_ARGS = [
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-features=WebRtcVadSuppression",
    ]

    def __init__(self):
        self._playwright = None
        self._browser:   Browser        = None
        self._context:   BrowserContext = None
        self.page:       Page           = None

    async def iniciar(self, url: str) -> Page:
        """Lanza el navegador, inyecta el script e ingresa a la URL."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=self.BROWSER_ARGS,
        )
        self._context = await self._browser.new_context(
            permissions=["microphone", "camera"],
            ignore_https_errors=True,
        )
        self.page = await self._context.new_page()
        await self.page.add_init_script(_INIT_SCRIPT)

        logger.info(f"Navegando a: {url}")
        await self.page.goto(url, timeout=30000)
        await self.page.wait_for_timeout(3000)
        return self.page

    async def unirse_a_sala(self) -> bool:
        """Hace clic en el botón de unirse. Retorna True si tuvo éxito."""
        try:
            join_btn = self.page.locator('button', has_text="Join meeting").first
            await join_btn.wait_for(timeout=8000)
            await join_btn.click()
            logger.info("Bot entró a la sala (selector 1)")
            return True
        except Exception:
            try:
                await self.page.click('[data-testid="prejoin.joinMeeting"]', timeout=5000)
                logger.info("Bot entró a la sala (selector 2)")
                return True
            except Exception as e:
                logger.warning(f"No pudo hacer clic en Join: {e}")
                return False

    async def iniciar_detector_voz(self):
        """Activa el AnalyserNode para detectar voz remota."""
        await self.page.evaluate("""
            () => {
                if (window._iniciarDetectorVoz && !window._detectorIniciado) {
                    window._detectorIniciado = true;
                    window._iniciarDetectorVoz();
                }
            }
        """)
        logger.info("Detector de voz iniciado")

    async def cerrar(self):
        """Cierra navegador y playwright."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error cerrando navegador: {e}")
        finally:
            self.page    = None
            self._browser = None