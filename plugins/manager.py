from typing import Dict, List

from plugins_config import PLUGINS_CONFIG, PluginClient


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, PluginClient] = {}
        self._initialize_plugins()
    
    def _initialize_plugins(self):
        """Инициализация плагинов"""
        for name, config in PLUGINS_CONFIG.items():
            plugin = PluginClient(name, config)
            if plugin.connect():
                self.plugins[name] = plugin
                print(f"✅ Plugin {name} initialized")
            else:
                print(f"❌ Plugin {name} failed to initialize")
    
    def get_available_plugins(self) -> Dict:
        """Получение списка доступных плагинов"""
        available = {}
        for name, plugin in self.plugins.items():
            health = plugin.health_check()
            available[name] = {
                "name": name,
                "version": "1.0.0",
                "description": plugin.config['description'],
                "capabilities": plugin.config['capabilities'],
                "supported_parameters": ["threshold", "strict_mode"],
                "status": health['status'],
                "endpoint": plugin.endpoint
            }
        return available
    
    def process_with_plugins(self, log_entries: List[Dict], plugin_names: List[str] = None) -> Dict:
        """Обработка логов через выбранные плагины"""
        if plugin_names is None:
            plugin_names = list(self.plugins.keys())
        
        results = {}
        all_findings = []
        all_metrics = {}
        
        for plugin_name in plugin_names:
            if plugin_name in self.plugins:
                print(f"Processing with plugin: {plugin_name}")
                result = self.plugins[plugin_name].process_logs(log_entries)
                results[plugin_name] = result
                
                if 'findings' in result:
                    for finding in result['findings']:
                        finding['plugin'] = plugin_name
                        all_findings.append(finding)
                
                if 'metrics' in result:
                    all_metrics[plugin_name] = result['metrics']
        
        # Сортировка findings по severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'LOW'), 4))
        
        return {
            "findings": all_findings,
            "metrics": all_metrics,
            "total_findings": len(all_findings),
            "plugins_used": list(results.keys())
        }