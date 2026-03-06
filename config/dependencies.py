from functools import lru_cache
from config.settings import get_settings

from src.infrastructure.outbound.llm.deepseek_adapter import DeepSeekAdapter
from src.infrastructure.outbound.tts.elevenlabs_adapter import ElevenLabsAdapter
from src.infrastructure.outbound.stt.whisper_adapter import WhisperAdapter
from src.infrastructure.outbound.sala.jitsi_adapter import JitsiAdapter
from src.infrastructure.outbound.pdf.s3_pdf_adapter import S3PDFAdapter
from src.infrastructure.outbound.cache.redis_adapter import RedisAdapter
from src.infrastructure.outbound.llm.gemini_adapter import GeminiAdapter

from src.application.use_cases.crear_clase_use_case import CrearClaseUseCase
from src.application.use_cases.gestionar_duda_use_case import GestionarDudaUseCase
from src.application.use_cases.controlar_sala_use_case import ControlarSalaUseCase
from src.application.use_cases.finalizar_clase_use_case import FinalizarClaseUseCase


# ========================
# ADAPTADORES (singletons)
# ========================

#@lru_cache()
# def get_llm_service() -> DeepSeekAdapter:
#    s = get_settings()
#    return DeepSeekAdapter(
#        api_key  = s.DEEPSEEK_API_KEY,
#       base_url = s.DEEPSEEK_BASE_URL,
#       model    = s.DEEPSEEK_MODEL
#   )
@lru_cache()
def get_llm_service() -> GeminiAdapter:
    s = get_settings()
    return GeminiAdapter(
        api_key = s.GEMINI_API_KEY,
        model   = s.GEMINI_MODEL
    )

@lru_cache()
def get_tts_service() -> ElevenLabsAdapter:
    s = get_settings()
    return ElevenLabsAdapter(
        api_key  = s.ELEVENLABS_API_KEY,
        voice_id = s.ELEVENLABS_VOICE_ID
    )

@lru_cache()
def get_stt_service() -> WhisperAdapter:
    s = get_settings()
    return WhisperAdapter(
        model_size = s.WHISPER_MODEL_SIZE,
        device     = s.WHISPER_DEVICE
    )

@lru_cache()
def get_sala_service() -> JitsiAdapter:
    s = get_settings()
    return JitsiAdapter(
        app_id           = s.JITSI_APP_ID,
        api_key_id       = s.JITSI_API_KEY_ID,
        private_key_path = s.JITSI_PRIVATE_KEY_PATH
    )

@lru_cache()
def get_pdf_service() -> S3PDFAdapter:
    s = get_settings()
    return S3PDFAdapter(
        aws_access_key = s.AWS_ACCESS_KEY_ID,
        aws_secret_key = s.AWS_SECRET_ACCESS_KEY,
        region         = s.AWS_REGION,
        bucket_name    = s.AWS_BUCKET_NAME
    )

@lru_cache()
def get_cache_service() -> RedisAdapter:
    s = get_settings()
    return RedisAdapter(url=s.REDIS_URL)


# ========================
# CASOS DE USO
# ========================

def get_crear_clase_use_case() -> CrearClaseUseCase:
    return CrearClaseUseCase(
        llm_service   = get_llm_service(),
        tts_service   = get_tts_service(),
        sala_service  = get_sala_service(),
        pdf_service   = get_pdf_service(),
        cache_service = get_cache_service()
    )

def get_gestionar_duda_use_case() -> GestionarDudaUseCase:
    return GestionarDudaUseCase(
        llm_service   = get_llm_service(),
        tts_service   = get_tts_service(),
        cache_service = get_cache_service()
    )

def get_controlar_sala_use_case() -> ControlarSalaUseCase:
    return ControlarSalaUseCase(
        sala_service  = get_sala_service(),
        cache_service = get_cache_service()
    )

def get_finalizar_clase_use_case() -> FinalizarClaseUseCase:
    return FinalizarClaseUseCase(
        sala_service  = get_sala_service(),
        cache_service = get_cache_service()
    )