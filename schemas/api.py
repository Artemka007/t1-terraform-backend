from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    capabilities: List[str]
    supported_parameters: List[str]

class LogEntry(BaseModel):
    level: str
    message: str
    timestamp: str
    metadata: Dict[str, str] = {}

class Finding(BaseModel):
    type: str
    severity: SeverityLevel
    message: str
    resource: str
    recommendations: List[str]
    metadata: Dict[str, str] = {}

class AnalysisResult(BaseModel):
    summary: str
    processed_count: int
    finding_count: int
    severity_level: str

class PluginResponse(BaseModel):
    result: AnalysisResult
    findings: List[Finding]
    metrics: Dict[str, str] = {}

class AnalysisResponse(BaseModel):
    status: str
    plugins_used: List[str]
    results: Dict[str, Any]

class FileListResponse(BaseModel):
    files: List[str]

class HealthResponse(BaseModel):
    status: str
    timestamp: str

class AnalysisRequest(BaseModel):
    filename: str
    plugins: List[str]
    parameters: Optional[Dict[str, str]] = None

class APIResponse(BaseModel):
    status: str = "success"
    data: Optional[Any] = None
    message: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {"key": "value"},
                "message": "Operation completed successfully"
            }
        }