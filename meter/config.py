import os

def load_config():
    return {
        "METER_INTERVAL": float(os.getenv("METER_INTERVAL", 2)),
        "SIMULATION_DURATION": int(os.getenv("SIMULATION_DURATION", 86400)),
        "HEALTH_PORT": int(os.getenv("METER_HEALTH_PORT", 8000))
    }