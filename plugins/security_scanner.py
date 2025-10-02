from concurrent import futures
import grpc
import logging
from datetime import datetime
import re
from typing import List, Dict

from models import plugin_pb2
from models import plugin_pb2_grpc

class SecurityScannerService(plugin_pb2_grpc.PluginServiceServicer):
    def __init__(self):
        self.name = "security-scanner"
        self.version = "1.0.0"
        self.sensitive_patterns = [
            (r'api[_-]?key\s*[=:]\s*[\'\"][^\'\"]+[\'\"]', "API Key exposure"),
            (r'password\s*[=:]\s*[\'\"][^\'\"]+[\'\"]', "Password exposure"),
            (r'secret\s*[=:]\s*[\'\"][^\'\"]+[\'\"]', "Secret exposure"),
            (r'token\s*[=:]\s*[\'\"][^\'\"]+[\'\"]', "Token exposure"),
            (r'-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----', "Private key exposure"),
        ]
    
    def HealthCheck(self, request, context):
        return plugin_pb2.HealthResponse(
            status="SERVING",
            timestamp=datetime.now().isoformat()
        )
    
    def GetInfo(self, request, context):
        return plugin_pb2.InfoResponse(
            name=self.name,
            version=self.version,
            description="Scans for security issues and sensitive data exposure",
            capabilities=["security_scanning", "sensitive_data_detection", "compliance_checking"],
            supported_parameters=["strict_mode", "scan_sensitive_data", "check_compliance"]
        )
    
    def Process(self, request, context):
        try:
            findings = []
            sensitive_data_found = False
            
            for entry in request.entries:
                # Проверяем на чувствительные данные
                for pattern, description in self.sensitive_patterns:
                    if re.search(pattern, entry.message, re.IGNORECASE):
                        findings.append(plugin_pb2.Finding(
                            type="SENSITIVE_DATA_EXPOSURE",
                            severity="CRITICAL",
                            message=f"Potential {description} detected in logs",
                            resource=entry.metadata.get("resource", "unknown"),
                            recommendations=[
                                "Remove sensitive data from logs and configurations",
                                "Use environment variables or secret management systems",
                                "Implement proper logging filters",
                                "Rotate exposed credentials immediately"
                            ],
                            metadata={
                                "pattern_matched": pattern,
                                "data_type": description.lower(),
                                "log_entry": entry.message[:100] + "..." if len(entry.message) > 100 else entry.message
                            }
                        ))
                        sensitive_data_found = True
                        break
            
            # Проверяем security best practices
            security_issues = self._check_security_practices(request.entries)
            findings.extend(security_issues)
            
            return plugin_pb2.ProcessResponse(
                result=plugin_pb2.AnalysisResult(
                    summary=f"Security scan completed: {len(findings)} security findings",
                    processed_count=len(request.entries),
                    finding_count=len(findings),
                    severity_level="CRITICAL" if sensitive_data_found else "LOW"
                ),
                findings=findings,
                metrics={
                    "scanned_entries": str(len(request.entries)),
                    "security_findings": str(len(findings)),
                    "sensitive_data_found": str(sensitive_data_found),
                    "patterns_checked": str(len(self.sensitive_patterns))
                }
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Security scan failed: {str(e)}")
            return plugin_pb2.ProcessResponse()
    
    def _check_security_practices(self, entries: List) -> List:
        """Проверка security best practices"""
        findings = []
        
        for entry in entries:
            message = entry.message.lower()
            
            # Проверяем на публичные ресурсы
            if any(pattern in message for pattern in ["0.0.0.0/0", "::/0", "public", "0.0.0.0"]):
                findings.append(plugin_pb2.Finding(
                    type="PUBLIC_ACCESS_CONFIGURED",
                    severity="HIGH",
                    message="Resource configured with public access",
                    resource=entry.metadata.get("resource", "unknown"),
                    recommendations=[
                        "Restrict resource access to specific IP ranges",
                        "Use security groups and network policies",
                        "Implement private networking where possible"
                    ]
                ))
            
            # Проверяем на небезопасные протоколы
            if "protocol.*=.*http" in message and "https" not in message:
                findings.append(plugin_pb2.Finding(
                    type="INSECURE_PROTOCOL",
                    severity="MEDIUM",
                    message="HTTP protocol detected - use HTTPS",
                    resource=entry.metadata.get("resource", "unknown"),
                    recommendations=[
                        "Use HTTPS instead of HTTP",
                        "Configure proper TLS/SSL certificates",
                        "Enable encryption in transit"
                    ]
                ))
        
        return findings

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    plugin_pb2_grpc.add_PluginServiceServicer_to_server(SecurityScannerService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("✅ Security Scanner plugin started on port 50052")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()