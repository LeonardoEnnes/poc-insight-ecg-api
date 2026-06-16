from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"
    AI_PROVIDER: str = "gemini"
    AI_API_KEY: str = "" 
    AI_MODEL_NAME: str 
    IF_API: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()