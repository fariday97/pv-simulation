import time
import threading
import signal
import random
import pika
import json
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
        self.connection = None
        self.channel = None
        self.setup_rabbitmq()

    def setup_rabbitmq(self) -> None:
        try:
            parameters = pika.ConnectionParameters(
                host=self.config["RABBITMQ_HOST"],
                port=self.config["RABBITMQ_PORT"],
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.config["RABBITMQ_QUEUE"], durable=True)
            print("[METER] Connected to RabbitMQ.")
        except Exception as e:
            print(f"[METER] Failed to connect to RabbitMQ: {e}")
            raise

    def close_rabbitmq(self) -> None:
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            print("[METER] Closed RabbitMQ connection.")
        except Exception as e:
            print(f"[METER] Error closing RabbitMQ connection: {e}")
            raise

    @staticmethod
    def generate_meter_value() -> float:
        return round(random.uniform(0.0, 10.0), 3)

    def publish(self, timestamp: float, value: float) -> None:
        message = {
            "timestamp": timestamp,
            "meter_value": value
        }
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=self.config["RABBITMQ_QUEUE"],
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # retain message
            )
            print(f"[METER] Published: {message}")
        except Exception as e:
            print(f"[METER] Failed to publish message: {e}")

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
                print("Simulation duration reached, shutting down gracefully.")
                break

            timestamp = now
            value = self.generate_meter_value()
            self.publish(timestamp, value)
            time.sleep(interval)
        self.close_rabbitmq()

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
