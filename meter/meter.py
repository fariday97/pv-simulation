import time
import threading
import signal
import random
import pika
import json
import sys
import logging
from typing import Any, Dict, Optional
from health_server import start_health_server
from config import load_config
from logging_utils import setup_logging, get_log_level

logger: Optional[logging.Logger] = None

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
            self.channel.queue_declare(
                queue=self.config["RABBITMQ_QUEUE"],
                durable=True
            )
            logger.info("Connected to RabbitMQ.")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
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
                properties=pika.BasicProperties(delivery_mode=2)# retain
                # message
            )
            logger.debug(f"Published: {message}")
        except Exception as e:
            logger.error(f"Failed to publish value at timestamp="
                         f"{timestamp}: {e}")

    def run(self) -> None:
        interval = self.config["METER_INTERVAL"]
        simulation_duration = self.config["SIMULATION_DURATION"]
        start_time = time.time()
        logger.info("Publisher started.")
        while True:
            if self.stop_event.is_set():
                logger.info("Shutting down gracefully.")
                break

            now = time.time()
            elapsed = now - start_time
            if elapsed >= simulation_duration:
                logger.info(f"Simulation duration of {simulation_duration}"
                            f" seconds reached, shutting down gracefully.")
                break

            timestamp = now
            value = self.generate_meter_value()
            self.publish(timestamp, value)
            time.sleep(interval)
        self.stop()

    def stop(self):
        if self.channel and self.channel.is_open:
            try:
                logger.info("Stopping channel")
                self.channel.close()
            except Exception as e:
                logger.error(f"Error closing channel: {e}")
        if self.connection and self.connection.is_open:
            logger.info("Closing connection")
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

def setup_signal_handlers(stop_event: threading.Event) -> None:
    def handler(signum, frame):
        logger.info("Received shutdown signal.")
        stop_event.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def main() -> None:
    global logger
    config = load_config()
    logger = setup_logging(log_level=get_log_level(config["LOG_LEVEL"]))
    stop_event = threading.Event()
    setup_signal_handlers(stop_event)
    health_server = start_health_server(config["HEALTH_PORT"], logger)

    publisher = MeterPublisher(config, stop_event)
    publisher.run()

    health_server.shutdown()
    logger.info("Health server shut down.")

if __name__ == "__main__":
    main()
