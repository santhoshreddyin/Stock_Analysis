import { useState } from 'react';
import Dashboard from './components/Dashboard';
import StockList from './components/StockList';
import StockDetail from './components/StockDetail';
import GraphView from './components/GraphView';
import NewsSummary from './components/NewsSummary';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import StockScreener from './components/StockScreener';
import StockProfile from './components/StockProfile';
import './App.css';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">📈 Stock Analysis Dashboard</h1>
        <nav className="app-nav">
          <button
            className={currentView === 'dashboard' ? 'active' : ''}
            onClick={handleBackToDashboard}
          >
            Dashboard
          </button>
          <button
            className={currentView === 'stocks' || currentView === 'detail' ? 'active' : ''}
            onClick={() => setCurrentView('stocks')}
          >
            Stock List
          </button>
          <button
            className={currentView === 'graph' ? 'active' : ''}
            onClick={() => setCurrentView('graph')}
          >
            Entity Graph
          </button>
          <button
            className={currentView === 'news' ? 'active' : ''}
            onClick={() => setCurrentView('news')}
          >
            News Analysis
          </button>
        </nav>
      </header>

      <main className="app-main">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'stocks' && <StockList onSelectStock={handleSelectStock} />}
        {currentView === 'detail' && selectedStock && (
          <StockDetail symbol={selectedStock} onBack={handleBackToList} />
        )}
        {currentView === 'graph' && <GraphView symbol={selectedStock} />}
        {currentView === 'news' && (
          <div>
            {!selectedStock ? (
              <div className="select-stock-prompt">
                <p>Select a stock from the Stock List to view news analysis</p>
                <button onClick={() => setCurrentView('stocks')}>Go to Stock List</button>
              </div>
            ) : (
              <NewsSummary symbol={selectedStock} />
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>© 2026 Stock Analysis System | Powered by FastAPI & React</p>
      </footer>
    </div>
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<StockScreener />} />
          <Route path="/profile" element={<StockProfile />} />
          <Route path="/profile/:symbol" element={<StockProfile />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
