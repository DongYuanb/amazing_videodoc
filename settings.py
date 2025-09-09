#!/usr/bin/env python3
"""Centralized application settings using pydantic-settings.
- Supports deployment modes via .env: DEPLOYMENT_MODE=local|production
- Computes API base URL and CORS based on env
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    # Deployment
    DEPLOYMENT_MODE: str = Field(default="local")  # local | production
    SERVER_HOST: str = Field(default="0.0.0.0")
    SERVER_PORT: int = Field(default=8001)
    API_BASE_URL: str | None = None  # override public URL, e.g. https://api.example.com
    FRONTEND_URL: str | None = None  # for CORS in production
    # Core model & API providers
    MODEL_ID: str = Field(default="mistralai/ministral-8b")
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    COHERE_API_KEY: str | None = None
    TENCENT_APPID: str | None = None
    TENCENT_SECRET_ID: str | None = None
    TENCENT_SECRET_KEY: str | None = None
    # System paths and tools
    FFMPEG_PATH: str = Field(default="ffmpeg")
    # Upload policy
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_EXTS: List[str] = Field(default_factory=lambda: ["mp4","avi","mov","mkv","webm"])
    # Progress weights
    PROGRESS_WEIGHTS: Dict[str, float] = Field(default_factory=lambda: {
        "extract_audio":0.10,
        "asr":0.20,
        "merge_text":0.20,
        "summary":0.20,
        "multimodal":0.30,
    })
    # ASR progress estimate (X=processing speed vs audio duration)
    ASR_PROGRESS_SPEED_X: float = 6.0
    ASR_PROGRESS_MIN_SECS: float = 8.0
    # Multimodal defaults
    MULTIMODAL_FRAME_FPS: float = 0.2
    MULTIMODAL_SIMILARITY_THRESHOLD: float = 0.9
    MULTIMODAL_MAX_CONCURRENT_SEGMENTS: int = 5
    MULTIMODAL_ENABLE_TEXT_ALIGNMENT: bool = True
    MULTIMODAL_MAX_ALIGNED_FRAMES: int = 3
    MULTIMODAL_EMBED_MODEL: str = "embed-v4.0"
    MULTIMODAL_BATCH_SIZE: int = 24
    MULTIMODAL_API_DELAY: float = 0.1

    @property
    def public_api_base_url(self) -> str:
        if self.API_BASE_URL:
            return self.API_BASE_URL.rstrip("/")
        if self.DEPLOYMENT_MODE == "local":
            return f"http://localhost:{self.SERVER_PORT}"
        return "/"  # same-origin by default when served behind reverse proxy


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

