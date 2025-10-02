from concurrent import futures
import grpc
import logging
from datetime import datetime
import re
from typing import List, Dict

from models import plugin_pb2
from models import plugin_pb2_grpc

class PerformanceAnalyzerService(plugin_pb2_grpc.PluginServiceServicer):
    def __init__(self):
        self.name = "performance-analyzer"
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
            description="Analyzes performance issues and bottlenecks",
            capabilities=["performance_analysis", "bottleneck_detection", "resource_optimization"],
            supported_parameters=["threshold_ms", "check_bottlenecks", "optimize_resources"]
        )
    
    def Process(self, request, context):
        try:
            findings = []
            slow_operations = 0
            resource_intensive_ops = 0
            
            # Анализируем временные метки для поиска медленных операций
            timestamps = []
            for entry in request.entries:
                if entry.timestamp:
                    try:
                        # Парсим timestamp (упрощенная версия)
                        if 'T' in entry.timestamp:
                            timestamps.append(entry.timestamp)
                    except:
                        pass
            
            # Анализ ресурсоемких операций
            for entry in request.entries:
                message = entry.message.lower()
                
                # Поиск медленных операций
                if any(word in message for word in ["slow", "timeout", "long", "bottleneck", "waiting"]):
                    slow_operations += 1
                    findings.append(plugin_pb2.Finding(
                        type="PERFORMANCE_BOTTLENECK",
                        severity="MEDIUM",
                        message="Potential performance bottleneck detected",
                        resource=entry.metadata.get("resource", "unknown"),
                        recommendations=[
                            "Optimize resource configuration",
                            "Check for network latency issues",
                            "Review dependency chains",
                            "Consider resource scaling"
                        ],
                        metadata={"operation": message[:50] + "..." if len(message) > 50 else message}
                    ))
                
                # Поиск ресурсоемких операций
                if any(word in message for word in ["large", "big", "memory", "cpu", "expensive"]):
                    resource_intensive_ops += 1
            
            # Если нашли много медленных операций
            if slow_operations > 3:
                findings.append(plugin_pb2.Finding(
                    type="MULTIPLE_PERFORMANCE_ISSUES",
                    severity="HIGH",
                    message=f"Found {slow_operations} potential performance issues",
                    resource="global",
                    recommendations=[
                        "Conduct comprehensive performance review",
                        "Optimize Terraform configuration",
                        "Consider parallel execution where possible",
                        "Review provider-specific performance guides"
                    ]
                ))
            
            return plugin_pb2.ProcessResponse(
                result=plugin_pb2.AnalysisResult(
                    summary=f"Performance analysis: {len(findings)} performance findings",
                    processed_count=len(request.entries),
                    finding_count=len(findings),
                    severity_level="HIGH" if slow_operations > 3 else "LOW"
                ),
                findings=findings,
                metrics={
                    "total_entries": str(len(request.entries)),
                    "slow_operations": str(slow_operations),
                    "resource_intensive_ops": str(resource_intensive_ops),
                    "performance_findings": str(len(findings))
                }
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Performance analysis failed: {str(e)}")
            return plugin_pb2.ProcessResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    plugin_pb2_grpc.add_PluginServiceServicer_to_server(PerformanceAnalyzerService(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    print("✅ Performance Analyzer plugin started on port 50053")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()