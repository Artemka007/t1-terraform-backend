import os
import shutil
from pathlib import Path
from typing import List
import logging

from core.config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.logs_dir = Path(settings.LOGS_DIR)
    
    def get_available_files(self) -> List[str]:
        """Получение списка доступных файлов логов"""
        try:
            if not self.logs_dir.exists():
                self.logs_dir.mkdir(parents=True, exist_ok=True)
                return []
            
            # Ищем только JSON файлы
            files = [
                f.name for f in self.logs_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in ['.json', '.log', '.txt']
            ]
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Failed to get file list: {e}")
            return []
    
    def file_exists(self, filename: str) -> bool:
        """Проверка существования файла"""
        try:
            file_path = self.logs_dir / filename
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def save_uploaded_file(self, file, filename: str) -> bool:
        """Сохранение загруженного файла"""
        try:
            # Создаем безопасное имя файла
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            
            file_path = self.logs_dir / safe_filename
            
            # Сохраняем файл
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"File saved: {safe_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            return False
    
    def delete_file(self, filename: str) -> bool:
        """Удаление файла"""
        try:
            file_path = self.logs_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {filename}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file {filename}: {e}")
            return False