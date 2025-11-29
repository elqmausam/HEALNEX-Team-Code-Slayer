import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../css/Dashboard.css';

interface HospitalAgent {
  id: string;
  name: string;
  personality: string;
  resources: {
    icu_beds?: number;
    ventilators?: number;
    wheelchairs?: number;
  };
  occupancy: number;
  status: string;
}

interface ParliamentStatus {
  parliament_status: string;
  total_agents: number;
  active_negotiations: number;
  agents: HospitalAgent[];
}

interface Alert {
  type: string;
  severity: string;
  message: string;
  timestamp: string;
}

interface AlertsResponse {
  status: string;
  hospital_id: string;
  alerts: Alert[];
  alert_count: number;
}

interface Session {
  id: string;
  status: string;
  initiator: string;
  resource_type: string;
  created_at: string;
}

interface SessionsResponse {
  success: boolean;
  sessions: Session[];
  count: number;
}

export default function Dashboard() {
  const [parliamentData, setParliamentData] = useState<ParliamentStatus | null>(null);
  const [alertsData, setAlertsData] = useState<AlertsResponse | null>(null);
  const [sessionsData, setSessionsData] = useState<SessionsResponse | null>(null);
  const [isLoadingHospitals, setIsLoadingHospitals] = useState(true);

  useEffect(() => {
    fetchParliamentStatus();
    fetchAlerts();
    fetchSessions();
    // Refresh every 10 seconds
    const interval = setInterval(() => {
      fetchParliamentStatus();
      fetchAlerts();
      fetchSessions();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/parliament/sessions');
      if (response.ok) {
        const data = await response.json();
        console.log('Sessions data received:', data);
        setSessionsData(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/predictions/alerts/H001');
      if (response.ok) {
        const data = await response.json();
        console.log('Alerts data received:', data);
        setAlertsData(data);
      }
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  };

  const fetchParliamentStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/parliament/status');
      if (response.ok) {
        const data = await response.json();
        console.log('Parliament data received:', data);
        setParliamentData(data);
      } else {
        console.error('Parliament API returned non-OK status:', response.status);
      }
    } catch (err) {
      console.error('Failed to fetch parliament status:', err);
    } finally {
      setIsLoadingHospitals(false);
    }
  };

  const getOccupancyStatus = (occupancy: number) => {
    if (occupancy >= 90) return { class: 'critical', label: 'Critical' };
    if (occupancy >= 75) return { class: 'warning', label: 'High' };
    return { class: 'good', label: 'Normal' };
  };

  const calculateAvailableBeds = (resources: any, occupancy: number) => {
    // Handle both object and number formats
    let totalBeds = 50; // default
    if (resources?.icu_beds) {
      if (typeof resources.icu_beds === 'object' && 'total' in resources.icu_beds) {
        totalBeds = resources.icu_beds.total;
      } else if (typeof resources.icu_beds === 'number') {
        totalBeds = resources.icu_beds;
      }
    }
    const occupied = Math.floor(totalBeds * (occupancy / 100));
    return `${totalBeds - occupied}/${totalBeds}`;
  };

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <div className="header-content">
          <h1>📊 Hospital Agent Dashboard</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>
            Real-time system overview and multi-hospital coordination
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
        <div className="stat-card">
          <div className="stat-icon">🏛️</div>
          <div className="stat-value">{parliamentData?.active_negotiations ?? 0}</div>
          <div className="stat-label">Active Negotiations</div>
          <div className="stat-change positive">Real-time data</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🤖</div>
          <div className="stat-value">{parliamentData?.total_agents ?? 0}</div>
          <div className="stat-label">Hospital Agents</div>
          <div className="stat-change positive">Parliament System</div>
        </div>
      </div>

      {/* Hospital Agents */}
      <div className="section-title">
        🤖 Hospital Agents Status
        {parliamentData && (
          <span style={{ fontSize: '14px', fontWeight: 'normal', marginLeft: '12px', color: '#6B7280' }}>
            ({parliamentData.total_agents} agents • {parliamentData.active_negotiations} active negotiations)
          </span>
        )}
      </div>
      <div className="agents-grid">
        {isLoadingHospitals ? (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            Loading hospital agents...
          </div>
        ) : parliamentData && parliamentData.agents.length > 0 ? (
          parliamentData.agents.map((agent, index) => {
            const occupancyStatus = getOccupancyStatus(agent.occupancy);
            const availableBeds = calculateAvailableBeds(agent.resources, agent.occupancy);
            
            return (
              <div key={agent.id} className="agent-card">
                <div className="agent-header">
                  <div>
                    <div className="agent-name">🏥 {agent.name}</div>
                    <div className={`agent-status ${agent.status === 'online' ? 'online' : 'offline'}`}>
                      ● {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
                    </div>
                  </div>
                  <div className="agent-badge">{index === 0 ? 'Primary' : 'Partner'}</div>
                </div>
                <div className="agent-stats">
                  <div className="agent-stat">
                    <span className="label">Occupancy:</span>
                    <span className={`value ${occupancyStatus.class}`}>{agent.occupancy}%</span>
                  </div>
                  <div className="agent-stat">
                    <span className="label">ICU Beds:</span>
                    <span className={`value ${occupancyStatus.class}`}>{availableBeds} available</span>
                  </div>
                  <div className="agent-stat">
                    <span className="label">Personality:</span>
                    <span className="value">{String(agent.personality)}</span>
                  </div>
                  {agent.resources?.ventilators && (
                    <div className="agent-stat">
                      <span className="label">Ventilators:</span>
                      <span className="value">
                        {typeof agent.resources.ventilators === 'object' 
                          ? `${(agent.resources.ventilators as any).available}/${(agent.resources.ventilators as any).total} available`
                          : agent.resources.ventilators
                        }
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            No hospital agents available. Please start the backend server.
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="content-grid">
        {/* Active Alerts */}
        <div className="panel">
          <div className="panel-header">
            <h3>⚠️ Active Alerts</h3>
            <Link to="/alerts" className="link">View All →</Link>
          </div>
          <div className="alerts-list">
            {alertsData && alertsData.alerts.length > 0 ? (
              alertsData.alerts.map((alert, index) => {
                const severityClass = alert.severity === 'high' ? 'critical' : alert.severity === 'medium' ? 'high' : 'warning';
                const badgeClass = alert.severity === 'high' ? 'critical-badge' : alert.severity === 'medium' ? 'high-badge' : 'warning-badge';
                const timeAgo = new Date(alert.timestamp).toLocaleString();
                
                return (
                  <div key={index} className={`alert-item ${severityClass}`}>
                    <div className="alert-indicator"></div>
                    <div className="alert-content">
                      <div className="alert-title">{alert.message}</div>
                      <div className="alert-time">{timeAgo}</div>
                    </div>
                    <div className={`alert-badge ${badgeClass}`}>
                      {alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                <div style={{ fontSize: '48px', marginBottom: '12px' }}>✅</div>
                <div style={{ fontSize: '16px', fontWeight: 500 }}>No Active Alerts</div>
                <div style={{ fontSize: '14px', marginTop: '4px' }}>All systems operating normally</div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="panel">
          <div className="panel-header">
            <h3>📋 Recent Activity</h3>
            <Link to="/history" className="link">View History →</Link>
          </div>
          <div className="activity-list">
            {sessionsData && sessionsData.sessions.length > 0 ? (
              sessionsData.sessions.slice(0, 4).map((session) => {
                const timeAgo = new Date(session.created_at).toLocaleString();
                const statusIcon = session.status === 'completed' ? '✅' : session.status === 'active' ? '🔄' : '⏳';
                
                return (
                  <div key={session.id} className="activity-item">
                    <div className="activity-icon">🏛️</div>
                    <div className="activity-content">
                      <div className="activity-title">
                        {statusIcon} Negotiation for {session.resource_type} - {session.status}
                      </div>
                      <div className="activity-time">{timeAgo}</div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
                <div style={{ fontSize: '48px', marginBottom: '12px' }}>📭</div>
                <div style={{ fontSize: '16px', fontWeight: 500 }}>No Recent Activity</div>
                <div style={{ fontSize: '14px', marginTop: '4px' }}>Negotiations will appear here</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="chart-panel">
        <div className="panel-header">
          <h3>📊 Admission Forecast - Next 7 Days</h3>
          <Link to="/predictions" className="link">View Details →</Link>
        </div>
        <div className="chart-placeholder">
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📈</div>
            <div style={{ fontSize: '18px', color: '#6B7280', marginBottom: '8px' }}>
              Chart Visualization
            </div>
            <div style={{ fontSize: '14px', color: '#9CA3AF' }}>
              Integrate Chart.js or D3.js for interactive charts
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
