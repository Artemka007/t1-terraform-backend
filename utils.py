import os

from werkzeug.utils import secure_filename

from settings import UPLOAD_FOLDER, ALLOWED_EXTENSIONS


def is_allowed_file(filename: str):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_path(filename: str):
    """Get safe file path within upload folder"""
    safe_filename = secure_filename(filename)
    return os.path.join(UPLOAD_FOLDER, safe_filename)


def get_apply_file_path(filename: str):
    """Get safe file path within upload folder"""
    safe_filename = secure_filename(filename)
    return os.path.join(UPLOAD_FOLDER, 'apply', safe_filename)


def get_plan_file_path(filename: str):
    """Get safe file path within upload folder"""
    safe_filename = secure_filename(filename)
    return os.path.join(UPLOAD_FOLDER, 'plan', safe_filename)


def is_file_exists(filename: str):
    """Check if file exists in upload folder"""
    filepath = get_file_path(filename)
    return os.path.exists(filepath)
