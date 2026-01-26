/**
 * StockScreener Component
 * Screen and filter stocks with advanced options
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import './StockScreener.css';

const StockScreener = () => {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    sector: '',
    frequency: '',
    limit: 100,
  });

  useEffect(() => {
    fetchSectors();
    fetchStocks();
  }, []);

  useEffect(() => {
    fetchStocks();
  }, [filters]);

  const fetchSectors = async () => {
    try {
      const data = await stockAPI.getSectors();
      setSectors(data.sectors || []);
    } catch (err) {
      console.error('Error fetching sectors:', err);
    }
  };

  const fetchStocks = async () => {
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
  };

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleStockClick = (symbol) => {
    navigate(`/profile/${symbol}`);
  };

  if (loading) {
    return (
      <div className="stock-screener">
        <div className="loading">Loading stocks...</div>
      </div>
    );
  }

  return (
    <div className="stock-screener">
      <div className="screener-header">
        <h2>Stock Screener</h2>
        <p className="screener-subtitle">Filter and analyze stocks based on your criteria</p>
      </div>

      <div className="filters-container">
        <div className="filter-group">
          <label htmlFor="sector-filter">Sector:</label>
          <select
            id="sector-filter"
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
          <label htmlFor="frequency-filter">Frequency:</label>
          <select
            id="frequency-filter"
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
          <label htmlFor="limit-filter">Results:</label>
          <select
            id="limit-filter"
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

      {error && <div className="error-message">{error}</div>}

      <div className="results-info">
        <span className="results-count">
          Showing {stocks.length} stock{stocks.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="stocks-grid">
        {stocks.map((stock) => (
          <div
            key={stock.symbol}
            className="stock-card"
            onClick={() => handleStockClick(stock.symbol)}
          >
            <div className="stock-card-header">
              <div className="stock-symbol">{stock.symbol}</div>
              {stock.current_price && (
                <div className="stock-price">${stock.current_price.toFixed(2)}</div>
              )}
            </div>
            <div className="stock-name">{stock.name}</div>
            <div className="stock-meta">
              {stock.sector && <span className="meta-tag sector-tag">{stock.sector}</span>}
              {stock.industry && <span className="meta-tag industry-tag">{stock.industry}</span>}
            </div>
          </div>
        ))}
      </div>

      {stocks.length === 0 && !loading && (
        <div className="no-results">
          <p>No stocks found matching your criteria</p>
        </div>
      )}
    </div>
  );
};

export default StockScreener;
