from flask import Flask, request, jsonify
import json
from datetime import datetime
from collections import Counter
import re

app = Flask(__name__)

class TerraformLogAnalyzer:
    def __init__(self, log_data):
        self.log_data = log_data
        self.analysis = {}
    
    def analyze(self):
        """Основной метод анализа лога"""
        self._extract_basic_info()
        self._analyze_log_levels()
        self._analyze_providers()
        self._analyze_resources()
        self._analyze_errors_warnings()
        self._analyze_performance()
        self._analyze_dependencies()
        
        return self.analysis
    
    def _extract_basic_info(self):
        """Извлечение базовой информации"""
        terraform_version = None
        go_version = None
        command = None
        timestamp = None
        
        for entry in self.log_data:
            if entry.get('@level') == 'info':
                if 'Terraform version' in entry.get('@message', ''):
                    terraform_version = entry['@message'].split(': ')[1]
                elif 'Go runtime version' in entry.get('@message', ''):
                    go_version = entry['@message'].split(': ')[1]
                elif 'CLI args' in entry.get('@message', ''):
                    command = entry['@message']
            
            if '@timestamp' in entry and not timestamp:
                timestamp = entry['@timestamp']
        
        self.analysis['basic_info'] = {
            'terraform_version': terraform_version,
            'go_version': go_version,
            'command': command,
            'timestamp': timestamp,
            'total_entries': len(self.log_data)
        }
    
    def _analyze_log_levels(self):
        """Анализ уровней логгирования"""
        levels = Counter(entry.get('@level', 'unknown') for entry in self.log_data)
        self.analysis['log_levels'] = dict(levels)
    
    def _analyze_providers(self):
        """Анализ информации о провайдерах"""
        providers = set()
        provider_versions = {}
        
        for entry in self.log_data:
            message = entry.get('@message', '')
            
            # Поиск информации о провайдерах
            if 'using' in message and 'github.com/' in message:
                match = re.search(r'using\s+([^\s]+)\s+([^\s]+)', message)
                if match:
                    provider = match.group(1)
                    version = match.group(2)
                    providers.add(provider)
                    provider_versions[provider] = version
            
            # Поиск загруженных провайдеров
            if 'found' in message and 'terraform/providers' in message:
                match = re.search(r'found\s+([^\s]+)\s+([^\s]+)', message)
                if match:
                    provider = match.group(1)
                    version = match.group(2)
                    providers.add(provider)
                    provider_versions[provider] = version
        
        self.analysis['providers'] = {
            'count': len(providers),
            'list': list(providers),
            'versions': provider_versions
        }
    
    def _analyze_resources(self):
        """Анализ ресурсов и data sources"""
        resources = set()
        data_sources = set()
        
        for entry in self.log_data:
            message = entry.get('@message', '')
            
            # Поиск ресурсов
            if 'Found resource type' in message:
                match = re.search(r'tf_resource_type="([^"]+)"', message)
                if match:
                    resources.add(match.group(1))
            
            # Поиск data sources
            if 'Found data source type' in message:
                match = re.search(r'tf_data_source_type="([^"]+)"', message)
                if match:
                    data_sources.add(match.group(1))
        
        self.analysis['resources'] = {
            'total': len(resources) + len(data_sources),
            'managed_resources': list(resources),
            'data_sources': list(data_sources),
            'managed_count': len(resources),
            'data_count': len(data_sources)
        }
    
    def _analyze_errors_warnings(self):
        """Анализ ошибок и предупреждений"""
        errors = []
        warnings = []
        
        for entry in self.log_data:
            level = entry.get('@level')
            message = entry.get('@message', '')
            
            if level == 'error':
                errors.append({
                    'message': message,
                    'timestamp': entry.get('@timestamp')
                })
            elif level == 'warning':
                warnings.append({
                    'message': message,
                    'timestamp': entry.get('@timestamp')
                })
        
        self.analysis['issues'] = {
            'errors': {
                'count': len(errors),
                'list': errors
            },
            'warnings': {
                'count': len(warnings),
                'list': warnings
            }
        }
    
    def _analyze_performance(self):
        """Анализ производительности"""
        timestamps = []
        
        for entry in self.log_data:
            if '@timestamp' in entry:
                try:
                    # Парсинг timestamp (упрощенный)
                    ts_str = entry['@timestamp'].replace('+03:00', '')
                    dt = datetime.fromisoformat(ts_str)
                    timestamps.append(dt)
                except:
                    continue
        
        if len(timestamps) >= 2:
            duration = max(timestamps) - min(timestamps)
            self.analysis['performance'] = {
                'start_time': min(timestamps).isoformat(),
                'end_time': max(timestamps).isoformat(),
                'duration_seconds': duration.total_seconds()
            }
        else:
            self.analysis['performance'] = {
                'duration_seconds': 0,
                'start_time': None,
                'end_time': None
            }
    
    def _analyze_dependencies(self):
        """Анализ зависимостей между ресурсами"""
        dependencies = []
        
        for entry in self.log_data:
            message = entry.get('@message', '')
            
            if 'references' in message:
                match = re.search(r'\"([^\"]+)\" references: \[([^\]]*)\]', message)
                if match:
                    resource = match.group(1)
                    deps = [dep.strip() for dep in match.group(2).split(',') if dep.strip()]
                    if deps:
                        dependencies.append({
                            'resource': resource,
                            'dependencies': deps
                        })
        
        self.analysis['dependencies'] = dependencies

# API endpoints
@app.route('/api/analyze', methods=['POST'])
def analyze_log():
    """Основной endpoint для анализа лога"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be JSON'}), 400
        
        # Чтение и парсинг JSON
        try:
            log_data = json.load(file)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        # Анализ лога
        analyzer = TerraformLogAnalyzer(log_data)
        analysis = analyzer.analyze()
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/stats', methods=['POST'])
def get_stats():
    """Получение статистики по логу"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        log_data = json.load(file)
        
        # Базовая статистика
        total_entries = len(log_data)
        levels = Counter(entry.get('@level', 'unknown') for entry in log_data)
        
        # Время выполнения
        timestamps = []
        for entry in log_data:
            if '@timestamp' in entry:
                try:
                    ts_str = entry['@timestamp'].replace('+03:00', '')
                    dt = datetime.fromisoformat(ts_str)
                    timestamps.append(dt)
                except:
                    continue
        
        duration = max(timestamps) - min(timestamps) if timestamps else 0
        
        return jsonify({
            'total_entries': total_entries,
            'log_levels': dict(levels),
            'duration_seconds': duration.total_seconds() if timestamps else 0,
            'time_range': {
                'start': min(timestamps).isoformat() if timestamps else None,
                'end': max(timestamps).isoformat() if timestamps else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_config():
    """Валидация конфигурации Terraform"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        log_data = json.load(file)
        
        errors = []
        warnings = []
        
        for entry in log_data:
            level = entry.get('@level')
            message = entry.get('@message', '')
            
            if level == 'error':
                errors.append(message)
            elif level == 'warning':
                warnings.append(message)
        
        return jsonify({
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'error_count': len(errors),
            'warning_count': len(warnings)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)