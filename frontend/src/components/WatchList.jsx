import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import './WatchList.css';

const WatchList = () => {
  const [watchList, setWatchList] = useState([]);
  const [stocks, setStocks] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadWatchList();
  }, []);

  const loadWatchList = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get watchlist items
      const watchListData = await stockAPI.getWatchList();
      setWatchList(watchListData);

      // Fetch stock details for each watchlist item
      const stockDetails = {};
      for (const item of watchListData) {
        try {
          const detail = await stockAPI.getStockDetail(item.symbol);
          stockDetails[item.symbol] = detail;
        } catch (err) {
          console.error(`Error fetching details for ${item.symbol}:`, err);
        }
      }
      setStocks(stockDetails);
    } catch (err) {
      setError('Failed to load watchlist');
      console.error('Error loading watchlist:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (symbol) => {
    try {
      await stockAPI.removeFromWatchList(symbol);
      // Reload the watchlist
      await loadWatchList();
    } catch (err) {
      alert(`Failed to remove ${symbol} from watchlist`);
      console.error('Error removing from watchlist:', err);
    }
  };

  const handleStockClick = (symbol) => {
    navigate(`/stock/${symbol}`);
  };

  if (loading) {
    return (
      <div className="watchlist-container">
        <div className="loading">Loading watchlist...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="watchlist-container">
        <div className="error">{error}</div>
      </div>
    );
  }

  return (
    <div className="watchlist-container">
      <div className="watchlist-header">
        <h1>My Watchlist</h1>
        <p className="watchlist-count">{watchList.length} stocks</p>
      </div>

      {watchList.length === 0 ? (
        <div className="empty-state">
          <h3>Your watchlist is empty</h3>
          <p>Add stocks from the Stock Profile page to track them here</p>
        </div>
      ) : (
        <div className="watchlist-grid">
          {watchList.map((item) => {
            const stock = stocks[item.symbol];
            return (
              <div key={item.id} className="watchlist-card">
                <div className="card-header">
                  <div className="stock-info" onClick={() => handleStockClick(item.symbol)}>
                    <h3 className="stock-symbol">{item.symbol}</h3>
                    {stock && <p className="stock-name">{stock.name}</p>}
                  </div>
                  <button 
                    className="remove-button"
                    onClick={() => handleRemove(item.symbol)}
                    title="Remove from watchlist"
                  >
                    ✕
                  </button>
                </div>
                
                {stock && (
                  <div className="card-body">
                    <div className="price-info">
                      <span className="current-price">${stock.current_price?.toFixed(2) || 'N/A'}</span>
                      {stock.price_change_percent !== null && (
                        <span className={`price-change ${stock.price_change_percent >= 0 ? 'positive' : 'negative'}`}>
                          {stock.price_change_percent >= 0 ? '+' : ''}
                          {stock.price_change_percent?.toFixed(2)}%
                        </span>
                      )}
                    </div>
                    
                    <div className="stock-details">
                      {stock.sector && <p className="detail-item"><strong>Sector:</strong> {stock.sector}</p>}
                      {stock.industry && <p className="detail-item"><strong>Industry:</strong> {stock.industry}</p>}
                      {stock.recommendation && (
                        <p className="detail-item">
                          <strong>Recommendation:</strong> 
                          <span className={`recommendation ${stock.recommendation.toLowerCase()}`}>
                            {stock.recommendation}
                          </span>
                        </p>
                      )}
                    </div>
                    
                    <div className="added-date">
                      Added {new Date(item.added_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default WatchList;
