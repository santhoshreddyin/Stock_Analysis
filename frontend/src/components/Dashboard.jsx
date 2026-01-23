/**
 * Dashboard Component
 * Displays key parameters and statistics
 */

import React, { useEffect, useState } from 'react';
import { stockAPI } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [keyParams, setKeyParams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchKeyParameters();
  }, []);

  const fetchKeyParameters = async () => {
    try {
      setLoading(true);
      const data = await stockAPI.getKeyParameters();
      setKeyParams(data);
      setError(null);
    } catch (err) {
      setError('Failed to load key parameters: ' + err.message);
      console.error('Error fetching key parameters:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!keyParams) {
    return <div className="error">No data available</div>;
  }

  return (
    <div className="dashboard">
      <h1>Stock Analysis Dashboard</h1>
      <p className="last-updated">
        Last Updated: {new Date(keyParams.last_updated).toLocaleString()}
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Stocks</h3>
          <p className="stat-value">{keyParams.total_stocks.toLocaleString()}</p>
        </div>

        <div className="stat-card">
          <h3>Stocks with Prices</h3>
          <p className="stat-value">{keyParams.stocks_with_prices.toLocaleString()}</p>
        </div>

        <div className="stat-card">
          <h3>Total Sectors</h3>
          <p className="stat-value">{keyParams.total_sectors}</p>
        </div>
      </div>

      <div className="recommendations-section">
        <h2>Recommendations Summary</h2>
        <div className="recommendations-grid">
          <div className="recommendation-card buy">
            <h3>Buy</h3>
            <p className="rec-value">{keyParams.buy_recommendations}</p>
          </div>

          <div className="recommendation-card hold">
            <h3>Hold</h3>
            <p className="rec-value">{keyParams.hold_recommendations}</p>
          </div>

          <div className="recommendation-card sell">
            <h3>Sell</h3>
            <p className="rec-value">{keyParams.sell_recommendations}</p>
          </div>
        </div>
      </div>

      <div className="top-stocks-section">
        <h2>Top 5 Stocks by Price</h2>
        <div className="top-stocks-list">
          {keyParams.top_stocks_by_price.map((stock, index) => (
            <div key={stock.symbol} className="top-stock-item">
              <span className="rank">#{index + 1}</span>
              <span className="symbol">{stock.symbol}</span>
              <span className="price">${stock.current_price.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
