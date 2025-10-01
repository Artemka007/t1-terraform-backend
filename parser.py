from enum import Enum
import json
import pandas as pd
from typing import Dict, List, Any

PLAN_OPERATION_COMPLETED = "plan operation completed"
PLAN_IS_COMPLETE = "Plan is complete"
PLAN_IS_APPLYABLE = "Plan is applyable"
PLAN_IS_NOT_APPLYABLE = "Plan is not applyable"
STARTING_APPLY_FOR = "Starting apply for "
APPLYING_PLANNED = "applying the planned "
APPLY_CALLING_APPLY = "apply calling Apply"
APPLY_CALLING_PLAN = "apply calling Plan"
PLAN_CALLING_PLAN = "plan calling Plan"
BUILDING_WALKING_PLAN_GRAPH = "Building and walking plan graph for NormalMode"
NO_PLANNED_CHANGES_SKIPPING_APPLY = "no planned changes, skipping apply graph check"
BUILDING_WALKING_APPLY_GRAPH = "Building and walking apply graph"
APPLY_START = "CLI args: \[\]string{\"terraform\", \"apply\""
PLAN_START = "CLI args: \[\]string{\"terraform\", \"plan\""
BUILDING_APPLY_GRAPH_CHECK_ERRORS = "building apply graph to check for errors"
ERROR_LEVEL = "error"


class ProcessType(Enum):
    MAIN_APPLY = "main_apply"
    MAIN_PLAN = "main_plan"
    SUB_APPLY = "sub_apply"
    SUB_PLAN = "sub_plan"
    BUILD_GRAPH_PLAN = "build_graph_plan"
    BUILD_GRAPH_APPLY = "build_graph_apply"


class ActionType(Enum):
    PLAN_START = 0
    PLAN_COMPLETED = 1
    BUILDING_APPLY_GRAPH = 2



class ProcessStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class Parser:
    def __init__(self, df: pd.DataFrame):
        self.df = df
    
    def extract_log_lines_by_timestamps(self, start_time: str, end_time: str, 
                                      process_type: str = None, 
                                      max_lines: int = None) -> pd.DataFrame:
        """
        Извлекает полные строки лога по временным меткам процесса
        
        Args:
            start_time: Начальная временная метка
            end_time: Конечная временная метка  
            process_type: Тип процесса (для информативности)
            max_lines: Максимальное количество строк для вывода
            
        Returns:
            DataFrame с полными записями лога за указанный период
        """
        # Находим записи в указанном временном интервале
        time_mask = (self.df['@timestamp'] >= start_time) & (self.df['@timestamp'] <= end_time)
        log_lines = self.df[time_mask].copy()
        
        if process_type:
            print(f"\n{'='*80}")
            print(f"ПОЛНЫЙ ЛОГ ПРОЦЕССА: {process_type}")
            print(f"Временной интервал: {start_time} - {end_time}")
            print(f"Количество записей: {len(log_lines)}")
            print(f"{'='*80}")
        else:
            print(f"\nЛог за период: {start_time} - {end_time} ({len(log_lines)} записей)")
        
        # Ограничиваем вывод если нужно
        if max_lines and len(log_lines) > max_lines:
            print(f"Показано первых {max_lines} записей из {len(log_lines)}:")
            log_lines = log_lines.head(max_lines)
        
        # Выводим в удобном формате
        for idx, row in log_lines.iterrows():
            level = row['@level'].ljust(8)
            timestamp = row['@timestamp']
            message = row['@message']
            print(f"{timestamp} | {level} | {message}")
        
        return log_lines
    
    def extract_detailed_process_log(self, process_data: Dict[str, Any], 
                                   include_subprocesses: bool = True,
                                   max_lines_per_process: int = 50) -> Dict[str, Any]:
        """
        Извлекает детализированный лог для всего процесса и его подпроцессов
        
        Args:
            process_data: Данные процесса из extract_apply_section или extract_plan_section
            include_subprocesses: Включать ли логи подпроцессов
            max_lines_per_process: Максимум строк на процесс
            
        Returns:
            Словарь с детализированными логами
        """
        detailed_logs = {}
        
        for process_key, main_process in process_data.items():
            print(f"\n{'#'*100}")
            print(f"ДЕТАЛИЗИРОВАННЫЙ АНАЛИЗ: {process_key.upper()}")
            print(f"Статус: {main_process['status']}")
            print(f"Тип: {main_process['type']}") 
            print(f"Время: {main_process['start']} - {main_process['end']}")
            print(f"{'#'*100}")
            
            # Лог главного процесса
            main_log = self.extract_log_lines_by_timestamps(
                main_process['start'], 
                main_process['end'],
                f"Главный процесс {main_process['type']}",
                max_lines_per_process
            )
            
            process_logs = {
                'main_process': {
                    'data': main_process,
                    'log': main_log
                },
                'subprocesses': []
            }
            
            # Логи подпроцессов
            if include_subprocesses and main_process.get('subprocesses'):
                print(f"\n{'─'*80}")
                print(f"ПОДПРОЦЕССЫ ({len(main_process['subprocesses'])}):")
                print(f"{'─'*80}")
                
                for i, subprocess in enumerate(main_process['subprocesses'], 1):
                    print(f"\n[{i}] Подпроцесс: {subprocess['type']} ({subprocess['status']})")
                    sub_log = self.extract_log_lines_by_timestamps(
                        subprocess['start'],
                        subprocess['end'], 
                        f"Подпроцесс {subprocess['type']}",
                        max_lines_per_process // 2
                    )
                    
                    process_logs['subprocesses'].append({
                        'data': subprocess,
                        'log': sub_log
                    })
                    
                    # Рекурсивно обрабатываем вложенные подпроцессы
                    if subprocess.get('subprocesses'):
                        self._extract_nested_subprocess_logs(
                            subprocess, 
                            process_logs,
                            max_lines_per_process // 4,
                            depth=1
                        )
            
            detailed_logs[process_key] = process_logs
        
        return detailed_logs
    
    def _extract_nested_subprocess_logs(self, parent_process: Dict[str, Any], 
                                      process_logs: Dict[str, Any],
                                      max_lines: int, 
                                      depth: int = 1):
        """Рекурсивно извлекает логи вложенных подпроцессов"""
        indent = "  " * depth
        
        for i, subprocess in enumerate(parent_process.get('subprocesses', []), 1):
            print(f"\n{indent}├─ [{i}] Вложенный подпроцесс ({depth} уровень): {subprocess['type']} ({subprocess['status']})")
            
            sub_log = self.extract_log_lines_by_timestamps(
                subprocess['start'],
                subprocess['end'],
                f"{indent}Вложенный подпроцесс {subprocess['type']}",
                max_lines
            )
            
            process_logs['subprocesses'].append({
                'data': subprocess,
                'log': sub_log,
                'depth': depth
            })
            
            # Рекурсивный вызов для более глубоких уровней
            if subprocess.get('subprocesses'):
                self._extract_nested_subprocess_logs(
                    subprocess, 
                    process_logs,
                    max_lines // 2,
                    depth + 1
                )
    
    def save_process_log_to_file(self, process_data: Dict[str, Any], 
                               filename: str = "process_detailed_log.txt",
                               include_subprocesses: bool = True):
        """
        Сохраняет детализированный лог процесса в файл
        """
        with open(filename, 'w', encoding='utf-8') as f:
            # Сохраняем заголовок
            f.write("ДЕТАЛИЗИРОВАННЫЙ ЛОГ ПРОЦЕССОВ TERRAFORM\n")
            f.write("=" * 80 + "\n\n")
            
            for process_key, main_process in process_data.items():
                f.write(f"ПРОЦЕСС: {process_key.upper()}\n")
                f.write(f"Тип: {main_process['type']}\n")
                f.write(f"Статус: {main_process['status']}\n")
                f.write(f"Время: {main_process['start']} - {main_process['end']}\n")
                f.write("-" * 80 + "\n")
                
                # Сохраняем логи главного процесса
                time_mask = (self.df['@timestamp'] >= main_process['start']) & (self.df['@timestamp'] <= main_process['end'])
                main_log = self.df[time_mask]
                
                for _, row in main_log.iterrows():
                    f.write(f"{row['@timestamp']} | {row['@level']:8} | {row['@message']}\n")
                
                # Сохраняем логи подпроцессов
                if include_subprocesses and main_process.get('subprocesses'):
                    f.write(f"\nПОДПРОЦЕССЫ ({len(main_process['subprocesses'])}):\n")
                    self._save_subprocess_logs_to_file(main_process['subprocesses'], f)
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"Детализированный лог сохранен в файл: {filename}")
    
    def _save_subprocess_logs_to_file(self, subprocesses: List[Dict[str, Any]], 
                                    file_handle, depth: int = 1):
        """Рекурсивно сохраняет логи подпроцессов в файл"""
        indent = "  " * depth
        
        for i, subprocess in enumerate(subprocesses, 1):
            file_handle.write(f"\n{indent}ПОДПРОЦЕСС [{i}]: {subprocess['type']} ({subprocess['status']})\n")
            file_handle.write(f"{indent}Время: {subprocess['start']} - {subprocess['end']}\n")
            file_handle.write(f"{indent}{'-' * (60 - len(indent)*2)}\n")
            
            # Сохраняем логи подпроцесса
            time_mask = (self.df['@timestamp'] >= subprocess['start']) & (self.df['@timestamp'] <= subprocess['end'])
            sub_log = self.df[time_mask]
            
            for _, row in sub_log.iterrows():
                file_handle.write(f"{indent}{row['@timestamp']} | {row['@level']:8} | {row['@message']}\n")
            
            # Рекурсивно сохраняем вложенные подпроцессы
            if subprocess.get('subprocesses'):
                self._save_subprocess_logs_to_file(subprocess['subprocesses'], file_handle, depth + 1)
    
    def extract_apply_section(self) -> Dict[str, Any]:
        """Извлекает основной процесс apply и все его подпроцессы"""
        result = {}
        
        # Находим основной процесс apply
        apply_main_start = self.df[self.df['@message'].str.contains(APPLY_START, na=False)]
        
        if apply_main_start.empty:
            print("Не найдено процесса Apply")
            return result
        
        main_start_row = apply_main_start.iloc[0]
        main_start_index = main_start_row.name
        main_start_time = main_start_row['@timestamp']
        
        print(f"Главный Apply процесс начался в: {main_start_time}")
        
        # Ищем конец основного процесса (до конца файла или следующего основного процесса)
        remaining_df = self.df.loc[main_start_index + 1:]
        plan_main_start_after = remaining_df[remaining_df['@message'].str.contains(PLAN_START, na=False)]
        
        if not plan_main_start_after.empty:
            main_end_index = plan_main_start_after.index[0] - 1
        else:
            main_end_index = self.df.index[-1]
        
        main_end_time = self.df.loc[main_end_index]['@timestamp']
        
        # Извлекаем подпроцессы внутри основного процесса
        main_section_df = self.df.loc[main_start_index:main_end_index]
        
        # Извлекаем все подпроцессы
        all_subprocesses = self._extract_subprocesses_from_section(main_section_df)
        
        # Проверяем есть ли ошибки в подпроцессах
        has_error = self._check_errors_in_subprocesses(all_subprocesses)
        
        # Проверяем есть ли ошибки в основном процессе
        main_process_has_error = main_section_df[main_section_df['@level'].str.contains(ERROR_LEVEL, na=False)].any().any()
        if main_process_has_error:
            has_error = True
        
        # Основной процесс apply
        main_process = {
            'start': main_start_time,
            'end': main_end_time,
            'type': ProcessType.MAIN_APPLY.value,
            'status': ProcessStatus.ERROR.value if has_error else ProcessStatus.SUCCESS.value,
            'subprocesses': all_subprocesses
        }
        
        result['apply'] = main_process
        return result
    
    def extract_plan_section(self) -> Dict[str, Any]:
        """Извлекает основной процесс plan и все его подпроцессы"""
        result = {}
        
        # Находим основной процесс plan
        plan_main_start = self.df[self.df['@message'].str.contains(PLAN_START, na=False)]
        
        if plan_main_start.empty:
            print("Не найдено основного процесса Plan")
            return result
        
        main_start_row = plan_main_start.iloc[0]
        main_start_index = main_start_row.name
        main_start_time = main_start_row['@timestamp']
        
        print(f"Главный Plan процесс начался в: {main_start_time}")
        
        # Ищем конец основного процесса (до конца файла или следующего основного процесса)
        remaining_df = self.df.loc[main_start_index + 1:]
        apply_main_start_after = remaining_df[remaining_df['@message'].str.contains(APPLY_START, na=False)]
        
        if not apply_main_start_after.empty:
            main_end_index = apply_main_start_after.index[0] - 1
        else:
            main_end_index = self.df.index[-1]
        
        main_end_time = self.df.loc[main_end_index]['@timestamp']
        
        # Извлекаем подпроцессы внутри основного процесса
        main_section_df = self.df.loc[main_start_index:main_end_index]
        
        # Извлекаем все подпроцессы
        all_subprocesses = self._extract_subprocesses_from_section(main_section_df)
        
        # Проверяем есть ли ошибки в подпроцессах
        has_error = self._check_errors_in_subprocesses(all_subprocesses)
        
        # Проверяем есть ли ошибки в основном процессе
        main_process_has_error = main_section_df[main_section_df['@level'].str.contains(ERROR_LEVEL, na=False)].any().any()
        if main_process_has_error:
            has_error = True
        
        # Основной процесс plan
        main_process = {
            'start': main_start_time,
            'end': main_end_time,
            'type': ProcessType.MAIN_PLAN.value,
            'status': ProcessStatus.ERROR.value if has_error else ProcessStatus.SUCCESS.value,
            'subprocesses': all_subprocesses
        }
        
        result['plan'] = main_process
        return result
    
    def _extract_subprocesses_from_section(self, section_df: pd.DataFrame, depth: int = 0) -> List[Dict[str, Any]]:
        """Извлекает все подпроцессы из секции, включая вложенные"""
        all_subprocesses = []
        
        # Определяем паттерны для разных типов процессов
        process_patterns = [
            {
                'type': ProcessType.SUB_APPLY,
                'start_patterns': [STARTING_APPLY_FOR, APPLY_CALLING_APPLY],
                'end_patterns': [APPLY_CALLING_PLAN]
            },
            {
                'type': ProcessType.SUB_PLAN,
                'start_patterns': [PLAN_CALLING_PLAN],
                'end_patterns': [PLAN_OPERATION_COMPLETED, PLAN_IS_COMPLETE, PLAN_IS_APPLYABLE, PLAN_IS_NOT_APPLYABLE]
            },
            {
                'type': ProcessType.BUILD_GRAPH_PLAN,
                'start_patterns': [BUILDING_WALKING_PLAN_GRAPH],
                'end_patterns': []
            },
            {
                'type': ProcessType.BUILD_GRAPH_APPLY,
                'start_patterns': [BUILDING_WALKING_APPLY_GRAPH, BUILDING_APPLY_GRAPH_CHECK_ERRORS],
                'end_patterns': []
            }
        ]
        
        # Собираем все стартовые точки
        all_starts = []
        for pattern in process_patterns:
            start_condition = section_df['@message'].str.contains('|'.join(pattern['start_patterns']), na=False)
            starts = section_df[start_condition]
            for idx, row in starts.iterrows():
                all_starts.append({
                    'index': idx,
                    'timestamp': row['@timestamp'],
                    'message': row['@message'],
                    'type': pattern['type'],
                    'end_patterns': pattern['end_patterns']
                })
        
        # Сортируем по индексу
        all_starts.sort(key=lambda x: x['index'])
        
        # Обрабатываем подпроцессы последовательно
        processed_indices = set()
        
        for start_info in all_starts:
            if start_info['index'] in processed_indices:
                continue
                
            start_index = start_info['index']
            start_time = start_info['timestamp']
            start_message = start_info['message']
            process_type = start_info['type']
            end_patterns = start_info['end_patterns']
            
            # Ищем конец подпроцесса
            remaining_df = section_df.loc[start_index + 1:]
            
            # Сначала ищем по end_patterns в @message
            end_condition_message = remaining_df['@message'].str.contains('|'.join(end_patterns), na=False)
            end_rows_message = remaining_df[end_condition_message]
            
            # Ищем ошибки в @level
            end_condition_error = remaining_df['@level'].str.contains(ERROR_LEVEL, na=False)
            end_rows_error = remaining_df[end_condition_error]
            
            # Выбираем ближайший конец
            end_rows = pd.concat([end_rows_message, end_rows_error]).sort_index()
            
            if not end_rows.empty:
                end_index = end_rows.index[0]
                end_row = end_rows.iloc[0]
                end_time = end_row['@timestamp']
                end_message = end_row['@message']
                status = ProcessStatus.ERROR.value if end_row['@level'] == ERROR_LEVEL else ProcessStatus.SUCCESS.value
            else:
                end_index = section_df.index[-1]
                end_time = section_df.loc[end_index]['@timestamp']
                end_message = "END_OF_SECTION"
                subprocess_section = section_df.loc[start_index:end_index]
                has_error_in_subprocess = subprocess_section[subprocess_section['@level'].str.contains(ERROR_LEVEL, na=False)].any().any()
                status = ProcessStatus.ERROR.value if has_error_in_subprocess else ProcessStatus.SUCCESS.value
            
            # Создаем подпроцесс
            subprocess = {
                'start': start_time,
                'end': end_time,
                'type': process_type.value,
                'status': status,
                'start_message': start_message,
                'end_message': end_message,
                'subprocesses': []
            }
            
            # Извлекаем вложенные подпроцессы (только если есть промежуток)
            if start_index < end_index:
                nested_section = section_df.loc[start_index + 1:end_index - 1]
                if not nested_section.empty:
                    nested_subprocesses = self._extract_subprocesses_from_section(nested_section, depth + 1)
                    subprocess['subprocesses'] = nested_subprocesses
            
            all_subprocesses.append(subprocess)
            processed_indices.add(start_index)
            
            indent = "  " * depth
            status_str = "ERROR" if status == ProcessStatus.ERROR.value else "SUCCESS"
            print(f"{indent}Подпроцесс {process_type.value} ({status_str}): {start_time} - {end_time}")
        
        return all_subprocesses
    
    def _check_errors_in_subprocesses(self, subprocesses: List[Dict[str, Any]]) -> bool:
        """Рекурсивно проверяет есть ли ошибки в подпроцессах"""
        for subprocess in subprocesses:
            if subprocess.get('status') == ProcessStatus.ERROR.value:
                return True
            if 'subprocesses' in subprocess and subprocess['subprocesses']:
                if self._check_errors_in_subprocesses(subprocess['subprocesses']):
                    return True
        return False