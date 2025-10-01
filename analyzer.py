import pandas as pd

from typing import List, Dict, Any, Optional

from filter import (FilterConfig, ProcessFilterConfig, FilterOperator,
                    FilterCondition, GroupByType, GroupByConfig, Aggregation,
                    ProcessFilterType)
from parser import Parser

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


class AnalysisConfig:
    """Универсальная конфигурация для анализа логов"""

    def __init__(self):
        self.filters = FilterConfig([])
        self.group_by = None
        self.process_filters: List[ProcessFilterConfig] = []
        self.max_results = 1000
        self.include_metadata = True

    def add_filter(self, field: str, operator: FilterOperator, value: Any = None):
        self.filters.conditions.append(FilterCondition(field, operator, value))
        return self

    def set_group_by(self, group_by: GroupByType, aggregations: List[Aggregation] = None):
        self.group_by = GroupByConfig(group_by, aggregations)
        return self

    def add_process_filter(self, filter_type: ProcessFilterType, process_types: List[str] = None):
        self.process_filters.append(ProcessFilterConfig(filter_type, process_types))
        return self


class LogAnalyzer:
    """Универсальный анализатор логов с фильтрацией и группировкой"""

    def __init__(self, parser: Parser):
        self.parser = parser
        self.df = parser.df

    def analyze(self, config: AnalysisConfig) -> Dict[str, Any]:
        """
        Основной метод анализа с применением конфигурации
        """
        result = {
            'metadata': {},
            'filtered_data': None,
            'grouped_data': None,
            'process_analysis': None
        }

        # Применяем фильтры к данным
        filtered_df = config.filters.apply(self.df)
        result['filtered_data'] = filtered_df
        result['metadata']['total_records'] = len(self.df)
        result['metadata']['filtered_records'] = len(filtered_df)

        # Применяем группировку если задана
        if config.group_by and not filtered_df.empty:
            grouped_result = self._apply_group_by(filtered_df, config.group_by)
            result['grouped_data'] = grouped_result

        # Анализ процессов если есть фильтры процессов
        if config.process_filters:
            process_analysis = self._analyze_processes(config.process_filters)
            result['process_analysis'] = process_analysis

        return result

    def _apply_group_by(self, df: pd.DataFrame, group_config: GroupByConfig) -> Dict[str, Any]:
        """
        Применяет группировку к данным
        """
        group_field = group_config.group_by.value

        if group_field not in df.columns:
            return {"error": f"Field {group_field} not found in data", "available_fields": list(df.columns)}

        if df[group_field].isna().all():
            return {"error": f"Field {group_field} has no values"}

        # Базовая группировка
        grouped = df.groupby(group_field)

        # Применяем агрегации

        aggregation_results = {}

        for agg in group_config.aggregations:
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
            'group_field': group_field,
            'groups': list(grouped.groups.keys()),
            'group_counts': grouped.size().to_dict(),
            'aggregations': aggregation_results
        }

        # Детальная информация по группам
        if group_config.include_details:
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

    def _analyze_processes(self, process_filters: List[ProcessFilterConfig]) -> Dict[str, Any]:
        """
        Анализирует процессы согласно фильтрам
        """
        result = {}

        # Извлекаем все процессы
        apply_result = self.parser.extract_apply_section()
        plan_result = self.parser.extract_plan_section()
        all_processes = {**apply_result, **plan_result}

        filtered_processes = {}

        for process_key, process_data in all_processes.items():
            filtered_process = self._apply_process_filters(process_data, process_filters)
            if filtered_process:
                filtered_processes[process_key] = filtered_process

        result['filtered_processes'] = filtered_processes
        result['total_processes'] = len(all_processes)
        result['filtered_count'] = len(filtered_processes)

        return result

    def _apply_process_filters(self,
                               process_data: Dict[str, Any],
                               filters: List[ProcessFilterConfig]) -> Optional[Dict[str, Any]]:
        """
        Применяет фильтры к отдельному процессу
        """
        for filter_config in filters:
            if not self._process_matches_filter(process_data, filter_config):
                return None

        return process_data

    def _process_matches_filter(self,
                                process_data: Dict[str, Any],
                                filter_config: ProcessFilterConfig) -> bool:
        """
        Проверяет соответствует ли процесс фильтру
        """
        filter_type = filter_config.filter_type

        if filter_type == ProcessFilterType.MAIN_PROCESS_ONLY:
            return process_data['type'] in ['main_apply', 'main_plan']

        elif filter_type == ProcessFilterType.SUBPROCESSES_ONLY:
            return process_data['type'] not in ['main_apply', 'main_plan']

        elif filter_type == ProcessFilterType.WITH_ERRORS:
            return process_data.get('status') == 'error'

        elif filter_type == ProcessFilterType.WITHOUT_ERRORS:
            return process_data.get('status') != 'error'

        elif filter_type == ProcessFilterType.SPECIFIC_TYPE:
            if filter_config.process_types:
                return process_data['type'] in filter_config.process_types
            return True

        return True

    def get_unique_values(self, field: str, limit: int = 50) -> List[Any]:
        """
        Возвращает уникальные значения для поля
        """
        if field not in self.df.columns:
            return []

        unique_vals = self.df[field].dropna().unique().tolist()
        return unique_vals[:limit]

    def get_field_stats(self, field: str) -> Dict[str, Any]:
        """
        Возвращает статистику по полю
        """
        if field not in self.df.columns:
            return {"error": f"Field {field} not found"}

        series = self.df[field]
        stats = {
            'count': len(series),
            'non_null_count': series.count(),
            'null_count': series.isna().sum(),
            'unique_count': series.nunique()
        }

        # Для числовых полей добавляем дополнительную статистику
        if pd.api.types.is_numeric_dtype(series):
            stats.update({
                'min': series.min(),
                'max': series.max(),
                'mean': series.mean(),
                'std': series.std()
            })

        return stats

    def quick_analysis(self) -> Dict[str, Any]:
        """
        Быстрый анализ всех данных
        """
        analysis = {
            'summary': {
                'total_records': len(self.df),
                'time_range': {
                    'start': self.df['@timestamp'].min(),
                    'end': self.df['@timestamp'].max()
                },
                'levels': self.df['@level'].value_counts().to_dict()
            },
            'top_fields': {}
        }

        # Анализ ключевых полей
        key_fields = [TF_RPC, TF_RESOURCE_TYPE, TF_DATA_SOURCE_TYPE, TF_REQ_ID, '@module']
        for field in key_fields:
            if field in self.df.columns:
                stats = self.get_field_stats(field)
                analysis['top_fields'][field] = stats

        return analysis


