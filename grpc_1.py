from plugins.models import plugin_pb2
from plugins.manager import PluginManager


plugin_manager = PluginManager()

class LogEntryConverter:
    @staticmethod
    def from_json_to_proto(json_entries):
        proto_entries = []
        for entry in json_entries:
            proto_entry = plugin_pb2.LogEntry(
                level=entry.get('@level', 'info'),
                message=entry.get('@message', ''),
                timestamp=entry.get('@timestamp', ''),
                metadata=entry.get('metadata', {})
            )
            proto_entries.append(proto_entry)
        return proto_entries

