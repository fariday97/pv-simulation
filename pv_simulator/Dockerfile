FROM python:3.13-slim

WORKDIR /app

COPY pv_simulator/ .
COPY utils/logging_utils.py logging_utils.py
COPY utils/health_server.py health_server.py
COPY utils/healthcheck.py healthcheck.py

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "pv_simulator.py"]
