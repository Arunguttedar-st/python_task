import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically find the inventory_api root directory
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
env_path = os.path.join(BASE_DIR, ".env")

# Explicitly load the .env file using its absolute path
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
  DATABASE_URL: str
  JWT_SECRET_KEY: str
  JWT_ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
  REFRESH_TOKEN_EXPIRE_DAYS: int = 7

  model_config = SettingsConfigDict(
      env_file=env_path, env_file_encoding="utf-8", extra="ignore"
  )


settings = Settings() 