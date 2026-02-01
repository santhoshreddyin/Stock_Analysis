/**
 * StockScreener Component
 * Screen and filter stocks with advanced options
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import './StockScreener.css';

const StockScreener = () => {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 1000 });
  const [filters, setFilters] = useState({
    sector: '',
    industry: '',
    frequency: '',
    recommendation: '',
    minPrice: 0,
    maxPrice: 1000,
    limit: 100,
  });

  const updatePriceRangeFromStocks = useCallback((stocksList) => {
    const prices = stocksList
      .map(s => s.current_price)
      .filter(p => p != null && p > 0);
    
    if (prices.length > 0) {
      const min = Math.floor(Math.min(...prices));
      const max = Math.ceil(Math.max(...prices));
      setPriceRange({ min, max });
    } else {
      setPriceRange({ min: 0, max: 1000 });
    }
  }, []);

  const fetchSectors = useCallback(async () => {
    try {
      const data = await stockAPI.getSectors();
      setSectors(data.sectors || []);
    } catch (err) {
      console.error('Error fetching sectors:', err);
    }
  }, []);

  const fetchIndustries = useCallback(async (sector = null) => {
    try {
      const data = await stockAPI.getIndustries(sector);
      setIndustries(data.industries || []);
    } catch (err) {
      console.error('Error fetching industries:', err);
    }
  }, []);

  const fetchStocks = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.sector) params.sector = filters.sector;
      if (filters.industry) params.industry = filters.industry;
      if (filters.frequency) params.frequency = filters.frequency;
      if (filters.recommendation) params.recommendation = filters.recommendation;
      if (filters.minPrice > priceRange.min) params.min_price = filters.minPrice;
      if (filters.maxPrice < priceRange.max) params.max_price = filters.maxPrice;
      params.limit = filters.limit;

      const data = await stockAPI.getStocks(params);
      setStocks(data);
      updatePriceRangeFromStocks(data);
      if (data.length === 0) {
        setError("No stocks found matching criteria");
      } else {
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching filtered stocks:', err);
      setError('Failed to fetch stocks');
    } finally {
      setLoading(false);
    }
  }, [filters, priceRange.min, priceRange.max, updatePriceRangeFromStocks]);

  useEffect(() => {
    fetchSectors();
    fetchIndustries();
    fetchStocks();
  }, [fetchSectors, fetchIndustries, fetchStocks]);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  useEffect(() => {
    // Only fetch when price filters change by user
    if (filters.minPrice >= priceRange.min && filters.maxPrice <= priceRange.max) {
      fetchStocks();
    }
  }, [filters.minPrice, filters.maxPrice, fetchStocks, priceRange.min, priceRange.max]);

  useEffect(() => {
    // Fetch industries when sector changes
    if (filters.sector) {
      fetchIndustries(filters.sector);
    } else {
      fetchIndustries();
    }
  }, [filters.sector, fetchIndustries]);
      updatePriceRangeFromStocks(data);
      
      setError(null);
    } catch (err) {
      setError('Failed to load stocks: ' + err.message);
      console.error('Error fetching stocks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters((prev) => {
      const newFilters = { ...prev, [field]: value };
      
      // Reset industry when sector changes
      if (field === 'sector') {
        newFilters.industry = '';
        newFilters.minPrice = priceRange.min;
        newFilters.maxPrice = priceRange.max;
      }
      
      // Reset price when changing industry, frequency, or recommendation
      if (field === 'industry' || field === 'frequency' || field === 'recommendation') {
        newFilters.minPrice = priceRange.min;
        newFilters.maxPrice = priceRange.max;
      }
      
      return newFilters;
    });
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
          <label htmlFor="industry-filter">Industry:</label>
          <select
            id="industry-filter"
            value={filters.industry}
            onChange={(e) => handleFilterChange('industry', e.target.value)}
            disabled={!filters.sector && industries.length === 0}
          >
            <option value="">{filters.sector ? 'All Industries' : 'Select Sector First'}</option>
            {industries.map((industry) => (
              <option key={industry} value={industry}>
                {industry}
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
          <label htmlFor="recommendation-filter">Recommendation:</label>
          <select
            id="recommendation-filter"
            value={filters.recommendation}
            onChange={(e) => handleFilterChange('recommendation', e.target.value)}
          >
            <option value="">All</option>
            <option value="Strong Buy">Strong Buy</option>
            <option value="Buy">Buy</option>
            <option value="Hold">Hold</option>
            <option value="Sell">Sell</option>
          </select>
        </div>

        <div className="filter-group price-range-group">
          <label>Price Range: ${filters.minPrice} - ${filters.maxPrice}</label>
          <div className="dual-range-slider">
            <input
              type="range"
              value={filters.minPrice}
              onChange={(e) => {
                const value = parseFloat(e.target.value);
                if (value <= filters.maxPrice) {
                  handleFilterChange('minPrice', value);
                }
              }}
              min={priceRange.min}
              max={priceRange.max}
              step="1"
              className="price-slider price-slider-min"
            />
            <input
              type="range"
              value={filters.maxPrice}
              onChange={(e) => {
                const value = parseFloat(e.target.value);
                if (value >= filters.minPrice) {
                  handleFilterChange('maxPrice', value);
                }
              }}
              min={priceRange.min}
              max={priceRange.max}
              step="1"
              className="price-slider price-slider-max"
            />
          </div>
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
              <div className="stock-symbol">{stock.name}</div>
              {stock.current_price && (
                <div className="stock-price">${stock.current_price.toFixed(2)}</div>
              )}
            </div>
            <div className="stock-name">{stock.symbol}</div>
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
