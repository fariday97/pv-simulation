import time
import threading
import signal
import random
from typing import Any, Dict
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import load_config

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(port: int) -> HTTPServer:
    server = HTTPServer(('', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class MeterPublisher:
    def __init__(self, config: Dict[str, Any], stop_event: threading.Event):
        self.config = config
        self.stop_event = stop_event
        # TODO: Rabbit connection initialization

    def generate_meter_value(self) -> float:
        return round(random.uniform(0.0, 10.0), 3)

    def publish(self, timestamp: float, value: float) -> None:
        # For now, just print
        print(f"[METER] {timestamp}: Meter={value} kW")
        # TODO: Publish to Rabbit

    def run(self) -> None:
        interval = self.config["METER_INTERVAL"]
        simulation_duration = self.config["SIMULATION_DURATION"]
        start_time = time.time()
        while True:
            if self.stop_event.is_set():
                break

            now = time.time()
            elapsed = now - start_time
            if elapsed >= simulation_duration:
                print("24 hours reached, shutting down gracefully.")
                break

            timestamp = now
            value = self.generate_meter_value()
            self.publish(timestamp, value)
            time.sleep(interval)

def setup_signal_handlers(stop_event: threading.Event) -> None:
    def handler(signum, frame):
        print("[METER] Received shutdown signal.")
        stop_event.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def main() -> None:
    config = load_config()
    stop_event = threading.Event()
    setup_signal_handlers(stop_event)
    health_server = start_health_server(config["HEALTH_PORT"])

    publisher = MeterPublisher(config, stop_event)
    publisher.run()

    health_server.shutdown()

if __name__ == "__main__":
    main()
