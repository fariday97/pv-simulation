

# PV Simulator 

## Overview

This project simulates a photovoltaic (PV) power system (consumer) and a household consumption meter (publisher), using event-driven communication via RabbitMQ.
**Outputs:** A timestamped CSV file containing meter readings, PV output, and their sum.

---
## Prerequisites

Before building or running the simulation stack, ensure you have:

* **Docker** (version 20.10 or higher recommended)
* **Docker Compose** (v2.x or higher, or included with Docker Desktop)
* (Optional) **Git** 

---

## Components

* **Meter Service:** Generates household consumption values at regular intervals and publishes them to RabbitMQ.
* **PV Simulator Service:** Listens for meter messages, generates a realistic PV power profile based on time-of-day, and logs results to a CSV file.
* **RabbitMQ Broker:** Message broker.

**All services run as separate containers via Docker Compose.**

---

## Configuration

All core parameters are to be configured via environment variables in a `.env` file (see `.env.example`):

| Variable                              | Default      | Description                                                                                                                                                                                                                                                                      |
|---------------------------------------|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `METER_INTERVAL`                      | `2`          | Seconds between meter readings                                                                                                                                                                                                                                                   |
| `SIMULATION_DURATION`                 | `86400`      | Duration of the simulation                                                                                                                                                                                                                                                       |
| `LOG_LEVEL`                           | `INFO`       | Logging verbosity (`INFO`, `DEBUG`, `WARNING`, `ERROR`) for meter and pv_simulator.<br/>*Note that the RabbitMQ log level is set at `INFO`                                                                                                                                       |
| `METER_HEALTH_PORT` (required)        | `_`          | Service Port used to expose the health server for the meter for periodic Docker heathchecks                                                                                                                                                                                      |
| `PV_SIM_HEALTH_PORT` (required)       | `_`          | Service Port used to expose the health server for the pv_simulator for periodic Docker heathchecks                                                                                                                                                                                                                |
| `RABBITMQ_HOST`                       | `rabbitmq`   | RabbitMQ broker Host address<br/>*Note that it should match the service name if running the stack from docker compose*                                                                                                                                                           |
| `RABBITMQ_PORT` (required)            | `_`          | Host Port used to expose the RabbitMQ broker                                                                                                                                                                                                                                     |
| `RABBITMQ_MANAGEMENT_PORT` (required) | `_`          | Host Port used to expose the RabbitMQ management portal                                                                                                                                                                                                                          |
| `RABBITMQ_QUEUE`                      | `meter_data` | Queue to publish and/or consume messages from                                                                                                                                                                                                                                    |
| `TIMEZONE`  (optional)                | `_`          | If running the stack on a VM (or WSL) where the clock is not synced with the host machine, set the timezone manually to adjust to local time.<br/>*Note: Make sure to uncomment the `- TZ=${TIMEZONE}` in the environment configuration for `pv_simulator` in `docker-compose.yml` |

---

## Quick Start

1. **Extract this repository, and change into its directory:**

   ```sh
   cd /path/to/pv-simulator-challenge
   ```
2. **Create `.env` file based on configuration template in `.env.example` and description above.**


3. **Build, start and stop the simulation stack once the desired duration ends:**

   ```sh
   docker compose up --abort-on-container-exit --exit-code-from meter

   ```

4. **After simulation (or after manual shutdown before simulation completes):**
    - results are available in:

      ```
      ./results/simulation_results.csv
      ```
    - logs of all the services are available in:
      ```
      ./logs/meter.log
      ./logs/pv_simulator.log    
      ./logs/rabbit.log  
      ```
   *Note: If you want each run's output in separate files, make sure to remove the previous run's files before starting a new one.*
   

5. **Finally, clean up resources (containers + network):**

   ```sh
   docker compose down
   ```

---

## Output

Each row in `./results/simulation_results.csv` contains:

| Column               | Description                                      |
|----------------------|--------------------------------------------------|
| `ISO Timestamp`      | Timestamp in ISO 8601 format                     |
| `Meter Power (KW)`   | Simulated household consumption (kW)             |
| `PV Power (KW)`      | Simulated PV output (realistic profile)          |
| `Sum of Powers (KW)` | `load power (PV) - generated Power (household)`) |

---

## Observability and Troubleshooting

* Both Meter and PV Simulator expose `/health` endpoints (minimal for now and can be heavily extended).
* Docker Compose uses these endpoints for periodic healthchecks.
* All the logs detailing a run afterward can be found in `./logs`.
* During a run, the management portal of the broker can be accessed at http://localhost:15672/.
   

---
