import subprocess
import sys
import os
import time
import signal
import atexit

# Добавляем текущую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

processes = []

def start_plugin(script_name, port):
    """Запуск плагина в отдельном процессе"""
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
    
    cmd = [sys.executable, script_name]
    process = subprocess.Popen(cmd, env=env)
    processes.append(process)
    
    # Даем время на запуск
    time.sleep(2)
    
    print(f"✅ Started {script_name} on port {port}")
    return process

def cleanup():
    """Остановка всех процессов"""
    print("\n🛑 Stopping plugins...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
    print("✅ All plugins stopped")

def main():
    # Регистрируем cleanup при выходе
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    
    print("🚀 Starting Terraform Analysis Plugins...")
    
    # Запускаем плагины
    plugins = [
        ("plugins/error_aggregator.py", 50051),
        ("plugins/security_scanner.py", 50052),
        ("plugins/performance_analyzer.py", 50053),
    ]
    
    for script, port in plugins:
        if not os.path.exists(script):
            print(f"❌ Plugin script not found: {script}")
            continue
        start_plugin(script, port)
    
    print(f"\n🎉 All plugins started! Available plugins:")
    print("   - error-aggregator (localhost:50051)")
    print("   - security-scanner (localhost:50052)") 
    print("   - performance-analyzer (localhost:50053)")
    print("\nPress Ctrl+C to stop all plugins")
    
    # Бесконечный цикл чтобы процессы не завершались
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()