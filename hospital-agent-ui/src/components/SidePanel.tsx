import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import '../css/SidePanel.css';

const SidePanel: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { path: '/dashboard', icon: '📊', label: 'Dashboard' },
    { path: '/parliament', icon: '🏛️', label: 'The Parliament' },
    { path: '/predictions', icon: '📈', label: 'Predictions' },
    { path: '/chat', icon: '💬', label: 'AI Chat' },
    { path: '/resources', icon: '📦', label: 'Resources' },
    { path: '/alerts', icon: '⚠️', label: 'Alerts' },
    { path: '/history', icon: '📜', label: 'History' },
    { path: '/documents', icon: '📚', label: 'Documents' },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <div className="sidebar">
      {menuItems.map((item) => (
        <div
          key={item.path}
          className={`sidebar-item ${location.pathname === item.path || (location.pathname === '/' && item.path === '/dashboard') ? 'active' : ''}`}
          onClick={() => handleNavigation(item.path)}
        >
          <span className="sidebar-icon">{item.icon}</span>
          {item.label}
        </div>
      ))}
    </div>
  );
};

export default SidePanel;
