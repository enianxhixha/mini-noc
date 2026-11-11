
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [devices, setDevices] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [busy, setBusy] = useState(null);

  // Refresh devices and incidents from Python
  const refreshData = useCallback(async () => {
    try {
      const [devicesResponse, incidentsResponse] =
        await Promise.all([
          fetch(`${API_URL}/api/devices`),
          fetch(`${API_URL}/api/incidents`)
        ]);

      if (!devicesResponse.ok || !incidentsResponse.ok) {
        throw new Error("Unable to load monitoring data");
      }

      const [deviceData, incidentData] = await Promise.all([
        devicesResponse.json(),
        incidentsResponse.json()
      ]);

      setDevices(deviceData);
      setIncidents(incidentData);
      setLastUpdated(new Date().toLocaleTimeString());
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Automatically refresh every 5 seconds
  useEffect(() => {
    refreshData();

    const interval = setInterval(refreshData, 5000);

    return () => clearInterval(interval);
  }, [refreshData]);

  // Simulate device failure or recovery
  async function toggleDevice(id) {
    setBusy(`device-${id}`);

    try {
      const response = await fetch(
        `${API_URL}/api/devices/${id}/toggle`,
        { method: "POST" }
      );

      if (!response.ok) {
        throw new Error("Failed to update device");
      }

      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  // Acknowledge or resolve an incident
  async function updateIncident(id, action) {
    setBusy(`incident-${id}`);

    try {
      const response = await fetch(
        `${API_URL}/api/incidents/${id}/${action}`,
        { method: "POST" }
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          body.detail || "Failed to update incident"
        );
      }

      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  const total = devices.length;

  const online = devices.filter(
    device => device.status === "online"
  ).length;

  const offline = total - online;

  const availability = total > 0
    ? Math.round((online / total) * 100)
    : 0;

  const activeIncidents = incidents.filter(
    incident => incident.status !== "resolved"
  ).length;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">◈</span>
          <span>MINI NOC</span>
        </div>

        <span className="demo-badge">
          ● SIMULATION MODE
        </span>
      </header>

      <main className="dashboard">
        <section className="welcome">
          <div>
            <p className="eyebrow">
              NETWORK OPERATIONS CENTER
            </p>
            <h1>Infrastructure Overview</h1>
            <p className="description">
              Network monitoring and incident management
            </p>
          </div>

          <div className="refresh-badge">
            ↻ Auto-refresh: 5 seconds
          </div>
        </section>

        {/* Network statistics */}
        <section className="stats-grid">
          <div className="stat-card">
            <p>Total Devices</p>
            <h2>{total}</h2>
            <span>Monitored infrastructure</span>
          </div>

          <div className="stat-card">
            <p>Online Devices</p>
            <h2 className="text-green">{online}</h2>
            <span>Operating normally</span>
          </div>

          <div className="stat-card">
            <p>Offline Devices</p>
            <h2 className="text-red">{offline}</h2>
            <span>Require attention</span>
          </div>
        </section>

        {/* Infrastructure health */}
        <section className="health-panel">
          <div className="health-header">
            <div>
              <h3>Infrastructure Health</h3>
              <p>Percentage of monitored devices online</p>
            </div>
            <strong>{availability}%</strong>
          </div>

          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${availability}%` }}
            />
          </div>
        </section>

        {error && (
          <div className="error-message">{error}</div>
        )}

        {/* Device monitoring */}
        <section className="devices-section">
          <div className="section-header">
            <div>
              <h2>Monitored Devices</h2>
              <p>Live device status and information</p>
            </div>

            <span className="last-update">
              Last updated: {lastUpdated || "Waiting..."}
            </span>
          </div>

          <div className="devices-grid">
            {devices.map(device => (
              <article className="device-card" key={device.id}>
                <div className="device-header">
                  <div className="device-icon">
                    {device.type === "Router" ? "🌐" :
                     device.type === "Switch" ? "🔀" :
                     device.type === "Encoder" ? "📡" : "🖥️"}
                  </div>

                  <span className={`status ${device.status}`}>
                    ● {device.status.toUpperCase()}
                  </span>
                </div>

                <h3>{device.name}</h3>

                <div className="device-details">
                  <p>
                    <span>Device Type</span>
                    <strong>{device.type}</strong>
                  </p>

                  <p>
                    <span>IP Address</span>
                    <strong>{device.ip}</strong>
                  </p>
                </div>

                <button
                  className="device-button"
                  disabled={busy !== null}
                  onClick={() => toggleDevice(device.id)}
                >
                  Toggle Device Status
                </button>
              </article>
            ))}
          </div>
        </section>

        {/* Incident management */}
        <section className="incidents-section">
          <div className="section-header">
            <div>
              <h2>Incident Management</h2>
              <p>Monitor, acknowledge and resolve alarms</p>
            </div>

            <span className="active-count">
              {activeIncidents} Active Incidents
            </span>
          </div>

          <div className="incident-table-wrapper">
            <table className="incident-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Device</th>
                  <th>Problem</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Detected</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="empty-incidents">
                      No incidents recorded
                    </td>
                  </tr>
                ) : (
                  incidents.map(incident => {
                    const device = devices.find(
                      d => d.id === incident.device_id
                    );

                    const deviceRecovered =
                      device?.status === "online";

                    return (
                      <tr key={incident.id}>
                        <td>INC-{String(incident.id).padStart(3, "0")}</td>

                        <td>{incident.device_name}</td>

                        <td>{incident.title}</td>

                        <td>
                          <span
                            className={`priority ${incident.severity.toLowerCase()}`}
                          >
                            {incident.severity}
                          </span>
                        </td>

                        <td>
                          <span
                            className={`incident-state ${incident.status}`}
                          >
                            {incident.status.toUpperCase()}
                          </span>
                        </td>

                        <td>
                          {new Date(
                            incident.created_at
                          ).toLocaleString()}
                        </td>

                        <td>
                          <div className="incident-actions">
                            {incident.status === "open" && (
                              <button
                                className="ack-button"
                                disabled={busy !== null}
                                onClick={() =>
                                  updateIncident(
                                    incident.id,
                                    "acknowledge"
                                  )
                                }
                              >
                                Acknowledge
                              </button>
                            )}

                            {incident.status !== "resolved" && (
                              <button
                                className="resolve-button"
                                disabled={
                                  busy !== null ||
                                  !deviceRecovered
                                }
                                title={
                                  deviceRecovered
                                    ? "Resolve incident"
                                    : "Recover the device first"
                                }
                                onClick={() =>
                                  updateIncident(
                                    incident.id,
                                    "resolve"
                                  )
                                }
                              >
                                Resolve
                              </button>
                            )}

                            {incident.status === "resolved" && (
                              <span className="completed-label">
                                ✓ Completed
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        <footer>
          MINI NOC — Network Monitoring Simulation
        </footer>
      </main>
    </div>
  );
}

export default App;
