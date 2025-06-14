import threading
import signal
import random
import pika
import json
from typing import Any, Dict
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import load_config

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
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

class PVSimulator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
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
            print("[PV_SIM] Connected to RabbitMQ.")
        except Exception as e:
            print(f"[PV_SIM] Failed to connect to RabbitMQ: {e}")
            raise

    def close_rabbitmq(self) -> None:
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            print("[PV_SIM] Closed RabbitMQ connection.")
        except Exception as e:
            print(f"[PV_SIM] Error closing RabbitMQ connection: {e}")

    @staticmethod
    def generate_pv_value(self) -> float:
        # TODO: Generate based on real PV profile
        return round(random.uniform(0.0, 10.0), 3)

    def handle_meter_message(self, ch, method, properties, body) -> None:
        try:
            meter_msg = json.loads(body)
            pv_value = self.generate_pv_value()
            print(f"[PV_SIM] Meter msg: {meter_msg}")
            print(f"PV value: {pv_value} kW")
            # TODO: File writing will be added in the next block
        except Exception as e:
            print(f"[PV_SIM] Failed to process message: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self) -> None:
        self.channel.basic_consume(
            queue=self.config["RABBITMQ_QUEUE"],
            on_message_callback=self.handle_meter_message
        )
        print("[PV_SIM] Waiting for messages.")
        try:
            self.channel.start_consuming()
        except Exception as e:
            print(f"[PV_SIM] Error in consuming: {e}")
        finally:
            self.stop()

    def stop(self):
        if self.channel and self.channel.is_open:
            try:
                print("[PV_SIM] Stopping consuming...")
                self.channel.close()
            except Exception as e:
                print(f"[PV_SIM] Error closing channel: {e}")
        if self.connection and self.connection.is_open:
            print("[PV_SIM] Closing connection...")
            try:
                self.connection.close()
            except Exception as e:
                print(f"[PV_SIM] Error closing connection: {e}")

def setup_signal_handlers(pv_simulator: PVSimulator) -> None:
    def handler(signum, frame):
        print("[PV_SIM] Received shutdown signal.")
        pv_simulator.channel.stop_consuming()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def main() -> None:
    config = load_config()
    health_server = start_health_server(config["HEALTH_PORT"])

    pv_sim = PVSimulator(config)
    setup_signal_handlers(pv_sim)
    pv_sim.run()

    health_server.shutdown()

if __name__ == "__main__":
    main()
