import os

def load_config():
    return {
        "RABBITMQ_HOST": os.getenv("RABBITMQ_HOST", "rabbitmq"),
        "RABBITMQ_PORT": int(os.getenv("RABBITMQ_PORT", 5672)),
        "RABBITMQ_QUEUE": os.getenv("RABBITMQ_QUEUE", "meter_data"),
        "HEALTH_PORT": int(os.getenv("PV_SIM_HEALTH_PORT", 8001)),
        "RESULTS_PATH": os.getenv("RESULTS_PATH", "/results/power_results.csv")
    }