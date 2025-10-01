# plugin_server.py
import time
import grpc
from concurrent import futures
import pandas as pd
import json
import numpy as np
from datetime import datetime

# Импорты сгенерированного gRPC-кода
import log_analyzer_plugin_pb2 as pb2
import log_analyzer_plugin_pb2_grpc as pb2_grpc

# Импорты ваших классов (скопированные или импортированные)
from enum import Enum
from typing import Dict, List, Any, Union, Optional
from dataclasses import dataclass

# --- Константы из вашего кода ---
TF_PROTO_VERSION = "tf_proto_version"
TF_PROVIDER_ADDR = "tf_provider_addr"
TF_REQ_ID = "tf_req_id"
TF_RPC = "tf_rpc"
TF_RESOURCE_TYPE = "tf_resource_type"
TF_DATA_SOURCE_TYPE = "tf_data_source_type"
TF_ATTR_PATH = "tf_attribute_path"
TF_HTTP_OP_TYPE = "tf_http_op_type"
TF_HTTP_REQ_METHOD = "tf_http_req_method"
TF_HTTP_RES_STATUS = "tf_http_res_status_code"
TF_REQ_DURATION_MS = "tf_req_duration_ms"
DIAGNOSTIC_SEVERITY = "diagnostic_severity"
MODULE = "@module"
CALLER = "@caller"

