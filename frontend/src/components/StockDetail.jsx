/**
 * StockDetail Component
 * Displays detailed information for a selected stock
 */

import React, { useEffect, useState, useCallback } from 'react';
import { stockAPI } from '../services/api';
import './StockDetail.css';

const StockDetail = ({ symbol, onBack }) => {
  const [stockDetail, setStockDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStockDetail = useCallback(async () => {
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
  }, [symbol]);

  const fetchStockHistory = useCallback(async () => {
    try {
      const data = await stockAPI.getStockHistory(symbol, 30);
      setHistory(data);
    } catch (err) {
      console.error('Error fetching stock history:', err);
    }
  }, [symbol]);

  useEffect(() => {
    if (symbol) {
      fetchStockDetail();
      fetchStockHistory();
    }
  }, [symbol, fetchStockDetail, fetchStockHistory]);

  if (loading) {
    return <div className="loading">Loading stock details...</div>;
  }

  if (error) {
    return (
      <div className="stock-detail-container">
        <button onClick={onBack} className="back-button">
          ← Back to List
        </button>
        <div className="error">{error}</div>
      </div>
    );
  }

  if (!stockDetail) {
    return <div className="error">No stock data available</div>;
  }

  return (
    <div className="stock-detail-container">
      <button onClick={onBack} className="back-button">
        ← Back to List
      </button>

      <div className="stock-header">
        <h1>
          {stockDetail.symbol} - {stockDetail.name}
        </h1>
        {stockDetail.current_price && (
          <div className="current-price">${stockDetail.current_price.toFixed(2)}</div>
        )}
      </div>

      <div className="stock-info-grid">
        <div className="info-card">
          <h3>Basic Information</h3>
          <div className="info-item">
            <span className="label">Sector:</span>
            <span className="value">{stockDetail.sector || 'N/A'}</span>
          </div>
          <div className="info-item">
            <span className="label">Industry:</span>
            <span className="value">{stockDetail.industry || 'N/A'}</span>
          </div>
          <div className="info-item">
            <span className="label">Frequency:</span>
            <span className="value">{stockDetail.frequency || 'N/A'}</span>
          </div>
        </div>

        <div className="info-card">
          <h3>Price Information</h3>
          <div className="info-item">
            <span className="label">Current Price:</span>
            <span className="value">
              {stockDetail.current_price ? `$${stockDetail.current_price.toFixed(2)}` : 'N/A'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">52-Week High:</span>
            <span className="value">
              {stockDetail.week52_high ? `$${stockDetail.week52_high.toFixed(2)}` : 'N/A'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">52-Week Low:</span>
            <span className="value">
              {stockDetail.week52_low ? `$${stockDetail.week52_low.toFixed(2)}` : 'N/A'}
            </span>
          </div>
        </div>

        <div className="info-card">
          <h3>Target Prices</h3>
          <div className="info-item">
            <span className="label">Target High:</span>
            <span className="value">
              {stockDetail.target_high ? `$${stockDetail.target_high.toFixed(2)}` : 'N/A'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">Target Low:</span>
            <span className="value">
              {stockDetail.target_low ? `$${stockDetail.target_low.toFixed(2)}` : 'N/A'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">Recommendation:</span>
            <span className={`value recommendation ${stockDetail.recommendation?.replace(/\s+/g, '-').toLowerCase()}`}>
              {stockDetail.recommendation || 'N/A'}
            </span>
          </div>
        </div>

        <div className="info-card">
          <h3>Volume & Metadata</h3>
          <div className="info-item">
            <span className="label">Avg Volume:</span>
            <span className="value">
              {stockDetail.average_volume ? stockDetail.average_volume.toLocaleString() : 'N/A'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">Last Updated:</span>
            <span className="value">
              {stockDetail.last_updated
                ? new Date(stockDetail.last_updated).toLocaleString()
                : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {stockDetail.description && (
        <div className="description-section">
          <h3>Description</h3>
          <p>{stockDetail.description}</p>
        </div>
      )}

      {history.length > 0 && (
        <div className="history-section">
          <h3>Recent Price History (Last 30 Days)</h3>
          <div className="history-table-wrapper">
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

export default StockDetail;
