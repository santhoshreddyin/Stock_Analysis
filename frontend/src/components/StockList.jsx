/**
 * StockList Component
 * Displays a list of stocks with filtering options
 */

import React, { useEffect, useState, useCallback } from 'react';
import { stockAPI } from '../services/api';
import './StockList.css';

const StockList = ({ onSelectStock }) => {
  const [stocks, setStocks] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    sector: '',
    frequency: '',
    limit: 100,
  });

  const fetchSectors = useCallback(async () => {
    try {
      const data = await stockAPI.getSectors();
      setSectors(data.sectors || []);
    } catch (err) {
      console.error('Error fetching sectors:', err);
    }
  }, []);

  const fetchStocks = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.sector) params.sector = filters.sector;
      if (filters.frequency) params.frequency = filters.frequency;
      params.limit = filters.limit;

      const data = await stockAPI.getStocks(params);
      setStocks(data);
      setError(null);
    } catch (err) {
      setError('Failed to load stocks: ' + err.message);
      console.error('Error fetching stocks:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchSectors();
    fetchStocks();
  }, [fetchSectors, fetchStocks]);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  if (loading) {
    return <div className="loading">Loading stocks...</div>;
  }

  return (
    <div className="stock-list-container">
      <h2>Stock List</h2>

      <div className="filters">
        <div className="filter-group">
          <label>Sector:</label>
          <select
            value={filters.sector}
            onChange={(e) => handleFilterChange('sector', e.target.value)}
          >
            <option value="">All Sectors</option>
            {sectors.map((sector) => (
              <option key={sector} value={sector}>
                {sector}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Frequency:</label>
          <select
            value={filters.frequency}
            onChange={(e) => handleFilterChange('frequency', e.target.value)}
          >
            <option value="">All</option>
            <option value="Daily">Daily</option>
            <option value="Weekly">Weekly</option>
            <option value="Monthly">Monthly</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Limit:</label>
          <select
            value={filters.limit}
            onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
          >
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
            <option value="500">500</option>
          </select>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="stocks-count">
        Showing {stocks.length} stock{stocks.length !== 1 ? 's' : ''}
      </div>

      <div className="stock-list">
        {stocks.map((stock) => (
          <div
            key={stock.symbol}
            className="stock-item"
            onClick={() => onSelectStock(stock.symbol)}
          >
            <div className="stock-symbol">{stock.symbol}</div>
            <div className="stock-name">{stock.name}</div>
            <div className="stock-meta">
              {stock.sector && <span className="sector">{stock.sector}</span>}
              {stock.industry && <span className="industry">{stock.industry}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StockList;