# --- Enums и Dataclasses из вашего кода ---
class FilterOperator(Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with" # Добавлен для совместимости, но не используется в новом списке
    ENDS_WITH = "ends_with"     # Добавлен для совместимости, но не используется в новом списке
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_NULL = "not_null"       # Добавлен для совместимости, но не используется в новом списке
    IS_NULL = "is_null"         # Добавлен для совместимости, но не используется в новом списке

@dataclass
class FilterCondition:
    field: str
    operator: FilterOperator
    value: Any = None

    def apply(self, df: pd.DataFrame) -> pd.Series:
        op = self.operator.value if isinstance(self.operator, FilterOperator) else self.operator
        if op == FilterOperator.EQUALS.value:
            return df[self.field] == self.value
        elif op == FilterOperator.CONTAINS.value:
            return df[self.field].astype(str).str.contains(str(self.value), na=False)
        elif op == FilterOperator.GREATER_THAN.value:
            return df[self.field] > self.value
        elif op == FilterOperator.LESS_THAN.value:
            return df[self.field] < self.value
        elif op == FilterOperator.IN.value:
            return df[self.field].isin(self.value)
        elif op == FilterOperator.NOT_NULL.value:
            return df[self.field].notna()
        elif op == FilterOperator.IS_NULL.value:
            return df[self.field].isna()
        elif op == FilterOperator.STARTS_WITH.value:
            return df[self.field].astype(str).str.startswith(str(self.value), na=False)
        elif op == FilterOperator.ENDS_WITH.value:
            return df[self.field].astype(str).str.endswith(str(self.value), na=False)
        else:
            # Для неизвестного оператора возвращаем False для всех
            print(f"Unknown operator: {op}")
            return pd.Series([False] * len(df), index=df.index)

@dataclass
class Aggregation:
    field: str
    operation: str  # 'count', 'min', 'max', 'mean', 'std', 'unique', 'first', 'last'
    output_name: str = None

    def __post_init__(self):
        if self.output_name is None:
            self.output_name = f"{self.field}_{self.operation}"

class Parser: # Простая заглушка для совместимости
    def __init__(self, df: pd.DataFrame):
        self.df = df

class LogAnalyzer:
    def __init__(self, parser):
        self.parser = parser
        self.df = parser.df

    def apply_filters(self, conditions: List[FilterCondition], logical_operator: str = "and") -> pd.DataFrame:
        """
        Применяет список фильтров к DataFrame.
        """
        if not conditions:
            return self.df

        combined_condition = None
        for condition in conditions:
            condition_mask = condition.apply(self.df)
            if combined_condition is None:
                combined_condition = condition_mask
            else:
                if logical_operator.lower() == "and":
                    combined_condition = combined_condition & condition_mask
                else: # "or"
                    combined_condition = combined_condition | condition_mask

        return self.df[combined_condition] if combined_condition is not None else pd.DataFrame()

    def apply_group_by(self, df: pd.DataFrame, group_by_field: str, aggregations: List[Aggregation], include_details: bool) -> Dict[str, Any]:
        """
        Применяет группировку к данным
        """
        if group_by_field not in df.columns:
            return {"error": f"Field {group_by_field} not found in data", "available_fields": list(df.columns)}

        if df[group_by_field].isna().all():
            return {"error": f"Field {group_by_field} has no values"}

        # Базовая группировка
        grouped = df.groupby(group_by_field)

        # Применяем агрегации
        aggregation_results = {}
        for agg in aggregations:
            if agg.field not in df.columns:
                continue
            try:
                if agg.operation == 'count':
                    result = grouped.size()
                    aggregation_results[agg.output_name] = result.to_dict()
                elif agg.operation == 'unique':
                    result = grouped[agg.field].unique()
                    aggregation_results[agg.output_name] = {k: list(v) for k, v in result.items()}
                elif agg.operation == 'first':
                    result = grouped[agg.field].first()
                    aggregation_results[agg.output_name] = result.to_dict()
                elif agg.operation == 'last':
                    result = grouped[agg.field].last()
                    aggregation_results[agg.output_name] = result.to_dict()
                else:
                    # Для числовых операций: min, max, mean, std
                    if pd.api.types.is_numeric_dtype(df[agg.field]):
                        result = getattr(grouped[agg.field], agg.operation)()
                        aggregation_results[agg.output_name] = result.to_dict()
                    else:
                        # Для нечисловых полей используем first
                        result = grouped[agg.field].first()
                        aggregation_results[agg.output_name] = result.to_dict()
            except Exception as e:
                aggregation_results[agg.output_name] = f"Error: {str(e)}"

        result = {
            'group_field': group_by_field,
            'groups': list(grouped.groups.keys()),
            'group_counts': grouped.size().to_dict(),
            'aggregations': aggregation_results
        }

        # Детальная информация по группам
        if include_details:
            result['details'] = {}
            for group_name, group_indices in grouped.groups.items():
                group_df = df.loc[group_indices]
                result['details'][group_name] = {
                    'count': len(group_df),
                    'time_range': {
                        'start': group_df['@timestamp'].min(),
                        'end': group_df['@timestamp'].max()
                    },
                    'levels': group_df['@level'].value_counts().to_dict(),
                    'sample_messages': group_df['@message'].head(3).tolist()
                }
        return result

# --- Сервер gRPC ---
class LogProcessorServicer(pb2_grpc.LogProcessorServicer):
    def FilterLogs(self, request, context):
        print(f"[Plugin] Received FilterLogs request with {len(request.log_entries)} entries and {len(request.conditions)} conditions")
        try:
            # Преобразовать protobuf LogEntry в DataFrame
            log_list = []
            for pb_entry in request.log_entries:
                py_entry = {
                    '@timestamp': pb_entry.timestamp,
                    '@level': pb_entry.level,
                    '@message': pb_entry.message,
                    '@module': pb_entry.module,
                    '@caller': pb_entry.caller,
                    'tf_req_id': pb_entry.tf_req_id,
                    'tf_resource_type': pb_entry.tf_resource_type,
                    'tf_data_source_type': pb_entry.tf_data_source_type,
                    'tf_rpc': pb_entry.tf_rpc,
                    'tf_req_duration_ms': pb_entry.tf_req_duration_ms if pb_entry.tf_req_duration_ms != 0 else np.nan, # Обработка 0 как NaN
                    'raw_json': pb_entry.raw_json
                }
                log_list.append(py_entry)

            df = pd.DataFrame(log_list)
            if df.empty:
                 return pb2.FilterResponse(success=True, status_message="No logs to filter", filtered_entries=[])

            # Преобразовать timestamp в datetime, если есть
            if '@timestamp' in df.columns and not df['@timestamp'].isna().all():
                 df['@timestamp'] = pd.to_datetime(df['@timestamp'], errors='coerce')

            parser = Parser(df)
            analyzer = LogAnalyzer(parser)

            # Преобразовать protobuf FilterCondition в наши FilterCondition
            filter_conditions = []
            for pb_cond in request.conditions:
                 op_enum = next((op for op in FilterOperator if op.value == pb_cond.operator), None)
                 if not op_enum:
                     context.set_details(f"Unknown filter operator: {pb_cond.operator}")
                     context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                     return pb2.FilterResponse(success=False, status_message=f"Unknown filter operator: {pb_cond.operator}")

                 # Определение значения на основе типа
                 value = None
                 if pb_cond.value_string:
                     value = pb_cond.value_string
                 elif pb_cond.value_int64:
                     value = pb_cond.value_int64
                 elif pb_cond.value_double:
                     value = pb_cond.value_double
                 elif pb_cond.value_timestamp:
                     # Преобразование строки timestamp в datetime для сравнения
                     try:
                         value = pd.to_datetime(pb_cond.value_timestamp, errors='coerce')
                         if pd.isna(value):
                             raise ValueError(f"Invalid timestamp format: {pb_cond.value_timestamp}")
                     except ValueError as e:
                         context.set_details(f"Invalid timestamp value: {pb_cond.value_timestamp}, error: {e}")
                         context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                         return pb2.FilterResponse(success=False, status_message=f"Invalid timestamp value: {pb_cond.value_timestamp}")
                 elif pb_cond.values:
                     # Если значение не задано отдельно, используем values[0] или весь список для IN
                     if pb_cond.operator == FilterOperator.IN.value:
                         # Парсим строковые значения в список, предполагая числа, если поле числовое
                         parsed_values = []
                         for val_str in pb_cond.values:
                             try:
                                 # Попробуем как int, затем float
                                 parsed_val = int(val_str)
                             except ValueError:
                                 try:
                                     parsed_val = float(val_str)
                                 except ValueError:
                                     parsed_val = val_str # строка
                             parsed_values.append(parsed_val)
                         value = parsed_values
                     else:
                         # Для других операторов используем первое значение
                         val_str = pb_cond.values[0]
                         try:
                             value = int(val_str)
                         except ValueError:
                             try:
                                 value = float(val_str)
                             except ValueError:
                                 value = val_str # строка
                 else:
                     # Если значение не задано нигде, используем pb_cond.value_int64 (или 0, если не задано)
                     # Для операторов like IS_NULL, NOT_NULL value может быть None
                     if pb_cond.operator not in [FilterOperator.IS_NULL.value, FilterOperator.NOT_NULL.value]:
                         context.set_details(f"Value required for operator {pb_cond.operator}")
                         context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                         return pb2.FilterResponse(success=False, status_message=f"Value required for operator {pb_cond.operator}")

                 filter_conditions.append(FilterCondition(
                     field=pb_cond.field,
                     operator=op_enum,
                     value=value
                 ))

            # Применить фильтры
            filtered_df = analyzer.apply_filters(filter_conditions, request.logical_operator)

            # Преобразовать результат обратно в protobuf LogEntry
            result_logs = []
            for _, row in filtered_df.iterrows():
                # Преобразование timestamp обратно в строку
                ts_str = row.get('@timestamp')
                if pd.notna(ts_str):
                    ts_str = ts_str.isoformat()
                else:
                    ts_str = ''
                pb_entry = pb2.LogEntry(
                    timestamp=ts_str,
                    level=row.get('@level', ''),
                    message=row.get('@message', ''),
                    module=row.get('@module', ''),
                    caller=row.get('@caller', ''),
                    tf_req_id=row.get('tf_req_id', ''),
                    tf_resource_type=row.get('tf_resource_type', ''),
                    tf_data_source_type=row.get('tf_data_source_type', ''),
                    tf_rpc=row.get('tf_rpc', ''),
                    tf_req_duration_ms=row.get('tf_req_duration_ms', 0), # 0 для NaN
                    raw_json=row.get('raw_json', '')
                )
                result_logs.append(pb_entry)

            return pb2.FilterResponse(
                filtered_entries=result_logs,
                status_message=f"Filtered {len(request.log_entries)} -> {len(result_logs)} entries",
                success=True
            )
        except Exception as e:
            context.set_details(f"Error processing FilterLogs: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return pb2.FilterResponse(success=False, status_message=str(e))

    def GroupLogs(self, request, context):
        print(f"[Plugin] Received GroupLogs request with {len(request.log_entries)} entries, grouping by {request.group_by_field}")
        try:
            # Преобразовать protobuf LogEntry в DataFrame
            log_list = []
            for pb_entry in request.log_entries:
                py_entry = {
                    '@timestamp': pb_entry.timestamp,
                    '@level': pb_entry.level,
                    '@message': pb_entry.message,
                    '@module': pb_entry.module,
                    '@caller': pb_entry.caller,
                    'tf_req_id': pb_entry.tf_req_id,
                    'tf_resource_type': pb_entry.tf_resource_type,
                    'tf_data_source_type': pb_entry.tf_data_source_type,
                    'tf_rpc': pb_entry.tf_rpc,
                    'tf_req_duration_ms': pb_entry.tf_req_duration_ms if pb_entry.tf_req_duration_ms != 0 else np.nan,
                    'raw_json': pb_entry.raw_json
                }
                log_list.append(py_entry)

            df = pd.DataFrame(log_list)
            if df.empty:
                 return pb2.GroupResponse(success=True, status_message="No logs to group", grouped_results={})

            # Преобразовать timestamp в datetime, если есть
            if '@timestamp' in df.columns and not df['@timestamp'].isna().all():
                 df['@timestamp'] = pd.to_datetime(df['@timestamp'], errors='coerce')

            parser = Parser(df)
            analyzer = LogAnalyzer(parser)

            # Преобразовать protobuf AggregationConfig в наши Aggregation
            aggregations = []
            for pb_agg in request.aggregations:
                 aggregations.append(Aggregation(
                     field=pb_agg.field,
                     operation=pb_agg.operation,
                     output_name=pb_agg.output_name
                 ))

            # Применить группировку
            group_result_dict = analyzer.apply_group_by(df, request.group_by_field, aggregations, request.include_details)

            if "error" in group_result_dict:
                context.set_details(group_result_dict["error"])
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return pb2.GroupResponse(success=False, status_message=group_result_dict["error"])

            # Преобразовать результат в protobuf GroupResponse
            pb_grouped_results = {}
            for group_key, group_data in group_result_dict.get('details', {}).items():
                 pb_sample_entries = []
                 if request.include_details:
                     # Преобразовать sample_messages обратно в LogEntry (упрощённо)
                     sample_messages = group_data.get('sample_messages', [])
                     for msg in sample_messages:
                         # Создаём фиктивную запись с сообщением
                         pb_sample_entries.append(pb2.LogEntry(message=msg, level="info"))

                 # Преобразование time_range в строки
                 time_range = group_data.get('time_range', {})
                 first_ts = time_range.get('start')
                 last_ts = time_range.get('end')
                 if pd.notna(first_ts):
                     first_ts_str = first_ts.isoformat()
                 else:
                     first_ts_str = ''
                 if pd.notna(last_ts):
                     last_ts_str = last_ts.isoformat()
                 else:
                     last_ts_str = ''

                 pb_grouped_results[str(group_key)] = pb2.GroupResult(
                     count=group_data.get('count', 0),
                     aggregations={k: str(v) for k, v in group_data.get('aggregations', {}).items()}, # Преобразуем значения в строки
                     sample_entries=pb_sample_entries,
                     first_timestamp=first_ts_str,
                     last_timestamp=last_ts_str,
                     level_counts={k: int(v) for k, v in group_data.get('levels', {}).items()} # Уровень -> счетчик (int)
                 )

            return pb2.GroupResponse(
                grouped_results=pb_grouped_results,
                status_message=f"Grouped {len(request.log_entries)} entries by {request.group_by_field}",
                success=True
            )
        except Exception as e:
            context.set_details(f"Error processing GroupLogs: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return pb2.GroupResponse(success=False, status_message=str(e))

def serve_plugin(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_LogProcessorServicer_to_server(LogProcessorServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    print(f"[Plugin Server] Starting server on port {port}...")
    server.start()
    try:
        while True:
            time.sleep(86400) # Спит 1 день, позволяет серверу работать
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve_plugin()