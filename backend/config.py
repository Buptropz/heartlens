from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-2.0-flash"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/heartlens"
    report_ttl_days: int = 30
    rate_limit_per_hour: int = 10
    cors_origins: str = "http://localhost:5173"
    share_domain: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
