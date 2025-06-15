import os

def load_config():
    return {
        "METER_INTERVAL": float(os.getenv("METER_INTERVAL", 2)),
        "SIMULATION_DURATION": int(os.getenv("SIMULATION_DURATION", 86400)),
        "HEALTH_PORT": int(os.getenv("METER_HEALTH_PORT", 8000)),
        "RABBITMQ_HOST": os.getenv("RABBITMQ_HOST", "rabbitmq"),
        "RABBITMQ_PORT": int(os.getenv("RABBITMQ_PORT", 5672)),
        "RABBITMQ_QUEUE": os.getenv("RABBITMQ_QUEUE", "meter_data"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO")
    }