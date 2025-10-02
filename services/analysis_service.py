import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from plugins.manager import PluginManager
from schemas.api import LogEntry, AnalysisResponse
from core.config import settings

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self):
        self.plugin_manager = PluginManager()
    
    async def analyze_log_file(self, filename: str, plugin_names: List[str], parameters: Dict[str, str] = None) -> AnalysisResponse:
        """Анализ файла лога с помощью выбранных плагинов"""
        try:
            # Загружаем файл лога
            log_entries = await self._load_log_file(filename)
            if not log_entries:
                return AnalysisResponse(
                    status="error",
                    plugins_used=[],
                    results={
                        "error": f"Failed to load or parse log file: {filename}",
                        "findings": [],
                        "metrics": {},
                        "total_findings": 0
                    }
                )
            
            # Обнаруживаем плагины
            available_plugins = await self.plugin_manager.discover_plugins()
            
            # Фильтруем запрошенные плагины по доступным
            valid_plugins = [p for p in plugin_names if p in available_plugins]
            
            if not valid_plugins:
                return AnalysisResponse(
                    status="error",
                    plugins_used=[],
                    results={
                        "error": "No valid plugins available for analysis",
                        "findings": [],
                        "metrics": {},
                        "total_findings": 0
                    }
                )
            
            # Запускаем анализ через каждый плагин
            plugin_results = {}
            all_findings = []
            all_metrics = {}
            
            for plugin_name in valid_plugins:
                logger.info(f"Processing with plugin: {plugin_name}")
                result = await self.plugin_manager.process_with_plugin(
                    plugin_name, log_entries, parameters
                )
                
                if result:
                    plugin_results[plugin_name] = result
                    
                    # Добавляем findings с информацией о плагине
                    for finding in result.findings:
                        finding_dict = finding.dict()
                        finding_dict["plugin"] = plugin_name
                        all_findings.append(finding_dict)
                    
                    # Сохраняем метрики
                    all_metrics[plugin_name] = result.metrics
            
            # Агрегируем результаты
            aggregated_results = {
                "findings": all_findings,
                "metrics": all_metrics,
                "total_findings": len(all_findings)
            }
            
            return AnalysisResponse(
                status="success",
                plugins_used=valid_plugins,
                results=aggregated_results
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return AnalysisResponse(
                status="error",
                plugins_used=[],
                results={
                    "error": str(e),
                    "findings": [],
                    "metrics": {},
                    "total_findings": 0
                }
            )
    
    async def _load_log_file(self, filename: str) -> List[LogEntry]:
        """Загрузка и парсинг файла лога"""
        try:
            file_path = Path(settings.LOGS_DIR) / filename
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Парсим JSON лог (каждая строка - JSON объект)
            log_entries = []
            for line in content.split('\n'):
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        entry = LogEntry(
                            level=log_data.get("@level", "info"),
                            message=log_data.get("@message", ""),
                            timestamp=log_data.get("@timestamp", ""),
                            metadata=log_data  # сохраняем все данные как metadata
                        )
                        log_entries.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse log line: {e}")
                        continue
            
            logger.info(f"Loaded {len(log_entries)} log entries from {filename}")
            return log_entries
            
        except Exception as e:
            logger.error(f"Failed to load log file {filename}: {e}")
            return []