# Предопределенные конфигурации для частых сценариев
class PredefinedConfigs:
    """Предопределенные конфигурации для частых сценариев анализа"""

    @staticmethod
    def error_analysis() -> AnalysisConfig:
        """Анализ ошибок"""
        config = AnalysisConfig()
        config.add_filter('@level', FilterOperator.EQUALS, 'error')
        config.set_group_by(GroupByType.MODULE, [
            Aggregation('@timestamp', 'min', 'first_error'),
            Aggregation('@timestamp', 'max', 'last_error'),
            Aggregation('@message', 'count', 'error_count')
        ])
        return config

    @staticmethod
    def request_analysis() -> AnalysisConfig:
        """Анализ запросов по tf_req_id"""
        config = AnalysisConfig()
        config.add_filter(TF_REQ_ID, FilterOperator.NOT_NULL)
        config.set_group_by(GroupByType.TF_REQ_ID, [
            Aggregation('@timestamp', 'min', 'start_time'),
            Aggregation('@timestamp', 'max', 'end_time'),
            Aggregation(TF_RPC, 'unique', 'rpc_types'),
            Aggregation(TF_REQ_DURATION_MS, 'mean', 'avg_duration_ms')
        ])
        return config

    @staticmethod
    def http_analysis() -> AnalysisConfig:
        """Анализ HTTP запросов"""
        config = AnalysisConfig()
        config.add_filter(TF_HTTP_OP_TYPE, FilterOperator.NOT_NULL)
        config.set_group_by(GroupByType.HTTP_STATUS, [
            Aggregation('@timestamp', 'min', 'first_request'),
            Aggregation('@timestamp', 'max', 'last_request'),
            Aggregation(TF_HTTP_REQ_METHOD, 'unique', 'methods')
        ])
        return config

    @staticmethod
    def rpc_analysis() -> AnalysisConfig:
        """Анализ RPC вызовов"""
        config = AnalysisConfig()
        config.add_filter(TF_RPC, FilterOperator.NOT_NULL)
        config.set_group_by(GroupByType.TF_RPC, [
            Aggregation('@timestamp', 'min', 'first_call'),
            Aggregation('@timestamp', 'max', 'last_call'),
            Aggregation(TF_REQ_DURATION_MS, 'mean', 'avg_duration'),
            Aggregation('@level', 'count', 'total_calls')
        ])
        return config
