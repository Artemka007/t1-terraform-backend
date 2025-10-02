import grpc
from concurrent import futures

from models import plugin_pb2
from models import plugin_pb2_grpc

class BasePlugin(plugin_pb2_grpc.PluginServiceServicer):
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description
        self.capabilities = []
        self.supported_parameters = []
        
    def GetInfo(self, request, context):
        return plugin_pb2.InfoResponse(
            name=self.name,
            version=self.version,
            description=self.description,
            capabilities=self.capabilities,
            supported_parameters=self.supported_parameters
        )
    
    def HealthCheck(self, request, context):
        return plugin_pb2.HealthResponse(
            status="SERVING",
            timestamp=self._get_timestamp()
        )
    
    def Process(self, request, context):
        """Базовый метод обработки - должен быть переопределен"""
        raise NotImplementedError("Subclasses must implement Process method")
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()
    
    def serve(self, port: int = 50051):
        """Запуск gRPC сервера плагина"""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        plugin_pb2_grpc.add_PluginServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        print(f"Plugin {self.name} started on port {port}")
        server.wait_for_termination()