from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "TrafficVision AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "x_ciCEUs6WtlWgoGEl4tmPYlzxAidc6Ra2IJ1xMGJXI"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL
    POSTGRES_USER: str = "postgres.xuddradndsordsejahzn"
    POSTGRES_PASSWORD: str = "gkQevQyO6I2V4ZnH"
    POSTGRES_HOST: str = "aws-0-ap-northeast-1.pooler.supabase.com"
    POSTGRES_PORT: int = 6543
    POSTGRES_DB: str = "postgres"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode=require"

    # MongoDB Atlas
    MONGODB_URI: str = "mongodb+srv://nagulworkspace_db_user:QvB0aK6vDdCd5Eic@smarttraffic.bkcbqmr.mongodb.net/?appName=SmartTraffic"
    MONGODB_DB_NAME: str = "smarttraffic"

    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()

