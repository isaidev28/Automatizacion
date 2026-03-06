from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # ========================
    # FLASK
    # ========================
    FLASK_ENV:    str = "development"
    FLASK_DEBUG:  bool = True
    SECRET_KEY:   str = "cambia_esto_en_produccion"

    # ========================
    # REDIS
    # ========================
    REDIS_URL: str = "redis://localhost:6379/0"

    # ========================
    # JITSI JaaS
    # ========================
    JITSI_APP_ID:          str = ""
    JITSI_API_KEY_ID:      str = ""
    JITSI_PRIVATE_KEY_PATH: str = "./config/jitsi_private_key.pem"
    JITSI_BASE_URL:        str = "https://8x8.vc"

    # ========================
    # AWS S3
    # ========================
    AWS_ACCESS_KEY_ID:     str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION:            str = "us-east-1"
    AWS_BUCKET_NAME:       str = ""

    # ========================
    # LLM
    # ========================
    LLM_PROVIDER:     str = "deepseek"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL:   str = "deepseek-chat"
    #Modelo usado actualmente
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-04-17"

    # ========================
    # ELEVENLABS
    # ========================
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # ========================
    # WHISPER LOCAL
    # ========================
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE:     str = "cpu"

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        case_sensitive    = True
        extra             = "ignore" 


@lru_cache()
def get_settings() -> Settings:
    return Settings()