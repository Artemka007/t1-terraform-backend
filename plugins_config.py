from datetime import datetime
import grpc
from concurrent import futures
import logging
from typing import List, Dict, Any
import json

# Конфигурация плагинов
PLUGINS_CONFIG = {
    "error-aggregator": {
        "host": "localhost",
        "port": 50051,
        "description": "Анализатор ошибок и паттернов",
        "capabilities": ["error_analysis", "pattern_detection"]
    },
    "security-scanner": {
        "host": "localhost", 
        "port": 50052,
        "description": "Сканер безопасности и чувствительных данных",
        "capabilities": ["security_scanning", "sensitive_data_detection"]
    },
    "performance-analyzer": {
        "host": "localhost",
        "port": 50053, 
        "description": "Анализатор производительности",
        "capabilities": ["performance_analysis", "bottleneck_detection"]
    }
}

class PluginClient:
    def __init__(self, plugin_name: str, config: dict):
        self.name = plugin_name
        self.config = config
        self.endpoint = f"{config['host']}:{config['port']}"
        self.channel = None
        self.stub = None
        
    def connect(self):
        """Установка соединения с плагином"""
        try:
            self.channel = grpc.insecure_channel(self.endpoint)
            # Здесь будет stub после генерации gRPC кода
            # self.stub = plugin_pb2_grpc.PluginServiceStub(self.channel)
            return True
        except Exception as e:
            print(f"Failed to connect to plugin {self.name}: {e}")
            return False
    
    def health_check(self):
        """Проверка здоровья плагина"""
        try:
            # Заглушка для демонстрации
            return {"status": "SERVING", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"status": "NOT_SERVING", "error": str(e)}
    
    def process_logs(self, log_entries: List[Dict]) -> Dict:
        """Обработка логов через плагин"""
        try:
            # Заглушка для демонстрации - возвращаем mock данные
            if self.name == "error-aggregator":
                return self._mock_error_analysis(log_entries)
            elif self.name == "security-scanner":
                return self._mock_security_analysis(log_entries)
            else:
                return self._mock_generic_analysis(log_entries)
        except Exception as e:
            return {"error": f"Plugin processing failed: {str(e)}"}
    
    def _mock_error_analysis(self, log_entries: List[Dict]) -> Dict:
        """Mock анализ ошибок"""
        error_count = sum(1 for entry in log_entries if entry.get('level') == 'error')
        
        findings = []
        if error_count > 0:
            findings.append({
                "type": "HIGH_ERROR_RATE",
                "severity": "HIGH", 
                "message": f"Найдено {error_count} ошибок в логах",
                "resource": "global",
                "recommendations": [
                    "Проверьте конфигурацию Terraform",
                    "Убедитесь в правильности credentials",
                    "Проверьте сетевые настройки"
                ]
            })
        
        return {
            "result": {
                "summary": f"Проанализировано {len(log_entries)} записей логов",
                "processed_count": len(log_entries),
                "finding_count": len(findings),
                "severity_level": "HIGH" if findings else "LOW"
            },
            "findings": findings,
            "metrics": {
                "total_entries": str(len(log_entries)),
                "error_count": str(error_count),
                "warning_count": str(sum(1 for entry in log_entries if entry.get('level') == 'warning'))
            }
        }
    
    def _mock_security_analysis(self, log_entries: List[Dict]) -> Dict:
        """Mock security анализ"""
        findings = []
        
        # Проверяем на чувствительные данные
        sensitive_patterns = ["password", "secret", "key", "token", "credential"]
        for entry in log_entries:
            message = entry.get('message', '').lower()
            if any(pattern in message for pattern in sensitive_patterns):
                findings.append({
                    "type": "SENSITIVE_DATA_EXPOSURE",
                    "severity": "CRITICAL",
                    "message": "Обнаружены потенциально чувствительные данные в логах",
                    "resource": "global", 
                    "recommendations": [
                        "Удалите чувствительные данные из логов",
                        "Используйте переменные окружения для секретов",
                        "Настройте фильтры логирования"
                    ]
                })
                break
        
        return {
            "result": {
                "summary": f"Security анализ {len(log_entries)} записей",
                "processed_count": len(log_entries),
                "finding_count": len(findings),
                "severity_level": "CRITICAL" if findings else "LOW"
            },
            "findings": findings,
            "metrics": {
                "scanned_entries": str(len(log_entries)),
                "security_findings": str(len(findings)),
                "sensitive_patterns": str(len(sensitive_patterns))
            }
        }
    
    def _mock_generic_analysis(self, log_entries: List[Dict]) -> Dict:
        """Mock общий анализ"""
        return {
            "result": {
                "summary": f"Общий анализ {len(log_entries)} записей",
                "processed_count": len(log_entries),
                "finding_count": 0,
                "severity_level": "LOW"
            },
            "findings": [],
            "metrics": {
                "processed_entries": str(len(log_entries)),
                "plugin": self.name
            }
        }

