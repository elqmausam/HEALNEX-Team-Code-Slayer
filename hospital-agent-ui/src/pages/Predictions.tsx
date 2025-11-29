import { useState, useEffect } from 'react';
import '../css/Predictions.css';

interface Prediction {
  date: string;
  predicted_admissions: number;
  risk_level: string;
  confidence: number;
  contributing_factors: string[];
}

interface ForecastData {
  hospital_id: string;
  predictions: Prediction[];
  confidence_score: number;
}

interface HistoricalData {
  date: string;
  predicted: number;
  actual: number;
  accuracy: number;
}

interface Factor {
  name: string;
  impact: string;
  value?: string;
}

export default function Predictions() {
  const [forecastHours, setForecastHours] = useState(48);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([]);
  const [factors, setFactors] = useState<Factor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchPredictions();
    fetchHistorical();
    fetchFactors();
  }, [forecastHours]);

  const fetchPredictions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/predictions/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hospital_id: 'H001',
          forecast_hours: forecastHours,
          include_detailed_analysis: true,
        }),
      });
      const data = await response.json();
      setForecastData(data.prediction);
    } catch (error) {
      console.error('Failed to fetch forecast:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistorical = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/predictions/historical/H001?days=7');
      const data = await response.json();
      setHistoricalData(data.historical_data || []);
    } catch (error) {
      console.error('Failed to fetch historical:', error);
    }
  };

  const fetchFactors = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/predictions/factors/H001');
      const data = await response.json();
      if (data.factors) {
        const formattedFactors: Factor[] = data.factors.map((f: string) => ({
          name: f,
          impact: ['Weather', 'AQI'].includes(f) ? 'high' : 
                  ['Seasonal', 'Historical'].includes(f) ? 'medium' : 'low'
        }));
        setFactors(formattedFactors);
      }
    } catch (error) {
      console.error('Failed to fetch factors:', error);
    }
  };

  const getFirstPrediction = () => {
    if (!forecastData?.predictions || forecastData.predictions.length === 0) {
      return { predicted_admissions: 0, confidence: 0, risk_level: 'unknown' };
    }
    return forecastData.predictions[0];
  };

  const firstPred = getFirstPrediction();

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>📈 Predictive Analytics</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>AI-powered admission forecasting</p>
        </div>
      </div>

      <div className="forecast-controls">
        <button 
          className={`control-btn ${forecastHours === 24 ? 'active' : ''}`}
          onClick={() => setForecastHours(24)}
        >
          Next 24h
        </button>
        <button 
          className={`control-btn ${forecastHours === 48 ? 'active' : ''}`}
          onClick={() => setForecastHours(48)}
        >
          Next 48h
        </button>
        <button 
          className={`control-btn ${forecastHours === 168 ? 'active' : ''}`}
          onClick={() => setForecastHours(168)}
        >
          Next 7 days
        </button>
      </div>

      <div className="prediction-card">
        <h2>📊 Admission Forecast</h2>
        {isLoading ? (
          <div className="forecast-value">Loading...</div>
        ) : (
          <>
            <div className="forecast-value">
              {firstPred.predicted_admissions} admissions
            </div>
            <div className="forecast-time">
              in next {forecastHours < 48 ? '24 hours' : forecastHours === 48 ? '48 hours' : '7 days'}
            </div>
            <div className="confidence">
              Confidence: {Math.round((firstPred.confidence || 0) * 100)}%
            </div>
          </>
        )}
        <div className="chart-placeholder">📊 Chart visualization here</div>
      </div>

      <div className="content-grid">
        <div className="panel">
          <h3>🔍 Contributing Factors</h3>
          <div className="factor-list">
            {factors.length > 0 ? (
              factors.map((factor, index) => (
                <div key={index} className="factor-item">
                  <span className="factor-name">{factor.name}</span>
                  <span className={`factor-impact ${factor.impact}`}>
                    {factor.impact === 'high' ? 'High Impact' : 
                     factor.impact === 'medium' ? 'Medium' : 'Low'}
                  </span>
                </div>
              ))
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#6B7280' }}>
                Loading factors...
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <h3>⚠️ Active Alerts</h3>
          {firstPred.risk_level === 'high' && (
            <div className="alert-badge critical">🔴 Surge Alert Active</div>
          )}
          {firstPred.risk_level === 'medium' && (
            <div className="alert-badge warning">⚠️ Capacity Warning</div>
          )}
          {firstPred.risk_level === 'low' && (
            <div className="alert-badge" style={{ background: '#10B981', color: 'white' }}>
              ✅ Normal Capacity
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <h3>📊 Historical Accuracy</h3>
        <table className="accuracy-table">
          <thead>
            <tr><th>Period</th><th>Predicted</th><th>Actual</th><th>Accuracy</th></tr>
          </thead>
          <tbody>
            {historicalData.length > 0 ? (
              historicalData.slice(0, 5).map((data, index) => (
                <tr key={index}>
                  <td>{new Date(data.date).toLocaleDateString()}</td>
                  <td>{data.predicted}</td>
                  <td>{data.actual}</td>
                  <td className={data.accuracy >= 90 ? 'accuracy-good' : 'accuracy-medium'}>
                    {Math.round(data.accuracy)}%
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '20px', color: '#6B7280' }}>
                  No historical data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
