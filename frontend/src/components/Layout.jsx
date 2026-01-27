/**
 * Layout Component
 * Main layout with top frame and left navigation bar
 */

import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

const Layout = ({ children }) => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <div className="layout">
      {/* Top Frame */}
      <header className="top-frame">
        <div className="top-frame-content">
          <h1 className="app-title">📈 Stock Analysis Dashboard</h1>
          <div className="top-frame-info">
            <span className="user-info">Welcome to Stock Analysis</span>
          </div>
        </div>
      </header>

      <div className="main-container">
        {/* Left Navigation Bar */}
        <nav className="left-nav">
          <div className="nav-items">
            <Link 
              to="/" 
              className={`nav-item ${isActive('/') ? 'active' : ''}`}
            >
              <span className="nav-icon">🔍</span>
              <span className="nav-text">Stock Screener</span>
            </Link>
            <Link 
              to="/profile" 
              className={`nav-item ${isActive('/profile') || location.pathname.startsWith('/profile/') || location.pathname.startsWith('/stock/') ? 'active' : ''}`}
            >
              <span className="nav-icon">📊</span>
              <span className="nav-text">Stock Profile</span>
            </Link>
            <Link 
              to="/portfolio" 
              className={`nav-item ${isActive('/portfolio') ? 'active' : ''}`}
            >
              <span className="nav-icon">💼</span>
              <span className="nav-text">Portfolio</span>
            </Link>
            <Link 
              to="/watchlist" 
              className={`nav-item ${isActive('/watchlist') ? 'active' : ''}`}
            >
              <span className="nav-icon">⭐</span>
              <span className="nav-text">Watch List</span>
            </Link>
          </div>
          <div className="nav-footer">
            <div className="nav-version">v1.0.0</div>
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="content-area">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
