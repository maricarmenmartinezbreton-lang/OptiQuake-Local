import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plugin_api import VibrationEvent
from plugin_loader import PluginManager

manager = PluginManager()
manager.load_directory(str(ROOT / "plugins"))
assert manager.describe()[0]["name"] == "example-console"
assert manager.start({"camera": "test-camera", "fps": 60}) == []
errors = manager.emit(VibrationEvent(t=1.0, score=2.0, baseline=0.5, robust_z=10.0))
assert errors == []
assert manager.stop() == []
print("PLUGIN_TEST_OK")
