import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI 호환 API 설정
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "claude-opus-4-5-20251101"

    # 데이터 저장 경로
    data_path: str = "/data"

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = ""
        env_file = ".env"


settings = Settings()
