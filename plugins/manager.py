
import logging
from typing import Any, Dict, List

from plugins_config import PLUGINS_CONFIG, PluginClient


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, PluginClient] = {}
        self.initialize_plugins()
    
    def initialize_plugins(self):
        """Инициализация плагинов"""
        for name, config in PLUGINS_CONFIG.items():
            plugin = PluginClient(name, config)
            if plugin.connect():
                self.plugins[name] = plugin
                logging.info(f"✅ Plugin {name} initialized and connected")
            else:
                logging.warning(f"❌ Plugin {name} failed to initialize")
    
    def get_available_plugins(self) -> Dict[str, Dict]:
        """Получение списка доступных плагинов с их статусом"""
        available = {}
        for name, plugin in self.plugins.items():
            # Проверяем здоровье плагина
            health = plugin.health_check()
            
            # Получаем информацию о плагине
            info = plugin.get_info()
            
            available[name] = {
                "name": info.get('name', name),
                "version": info.get('version', 'unknown'),
                "description": info.get('description', plugin.config['description']),
                "capabilities": info.get('capabilities', plugin.config['capabilities']),
                "supported_parameters": info.get('supported_parameters', []),
                "status": health.get('status', 'UNKNOWN'),
                "endpoint": plugin.endpoint,
                "connected": plugin.connected,
                "last_health_check": plugin.last_health_check.isoformat() if plugin.last_health_check else None
            }
            
            # Добавляем ошибку если есть
            if 'error' in info:
                available[name]['error'] = info['error']
            if 'error' in health:
                available[name]['health_error'] = health['error']
        
        return available
    
    def process_with_plugins(self, log_entries: List[Dict], plugin_names: List[str] = None, parameters: Dict = None) -> Dict[str, Any]:
        """Обработка логов через выбранные плагины"""
        if plugin_names is None:
            plugin_names = list(self.plugins.keys())
        
        if parameters is None:
            parameters = {}
        
        results = {}
        all_findings = []
        all_metrics = {}
        failed_plugins = []
        
        for plugin_name in plugin_names:
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                
                if not plugin.connected:
                    failed_plugins.append(plugin_name)
                    continue
                
                logging.info(f"🔄 Processing with plugin: {plugin_name}")
                
                # Передаем параметры конкретному плагину
                plugin_params = parameters.get(plugin_name, {})
                result = plugin.process_logs(log_entries, plugin_params)
                
                if 'error' in result:
                    failed_plugins.append(plugin_name)
                    results[plugin_name] = result
                    logging.error(f"❌ Plugin {plugin_name} failed: {result['error']}")
                else:
                    results[plugin_name] = result
                    
                    if 'findings' in result:
                        for finding in result['findings']:
                            finding['plugin'] = plugin_name
                            all_findings.append(finding)
                    
                    if 'metrics' in result:
                        all_metrics[plugin_name] = result['metrics']
                    
                    logging.info(f"✅ Plugin {plugin_name} completed successfully")
        
        # Сортировка findings по severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'LOW'), 4))
        
        return {
            "findings": all_findings,
            "metrics": all_metrics,
            "total_findings": len(all_findings),
            "plugins_used": list(results.keys()),
            "failed_plugins": failed_plugins,
            "successful_plugins": [p for p in plugin_names if p not in failed_plugins],
            "total_plugins_called": len(plugin_names)
        }
    
    def refresh_connections(self):
        """Обновление соединений со всеми плагинами"""
        logging.info("🔄 Refreshing plugin connections...")
        for name, plugin in self.plugins.items():
            plugin.close()
            plugin.connect()
    
    def close_all(self):
        """Закрытие всех соединений"""
        for plugin in self.plugins.values():
            plugin.close()
        logging.info("All plugin connections closed")