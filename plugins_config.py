from datetime import datetime
import time
import grpc
from concurrent import futures
import logging
from typing import List, Dict, Any
import json

from plugins.models import plugin_pb2, plugin_pb2_grpc

# Конфигурация плагинов

# Конфигурация плагинов
PLUGINS_CONFIG = {
    "error-aggregator": {
        "host": "error-aggregator",
        "port": 50051,
        "description": "Анализатор ошибок и паттернов",
        "capabilities": ["error_analysis", "pattern_detection"]
    },
    "security-scanner": {
        "host": "security-scanner", 
        "port": 50052,
        "description": "Сканер безопасности и чувствительных данных",
        "capabilities": ["security_scanning", "sensitive_data_detection"]
    },
    "performance-analyzer": {
        "host": "performance-analyzer",
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
        self.connected = False
        self.last_health_check = None
        
    def connect(self) -> bool:
        """Установка соединения с плагином"""
        try:
            self.channel = grpc.insecure_channel(self.endpoint)
            self.stub = plugin_pb2_grpc.PluginServiceStub(self.channel)
            
            # Проверяем соединение
            health_response = self.health_check()
            self.connected = health_response.get('status') == 'SERVING'
            
            if self.connected:
                logging.info(f"✅ Successfully connected to plugin {self.name} at {self.endpoint}")
            else:
                logging.warning(f"⚠️ Plugin {self.name} is not serving")
                
            return self.connected
            
        except Exception as e:
            logging.error(f"❌ Failed to connect to plugin {self.name}: {e}")
            self.connected = False
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья плагина"""
        try:
            if not self.stub:
                return {"status": "NOT_CONNECTED", "error": "Stub not initialized"}
            
            request = plugin_pb2.HealthRequest()
            response = self.stub.HealthCheck(request, timeout=5.0)
            
            self.last_health_check = datetime.now()
            return {
                "status": response.status,
                "timestamp": response.timestamp,
                "plugin": self.name
            }
            
        except grpc.RpcError as e:
            error_status = self._grpc_error_to_status(e)
            return {
                "status": error_status,
                "error": str(e),
                "plugin": self.name
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "plugin": self.name
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Получение информации о плагине"""
        try:
            if not self.stub:
                return {"error": "Plugin not connected"}
            
            request = plugin_pb2.InfoRequest()
            response = self.stub.GetInfo(request, timeout=5.0)
            
            return {
                "name": response.name,
                "version": response.version,
                "description": response.description,
                "capabilities": list(response.capabilities),
                "supported_parameters": list(response.supported_parameters),
                "plugin": self.name
            }
            
        except grpc.RpcError as e:
            return {
                "error": f"gRPC error: {e.details()}",
                "code": e.code().name,
                "plugin": self.name
            }
        except Exception as e:
            return {
                "error": str(e),
                "plugin": self.name
            }
    
    def process_logs(self, log_entries: List[Dict], parameters: Dict[str, str] = None) -> Dict[str, Any]:
        """Обработка логов через плагин"""
        try:
            if not self.stub:
                return {"error": "Plugin not connected"}
            
            if parameters is None:
                parameters = {}
            
            # Конвертируем log_entries в gRPC сообщения
            entries_proto = []
            for entry in log_entries:
                # Создаем metadata как dict
                metadata = {}
                if 'metadata' in entry and isinstance(entry['metadata'], dict):
                    metadata = {str(k): str(v) for k, v in entry['metadata'].items()}
                
                entry_proto = plugin_pb2.LogEntry(
                    level=str(entry.get('level', 'info')),
                    message=str(entry.get('message', '')),
                    timestamp=str(entry.get('timestamp', '')),
                    metadata=metadata
                )
                entries_proto.append(entry_proto)
            
            # Создаем запрос
            request = plugin_pb2.ProcessRequest(
                entries=entries_proto,
                parameters={str(k): str(v) for k, v in parameters.items()}
            )
            
            # Вызываем плагин с таймаутом
            start_time = time.time()
            response = self.stub.Process(request, timeout=30.0)
            processing_time = time.time() - start_time
            
            # Конвертируем ответ в словарь
            findings = []
            for finding in response.findings:
                finding_dict = {
                    "type": finding.type,
                    "severity": finding.severity,
                    "message": finding.message,
                    "resource": finding.resource,
                    "recommendations": list(finding.recommendations),
                    "metadata": dict(finding.metadata)
                }
                findings.append(finding_dict)
            
            result = {
                "result": {
                    "summary": response.result.summary,
                    "processed_count": response.result.processed_count,
                    "finding_count": response.result.finding_count,
                    "severity_level": response.result.severity_level
                },
                "findings": findings,
                "metrics": dict(response.metrics)
            }
            
            # Добавляем метрики производительности
            result["metrics"]["processing_time_seconds"] = str(round(processing_time, 3))
            result["metrics"]["entries_processed"] = str(len(log_entries))
            
            logging.info(f"✅ Plugin {self.name} processed {len(log_entries)} entries in {processing_time:.3f}s")
            
            return result
            
        except grpc.RpcError as e:
            error_info = self._grpc_error_to_dict(e)
            logging.error(f"❌ gRPC error from plugin {self.name}: {error_info}")
            return {
                "error": f"gRPC error: {e.details()}",
                "grpc_code": e.code().name,
                "plugin": self.name
            }
        except Exception as e:
            logging.error(f"❌ Error processing logs with plugin {self.name}: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return {
                "error": str(e),
                "plugin": self.name
            }
    def _grpc_error_to_status(self, error: grpc.RpcError) -> str:
        """Конвертация gRPC ошибки в статус"""
        error_codes = {
            grpc.StatusCode.UNAVAILABLE: "UNAVAILABLE",
            grpc.StatusCode.DEADLINE_EXCEEDED: "TIMEOUT",
            grpc.StatusCode.UNIMPLEMENTED: "UNIMPLEMENTED",
            grpc.StatusCode.INTERNAL: "INTERNAL_ERROR",
        }
        return error_codes.get(error.code(), "UNKNOWN_ERROR")
    
    def _grpc_error_to_dict(self, error: grpc.RpcError) -> Dict[str, Any]:
        """Конвертация gRPC ошибки в словарь"""
        return {
            "code": error.code().name,
            "details": error.details(),
            "trailing_metadata": dict(error.trailing_metadata()) if error.trailing_metadata() else {}
        }
    
    def close(self):
        """Закрытие соединения"""
        if self.channel:
            self.channel.close()
            self.connected = False
            logging.info(f"Closed connection to plugin {self.name}")