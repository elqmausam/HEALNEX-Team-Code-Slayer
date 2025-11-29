import React, { useState, useEffect, useRef } from 'react';
import '../css/Header.css';

interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  features: string[];
}

interface Alert {
  type: string;
  priority: string;
  message: string;
  timestamp: string;
  metric?: string;
  value?: number;
  threshold?: number;
}

const Header: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealthStatus();
    fetchAlerts();

    // Refresh health status every 5 seconds
    const healthInterval = setInterval(fetchHealthStatus, 5000);
    // Refresh alerts every 30 seconds
    const alertsInterval = setInterval(fetchAlerts, 30000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(alertsInterval);
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/', {
        method: 'GET',
        headers: {
          'accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setHealthData(data);
      setError(null);
    } catch (err) {
      setHealthData(null);
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/predictions/alerts/H001');
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error('Error fetching alerts:', err);
    }
  };

  const getTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp);
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical': return '🔴';
      case 'high': return '🟠';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  // Get latest 5 alerts
  const latestAlerts = alerts.slice(0, 5);

  return (
    <div className="header-bar">
      <div className="header-content">
        <div className="logo-section">
          <span className="logo-icon">🏥</span>
          <span className="logo-text">Healnex</span>
        </div>
        <div className="header-right">
          {error ? (
            <div className="status-badge error-status" title={error}>
              <span className="status-dot error-dot"></span>
              System Offline
            </div>
          ) : healthData ? (
            <div className="status-badge success-status" title={`${healthData.service} v${healthData.version}`}>
              <span className="status-dot success-dot"></span>
              {healthData.status.charAt(0).toUpperCase() + healthData.status.slice(1)}
            </div>
          ) : (
            <div className="status-badge loading-status">
              <span className="status-dot loading-dot"></span>
              Checking...
            </div>
          )}
          <div className="status-badge parliament-badge">
            ⚡ Parliament: Active
          </div>
          <div className="notification-bell" ref={dropdownRef}>
            <div
              className="notification-icon"
              onClick={() => setShowNotifications(!showNotifications)}
            >
              🔔
              {alerts.length > 0 && (
                <span className="notification-count">{alerts.length}</span>
              )}
            </div>

            {showNotifications && (
              <div className="notification-dropdown">
                <div className="notification-header">
                  <h3>Notifications</h3>
                  <span className="notification-total">{alerts.length} total</span>
                </div>

                <div className="notification-list">
                  {latestAlerts.length === 0 ? (
                    <div className="notification-empty">
                      <span style={{ fontSize: '32px', marginBottom: '8px' }}>✅</span>
                      <p>No active alerts</p>
                    </div>
                  ) : (
                    latestAlerts.map((alert, index) => (
                      <div key={index} className={`notification-item priority-${alert.priority.toLowerCase()}`}>
                        <div className="notification-item-header">
                          <span className="notification-priority">
                            {getPriorityIcon(alert.priority)}
                          </span>
                          <span className="notification-time">{getTimeAgo(alert.timestamp)}</span>
                        </div>
                        <div className="notification-content">
                          <h4>{alert.type}</h4>
                          <p>{alert.message}</p>
                          {alert.metric && (
                            <div className="notification-metric">
                              <strong>{alert.metric}:</strong> {alert.value}
                              {alert.threshold && ` (Threshold: ${alert.threshold})`}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {alerts.length > 5 && (
                  <div className="notification-footer">
                    <a href="#/alerts">View all {alerts.length} alerts →</a>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="user-profile">👤 Admin</div>
        </div>
      </div>
    </div>
  );
};

export default Header;