import os
import json

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_cors import CORS

from parser import Parser
from utils import get_apply_file_path, get_plan_file_path, is_allowed_file, is_file_exists, get_file_path
from settings import UPLOAD_FOLDER, MAX_CONTENT_LENGTH

import pandas as pd

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
