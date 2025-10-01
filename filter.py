import pandas as pd

from enum import Enum
from typing import List, Any
from dataclasses import dataclass


class FilterOperator(Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_NULL = "not_null"
    IS_NULL = "is_null"


class GroupByType(Enum):
    TF_REQ_ID = "tf_req_id"
    TF_RPC = "tf_rpc"
    TF_RESOURCE_TYPE = "tf_resource_type"
    TF_DATA_SOURCE_TYPE = "tf_data_source_type"
    MODULE = "@module"
    LEVEL = "@level"
    HTTP_STATUS = "tf_http_res_status_code"
    PROTO_VERSION = "tf_proto_version"
    TF_PROVIDER_ADDR = "tf_provider_addr"


class ProcessFilterType(Enum):
    MAIN_PROCESS_ONLY = "main_process_only"
    SUBPROCESSES_ONLY = "subprocesses_only"
    WITH_ERRORS = "with_errors"
    WITHOUT_ERRORS = "without_errors"
    SPECIFIC_TYPE = "specific_type"


@dataclass
class FilterCondition:
    field: str
    operator: FilterOperator
    value: Any = None

    def apply(self, df: pd.DataFrame) -> pd.Series:
        if self.operator == FilterOperator.EQUALS:
            return df[self.field] == self.value
        elif self.operator == FilterOperator.CONTAINS:
            return df[self.field].str.contains(str(self.value), na=False)
        elif self.operator == FilterOperator.STARTS_WITH:
            return df[self.field].str.startswith(str(self.value), na=False)
        elif self.operator == FilterOperator.ENDS_WITH:
            return df[self.field].str.endswith(str(self.value), na=False)
        elif self.operator == FilterOperator.GREATER_THAN:
            return df[self.field] > self.value
        elif self.operator == FilterOperator.LESS_THAN:
            return df[self.field] < self.value
        elif self.operator == FilterOperator.IN:
            return df[self.field].isin(self.value)
        elif self.operator == FilterOperator.NOT_NULL:
            return df[self.field].notna()
        elif self.operator == FilterOperator.IS_NULL:
            return df[self.field].isna()


@dataclass
class FilterConfig:
    conditions: List[FilterCondition]
    logical_operator: str = "and"  # "and", "or"

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.conditions:
            return df

        combined_condition = None
        for condition in self.conditions:
            condition_mask = condition.apply(df)

            if combined_condition is None:
                combined_condition = condition_mask
            else:
                if self.logical_operator == "and":
                    combined_condition = combined_condition & condition_mask
                else:
                    combined_condition = combined_condition | condition_mask

        return df[combined_condition] if combined_condition is not None else df


@dataclass
class Aggregation:
    """Конфигурация агрегации для группировки"""
    field: str
    operation: str  # 'count', 'min', 'max', 'mean', 'std', 'unique', 'first', 'last'
    output_name: str = None

    def __post_init__(self):
        if self.output_name is None:
            self.output_name = f"{self.field}_{self.operation}"


@dataclass
class GroupByConfig:
    group_by: GroupByType
    aggregations: List[Aggregation] = None
    include_details: bool = True

    def __post_init__(self):
        if self.aggregations is None:
            self.aggregations = [
                Aggregation('@timestamp', 'min', 'first_timestamp'),
                Aggregation('@timestamp', 'max', 'last_timestamp'),
                Aggregation('@level', 'count', 'total_count')
            ]


@dataclass
class ProcessFilterConfig:
    filter_type: ProcessFilterType
    process_types: List[str] = None
    include_nested: bool = True
