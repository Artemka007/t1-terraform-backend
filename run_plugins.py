import threading
import subprocess
import time
import sys
import os

def run_plugin(plugin_script, port):
    """Запуск плагина в отдельном процессе"""
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    
    cmd = [sys.executable, plugin_script, str(port)]
    process = subprocess.Popen(cmd, env=env)
    return process

def run_plugins():
    # Запуск плагинов
    plugins = [
        ('plugins/error_aggregator.py', 50051),
        ('plugins/security_scanner.py', 50052),
    ]
    
    processes = []
    for plugin_script, port in plugins:
        print(f"Starting {plugin_script} on port {port}")
        process = run_plugin(plugin_script, port)
        processes.append(process)
        time.sleep(1)  # Даем время на запуск
