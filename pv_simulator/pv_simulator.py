import threading
import signal
import random
import pika
import json
import math
import time
import os
import csv
import queue
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING
from health_server import start_health_server
from config import load_config
from logging_utils import setup_logging, get_log_level

if TYPE_CHECKING:
    from pika.adapters.blocking_connection import BlockingConnection, \
    BlockingChannel
    from logging import Logger
    from http.server import HTTPServer
    from io import TextIOWrapper
    from _csv import _writer

class PVSimulator:
    MAX_POWER = 3.2  # kW, estimated from profile in prompt
    SUNRISE = 5.5 * 3600 # (5:30 AM), estimated from PV profile in prompt
    SUNSET = 20.5 * 3600 # (8:30 PM), estimated from PV profile in prompt

    @dataclass(frozen=True)
    class Result:
        iso_timestamp: str
        meter_value: float
        pv_value: float
        total_power: float

    def __init__(self, config: Dict[str, Any], health_server: "HTTPServer",
                 logger: "Logger") -> None:
        self.config = config
        self.logger = logger
        self.health_server = health_server
        self.connection: Optional["BlockingConnection"] = None
        self.channel: Optional["BlockingChannel"] = None
        self.results_file: Optional["TextIOWrapper"] = None
        self.results_writer: Optional[_writer] = None
        self.setup_rabbitmq()
        self.open_csv_writer()
        self.result_queue = queue.Queue()
        self.writer_thread = threading.Thread(target=self.write, daemon=True)
        self._running = True
        self.writer_thread.start()

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
            self.logger.info("Connected to RabbitMQ.")
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            sys.exit(1)

    def generate_pv_value(self, timestamp: float) -> float:
        tm = time.localtime(timestamp)
        seconds_since_midnight = tm.tm_hour * 3600 + tm.tm_min * 60 + tm.tm_sec
        if seconds_since_midnight < self.SUNRISE or seconds_since_midnight > self.SUNSET:
            return 0.0
        t = (seconds_since_midnight - self.SUNRISE) / (self.SUNSET - self.SUNRISE) * math.pi
        pv = self.MAX_POWER * math.sin(t) + random.uniform(-0.1, 0.1) # some noise for realism
        return round(max(pv, 0.0), 3)

    def open_csv_writer(self):
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "results")
        os.makedirs(results_dir, exist_ok=True)
        path = os.path.join(results_dir, "simulation_results.csv")
        try:
            is_new = not os.path.exists(path)
            self.results_file = open(path, mode='a', newline='', buffering=1)
            self.results_writer = csv.writer(self.results_file)
            if is_new:
                self.results_writer.writerow([
                    'ISO Timestamp',
                    'Meter Power (KW)',
                    'PV Power (KW)',
                    'Total Power (KW)'
                ])
            self.logger.info(f"CSV writer successfully activated.")
        except Exception as e:
            self.logger.error(f"Unable to open or write into CSV file: {e}")
            self.health_server.shutdown()
            self.health_server.is_up = False
            self.logger.info("Health server shut down as no results are being "
                        "logged into disk.")

    def write(self) -> None:
        while self._running or not self.result_queue.empty():
            try:
                result = self.result_queue.get()
                self.results_writer.writerow([
                    result.iso_timestamp,
                    result.meter_value,
                    result.pv_value,
                    result.total_power
                ])
                self.result_queue.task_done()
                self.logger.debug(f"Wrote result at {result.iso_timestamp} "
                             f"successfully")
            except Exception as e:
                self.logger.error(f"Error writing result: {e}")

    def handle_meter_message(self, ch, method, properties, body) -> None:
        try:
            meter_msg = json.loads(body)
            timestamp = meter_msg["timestamp"]
            meter_value = meter_msg["meter_value"]
            pv_value = self.generate_pv_value(timestamp)
            iso_timestamp = datetime.fromtimestamp(timestamp).isoformat(
                    timespec="milliseconds")
            result = self.Result(
                iso_timestamp=iso_timestamp,
                meter_value=meter_value,
                pv_value=pv_value,
                total_power=round(meter_value - pv_value, 3)
            )
            self.result_queue.put(result)
            self.logger.debug(f"Result at {result.iso_timestamp} queued "
                         f"successfully")
        except Exception as e:
            self.logger.error(f"Failed to process meter message: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self) -> None:
        self.channel.basic_consume(
            queue=self.config["RABBITMQ_QUEUE"],
            on_message_callback=self.handle_meter_message
        )
        self.logger.info("Ready to consume messages.")
        try:
            self.channel.start_consuming()
        except Exception as e:
            self.logger.error(f"[PV_SIM] Error in consuming: {e}")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self.channel and self.channel.is_open:
            try:
                self.logger.info("Stopping channel.")
                self.channel.close()
            except Exception as e:
                self.logger.error(f"Error closing channel: {e}")
        if self.connection and self.connection.is_open:
            self.logger.info("Closing connection.")
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=2)
        if self.results_file:
            try:
                self.results_file.close()
                self.logger.info("CSV file closed.")
            except Exception as e:
                self.logger.error(f"Error closing file: {e}")

def setup_signal_handlers(pv_simulator: PVSimulator, logger: "Logger") -> None:
    def handler(signum, frame):
        logger.info("Received shutdown signal. Gracefully shutting down.")
        pv_simulator.channel.stop_consuming()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

def main() -> None:
    config = load_config()
    logger = setup_logging(log_level=get_log_level(config["LOG_LEVEL"]))
    health_server = start_health_server(config["HEALTH_PORT"])
    logger.info(f"Health server started on port {config['HEALTH_PORT']}.")

    pv_sim = PVSimulator(config, health_server, logger)
    setup_signal_handlers(pv_sim, logger)
    pv_sim.run()

    if health_server.is_up:
        health_server.shutdown()
        logger.info("Health server shut down.")

if __name__ == "__main__":
    main()
