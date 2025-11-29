import { useState, useEffect } from 'react';
import '../css/Alerts.css';

interface Alert {
  type: string;
  priority: string;
  message: string;
  timestamp: string;
  metric?: string;
  value?: number;
  threshold?: number;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/predictions/alerts/H001');
        const data = await response.json();
        setAlerts(data.alerts || []);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching alerts:', error);
        setIsLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleAcknowledge = (index: number) => {
    setAlerts(prev => prev.filter((_, i) => i !== index));
  };

  const filteredAlerts = filter === 'all' 
    ? alerts 
    : alerts.filter(alert => alert.priority.toLowerCase() === filter.toLowerCase());

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

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>⚠️ Alerts & Notifications</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>Real-time alert management</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ color: '#6B7280' }}>
            {filteredAlerts.length} active {filteredAlerts.length === 1 ? 'alert' : 'alerts'}
          </span>
        </div>
      </div>

      <div className="filter-bar">
        <button 
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button 
          className={`filter-btn ${filter === 'critical' ? 'active' : ''}`}
          onClick={() => setFilter('critical')}
        >
          Critical
        </button>
        <button 
          className={`filter-btn ${filter === 'high' ? 'active' : ''}`}
          onClick={() => setFilter('high')}
        >
          High
        </button>
        <button 
          className={`filter-btn ${filter === 'medium' ? 'active' : ''}`}
          onClick={() => setFilter('medium')}
        >
          Medium
        </button>
      </div>

      <div className="alerts-list">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            Loading alerts...
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            No {filter !== 'all' ? filter : ''} alerts at this time
          </div>
        ) : (
          filteredAlerts.map((alert, index) => (
            <div key={index} className={`alert-card ${alert.priority.toLowerCase()}`}>
              <div className="alert-header">
                <span className="alert-priority">
                  {getPriorityIcon(alert.priority)} {alert.priority}
                </span>
                <span className="alert-time">{getTimeAgo(alert.timestamp)}</span>
              </div>
              <h3>{alert.type}</h3>
              <p>{alert.message}</p>
              {alert.metric && (
                <div style={{ 
                  marginTop: '12px', 
                  padding: '8px 12px', 
                  backgroundColor: 'rgba(0,0,0,0.05)', 
                  borderRadius: '4px',
                  fontSize: '14px'
                }}>
                  <strong>{alert.metric}:</strong> {alert.value}
                  {alert.threshold && ` (Threshold: ${alert.threshold})`}
                </div>
              )}
              <div className="alert-actions">
                <button className="btn" onClick={() => handleAcknowledge(index)}>
                  Acknowledge
                </button>
                <button className="btn">View Details</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
