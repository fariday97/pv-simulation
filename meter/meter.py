import time
import signal
import random
import pika
import json
import sys
from threading import Event
from typing import Any, Dict, Optional, TYPE_CHECKING
from health_server import start_health_server
from config import load_config
from logging_utils import setup_logging, get_log_level

if TYPE_CHECKING:
    from pika.adapters.blocking_connection import BlockingConnection, \
    BlockingChannel
    from logging import Logger

class MeterPublisher:
    def __init__(self, config: Dict[str, Any], stop_event: Event,
                 logger: "Logger") -> None:
        self.config = config
        self.stop_event = stop_event
        self.logger = logger
        self.connection: Optional["BlockingConnection"] = None
        self.channel: Optional["BlockingChannel"] = None
        self.setup_rabbitmq()

    def setup_rabbitmq(self) -> None:
        try:
            parameters = pika.ConnectionParameters(
                host=self.config["RABBITMQ_HOST"],
                port=self.config["RABBITMQ_PORT"],
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection: BlockingConnection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(
                queue=self.config["RABBITMQ_QUEUE"],
                durable=True
            )
            self.logger.info("Connected to RabbitMQ.")
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            sys.exit(1)

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
                properties=pika.BasicProperties(delivery_mode=2)
            )
            self.logger.debug(f"Published: {message}")
        except Exception as e:
            self.logger.error(f"Failed to publish value at timestamp="
                         f"{timestamp}: {e}")

    def run(self) -> None:
        interval = self.config["METER_INTERVAL"]
        simulation_duration = self.config["SIMULATION_DURATION"]
        start_time = time.time()
        self.logger.info("Publisher started.")
        while True:
            if self.stop_event.is_set():
                self.logger.info("Shutting down gracefully.")
                break

            now = time.time()
            elapsed = now - start_time
            if elapsed >= simulation_duration:
                self.logger.info(f"Simulation duration of {simulation_duration}"
                            f" seconds reached, shutting down gracefully.")
                break

            timestamp = now
            value = self.generate_meter_value()
            self.publish(timestamp, value)
            time.sleep(interval)
        self.stop()

    def stop(self) -> None:
        if self.channel and self.channel.is_open:
            try:
                self.logger.info("Stopping channel")
                self.channel.close()
            except Exception as e:
                self.logger.error(f"Error closing channel: {e}")
        if self.connection and self.connection.is_open:
            self.logger.info("Closing connection")
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")

def setup_signal_handlers(stop_event: Event, logger: "Logger") -> None:
    def handler(signum, frame):
        logger.info("Received shutdown signal.")
        stop_event.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def main() -> None:
    config = load_config()
    logger = setup_logging(log_level=get_log_level(config["LOG_LEVEL"]))
    stop_event = Event()
    setup_signal_handlers(stop_event, logger)
    health_server = start_health_server(config["HEALTH_PORT"])
    logger.info(f"Health server started on port {config['HEALTH_PORT']}.")

    publisher = MeterPublisher(config, stop_event, logger)
    publisher.run()

    health_server.shutdown()
    logger.info("Health server shut down.")

if __name__ == "__main__":
    main()
