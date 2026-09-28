"""Minimal OptiQuake Local community plugin example."""
from plugin_api import VibrationEvent

class ConsolePlugin:
    name = "example-console"
    version = "0.1.0"
    api_version = "1"

    def on_start(self, context):
        print(f"[plugin:{self.name}] started for {context.get('camera')}")

    def on_event(self, event: VibrationEvent):
        print(f"[plugin:{self.name}] vibration z={event.robust_z:.2f} score={event.score:.4f}")

    def on_stop(self):
        print(f"[plugin:{self.name}] stopped")

def create_plugin():
    return ConsolePlugin()
