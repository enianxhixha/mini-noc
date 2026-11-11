
# Mini NOC — Network Operations Center

A full-stack network monitoring and incident management
simulation built with Python, FastAPI, React and SQLite.

## Features

- Network device monitoring
- Online/offline status indicators
- Infrastructure health statistics
- Automatic incident generation
- P1/P2/P3 incident priorities
- Incident acknowledgement and resolution
- Persistent incident history using SQLite
- Automatic dashboard refresh every five seconds
- REST API
- Automated backend tests

## Technology Stack

Backend:
- Python
- FastAPI
- SQLite

Frontend:
- React
- JavaScript
- CSS
- Vite

Testing:
- pytest
- FastAPI TestClient

## Running the Project

### Backend

Create and activate a Python virtual environment.

Install dependencies:

pip install "fastapi[standard]"

From the backend directory, run:

python -m uvicorn main:app --reload

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### Frontend

From the frontend directory:

npm install
npm run dev

Frontend: http://localhost:5173

## Running Tests

From the backend directory:

pip install pytest httpx
python -m pytest -v

## How It Works

The application starts with five simulated network devices.

When a device transitions offline, the backend creates
an incident and assigns a priority based on device type.

Incidents can be acknowledged by an operator.

Once the device is online again, the incident can be
resolved.

Device states and incidents are saved in SQLite.

## Limitations

This is a simulation, not a production NOC platform.

Device statuses are changed manually rather than
collected from actual network equipment.

Incident priorities use simplified demonstration rules.

There is no authentication or user management.

## Future Improvements

- ICMP and SNMP monitoring
- Live network metrics
- Broadcast stream monitoring
- Email notifications
- Docker deployment
- User authentication
- Prometheus and Grafana integration
