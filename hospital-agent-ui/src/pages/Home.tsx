import { Link } from 'react-router-dom';
import './Home.css';

export default function Home() {
  return (
    <div className="home-container">
      <div className="home-content">
        <div className="home-header">
          <h1>🏥 Hospital Agent</h1>
          <p>Interactive Dashboard - Multi-Agent Coordination System</p>
        </div>

        <div className="mockups-grid">
          <Link to="/dashboard" className="mockup-card">
            <div className="mockup-icon">📊</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">Dashboard Overview</div>
            <div className="mockup-desc">
              Main dashboard showing system health, hospital agents status, active negotiations, predictions, alerts, and recent activity feed.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Agent Status</span>
              <span className="feature-tag">Stat Cards</span>
              <span className="feature-tag">Alerts</span>
              <span className="feature-tag">Activity Feed</span>
            </div>
            <span className="view-button">View Dashboard →</span>
          </Link>

          <Link to="/parliament" className="mockup-card">
            <div className="mockup-icon">🏛️</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">The Parliament</div>
            <div className="mockup-desc">
              Real-time AI-to-AI negotiation interface showing autonomous resource negotiations between hospital agents with live event streaming.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Live Stream</span>
              <span className="feature-tag">Event Timeline</span>
              <span className="feature-tag">Offer Management</span>
              <span className="feature-tag">AI Decision Making</span>
            </div>
            <span className="view-button">View Parliament →</span>
          </Link>

          <Link to="/predictions" className="mockup-card">
            <div className="mockup-icon">📈</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">Predictive Analytics</div>
            <div className="mockup-desc">
              Advanced forecasting dashboard with admission predictions, contributing factors analysis, active alerts, and historical accuracy tracking.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Forecasting</span>
              <span className="feature-tag">Factor Analysis</span>
              <span className="feature-tag">Alert System</span>
              <span className="feature-tag">Accuracy Tracking</span>
            </div>
            <span className="view-button">View Predictions →</span>
          </Link>

          <Link to="/chat" className="mockup-card">
            <div className="mockup-icon">💬</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">AI Chat Assistant</div>
            <div className="mockup-desc">
              Intelligent conversational interface with suggested questions, context awareness, RAG-powered protocol search, and streaming support.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Chat Interface</span>
              <span className="feature-tag">Quick Suggestions</span>
              <span className="feature-tag">RAG Search</span>
              <span className="feature-tag">Streaming</span>
            </div>
            <span className="view-button">View Chat →</span>
          </Link>

          <Link to="/resources" className="mockup-card">
            <div className="mockup-icon">📦</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">Hospital Resources</div>
            <div className="mockup-desc">
              Comprehensive resource inventory tracking with availability monitoring, multi-hospital comparison, and financial overview.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Inventory</span>
              <span className="feature-tag">Progress Tracking</span>
              <span className="feature-tag">Comparison</span>
              <span className="feature-tag">Financial</span>
            </div>
            <span className="view-button">View Resources →</span>
          </Link>

          <Link to="/alerts" className="mockup-card">
            <div className="mockup-icon">⚠️</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">Alerts & Notifications</div>
            <div className="mockup-desc">
              Real-time alert management with priority-based filtering, configuration settings, and notification preferences.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Alert Cards</span>
              <span className="feature-tag">Filtering</span>
              <span className="feature-tag">Configuration</span>
              <span className="feature-tag">Actions</span>
            </div>
            <span className="view-button">View Alerts →</span>
          </Link>

          <Link to="/history" className="mockup-card">
            <div className="mockup-icon">📜</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">History & Activity Log</div>
            <div className="mockup-desc">
              Comprehensive activity timeline showing negotiations, predictions, alerts, chat sessions, and system events with filtering.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Timeline View</span>
              <span className="feature-tag">Event Tracking</span>
              <span className="feature-tag">Filters</span>
              <span className="feature-tag">Export</span>
            </div>
            <span className="view-button">View History →</span>
          </Link>

          <Link to="/documents" className="mockup-card">
            <div className="mockup-icon">📚</div>
            <div className="status-badge">✨ Complete</div>
            <div className="mockup-title">Documents & Protocols</div>
            <div className="mockup-desc">
              Hospital protocols and clinical guidelines library with category organization, search functionality, and document management.
            </div>
            <div className="mockup-features">
              <span className="feature-tag">Categories</span>
              <span className="feature-tag">Search</span>
              <span className="feature-tag">Upload</span>
              <span className="feature-tag">RAG Ready</span>
            </div>
            <span className="view-button">View Documents →</span>
          </Link>
        </div>

        <div className="home-footer">
          <p>
            Built for Hospital Agent v2.0.0 with Multi-Agent Coordination
          </p>
        </div>
      </div>
    </div>
  );
}
