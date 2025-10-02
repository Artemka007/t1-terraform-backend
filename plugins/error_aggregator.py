import re
from collections import defaultdict, Counter
from plugins.base_plugin import BasePlugin
from models import plugin_pb2

class ErrorAggregatorPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="error-aggregator",
            version="1.0.0",
            description="Aggregates and categorizes Terraform errors by patterns and frequency"
        )
        self.capabilities = ["error_analysis", "pattern_detection", "frequency_analysis"]
        self.supported_parameters = ["min_frequency", "group_by_type", "include_warnings"]
        
        # Паттерны для категоризации ошибок
        self.error_patterns = {
            "authentication": [
                r"auth", r"credential", r"token", r"permission", r"unauthorized"
            ],
            "network": [
                r"timeout", r"connection", r"network", r"dns", r"connect"
            ],
            "resource": [
                r"not found", r"already exists", r"conflict", r"limit exceeded"
            ],
            "configuration": [
                r"invalid", r"validation", r"syntax", r"missing", r"required"
            ]
        }
    
    def Process(self, request, context):
        entries = request.entries
        parameters = dict(request.parameters)
        
        # Анализ ошибок
        error_analysis = self._analyze_errors(entries, parameters)
        
        # Создание findings
        findings = self._create_findings(error_analysis)
        
        return plugin_pb2.ProcessResponse(
            result=plugin_pb2.AnalysisResult(
                summary=f"Found {len(findings)} error patterns across {len(entries)} log entries",
                processed_count=len(entries),
                finding_count=len(findings),
                severity_level=self._calculate_severity(findings)
            ),
            findings=findings,
            metrics={
                "total_errors": str(error_analysis["total_errors"]),
                "unique_patterns": str(len(error_analysis["patterns"])),
                "most_frequent_error": error_analysis["most_frequent"],
                "analysis_duration": "0.1s"  # В реальности нужно измерять
            }
        )
    
    def _analyze_errors(self, entries, parameters):
        errors = [e for e in entries if e.level in ["error", "warning"]]
        error_messages = [e.message for e in errors]
        
        # Группировка по паттернам
        patterns = self._categorize_errors(error_messages)
        
        # Анализ частоты
        frequency = Counter(error_messages)
        
        return {
            "total_errors": len(errors),
            "patterns": patterns,
            "frequency": dict(frequency),
            "most_frequent": frequency.most_common(1)[0] if frequency else ("None", 0)
        }
    
    def _categorize_errors(self, error_messages):
        categorized = defaultdict(list)
        
        for error in error_messages:
            for category, patterns in self.error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, error, re.IGNORECASE):
                        categorized[category].append(error)
                        break
        
        return dict(categorized)
    
    def _create_findings(self, analysis):
        findings = []
        
        # Finding для частых ошибок
        if analysis["most_frequent"][1] > 1:
            findings.append(plugin_pb2.Finding(
                type="FREQUENT_ERROR",
                severity="HIGH",
                message=f"Most frequent error: '{analysis['most_frequent'][0]}' occurred {analysis['most_frequent'][1]} times",
                resource="global",
                recommendations=[
                    "Investigate the root cause of this recurring error",
                    "Check if this is a configuration issue",
                    "Consider adding retry logic if applicable"
                ]
            ))
        
        # Findings по категориям
        for category, errors in analysis["patterns"].items():
            if errors:
                findings.append(plugin_pb2.Finding(
                    type=f"{category.upper()}_ERRORS",
                    severity="MEDIUM",
                    message=f"Found {len(errors)} {category}-related errors",
                    resource="global",
                    recommendations=self._get_category_recommendations(category),
                    metadata={"error_count": str(len(errors))}
                ))
        
        return findings
    
    def _get_category_recommendations(self, category):
        recommendations = {
            "authentication": [
                "Verify credentials and API tokens",
                "Check IAM roles and permissions",
                "Ensure token expiration is handled"
            ],
            "network": [
                "Check network connectivity",
                "Verify DNS resolution",
                "Review firewall rules"
            ],
            "resource": [
                "Check resource naming conflicts",
                "Verify resource limits",
                "Review dependency order"
            ],
            "configuration": [
                "Validate Terraform configuration",
                "Check variable types and values",
                "Review required fields"
            ]
        }
        return recommendations.get(category, ["Review the specific error details"])
    
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