from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Настройки приложения"""
    APP_NAME: str = "Terraform Plugin Analyzer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # CORS настройки
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Настройки плагинов
    PLUGINS: dict = {
        "error-aggregator": "localhost:50051",
        "security-scanner": "localhost:50052",
        "cost-analyzer": "localhost:50053",
    }
    
    # Настройки файлов
    LOGS_DIR: str = "logs"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"

settings = Settings()

# Создаем директорию для логов если не существует
os.makedirs(settings.LOGS_DIR, exist_ok=True)