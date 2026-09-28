class DemoPlugin:
    name = "community-demo"
    version = "0.1.0"
    api_version = "1"

    def on_start(self, context):
        self.camera = context.get("camera")

    def on_event(self, event):
        print(f"[community-demo] {event.event} z={event.robust_z}")

    def on_stop(self):
        pass

def create_plugin():
    return DemoPlugin()
