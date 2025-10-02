from concurrent import futures
import grpc
import logging
from datetime import datetime
import re
from typing import List, Dict

from models import plugin_pb2
from models import plugin_pb2_grpc

class ErrorAggregatorService(plugin_pb2_grpc.PluginServiceServicer):
    def __init__(self):
        self.name = "error-aggregator"
        self.version = "1.0.0"
    
    def HealthCheck(self, request, context):
        return plugin_pb2.HealthResponse(
            status="SERVING",
            timestamp=datetime.now().isoformat()
        )
    
    def GetInfo(self, request, context):
        return plugin_pb2.InfoResponse(
            name=self.name,
            version=self.version,
            description="Aggregates and analyzes Terraform errors",
            capabilities=["error_analysis", "pattern_detection", "frequency_analysis"],
            supported_parameters=["min_severity", "group_by_type", "include_warnings"]
        )
    
    def Process(self, request, context):
        try:
            # Анализ ошибок
            error_count = 0
            warning_count = 0
            error_patterns = {}
            
            for entry in request.entries:
                if entry.level == "error":
                    error_count += 1
                    # Анализ паттернов ошибок
                    self._analyze_error_pattern(entry.message, error_patterns)
                elif entry.level == "warning":
                    warning_count += 1
            
            # Создаем findings
            findings = []
            if error_count > 0:
                findings.append(plugin_pb2.Finding(
                    type="HIGH_ERROR_RATE",
                    severity="HIGH",
                    message=f"Found {error_count} errors in Terraform execution",
                    resource="global",
                    recommendations=[
                        "Review Terraform configuration for syntax errors",
                        "Check provider credentials and permissions",
                        "Verify network connectivity to cloud providers"
                    ],
                    metadata={"error_count": str(error_count)}
                ))
            
            # Добавляем findings для частых паттернов
            for pattern, count in error_patterns.items():
                if count > 1:
                    findings.append(plugin_pb2.Finding(
                        type="REPEATED_ERROR_PATTERN",
                        severity="MEDIUM", 
                        message=f"Error pattern '{pattern}' occurred {count} times",
                        resource="global",
                        recommendations=[
                            "Investigate the root cause of this recurring error",
                            "Check resource dependencies and order",
                            "Review variable definitions and types"
                        ],
                        metadata={"pattern": pattern, "occurrences": str(count)}
                    ))
            
            return plugin_pb2.ProcessResponse(
                result=plugin_pb2.AnalysisResult(
                    summary=f"Analyzed {len(request.entries)} log entries, found {error_count} errors",
                    processed_count=len(request.entries),
                    finding_count=len(findings),
                    severity_level="HIGH" if error_count > 0 else "LOW"
                ),
                findings=findings,
                metrics={
                    "total_entries": str(len(request.entries)),
                    "error_count": str(error_count),
                    "warning_count": str(warning_count),
                    "unique_error_patterns": str(len(error_patterns))
                }
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Processing failed: {str(e)}")
            return plugin_pb2.ProcessResponse()
    
    def _analyze_error_pattern(self, message: str, patterns: Dict[str, int]):
        """Анализ паттернов ошибок"""
        common_patterns = [
            (r"timeout", "Timeout occurred"),
            (r"permission denied", "Permission denied"),
            (r"not found", "Resource not found"),
            (r"already exists", "Resource already exists"),
            (r"authentication", "Authentication failed"),
            (r"connection refused", "Connection refused"),
            (r"limit exceeded", "Limit exceeded"),
        ]
        
        for pattern, description in common_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                if description in patterns:
                    patterns[description] += 1
                else:
                    patterns[description] = 1
                break

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    plugin_pb2_grpc.add_PluginServiceServicer_to_server(ErrorAggregatorService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("✅ Error Aggregator plugin started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()