import { useState, useEffect } from 'react';
import '../css/History.css';

interface HistoryEvent {
  id: string;
  type: 'negotiation' | 'prediction' | 'alert' | 'chat';
  title: string;
  description: string;
  timestamp: Date;
  metadata?: any;
}

export default function History() {
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const allEvents: HistoryEvent[] = [];

        // Fetch Parliament sessions
        try {
          const parliamentResponse = await fetch('http://localhost:8000/api/v1/parliament/sessions');
          const parliamentData = await parliamentResponse.json();
          
          if (parliamentData.sessions) {
            parliamentData.sessions.slice(0, 5).forEach((session: any) => {
              allEvents.push({
                id: `parl-${session.session_id}`,
                type: 'negotiation',
                title: 'AI Negotiation Session',
                description: `Session ${session.session_id}: ${session.current_round || 0} rounds completed. Status: ${session.status}`,
                timestamp: new Date(session.created_at),
                metadata: session
              });
            });
          }
        } catch (err) {
          console.error('Failed to fetch parliament data:', err);
        }

        // Fetch Alerts
        try {
          const alertsResponse = await fetch('http://localhost:8000/api/v1/predictions/alerts/H001');
          const alertsData = await alertsResponse.json();
          
          if (alertsData.alerts) {
            alertsData.alerts.slice(0, 5).forEach((alert: any, index: number) => {
              allEvents.push({
                id: `alert-${index}`,
                type: 'alert',
                title: `${alert.priority} Alert: ${alert.type}`,
                description: alert.message,
                timestamp: new Date(alert.timestamp),
                metadata: alert
              });
            });
          }
        } catch (err) {
          console.error('Failed to fetch alerts:', err);
        }

        // Fetch Predictions history
        try {
          const predResponse = await fetch('http://localhost:8000/api/v1/predictions/H001/admissions?days=7');
          const predData = await predResponse.json();
          
          if (predData.predictions && predData.predictions.length > 0) {
            allEvents.push({
              id: 'pred-latest',
              type: 'prediction',
              title: 'Admission Forecast Generated',
              description: `Predicted ${predData.predictions[0]?.predicted_admissions || 0} admissions with ${(predData.accuracy * 100).toFixed(1)}% accuracy`,
              timestamp: new Date(),
              metadata: predData
            });
          }
        } catch (err) {
          console.error('Failed to fetch predictions:', err);
        }

        // Sort by timestamp (newest first)
        allEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
        setEvents(allEvents);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching history:', error);
        setIsLoading(false);
      }
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const filteredEvents = filter === 'all' 
    ? events 
    : events.filter(event => {
        if (filter === 'negotiations') return event.type === 'negotiation';
        if (filter === 'predictions') return event.type === 'prediction';
        if (filter === 'alerts') return event.type === 'alert';
        return true;
      });

  const getTimeAgo = (timestamp: Date) => {
    const seconds = Math.floor((new Date().getTime() - timestamp.getTime()) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hour${Math.floor(seconds / 3600) > 1 ? 's' : ''} ago`;
    return `${Math.floor(seconds / 86400)} day${Math.floor(seconds / 86400) > 1 ? 's' : ''} ago`;
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'negotiation': return '🏛️';
      case 'prediction': return '📈';
      case 'alert': return '⚠️';
      case 'chat': return '💬';
      default: return '📝';
    }
  };

  const getEventLabel = (type: string) => {
    switch (type) {
      case 'negotiation': return 'Negotiation';
      case 'prediction': return 'Prediction';
      case 'alert': return 'Alert';
      case 'chat': return 'Chat';
      default: return 'Event';
    }
  };

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>📜 History & Activity Log</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>Complete system event timeline</p>
        </div>
      </div>

      <div className="history-filters">
        <button 
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All Events
        </button>
        <button 
          className={`filter-btn ${filter === 'negotiations' ? 'active' : ''}`}
          onClick={() => setFilter('negotiations')}
        >
          Negotiations
        </button>
        <button 
          className={`filter-btn ${filter === 'predictions' ? 'active' : ''}`}
          onClick={() => setFilter('predictions')}
        >
          Predictions
        </button>
        <button 
          className={`filter-btn ${filter === 'alerts' ? 'active' : ''}`}
          onClick={() => setFilter('alerts')}
        >
          Alerts
        </button>
      </div>

      <div className="timeline-container">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            Loading history...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
            No {filter !== 'all' ? filter : 'events'} found
          </div>
        ) : (
          filteredEvents.map((event) => (
            <div key={event.id} className="timeline-item">
              <div className={`timeline-marker ${event.type}`}></div>
              <div className="timeline-card">
                <div className="card-header">
                  <span className="event-type">
                    {getEventIcon(event.type)} {getEventLabel(event.type)}
                  </span>
                  <span className="event-time">{getTimeAgo(event.timestamp)}</span>
                </div>
                <h4>{event.title}</h4>
                <p>{event.description}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
