import { useState, useEffect, useRef } from 'react';
import '../css/Resources.css';

interface NegotiationRequest {
  requesting_hospital: string;
  num_offering_hospitals: number;
  resource_type: string;
  quantity: number;
  scenario_type: string;
  urgency: string;
}

interface Notification {
  type: string;
  title: string;
  message: string;
  timestamp: string;
  action_required?: string;
}

interface NegotiationResult {
  status: string;
  message: string;
  scenario: string;
  fake_hospitals_generated: number;
  workflow_result?: any;
  notification?: Notification;
  contract?: any;
  total_time_seconds: number;
}

interface HMISData {
  departments: {
    icu: {
      patients: number;
      capacity: number;
      occupancy_rate: number;
      ventilators_in_use: number;
    };
    emergency: {
      patients: number;
      capacity: number;
    };
  };
  bed_summary: {
    total_beds: number;
    occupied_beds: number;
    available_beds: number;
  };
}

interface ResourceData {
  icon: string;
  name: string;
  current: number;
  total: number;
  status: 'critical' | 'warning' | 'good';
}

interface NegotiationEvent {
  event: string;
  message?: string;
  agent?: string;
  offer?: any;
  reason?: string;
  decision?: any;
  [key: string]: any;
}

export default function Resources() {
  const [isNegotiating, setIsNegotiating] = useState(false);
  const [negotiationResult, setNegotiationResult] = useState<NegotiationResult | null>(null);
  const [negotiationEvents, setNegotiationEvents] = useState<NegotiationEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [resourcesData, setResourcesData] = useState<ResourceData[]>([]);
  const [hospitalData, setHospitalData] = useState<Record<string, HMISData>>({});
  const [isLoading, setIsLoading] = useState(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [formData, setFormData] = useState<NegotiationRequest>({
    requesting_hospital: 'H001',
    num_offering_hospitals: 3,
    resource_type: 'ventilators',
    quantity: 5,
    scenario_type: 'normal',
    urgency: 'high'
  });

  // Fetch resources data from HMIS API
  useEffect(() => {
    const fetchResources = async () => {
      try {
        const hospitals = ['H001', 'H002', 'H003'];
        const hospitalPromises = hospitals.map(id =>
          fetch(`http://localhost:8000/api/v1/mock/hmis/hospitals/${id}/admissions`, {
            headers: { 'Authorization': 'Bearer hmis_demo_key_12345' }
          }).then(res => res.json())
        );

        const results = await Promise.all(hospitalPromises);

        // Store all hospital data
        const data: Record<string, HMISData> = {};
        results.forEach((result, index) => {
          data[hospitals[index]] = result;
        });
        setHospitalData(data);

        // Process Apollo City (H001) data for resource cards
        const apolloData = results[0];
        const icuAvailable = apolloData.departments.icu.capacity - apolloData.departments.icu.patients;
        const icuPercent = (apolloData.departments.icu.patients / apolloData.departments.icu.capacity) * 100;

        const ventilatorsTotal = 45;
        const ventilatorsInUse = apolloData.departments.icu.ventilators_in_use;
        const ventilatorsPercent = (ventilatorsInUse / ventilatorsTotal) * 100;

        const wheelchairsTotal = 50;
        const wheelchairsInUse = 32;
        const wheelchairsPercent = (wheelchairsInUse / wheelchairsTotal) * 100;

        setResourcesData([
          {
            icon: '🛏️',
            name: 'ICU Beds',
            current: icuAvailable,
            total: apolloData.departments.icu.capacity,
            status: icuPercent > 90 ? 'critical' : icuPercent > 75 ? 'warning' : 'good'
          },
          {
            icon: '🚑',
            name: 'Ventilators',
            current: ventilatorsInUse,
            total: ventilatorsTotal,
            status: ventilatorsPercent > 85 ? 'critical' : ventilatorsPercent > 70 ? 'warning' : 'good'
          },
          {
            icon: '♿',
            name: 'Wheelchairs',
            current: wheelchairsInUse,
            total: wheelchairsTotal,
            status: wheelchairsPercent > 85 ? 'critical' : wheelchairsPercent > 70 ? 'warning' : 'good'
          }
        ]);

        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching resources:', error);
        setIsLoading(false);
      }
    };

    fetchResources();
    const interval = setInterval(fetchResources, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'num_offering_hospitals' || name === 'quantity' ? parseInt(value) : value
    }));
  };

  const handleNegotiate = async () => {
    setIsNegotiating(true);
    setError(null);
    setNegotiationResult(null);
    setNegotiationEvents([]);

    abortControllerRef.current = new AbortController();

    try {
      // Use the Parliament endpoint with proper SSE handling
      const response = await fetch('http://localhost:8000/api/v1/parliament/negotiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initiator_hospital_id: 'HOSP_A',
          resource_type: formData.resource_type,
          quantity: formData.quantity,
          urgency: formData.urgency,
          duration_days: 7,
          max_budget: 100000
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Handle SSE stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let finalDecision: any = null;

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('Stream complete');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              console.log('Event:', eventData);

              // Add to events list
              setNegotiationEvents(prev => [...prev, eventData]);

              // Store final decision
              if (eventData.event === 'negotiation_completed') {
                finalDecision = eventData.decision;
              }

              if (eventData.event === 'stream_complete') {
                // Convert to old format for compatibility
                if (finalDecision) {
                  setNegotiationResult({
                    status: finalDecision.success ? 'success' : 'failed',
                    message: finalDecision.success ? 'Negotiation completed successfully' : 'Negotiation failed',
                    scenario: formData.scenario_type,
                    fake_hospitals_generated: formData.num_offering_hospitals,
                    notification: {
                      type: finalDecision.success ? 'success' : 'error',
                      title: finalDecision.success ? 'Deal Reached' : 'No Deal',
                      message: finalDecision.reasoning || finalDecision.reason || '',
                      timestamp: new Date().toISOString()
                    },
                    total_time_seconds: 0,
                    workflow_result: {
                      final_state: {
                        current_step: 'complete',
                        analysis_complete: true,
                        offers_collected: true,
                        negotiation_complete: true,
                        best_offer: finalDecision.selected_offers?.[0] || null
                      }
                    }
                  });
                }
                setIsNegotiating(false);
                return;
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }

      setIsNegotiating(false);

    } catch (err) {
      console.error('Negotiation error:', err);

      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err instanceof Error ? err.message : 'An error occurred during negotiation');
      }

      setIsNegotiating(false);
    }
  };

  const stopNegotiation = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsNegotiating(false);
      setNegotiationEvents(prev => [...prev, {
        event: 'cancelled',
        message: 'Negotiation cancelled by user'
      }]);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>📦 Hospital Resources</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>Inventory & capacity management</p>
        </div>
      </div>

      <div className="resources-grid">
        {isLoading ? (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px' }}>
            Loading resources...
          </div>
        ) : (
          resourcesData.map((resource, index) => {
            const percentage = (resource.current / resource.total) * 100;
            return (
              <div key={index} className="resource-card">
                <div className="resource-icon">{resource.icon}</div>
                <div className="resource-name">{resource.name}</div>
                <div className="resource-count">{resource.current} / {resource.total}</div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${percentage}%` }}></div>
                </div>
                <div className={`resource-status ${resource.status}`}>
                  {resource.status === 'critical' ? 'Critical' : resource.status === 'warning' ? 'Warning' : 'Good'}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="panel">
        <h3>🏥 Multi-Hospital Comparison</h3>
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>Loading comparison data...</div>
        ) : (
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Resource</th>
                <th>Apollo City</th>
                <th>Fortis</th>
                <th>Max Centre</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>ICU Beds</td>
                <td>
                  {hospitalData['H001']?.departments?.icu ?
                    `${hospitalData['H001'].departments.icu.capacity - hospitalData['H001'].departments.icu.patients}/${hospitalData['H001'].departments.icu.capacity}`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H002']?.departments?.icu ?
                    `${hospitalData['H002'].departments.icu.capacity - hospitalData['H002'].departments.icu.patients}/${hospitalData['H002'].departments.icu.capacity}`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H003']?.departments?.icu ?
                    `${hospitalData['H003'].departments.icu.capacity - hospitalData['H003'].departments.icu.patients}/${hospitalData['H003'].departments.icu.capacity}`
                    : '...'}
                </td>
              </tr>
              <tr>
                <td>Ventilators</td>
                <td>
                  {hospitalData['H001']?.departments?.icu ?
                    `${hospitalData['H001'].departments.icu.ventilators_in_use}/45`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H002']?.departments?.icu ?
                    `${hospitalData['H002'].departments.icu.ventilators_in_use}/35`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H003']?.departments?.icu ?
                    `${hospitalData['H003'].departments.icu.ventilators_in_use}/30`
                    : '...'}
                </td>
              </tr>
              <tr>
                <td>Total Beds</td>
                <td>
                  {hospitalData['H001']?.bed_summary ?
                    `${hospitalData['H001'].bed_summary.available_beds}/${hospitalData['H001'].bed_summary.total_beds}`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H002']?.bed_summary ?
                    `${hospitalData['H002'].bed_summary.available_beds}/${hospitalData['H002'].bed_summary.total_beds}`
                    : '...'}
                </td>
                <td>
                  {hospitalData['H003']?.bed_summary ?
                    `${hospitalData['H003'].bed_summary.available_beds}/${hospitalData['H003'].bed_summary.total_beds}`
                    : '...'}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* Autonomous Negotiation Section */}
      <div className="panel" style={{ marginTop: '24px' }}>
        <h3>🤝 Autonomous Resource Negotiation</h3>
        <p style={{ color: '#6B7280', marginBottom: '20px' }}>
          Initiate AI-powered negotiations with other hospitals to secure critical resources
        </p>

        <div className="negotiation-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Resource Type</label>
              <select
                name="resource_type"
                value={formData.resource_type}
                onChange={handleInputChange}
                disabled={isNegotiating}
              >
                <option value="ventilators">Ventilators</option>
                <option value="icu_beds">ICU Beds</option>
                <option value="pulmonologists">Pulmonologists</option>
                <option value="nurses">Nurses</option>
              </select>
            </div>

            <div className="form-group">
              <label>Quantity</label>
              <input
                type="number"
                name="quantity"
                value={formData.quantity}
                onChange={handleInputChange}
                min="1"
                disabled={isNegotiating}
              />
            </div>

            <div className="form-group">
              <label>Urgency Level</label>
              <select
                name="urgency"
                value={formData.urgency}
                onChange={handleInputChange}
                disabled={isNegotiating}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          {!isNegotiating ? (
            <button
              className="negotiate-button"
              onClick={handleNegotiate}
            >
              🚀 Start AI Negotiation
            </button>
          ) : (
            <button
              className="negotiate-button"
              onClick={stopNegotiation}
              style={{ background: '#ef4444' }}
            >
              ⏹️ Stop Negotiation
            </button>
          )}
        </div>

        {/* Live Negotiation Events */}
        {negotiationEvents.length > 0 && (
          <div style={{ marginTop: '20px', padding: '16px', background: '#f9fafb', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '12px' }}>📡 Live Events</h4>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {negotiationEvents.map((event, index) => (
                <div key={index} style={{
                  padding: '8px',
                  marginBottom: '8px',
                  background: 'white',
                  borderLeft: '3px solid #667eea',
                  borderRadius: '4px'
                }}>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>
                    {event.event}
                  </div>
                  {event.agent && (
                    <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                      Agent: {event.agent}
                    </div>
                  )}
                  {event.message && (
                    <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                      {event.message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="negotiation-error">
            <h4>❌ Error</h4>
            <p>{error}</p>
          </div>
        )}

        {/* Negotiation Results */}
        {negotiationResult && (
          <div className="negotiation-results">
            <div className="result-header">
              <h4>{negotiationResult.message}</h4>
              <span className={`status-badge ${negotiationResult.status}`}>
                {negotiationResult.status}
              </span>
            </div>

            {/* Notification */}
            {negotiationResult.notification && (
              <div className={`notification ${negotiationResult.notification.type}`}>
                <div className="notification-header">
                  <strong>{negotiationResult.notification.title}</strong>
                  <span className="notification-time">
                    {new Date(negotiationResult.notification.timestamp).toLocaleString()}
                  </span>
                </div>
                <p>{negotiationResult.notification.message}</p>
              </div>
            )}

            {/* Workflow Details */}
            {negotiationResult.workflow_result?.final_state && (
              <div className="workflow-details">
                <h5>📊 Workflow Details</h5>
                <div className="workflow-grid">
                  <div className="workflow-item">
                    <span className="workflow-label">Current Step:</span>
                    <span className="workflow-value">
                      {negotiationResult.workflow_result.final_state.current_step}
                    </span>
                  </div>
                  <div className="workflow-item">
                    <span className="workflow-label">Analysis Complete:</span>
                    <span className="workflow-value">
                      {negotiationResult.workflow_result.final_state.analysis_complete ? '✅' : '❌'}
                    </span>
                  </div>
                  <div className="workflow-item">
                    <span className="workflow-label">Offers Collected:</span>
                    <span className="workflow-value">
                      {negotiationResult.workflow_result.final_state.offers_collected ? '✅' : '❌'}
                    </span>
                  </div>
                  <div className="workflow-item">
                    <span className="workflow-label">Negotiation Complete:</span>
                    <span className="workflow-value">
                      {negotiationResult.workflow_result.final_state.negotiation_complete ? '✅' : '❌'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}