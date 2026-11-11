
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mini NOC Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DATABASE = Path(__file__).with_name("mini_noc.db")


def now():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


@contextmanager
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def severity_for(device_type):
    priorities = {
        "Router": "P1",
        "Switch": "P2",
        "Encoder": "P2",
        "Server": "P3",
    }
    return priorities.get(device_type, "P3")


def create_incident(db, device):
    db.execute(
        """
        INSERT INTO incidents
        (device_id, title, severity, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            device["id"],
            f"{device['name']} is offline",
            severity_for(device["type"]),
            "open",
            now(),
        ),
    )


def initialize_database():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT,
                FOREIGN KEY (device_id)
                    REFERENCES devices(id)
            )
            """
        )

        count = db.execute(
            "SELECT COUNT(*) FROM devices"
        ).fetchone()[0]

        if count == 0:
            initial_devices = [
                (1, "Core Router", "192.0.2.1",
                 "Router", "online"),
                (2, "Switch 01", "192.0.2.2",
                 "Switch", "online"),
                (3, "Streaming Server", "192.0.2.3",
                 "Server", "online"),
                (4, "Encoder 01", "192.0.2.4",
                 "Encoder", "offline"),
                (5, "Backup Server", "192.0.2.5",
                 "Server", "online"),
            ]

            db.executemany(
                """
                INSERT INTO devices
                (id, name, ip, type, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                initial_devices,
            )

            # Create an initial incident for Encoder 01
            encoder = db.execute(
                "SELECT * FROM devices WHERE id = 4"
            ).fetchone()

            create_incident(db, encoder)


initialize_database()


@app.get("/")
def home():
    return {"message": "Mini NOC API is running"}


@app.get("/api/devices")
def get_devices():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM devices ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]


@app.get("/api/summary")
def get_summary():
    with get_db() as db:
        rows = db.execute(
            "SELECT status FROM devices"
        ).fetchall()

        online = sum(
            1 for row in rows
            if row["status"] == "online"
        )

        return {
            "total": len(rows),
            "online": online,
            "offline": len(rows) - online,
        }


@app.post("/api/devices/{device_id}/toggle")
def toggle_device(device_id: int):
    with get_db() as db:
        device = db.execute(
            "SELECT * FROM devices WHERE id = ?",
            (device_id,),
        ).fetchone()

        if device is None:
            raise HTTPException(
                status_code=404,
                detail="Device not found",
            )

        new_status = (
            "offline"
            if device["status"] == "online"
            else "online"
        )

        db.execute(
            "UPDATE devices SET status = ? WHERE id = ?",
            (new_status, device_id),
        )

        # Create an incident for a new outage
        if new_status == "offline":
            existing = db.execute(
                """
                SELECT id FROM incidents
                WHERE device_id = ?
                  AND status != 'resolved'
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()

            if existing is None:
                create_incident(db, device)

        updated = db.execute(
            "SELECT * FROM devices WHERE id = ?",
            (device_id,),
        ).fetchone()

        return dict(updated)


@app.get("/api/incidents")
def get_incidents():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT
                incidents.*,
                devices.name AS device_name
            FROM incidents
            JOIN devices
                ON incidents.device_id = devices.id
            ORDER BY incidents.id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


@app.post("/api/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: int):
    with get_db() as db:
        incident = db.execute(
            "SELECT * FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise HTTPException(
                status_code=404,
                detail="Incident not found",
            )

        if incident["status"] == "resolved":
            raise HTTPException(
                status_code=409,
                detail="Incident is already resolved",
            )

        if incident["status"] == "open":
            db.execute(
                """
                UPDATE incidents
                SET status = 'acknowledged',
                    acknowledged_at = ?
                WHERE id = ?
                """,
                (now(), incident_id),
            )

        updated = db.execute(
            "SELECT * FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()

        return dict(updated)


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int):
    with get_db() as db:
        incident = db.execute(
            """
            SELECT incidents.*,
                   devices.status AS device_status
            FROM incidents
            JOIN devices
                ON incidents.device_id = devices.id
            WHERE incidents.id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise HTTPException(
                status_code=404,
                detail="Incident not found",
            )

        if incident["device_status"] == "offline":
            raise HTTPException(
                status_code=409,
                detail="Device must be online before resolution",
            )

        if incident["status"] != "resolved":
            db.execute(
                """
                UPDATE incidents
                SET status = 'resolved',
                    resolved_at = ?
                WHERE id = ?
                """,
                (now(), incident_id),
            )

        updated = db.execute(
            "SELECT * FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()

        return dict(updated)
