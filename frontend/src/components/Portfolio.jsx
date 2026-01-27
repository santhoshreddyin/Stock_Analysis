import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import './Portfolio.css';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [stocks, setStocks] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    symbol: '',
    shares: '',
    purchase_price: '',
    purchase_date: new Date().toISOString().split('T')[0]
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get portfolio items
      const portfolioData = await stockAPI.getPortfolio();
      setPortfolio(portfolioData);

      // Fetch stock details for each portfolio item
      const stockDetails = {};
      for (const item of portfolioData) {
        try {
          const detail = await stockAPI.getStockDetail(item.symbol);
          stockDetails[item.symbol] = detail;
        } catch (err) {
          console.error(`Error fetching details for ${item.symbol}:`, err);
        }
      }
      setStocks(stockDetails);
    } catch (err) {
      setError('Failed to load portfolio');
      console.error('Error loading portfolio:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddClick = () => {
    setEditingItem(null);
    setFormData({
      symbol: '',
      shares: '',
      purchase_price: '',
      purchase_date: new Date().toISOString().split('T')[0]
    });
    setShowAddModal(true);
  };

  const handleEditClick = (item) => {
    setEditingItem(item);
    setFormData({
      symbol: item.symbol,
      shares: item.shares.toString(),
      purchase_price: item.purchase_price.toString(),
      purchase_date: item.purchase_date
    });
    setShowAddModal(true);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingItem) {
        // Update existing item
        await stockAPI.updatePortfolio(editingItem.id, {
          shares: parseFloat(formData.shares),
          purchase_price: parseFloat(formData.purchase_price),
          purchase_date: formData.purchase_date
        });
      } else {
        // Add new item
        await stockAPI.addToPortfolio({
          symbol: formData.symbol.toUpperCase(),
          shares: parseFloat(formData.shares),
          purchase_price: parseFloat(formData.purchase_price),
          purchase_date: formData.purchase_date
        });
      }
      
      setShowAddModal(false);
      await loadPortfolio();
    } catch (err) {
      alert(`Failed to ${editingItem ? 'update' : 'add'} portfolio item`);
      console.error('Error saving portfolio item:', err);
    }
  };

  const handleRemove = async (portfolioId) => {
    if (!window.confirm('Are you sure you want to remove this stock from your portfolio?')) {
      return;
    }
    
    try {
      await stockAPI.removeFromPortfolio(portfolioId);
      await loadPortfolio();
    } catch (err) {
      alert('Failed to remove stock from portfolio');
      console.error('Error removing from portfolio:', err);
    }
  };

  const handleStockClick = (symbol) => {
    navigate(`/stock/${symbol}`);
  };

  const calculateGainLoss = (item, currentPrice) => {
    if (!currentPrice) return null;
    const totalCost = item.shares * item.purchase_price;
    const currentValue = item.shares * currentPrice;
    const gainLoss = currentValue - totalCost;
    const gainLossPercent = (gainLoss / totalCost) * 100;
    return { gainLoss, gainLossPercent };
  };

  const calculateTotalValue = () => {
    let totalInvested = 0;
    let totalCurrent = 0;
    
    portfolio.forEach(item => {
      const stock = stocks[item.symbol];
      totalInvested += item.shares * item.purchase_price;
      if (stock?.current_price) {
        totalCurrent += item.shares * stock.current_price;
      }
    });
    
    const totalGainLoss = totalCurrent - totalInvested;
    const totalGainLossPercent = totalInvested > 0 ? (totalGainLoss / totalInvested) * 100 : 0;
    
    return { totalInvested, totalCurrent, totalGainLoss, totalGainLossPercent };
  };

  if (loading) {
    return (
      <div className="portfolio-container">
        <div className="loading">Loading portfolio...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portfolio-container">
        <div className="error">{error}</div>
      </div>
    );
  }

  const totals = calculateTotalValue();

  return (
    <div className="portfolio-container">
      <div className="portfolio-header">
        <div>
          <h1>My Portfolio</h1>
          <p className="portfolio-count">{portfolio.length} positions</p>
        </div>
        <button className="add-button" onClick={handleAddClick}>
          + Add Position
        </button>
      </div>

      {portfolio.length > 0 && (
        <div className="portfolio-summary">
          <div className="summary-card">
            <span className="summary-label">Total Invested</span>
            <span className="summary-value">${totals.totalInvested.toFixed(2)}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Current Value</span>
            <span className="summary-value">${totals.totalCurrent.toFixed(2)}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Total Gain/Loss</span>
            <span className={`summary-value ${totals.totalGainLoss >= 0 ? 'positive' : 'negative'}`}>
              ${totals.totalGainLoss.toFixed(2)} ({totals.totalGainLossPercent >= 0 ? '+' : ''}{totals.totalGainLossPercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      )}

      {portfolio.length === 0 ? (
        <div className="empty-state">
          <h3>Your portfolio is empty</h3>
          <p>Add your first stock position to start tracking your investments</p>
        </div>
      ) : (
        <div className="portfolio-table-container">
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Shares</th>
                <th>Purchase Price</th>
                <th>Current Price</th>
                <th>Total Cost</th>
                <th>Current Value</th>
                <th>Gain/Loss</th>
                <th>Purchase Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map((item) => {
                const stock = stocks[item.symbol];
                const gainLoss = calculateGainLoss(item, stock?.current_price);
                const totalCost = item.shares * item.purchase_price;
                const currentValue = stock?.current_price ? item.shares * stock.current_price : 0;

                return (
                  <tr key={item.id}>
                    <td>
                      <span 
                        className="clickable-symbol" 
                        onClick={() => handleStockClick(item.symbol)}
                      >
                        {item.symbol}
                      </span>
                    </td>
                    <td>{stock?.name || 'Loading...'}</td>
                    <td>{item.shares.toFixed(2)}</td>
                    <td>${item.purchase_price.toFixed(2)}</td>
                    <td>${stock?.current_price?.toFixed(2) || 'N/A'}</td>
                    <td>${totalCost.toFixed(2)}</td>
                    <td>${currentValue.toFixed(2)}</td>
                    <td>
                      {gainLoss ? (
                        <span className={gainLoss.gainLoss >= 0 ? 'gain' : 'loss'}>
                          ${gainLoss.gainLoss.toFixed(2)} ({gainLoss.gainLossPercent >= 0 ? '+' : ''}{gainLoss.gainLossPercent.toFixed(2)}%)
                        </span>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td>{new Date(item.purchase_date).toLocaleDateString()}</td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="edit-btn"
                          onClick={() => handleEditClick(item)}
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button 
                          className="delete-btn"
                          onClick={() => handleRemove(item.id)}
                          title="Remove"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingItem ? 'Edit Position' : 'Add Position'}</h2>
              <button className="close-btn" onClick={() => setShowAddModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="symbol">Stock Symbol</label>
                <input
                  type="text"
                  id="symbol"
                  name="symbol"
                  value={formData.symbol}
                  onChange={handleInputChange}
                  disabled={!!editingItem}
                  placeholder="e.g., AAPL"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="shares">Number of Shares</label>
                <input
                  type="number"
                  id="shares"
                  name="shares"
                  value={formData.shares}
                  onChange={handleInputChange}
                  step="0.01"
                  min="0.01"
                  placeholder="e.g., 10"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="purchase_price">Purchase Price</label>
                <input
                  type="number"
                  id="purchase_price"
                  name="purchase_price"
                  value={formData.purchase_price}
                  onChange={handleInputChange}
                  step="0.01"
                  min="0.01"
                  placeholder="e.g., 150.00"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="purchase_date">Purchase Date</label>
                <input
                  type="date"
                  id="purchase_date"
                  name="purchase_date"
                  value={formData.purchase_date}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="submit-btn">
                  {editingItem ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Portfolio;
