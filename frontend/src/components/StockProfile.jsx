/**
 * StockProfile Component
 * Detailed view of a specific stock
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import './StockProfile.css';

const StockProfile = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [stockDetail, setStockDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (symbol) {
      fetchStockDetail();
      fetchStockHistory();
    }
  }, [symbol]);

  const fetchStockDetail = async () => {
    try {
      setLoading(true);
      const data = await stockAPI.getStockDetail(symbol);
      setStockDetail(data);
      setError(null);
    } catch (err) {
      setError('Failed to load stock details: ' + err.message);
      console.error('Error fetching stock detail:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStockHistory = async () => {
    try {
      const data = await stockAPI.getStockHistory(symbol, 30);
      setHistory(data);
    } catch (err) {
      console.error('Error fetching stock history:', err);
    }
  };

  if (!symbol) {
    return (
      <div className="stock-profile">
        <div className="no-stock-selected">
          <h2>No Stock Selected</h2>
          <p>Please select a stock from the Stock Screener to view its profile.</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            Go to Stock Screener
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="stock-profile">
        <div className="loading">Loading stock profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stock-profile">
        <div className="error-container">
          <div className="error-message">{error}</div>
          <button onClick={() => navigate('/')} className="btn-secondary">
            ← Back to Stock Screener
          </button>
        </div>
      </div>
    );
  }

  if (!stockDetail) {
    return (
      <div className="stock-profile">
        <div className="error-message">No stock data available</div>
      </div>
    );
  }

  return (
    <div className="stock-profile">
      <div className="profile-header">
        <button onClick={() => navigate('/')} className="back-button">
          ← Back to Stock Screener
        </button>
        <div className="stock-title-section">
          <h1 className="stock-title">
            {stockDetail.symbol} - {stockDetail.name}
          </h1>
          {stockDetail.current_price && (
            <div className="current-price-display">
              ${stockDetail.current_price.toFixed(2)}
            </div>
          )}
        </div>
      </div>

      <div className="profile-grid">
        <div className="info-card">
          <h3 className="card-title">Basic Information</h3>
          <div className="info-items">
            <div className="info-item">
              <span className="info-label">Sector:</span>
              <span className="info-value">{stockDetail.sector || 'N/A'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Industry:</span>
              <span className="info-value">{stockDetail.industry || 'N/A'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Frequency:</span>
              <span className="info-value">{stockDetail.frequency || 'N/A'}</span>
            </div>
          </div>
        </div>

        <div className="info-card">
          <h3 className="card-title">Price Information</h3>
          <div className="info-items">
            <div className="info-item">
              <span className="info-label">Current Price:</span>
              <span className="info-value price-value">
                {stockDetail.current_price ? `$${stockDetail.current_price.toFixed(2)}` : 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">52-Week High:</span>
              <span className="info-value">
                {stockDetail.week52_high ? `$${stockDetail.week52_high.toFixed(2)}` : 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">52-Week Low:</span>
              <span className="info-value">
                {stockDetail.week52_low ? `$${stockDetail.week52_low.toFixed(2)}` : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="info-card">
          <h3 className="card-title">Target Prices</h3>
          <div className="info-items">
            <div className="info-item">
              <span className="info-label">Target High:</span>
              <span className="info-value">
                {stockDetail.target_high ? `$${stockDetail.target_high.toFixed(2)}` : 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Target Low:</span>
              <span className="info-value">
                {stockDetail.target_low ? `$${stockDetail.target_low.toFixed(2)}` : 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Recommendation:</span>
              <span className={`info-value recommendation ${stockDetail.recommendation?.replace(/\s+/g, '-').toLowerCase()}`}>
                {stockDetail.recommendation || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="info-card">
          <h3 className="card-title">Volume & Metadata</h3>
          <div className="info-items">
            <div className="info-item">
              <span className="info-label">Avg Volume:</span>
              <span className="info-value">
                {stockDetail.average_volume ? stockDetail.average_volume.toLocaleString() : 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Updated:</span>
              <span className="info-value">
                {stockDetail.last_updated
                  ? new Date(stockDetail.last_updated).toLocaleString()
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {stockDetail.description && (
        <div className="description-card">
          <h3 className="card-title">Description</h3>
          <p className="description-text">{stockDetail.description}</p>
        </div>
      )}

      {history.length > 0 && (
        <div className="history-card">
          <h3 className="card-title">Recent Price History (Last 30 Days)</h3>
          <div className="table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Open</th>
                  <th>Close</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 10).map((record, index) => (
                  <tr key={index}>
                    <td>{new Date(record.date).toLocaleDateString()}</td>
                    <td>{record.open_price ? `$${record.open_price.toFixed(2)}` : 'N/A'}</td>
                    <td>{record.close_price ? `$${record.close_price.toFixed(2)}` : 'N/A'}</td>
                    <td>{record.high_price ? `$${record.high_price.toFixed(2)}` : 'N/A'}</td>
                    <td>{record.low_price ? `$${record.low_price.toFixed(2)}` : 'N/A'}</td>
                    <td>{record.volume ? record.volume.toLocaleString() : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockProfile;
