from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rto:rto@localhost:5432/rto"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    sms_provider: str = ""
    sms_api_key: str = ""

    telegram_provider: str = ""
    telegram_bot_token: str = ""

    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "rto-files"


settings = Settings()
