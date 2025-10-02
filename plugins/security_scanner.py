import re
from plugins.base_plugin import BasePlugin
from models import plugin_pb2

class SecurityScannerPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="security-scanner",
            version="1.0.0",
            description="Scans Terraform logs for security issues and sensitive data exposure"
        )
        self.capabilities = ["security_scanning", "sensitive_data_detection", "compliance_checking"]
        self.supported_parameters = ["scan_sensitive_data", "check_compliance", "strict_mode"]
        
        # Регулярные выражения для поиска чувствительных данных
        self.sensitive_patterns = {
            "api_keys": [
                r"api[_-]?key['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]",
                r"apikey['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]"
            ],
            "passwords": [
                r"password['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]",
                r"pwd['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]"
            ],
            "secrets": [
                r"secret['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]",
                r"token['\"]?\\s*[:=]\\s*['\"]([^'\"]+)['\"]"
            ],
            "private_keys": [
                r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"
            ]
        }
        
        # Security best practices проверки
        self.security_checks = [
            self._check_public_resources,
            self._check_insecure_configs,
            self._check_missing_encryption
        ]
    
    def Process(self, request, context):
        entries = request.entries
        parameters = dict(request.parameters)
        
        security_findings = []
        
        # Проверка на чувствительные данные
        if parameters.get("scan_sensitive_data", "true").lower() == "true":
            sensitive_findings = self._scan_sensitive_data(entries)
            security_findings.extend(sensitive_findings)
        
        # Проверка security best practices
        practice_findings = self._check_security_practices(entries)
        security_findings.extend(practice_findings)
        
        return plugin_pb2.ProcessResponse(
            result=plugin_pb2.AnalysisResult(
                summary=f"Security scan completed: {len(security_findings)} findings",
                processed_count=len(entries),
                finding_count=len(security_findings),
                severity_level=self._calculate_severity(security_findings)
            ),
            findings=security_findings,
            metrics={
                "sensitive_data_findings": str(len([f for f in security_findings if "SENSITIVE" in f.type])),
                "security_violations": str(len([f for f in security_findings if "VIOLATION" in f.type])),
                "scan_coverage": "100%"
            }
        )
    
    def _scan_sensitive_data(self, entries):
        findings = []
        
        for entry in entries:
            for data_type, patterns in self.sensitive_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, entry.message, re.IGNORECASE)
                    if matches:
                        # Маскируем найденные чувствительные данные
                        masked_message = re.sub(pattern, f"{data_type}=[REDACTED]", entry.message)
                        
                        findings.append(plugin_pb2.Finding(
                            type=f"SENSITIVE_DATA_{data_type.upper()}",
                            severity="CRITICAL",
                            message=f"Potential {data_type} exposure detected",
                            resource=entry.metadata.get("resource", "unknown"),
                            recommendations=[
                                "Remove sensitive data from logs and configurations",
                                "Use environment variables or secret management",
                                "Review access controls and permissions"
                            ],
                            metadata={
                                "original_message": masked_message,
                                "pattern_matched": pattern,
                                "match_count": str(len(matches))
                            }
                        ))
        
        return findings
    
    def _check_security_practices(self, entries):
        findings = []
        
        for check in self.security_checks:
            findings.extend(check(entries))
        
        return findings
    
    def _check_public_resources(self, entries):
        findings = []
        public_resource_indicators = [
            "0.0.0.0/0", "::/0", "public", "0.0.0.0", "internet"
        ]
        
        for entry in entries:
            for indicator in public_resource_indicators:
                if indicator in entry.message.lower():
                    findings.append(plugin_pb2.Finding(
                        type="SECURITY_PUBLIC_ACCESS",
                        severity="HIGH",
                        message="Resource configured with public access",
                        resource=entry.metadata.get("resource", "unknown"),
                        recommendations=[
                            "Restrict resource access to specific IP ranges",
                            "Use security groups and network policies",
                            "Implement private networking where possible"
                        ]
                    ))
                    break
        
        return findings
    
    def _check_insecure_configs(self, entries):
        findings = []
        insecure_patterns = [
            (r"protocol.*=.*['\"]http['\"]", "HTTP protocol detected - use HTTPS"),
            (r"encryption.*=.*false", "Encryption disabled"),
            (r"ssl.*=.*false", "SSL/TLS disabled")
        ]
        
        for entry in entries:
            for pattern, description in insecure_patterns:
                if re.search(pattern, entry.message, re.IGNORECASE):
                    findings.append(plugin_pb2.Finding(
                        type="SECURITY_INSECURE_CONFIG",
                        severity="MEDIUM",
                        message=description,
                        resource=entry.metadata.get("resource", "unknown"),
                        recommendations=[
                            "Enable encryption for data in transit and at rest",
                            "Use HTTPS instead of HTTP",
                            "Configure proper TLS settings"
                        ]
                    ))
        
        return findings
    
    def _check_missing_encryption(self, entries):
        findings = []
        encryption_required = [
            "bucket", "volume", "database", "storage"
        ]
        
        for entry in entries:
            for resource_type in encryption_required:
                if resource_type in entry.message.lower() and "encryption" not in entry.message.lower():
                    findings.append(plugin_pb2.Finding(
                        type="SECURITY_MISSING_ENCRYPTION",
                        severity="MEDIUM",
                        message=f"{resource_type} resource may lack encryption",
                        resource=entry.metadata.get("resource", "unknown"),
                        recommendations=[
                            "Enable encryption for the resource",
                            "Use customer-managed keys where required",
                            "Verify encryption settings in configuration"
                        ]
                    ))
                    break
        
        return findings
    
    def _calculate_severity(self, findings):
        severities = [f.severity for f in findings]
        if "CRITICAL" in severities:
            return "CRITICAL"
        elif "HIGH" in severities:
            return "HIGH"
        elif "MEDIUM" in severities:
            return "MEDIUM"
        else:
            return "LOW"