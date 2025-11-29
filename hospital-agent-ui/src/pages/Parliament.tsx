import { useState, useEffect, useRef } from 'react';
import '../css/Parliament.css';

interface NegotiationEvent {
  event: string;
  message?: string;
  timestamp?: string;
  data?: any;
  agent?: string;
  offer?: any;
  reason?: string;
  reasoning?: string;
  decision?: any;
  session_id?: string;
  participants?: string[];
  offers_count?: number;
}

export default function Parliament() {
  const [resourceType, setResourceType] = useState('ventilators');
  const [quantity, setQuantity] = useState(8);
  const [maxBudget, setMaxBudget] = useState(80000);
  const [urgency, setUrgency] = useState('high');
  const [isNegotiating, setIsNegotiating] = useState(false);
  const [events, setEvents] = useState<NegotiationEvent[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const startNegotiation = async () => {
    setIsNegotiating(true);
    setEvents([]);
    setSessionId('');

    // Create abort controller for cleanup
    abortControllerRef.current = new AbortController();

    // Add initial event
    setEvents([{
      event: 'negotiation_started',
      message: 'Initiating AI-to-AI Negotiation',
      data: `Requesting ${quantity} ${resourceType} with max budget ₹${maxBudget.toLocaleString()}`,
      timestamp: new Date().toLocaleTimeString()
    }]);

    try {
      // Call the CORRECT parliament endpoint with SSE streaming
      const response = await fetch('http://localhost:8000/api/v1/parliament/negotiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initiator_hospital_id: 'HOSP_A', // Apollo City Hospital
          resource_type: resourceType,
          quantity: quantity,
          urgency: urgency,
          duration_days: 7,
          max_budget: maxBudget,
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // Read the SSE stream properly
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('Stream complete');
          break;
        }

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Split by lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        // Process each line
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
              console.log('Event received:', eventData);

              // Process the event
              processNegotiationEvent(eventData);

              // Check if stream is complete
              if (eventData.event === 'stream_complete') {
                setIsNegotiating(false);
                return;
              }
            } catch (e) {
              console.error('Failed to parse event:', line, e);
            }
          }
        }
      }

      setIsNegotiating(false);

    } catch (error) {
      console.error('Negotiation error:', error);

      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Negotiation aborted');
      } else {
        setEvents(prev => [...prev, {
          event: 'error',
          message: '⚠️ Negotiation Error',
          data: error instanceof Error ? error.message : 'Unknown error occurred',
          timestamp: new Date().toLocaleTimeString()
        }]);
      }

      setIsNegotiating(false);
    }
  };

  const processNegotiationEvent = (eventData: NegotiationEvent) => {
    const timestamp = new Date().toLocaleTimeString();

    switch (eventData.event) {
      case 'negotiation_initiated':
        setSessionId(eventData.session_id || '');
        setEvents(prev => [...prev, {
          event: 'negotiation_initiated',
          message: '✓ Negotiation Session Created',
          data: `Session ID: ${eventData.session_id?.slice(0, 8)}...`,
          timestamp
        }]);
        break;

      case 'broadcasting_request':
        setEvents(prev => [...prev, {
          event: 'broadcasting_request',
          message: '📡 Broadcasting Request',
          data: `Sending to: ${eventData.participants?.join(', ')}`,
          timestamp
        }]);
        break;

      case 'agent_analyzing':
        setEvents(prev => [...prev, {
          event: 'agent_analyzing',
          message: `🤖 ${eventData.agent} Analyzing`,
          data: 'Agent is evaluating the resource request...',
          timestamp
        }]);
        break;

      case 'offer_received':
        const offer = eventData.offer;
        setEvents(prev => [...prev, {
          event: 'offer_received',
          message: `✓ Offer from ${eventData.agent}`,
          data: `${offer?.quantity || 0} units @ ₹${offer?.price_per_unit?.toLocaleString() || 0}/unit`,
          offer: offer,
          reasoning: eventData.reasoning,
          timestamp
        }]);
        break;

      case 'offer_declined':
        setEvents(prev => [...prev, {
          event: 'offer_declined',
          message: `✗ ${eventData.agent} Declined`,
          data: eventData.reason || 'Unable to fulfill request',
          timestamp
        }]);
        break;

      case 'negotiation_round_started':
        setEvents(prev => [...prev, {
          event: 'negotiation_round_started',
          message: '🔄 Negotiation Round Started',
          data: `Processing ${eventData.offers_count} offers`,
          timestamp
        }]);
        break;

      case 'offer_adjusted':
        setEvents(prev => [...prev, {
          event: 'offer_adjusted',
          message: `↻ ${eventData.agent} Adjusted Offer`,
          data: 'Agent modified their proposal to be more competitive',
          timestamp
        }]);
        break;

      case 'making_decision':
        setEvents(prev => [...prev, {
          event: 'making_decision',
          message: '🎯 AI Making Final Decision',
          data: 'Analyzing all offers to select the best option...',
          timestamp
        }]);
        break;

      case 'negotiation_completed':
        const decision = eventData.decision;
        if (decision?.success) {
          const selectedOffers = decision.selected_offers || [];
          const totalCost = decision.total_cost || 0;

          setEvents(prev => [...prev, {
            event: 'negotiation_completed',
            message: '✅ Deal Reached!',
            data: `Total Cost: ₹${totalCost.toLocaleString()}`,
            decision: decision,
            timestamp
          }]);

          // Add details for each selected offer
          selectedOffers.forEach((offer: any, index: number) => {
            setTimeout(() => {
              setEvents(prev => [...prev, {
                event: 'offer_selected',
                message: `📋 Selected: ${offer.hospital}`,
                data: `${offer.quantity} units for ₹${offer.total_cost?.toLocaleString()}`,
                timestamp: new Date().toLocaleTimeString()
              }]);
            }, (index + 1) * 200);
          });
        } else {
          setEvents(prev => [...prev, {
            event: 'negotiation_failed',
            message: '✗ No Deal',
            data: decision?.reason || 'No suitable offers received',
            timestamp
          }]);
        }
        break;

      case 'error':
        setEvents(prev => [...prev, {
          event: 'error',
          message: '⚠️ Error Occurred',
          data: eventData.message || 'An error occurred during negotiation',
          timestamp
        }]);
        break;

      default:
        console.log('Unknown event type:', eventData.event);
    }
  };

  const getEventIcon = (eventType: string) => {
    const iconMap: Record<string, string> = {
      'negotiation_started': '🚀',
      'negotiation_initiated': '✓',
      'broadcasting_request': '📡',
      'agent_analyzing': '🤖',
      'offer_received': '📥',
      'offer_declined': '✗',
      'offer_adjusted': '↻',
      'negotiation_round_started': '🔄',
      'making_decision': '🎯',
      'negotiation_completed': '✅',
      'negotiation_failed': '✗',
      'offer_selected': '📋',
      'error': '⚠️',
    };
    return iconMap[eventType] || '📋';
  };

  const getEventClass = (eventType: string) => {
    if (eventType.includes('start') || eventType.includes('initiat')) return 'initiated';
    if (eventType.includes('broadcast')) return 'broadcast';
    if (eventType.includes('analyzing')) return 'evaluation';
    if (eventType.includes('offer_received') || eventType.includes('selected')) return 'offer';
    if (eventType.includes('decline') || eventType.includes('failed')) return 'decline';
    if (eventType.includes('decision') || eventType.includes('round')) return 'evaluation';
    if (eventType.includes('completed')) return 'success';
    if (eventType.includes('error')) return 'decline';
    return 'default';
  };

  const stopNegotiation = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsNegotiating(false);
      setEvents(prev => [...prev, {
        event: 'cancelled',
        message: '⏹️ Negotiation Cancelled',
        data: 'User stopped the negotiation',
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>🏛️ The Parliament</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>
            Real-time AI-to-AI multi-agent negotiation interface
          </p>
        </div>
      </div>

      <div className="session-info">
        <div className="info-card">
          <div className="info-label">Session ID</div>
          <div className="info-value">
            {sessionId ? sessionId.slice(0, 8) + '...' : 'Not started'}
          </div>
        </div>
        <div className="info-card">
          <div className="info-label">Status</div>
          <div className="info-value">
            <span className={`status-badge ${isNegotiating ? 'active' : 'inactive'}`}>
              ● {isNegotiating ? 'Negotiating' : 'Ready'}
            </span>
          </div>
        </div>
        <div className="info-card">
          <div className="info-label">Participants</div>
          <div className="info-value">3 AI Agents</div>
        </div>
        <div className="info-card">
          <div className="info-label">Events</div>
          <div className="info-value">{events.length}</div>
        </div>
      </div>

      <div className="content-layout">
        <div className="negotiation-panel">
          <div className="panel-header">
            <h3>🤖 Initiate New Negotiation</h3>
          </div>

          <div className="form-group">
            <label>Resource Type</label>
            <select
              className="form-control"
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              disabled={isNegotiating}
            >
              <option value="ventilators">Ventilators</option>
              <option value="icu_beds">ICU Beds</option>
              <option value="pulmonologists">Pulmonologists</option>
              <option value="nurses">Nurses</option>
            </select>
          </div>

          <div className="form-group">
            <label>Quantity Needed</label>
            <input
              type="number"
              className="form-control"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              disabled={isNegotiating}
              min="1"
              max="50"
            />
          </div>

          <div className="form-group">
            <label>Max Budget (₹)</label>
            <input
              type="number"
              className="form-control"
              value={maxBudget}
              onChange={(e) => setMaxBudget(Number(e.target.value))}
              disabled={isNegotiating}
              min="1000"
              step="1000"
            />
          </div>

          <div className="form-group">
            <label>Urgency Level</label>
            <select
              className="form-control"
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
              disabled={isNegotiating}
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {!isNegotiating ? (
            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '16px' }}
              onClick={startNegotiation}
            >
              🤖 Start AI Negotiation
            </button>
          ) : (
            <button
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: '16px', background: '#ef4444' }}
              onClick={stopNegotiation}
            >
              ⏹️ Stop Negotiation
            </button>
          )}
        </div>

        <div className="events-panel">
          <div className="panel-header">
            <h3>📡 Live Event Stream</h3>
            {isNegotiating && <span className="pulse-dot"></span>}
          </div>

          <div className="timeline">
            {events.length > 0 ? (
              events.map((event, index) => {
                const eventTitle = event.message || event.event || 'Event';
                const eventDesc = event.data || '';

                return (
                  <div key={index} className="timeline-item">
                    <div className={`timeline-dot ${getEventClass(event.event || 'default')}`}></div>
                    <div className="timeline-content">
                      <div className="event-title">
                        {getEventIcon(event.event || '')} {eventTitle}
                      </div>
                      {eventDesc && (
                        <div className="event-desc">
                          {eventDesc}
                        </div>
                      )}
                      {event.reasoning && (
                        <div className="event-desc" style={{ fontStyle: 'italic', marginTop: '4px' }}>
                          Reasoning: {event.reasoning}
                        </div>
                      )}
                      <div className="event-time">
                        {event.timestamp || new Date().toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6B7280' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>🏛️</div>
                <div style={{ fontSize: '18px', fontWeight: 500, marginBottom: '8px' }}>
                  Ready for Negotiation
                </div>
                <div style={{ fontSize: '14px' }}>
                  Configure parameters and click "Start AI Negotiation" to begin
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-label">Total Sessions Today</span>
          <span className="stat-value">24</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Success Rate</span>
          <span className="stat-value">87%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Duration</span>
          <span className="stat-value">22 sec</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Total Saved</span>
          <span className="stat-value">₹2.4M</span>
        </div>
      </div>
    </div>
  );
}