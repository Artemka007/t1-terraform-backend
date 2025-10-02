import os
import json

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_cors import CORS

from grpc_1 import LogEntryConverter
from parser import Parser
from plugins.manager import PluginManager
import run_plugins
from utils import get_apply_file_path, get_plan_file_path, is_allowed_file, is_file_exists, get_file_path
from settings import UPLOAD_FOLDER, MAX_CONTENT_LENGTH
import atexit

import pandas as pd

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'apply'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'plan'), exist_ok=True)

# Инициализация менеджера плагинов
plugin_manager = PluginManager()
atexit.register(plugin_manager.close_all)

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/v1/plugins', methods=['GET'])
def get_plugins():
    """Получение списка доступных плагинов"""
    try:
        plugins = plugin_manager.get_available_plugins()
        return jsonify({
            'status': 'success',
            'plugins': plugins,
            'total_plugins': len(plugins)
        })
    except Exception as e:
        print(f"Failed to get plugins: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'plugins': {}
        }), 500
    

@app.route('/api/v1/files', methods=['GET'])
def get_files():
    """Получение списка доступных файлов"""
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = get_file_path(filename)
            if os.path.isfile(filepath) and is_allowed_file(filename):
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'uploaded_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'can_analyze': True
                })
        
        return jsonify({
            'status': 'success',
            'files': files,
            'total_files': len(files)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'files': []
        }), 500

@app.route('/api/v1/analyze/', methods=['POST'])
def analyze_file():
    """Анализ файла с помощью плагинов"""
    try:
        filename = request.form.get('filename', '')
        if not is_file_exists(filename):
            return jsonify({'error': 'File not found'}), 404

        # Получаем список плагинов из запроса
        plugins = request.form.get('plugins', '')
        plugin_list = [p.strip() for p in plugins.split(',') if p.strip()]
        
        # Загружаем файл
        filepath = get_file_path(filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # Конвертируем в формат для плагинов
        log_entries = []
        for entry in log_data:
            if isinstance(entry, dict):
                log_entries.append({
                    'level': entry.get('@level', 'info'),
                    'message': entry.get('@message', ''),
                    'timestamp': entry.get('@timestamp', ''),
                    'metadata': entry
                })
        
        # Запускаем анализ
        results = plugin_manager.process_with_plugins(log_entries, plugin_list)
        
        return jsonify({
            'status': 'success',
            'plugins_used': results['plugins_used'],
            'results': results
        })
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
    

@app.route('/api/v1/logs/upload', methods=['POST'])
def upload_json():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file or not is_allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only JSON files are allowed.'}), 400

    json_data = [json.loads(i) for i in file.readlines()]

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'w') as f:
        json.dump(json_data, f)
    
    parser = Parser(pd.json_normalize(json_data))

    a = parser.extract_apply_section()
    p = parser.extract_plan_section()
    
    apply_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'apply', filename)
    plan_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'apply', filename)

    if a:
        with open(apply_filepath, 'w') as f:
            json.dump(a, f)
    if p:
        with open(plan_filepath, 'w') as f:
            json.dump(p, f)

    try:
        return jsonify({
            'id': filename,
            'fileName': filename,
            'size': 0,
            'uploadedAt': 'today',
            'totalEntries': 0,
            'status': 'success',
        }), 200
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400


@app.route('/api/v1/logs/file/<filename>', methods=['GET'])
def get_log_file(filename: str):
    """Get log file by filename"""
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400

    if not is_file_exists(filename):
        return jsonify({'error': 'File not found'}), 404

    filepath = get_file_path(filename)

    try:
        # Read and return the JSON data
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        return jsonify({
            'logs': json_data,
            'fileName': filename,
            'totalEntries': len(json_data) if isinstance(json_data, list) else 1,
            'status': 'success'
        }), 200

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Error reading JSON file: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500



@app.route('/api/v1/sections/file/<filename>', methods=['GET'])
def get_apply_plan_sections_file(filename: str):
    """Get log file by filename"""
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400

    afilepath = get_apply_file_path(filename)
    pfilepath = get_plan_file_path(filename)

    res = {'apply': None, 'plan': None}

    try:
        with open(afilepath, 'r', encoding='utf-8') as f:
            res = json.load(f)
    except Exception:
        pass

    return jsonify(res), 200


@app.route('/api/v1/analyze/<filename>', methods=['POST'])
def analyze_with_plugins(filename: str):
    """Основной endpoint для анализа с плагинами"""
    with open(get_file_path(filename, 'r')) as file:
        # Загрузка логов
        log_data = json.load(file)
        
        # Параметры
        plugins = request.form.get('plugins', '').split(',')
        if not plugins or plugins == ['']:
            plugins = None
        
        # Обновление доступных плагинов
        plugin_manager.discover_plugins()
        
        # Конвертация логов
        log_entries = LogEntryConverter.from_json_to_proto(log_data)
        
        # Обработка через плагины
        results = plugin_manager.process_with_plugins(log_entries, plugins)
        
        # Агрегация результатов
        aggregated_results = aggregate_results(results)
        
        return jsonify({
            'status': 'success',
            'plugins_used': list(results.keys()),
            'results': aggregated_results
        })

@app.route('/api/v1/plugins', methods=['GET'])
def list_plugins():
    """Список доступных плагинов"""
    plugin_manager.discover_plugins()
    
    plugins_info = {}
    for name, stub in plugin_manager.plugins.items():
        try:
            info = plugin_manager.get_plugin_info(name)
            plugins_info[name] = {
                'name': info.name,
                'version': info.version,
                'description': info.description,
                'capabilities': list(info.capabilities)
            }
        except:
            plugins_info[name] = {'error': 'Cannot get plugin info'}
    
    return jsonify({'plugins': plugins_info})

def aggregate_results(plugin_results):
    """Агрегация результатов от всех плагинов"""
    all_findings = []
    summary_metrics = {}
    
    for plugin_name, response in plugin_results.items():
        if hasattr(response, 'findings'):
            for finding in response.findings:
                finding_dict = {
                    'plugin': plugin_name,
                    'type': finding.type,
                    'severity': finding.severity,
                    'message': finding.message,
                    'resource': finding.resource,
                    'recommendations': list(finding.recommendations)
                }
                all_findings.append(finding_dict)
        
        if hasattr(response, 'metrics'):
            summary_metrics[plugin_name] = dict(response.metrics)
    
    # Сортировка по severity
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    all_findings.sort(key=lambda x: severity_order.get(x['severity'], 4))
    
    return {
        'findings': all_findings,
        'metrics': summary_metrics,
        'total_findings': len(all_findings)
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
