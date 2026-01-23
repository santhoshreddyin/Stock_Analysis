import { useState } from 'react';
import Dashboard from './components/Dashboard';
import StockList from './components/StockList';
import StockDetail from './components/StockDetail';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedStock, setSelectedStock] = useState(null);

  const handleSelectStock = (symbol) => {
    setSelectedStock(symbol);
    setCurrentView('detail');
  };

  const handleBackToList = () => {
    setCurrentView('stocks');
    setSelectedStock(null);
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
    setSelectedStock(null);
  };

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
        </nav>
      </header>

      <main className="app-main">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'stocks' && <StockList onSelectStock={handleSelectStock} />}
        {currentView === 'detail' && selectedStock && (
          <StockDetail symbol={selectedStock} onBack={handleBackToList} />
        )}
      </main>

      <footer className="app-footer">
        <p>© 2026 Stock Analysis System | Powered by FastAPI & React</p>
      </footer>
    </div>
  );
}

export default App;
