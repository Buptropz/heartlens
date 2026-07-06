from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/heartlens"
    report_ttl_days: int = 30
    rate_limit_per_hour: int = 10
    cors_origins: str = "http://localhost:5173"
    share_domain: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
