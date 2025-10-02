
import atexit
import os
import signal
import subprocess
import sys
import time


processes = []

def start_plugin(script_name, port):
    """Запуск плагина в отдельном процессе"""
    env = os.environ.copy()
    
    # В Docker используем прямой запуск Python
    cmd = [sys.executable, script_name]
    process = subprocess.Popen(cmd, env=env)
    processes.append(process)
    
    # Даем больше времени на запуск в Docker
    time.sleep(3)
    
    # Проверяем, что процесс жив
    if process.poll() is None:
        print(f"✅ Started {script_name} on port {port}")
        return process
    else:
        print(f"❌ Failed to start {script_name}")
        processes.remove(process)
        return None

def cleanup():
    """Остановка всех процессов"""
    print("\n🛑 Stopping plugins...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            print(f"✅ Stopped process {process.pid}")
        except subprocess.TimeoutExpired:
            print(f"❌ Force killing process {process.pid}")
            process.kill()
    print("✅ All plugins stopped")

def main():
    # Регистрируем cleanup при выходе
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    
    print("🚀 Starting Terraform Analysis Plugins...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"📁 Contents: {os.listdir('.')}")
    
    # Проверяем существование директории плагинов
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        print(f"❌ Plugins directory not found: {plugins_dir}")
        return
    
    print(f"📁 Plugins directory contents: {os.listdir(plugins_dir)}")
    
    # Запускаем плагины
    plugins = [
        ("plugins/error_aggregator.py", 50051),
        ("plugins/security_scanner.py", 50052),
        ("plugins/performance_analyzer.py", 50053),
    ]
    
    started_count = 0
    for script, port in plugins:
        if not os.path.exists(script):
            print(f"❌ Plugin script not found: {script}")
            continue
            
        process = start_plugin(script, port)
        if process:
            started_count += 1
    
    print(f"\n🎉 Started {started_count}/{len(plugins)} plugins")
    
    if started_count == 0:
        print("❌ No plugins were started successfully")
        return
    
    print("\nPress Ctrl+C to stop all plugins")
    
    # Бесконечный цикл чтобы процессы не завершались
    try:
        while True:
            # Проверяем статус процессов и перезапускаем упавшие
            for i, process in enumerate(processes[:]):
                if process.poll() is not None:
                    print(f"⚠️ Plugin died, restarting...")
                    # Находим соответствующий скрипт и порт
                    script, port = plugins[i]
                    new_process = start_plugin(script, port)
                    if new_process:
                        processes[i] = new_process
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")

if __name__ == '__main__':
    main()