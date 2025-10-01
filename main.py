import os
from flask import Flask, request, jsonify
import json
from datetime import datetime
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'  # Directory to save uploaded files
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size (e.g., 16MB)

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_path(filename):
    """Get safe file path within upload folder"""
    safe_filename = secure_filename(filename)
    return os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

def file_exists(filename):
    """Check if file exists in upload folder"""
    filepath = get_file_path(filename)
    return os.path.exists(filepath)

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

    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only JSON files are allowed.'}), 400
    
    json_data = [json.loads(i) for i in file.readlines()]

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'w') as f:
        json.dump(json_data, f)

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
def get_log_file(filename):
    """Get log file by filename"""
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    if not file_exists(filename):
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)