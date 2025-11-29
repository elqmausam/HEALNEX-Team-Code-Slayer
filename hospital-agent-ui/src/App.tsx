import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SidePanel from './components/SidePanel';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Parliament from './pages/Parliament';
import Chat from './pages/Chat';
import Predictions from './pages/Predictions';
import Resources from './pages/Resources';
import Alerts from './pages/Alerts';
import History from './pages/History';
import Documents from './pages/Documents';
import './css/App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <SidePanel />
        <Header />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/parliament" element={<Parliament />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/history" element={<History />} />
            <Route path="/documents" element={<Documents />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
