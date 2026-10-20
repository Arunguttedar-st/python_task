from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  PROJECT_NAME: str = "Inventory Management API"
  API_V1_STR: str = "/api/v1"

  MYSQL_USER: str
  MYSQL_PASSWORD: str
  MYSQL_SERVER: str = "localhost"
  MYSQL_PORT: int = 3306
  MYSQL_DB: str

  @property
  def DATABASE_URL(self) -> str:
    return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

  model_config = SettingsConfigDict(
      env_file=".env", env_file_encoding="utf-8", extra="ignore"
  )


settings = Settings()