from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProcessRequest(_message.Message):
    __slots__ = ("entries", "parameters", "plugin_config")
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    PLUGIN_CONFIG_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    parameters: _containers.ScalarMap[str, str]
    plugin_config: str
    def __init__(self, entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ..., parameters: _Optional[_Mapping[str, str]] = ..., plugin_config: _Optional[str] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("level", "message", "timestamp", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    level: str
    message: str
    timestamp: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, level: _Optional[str] = ..., message: _Optional[str] = ..., timestamp: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ProcessResponse(_message.Message):
    __slots__ = ("result", "findings", "metrics")
    class MetricsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    RESULT_FIELD_NUMBER: _ClassVar[int]
    FINDINGS_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    result: AnalysisResult
    findings: _containers.RepeatedCompositeFieldContainer[Finding]
    metrics: _containers.ScalarMap[str, str]
    def __init__(self, result: _Optional[_Union[AnalysisResult, _Mapping]] = ..., findings: _Optional[_Iterable[_Union[Finding, _Mapping]]] = ..., metrics: _Optional[_Mapping[str, str]] = ...) -> None: ...

class AnalysisResult(_message.Message):
    __slots__ = ("summary", "processed_count", "finding_count", "severity_level")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    PROCESSED_COUNT_FIELD_NUMBER: _ClassVar[int]
    FINDING_COUNT_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    summary: str
    processed_count: int
    finding_count: int
    severity_level: str
    def __init__(self, summary: _Optional[str] = ..., processed_count: _Optional[int] = ..., finding_count: _Optional[int] = ..., severity_level: _Optional[str] = ...) -> None: ...

class Finding(_message.Message):
    __slots__ = ("type", "severity", "message", "resource", "recommendations", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    RECOMMENDATIONS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    type: str
    severity: str
    message: str
    resource: str
    recommendations: _containers.RepeatedScalarFieldContainer[str]
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, type: _Optional[str] = ..., severity: _Optional[str] = ..., message: _Optional[str] = ..., resource: _Optional[str] = ..., recommendations: _Optional[_Iterable[str]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class InfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class InfoResponse(_message.Message):
    __slots__ = ("name", "version", "description", "capabilities", "supported_parameters")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    SUPPORTED_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: str
    description: str
    capabilities: _containers.RepeatedScalarFieldContainer[str]
    supported_parameters: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., version: _Optional[str] = ..., description: _Optional[str] = ..., capabilities: _Optional[_Iterable[str]] = ..., supported_parameters: _Optional[_Iterable[str]] = ...) -> None: ...

class HealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthResponse(_message.Message):
    __slots__ = ("status", "timestamp")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    status: str
    timestamp: str
    def __init__(self, status: _Optional[str] = ..., timestamp: _Optional[str] = ...) -> None: ...
