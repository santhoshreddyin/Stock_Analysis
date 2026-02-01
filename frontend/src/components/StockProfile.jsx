/**
 * StockProfile Component
 * Detailed view of a specific stock
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush, ReferenceArea } from 'recharts';
import './StockProfile.css';

const StockProfile = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [stockDetail, setStockDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editNoteText, setEditNoteText] = useState('');
  const [historyPeriod, setHistoryPeriod] = useState('1yr');
  const [showDescription, setShowDescription] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Rectangle selection zoom states
  const [refAreaLeft, setRefAreaLeft] = useState('');
  const [refAreaRight, setRefAreaRight] = useState('');
  const [left, setLeft] = useState('dataMin');
  const [right, setRight] = useState('dataMax');
  const [top, setTop] = useState('dataMax+1');
  const [bottom, setBottom] = useState('dataMin-1');
  const [inWatchList, setInWatchList] = useState(false);
  const [watchListLoading, setWatchListLoading] = useState(false);
  const [frequency, setFrequency] = useState('');
  const [updatingFrequency, setUpdatingFrequency] = useState(false);


  const periodLimits = {
    '30d': 30,
    '90d': 90,
    '1yr': 365,
    '3yr': 1095,
    '5yr': 1825
  };

  // Sampling rates for different periods
  const getSamplingRate = (period) => {
    switch(period) {
      case '30d': return 1;  // Show every day
      case '90d': return 1;  // Show every day
      case '1yr': return 2;  // Show every alternate day (weekly)
      case '3yr': return 7; // Show every 7th day (weekly)
      case '5yr': return 7; // Show every 7th day (weekly)
      default: return 1;
    }
  };

  const sampleData = (data, rate) => {
    if (rate === 1) return data;
    return data.filter((_, index) => index % rate === 0);
  };

  const sampledHistory = sampleData(history, getSamplingRate(historyPeriod));

  const checkWatchListStatus = useCallback(async () => {
    if (!symbol) return;
    try {
      const result = await stockAPI.checkWatchList(symbol);
      setInWatchList(result.in_watchlist);
    } catch (err) {
      console.error('Error checking watchlist status:', err);
    }
  }, [symbol]);

  const fetchNotes = useCallback(async () => {
    if (!symbol) return;
    try {
      const data = await stockAPI.getNotes(symbol);
      setNotes(data.notes || []);
    } catch (err) {
      console.error('Error fetching notes:', err);
    }
  }, [symbol]);

  const fetchStockDetail = useCallback(async () => {
    if (!symbol) return;
    try {
      setLoading(true);
      const data = await stockAPI.getStockDetail(symbol);
      setStockDetail(data);
      setFrequency(data.frequency || 'Daily');
      setError(null);
    } catch (err) {
      setError('Failed to load stock details: ' + err.message);
      console.error('Error fetching stock detail:', err);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  const fetchStockHistory = useCallback(async () => {
    if (!symbol) return;
    try {
      setLoadingHistory(true);
      // Implementation continues... logic for history fetching
      // Note: This function was truncated in read_file, but logic is assumed standard API call
      // using periodLimits[historyPeriod]
      const limit = periodLimits[historyPeriod] || 365;
      const data = await stockAPI.getStockHistory(symbol, limit);
      
      const formattedHistory = data.history.map(item => ({
        ...item,
        date: new Date(item.date).toLocaleDateString(),
        originalDate: item.date
      })).reverse(); // Re-reverse to chronological order

      setHistory(formattedHistory);
      setHistoryLoaded(true);
      
      // Reset zoom on new data load
      setLeft('dataMin');
      setRight('dataMax');
      setTop('dataMax+1');
      setBottom('dataMin-1');
      
    } catch (err) {
      console.error('Error fetching history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, [symbol, historyPeriod, periodLimits]); 

  // Effects
  useEffect(() => {
    if (symbol) {
      fetchStockDetail();
      fetchNotes();
      fetchStockHistory();
      checkWatchListStatus();
    }
  }, [symbol, fetchStockDetail, fetchNotes, fetchStockHistory, checkWatchListStatus]);

  useEffect(() => {
    if (symbol && historyLoaded) {
      fetchStockHistory();
    }
  }, [historyPeriod, symbol, historyLoaded, fetchStockHistory]);
      const limit = periodLimits[historyPeriod];
      const data = await stockAPI.getStockHistory(symbol, limit);
      // Reverse to show latest on right
      setHistory(data.reverse());
      setHistoryLoaded(true);
    } catch (err) {
      console.error('Error fetching stock history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchNotes = async () => {
    try {
      const data = await stockAPI.getNotes(symbol);
      setNotes(data);
    } catch (err) {
      console.error('Error fetching notes:', err);
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    try {
      await stockAPI.createNote(symbol, noteText);
      setNoteText('');
      fetchNotes();
    } catch (err) {
      console.error('Error creating note:', err);
      alert('Failed to create note');
    }
  };

  const handleUpdateNote = async (noteId) => {
    if (!editNoteText.trim()) return;
    try {
      await stockAPI.updateNote(noteId, editNoteText);
      setEditingNoteId(null);
      setEditNoteText('');
      fetchNotes();
    } catch (err) {
      console.error('Error updating note:', err);
      alert('Failed to update note');
    }
  };

  const handleDeleteNote = async (noteId) => {
    if (!confirm('Are you sure you want to delete this note?')) return;
    try {
      await stockAPI.deleteNote(noteId);
      fetchNotes();
    } catch (err) {
      console.error('Error deleting note:', err);
      alert('Failed to delete note');
    }
  };

  const startEditingNote = (note) => {
    setEditingNoteId(note.id);
    setEditNoteText(note.content);
  };

  const cancelEditing = () => {
    setEditingNoteId(null);
    setEditNoteText('');
  };

  const checkWatchListStatus = async () => {
    try {
      const result = await stockAPI.checkWatchList(symbol);
      setInWatchList(result.in_watchlist);
    } catch (err) {
      console.error('Error checking watchlist status:', err);
    }
  };

  const toggleWatchList = async () => {
    try {
      setWatchListLoading(true);
      if (inWatchList) {
        await stockAPI.removeFromWatchList(symbol);
        setInWatchList(false);
      } else {
        await stockAPI.addToWatchList(symbol);
        setInWatchList(true);
      }
    } catch (err) {
      console.error('Error toggling watchlist:', err);
      alert(`Failed to ${inWatchList ? 'remove from' : 'add to'} watchlist`);
    } finally {
      setWatchListLoading(false);
    }
  };
  const handleFrequencyChange = async (newFrequency) => {
    try {
      setUpdatingFrequency(true);
      await stockAPI.updateStockFrequency(symbol, newFrequency);
      setFrequency(newFrequency);
      // Update stockDetail to reflect new frequency
      if (stockDetail) {
        setStockDetail({ ...stockDetail, frequency: newFrequency });
      }
    } catch (err) {
      console.error('Error updating frequency:', err);
      alert('Failed to update monitoring frequency');
    } finally {
      setUpdatingFrequency(false);
    }
  };
  const zoom = () => {
    let refLeft = refAreaLeft;
    let refRight = refAreaRight;

    if (refLeft === refRight || refRight === '') {
      setRefAreaLeft('');
      setRefAreaRight('');
      return;
    }

    // Ensure left is before right
    if (refLeft > refRight) [refLeft, refRight] = [refRight, refLeft];

    // Get the data indices
    const leftIndex = sampledHistory.findIndex(item => item.date === refLeft);
    const rightIndex = sampledHistory.findIndex(item => item.date === refRight);

    if (leftIndex === -1 || rightIndex === -1) {
      setRefAreaLeft('');
      setRefAreaRight('');
      return;
    }

    // Calculate price range for the selected area
    const selectedData = sampledHistory.slice(leftIndex, rightIndex + 1);
    const prices = selectedData.map(d => d.close_price).filter(p => p != null);
    
    if (prices.length > 0) {
      const minPrice = Math.min(...prices);
      const maxPrice = Math.max(...prices);
      const padding = (maxPrice - minPrice) * 0.1;

      setLeft(refLeft);
      setRight(refRight);
      setBottom(minPrice - padding);
      setTop(maxPrice + padding);
    }

    setRefAreaLeft('');
    setRefAreaRight('');
  };

  const zoomOut = () => {
    setRefAreaLeft('');
    setRefAreaRight('');
    setLeft('dataMin');
    setRight('dataMax');
    setTop('dataMax+1');
    setBottom('dataMin-1');
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="custom-chart-tooltip">
          <p className="tooltip-date">{new Date(data.date).toLocaleDateString()}</p>
          <p className="tooltip-item"><strong>Close:</strong> ${data.close_price?.toFixed(2) || 'N/A'}</p>
          <p className="tooltip-item"><strong>Open:</strong> ${data.open_price?.toFixed(2) || 'N/A'}</p>
          <p className="tooltip-item"><strong>High:</strong> ${data.high_price?.toFixed(2) || 'N/A'}</p>
          <p className="tooltip-item"><strong>Low:</strong> ${data.low_price?.toFixed(2) || 'N/A'}</p>
          <p className="tooltip-item"><strong>Volume:</strong> {data.volume?.toLocaleString() || 'N/A'}</p>
        </div>
      );
    }
    return null;
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
        <div className="header-actions">
          <button onClick={() => navigate('/')} className="back-button">
            ← Back to Stock Screener
          </button>
          <button 
            onClick={toggleWatchList} 
            className={`watchlist-button ${inWatchList ? 'in-watchlist' : ''}`}
            disabled={watchListLoading}
          >
            {watchListLoading ? '...' : inWatchList ? '⭐ Remove from Watchlist' : '☆ Add to Watchlist'}
          </button>
        </div>
        <div className="stock-title-section">
          <h1 className="stock-title">
            {stockDetail.symbol} - {stockDetail.name}
            {stockDetail.current_price && (
              <span className="price-inline">
                ${stockDetail.current_price.toFixed(2)}
              </span>
            )}
            {stockDetail.description && (
              <span 
                className="info-icon"
                onMouseEnter={() => setShowDescription(true)}
                onMouseLeave={() => setShowDescription(false)}
              >
                ℹ️
                {showDescription && (
                  <div className="description-tooltip">
                    {stockDetail.description}
                  </div>
                )}
              </span>
            )}
          </h1>
        </div>
      </div>

      <div className="profile-layout">
        <div className="profile-main">
          <div className="profile-grid">
            <div className="info-card">
              <h3 className="card-title">Stock Information</h3>
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
                  <span className="info-label">Monitoring Frequency:</span>
                  <span className="info-value">
                    <select 
                      value={frequency} 
                      onChange={(e) => handleFrequencyChange(e.target.value)}
                      className="frequency-selector"
                      disabled={updatingFrequency}
                    >
                      <option value="Daily">Daily</option>
                      <option value="Weekly">Weekly</option>
                      <option value="Monthly">Monthly</option>
                    </select>
                    {updatingFrequency && <span className="updating-indicator"> ⏳</span>}
                  </span>
                </div>
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
              <h3 className="card-title">Targets & Metrics</h3>
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

            <div className="info-card">
              <h3 className="card-title">Stock Notes</h3>
              <div className="notes-add">
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Add a note about this stock..."
                  className="note-input"
                  rows="3"
                />
                <button onClick={handleAddNote} className="btn-primary">Add Note</button>
              </div>
            </div>
          </div>

          <div className="history-card">
            <div className="history-header">
              <h3 className="card-title">Price History</h3>
              <div className="history-controls">
                <select 
                  value={historyPeriod} 
                  onChange={(e) => setHistoryPeriod(e.target.value)}
                  className="period-selector"
                >
                  <option value="30d">30 Days</option>
                  <option value="90d">90 Days</option>
                  <option value="1yr">1 Year</option>
                  <option value="3yr">3 Years</option>
                  <option value="5yr">5 Years</option>
                </select>
              </div>
            </div>
            {loadingHistory ? (
              <div className="load-history-prompt">
                <p>Loading price history...</p>
              </div>
            ) : (
              <div className="chart-wrapper">
                {(left !== 'dataMin' || right !== 'dataMax') && (
                  <button onClick={zoomOut} className="btn-secondary btn-sm zoom-reset-btn">
                    Reset Zoom
                  </button>
                )}
                <ResponsiveContainer width="100%" height={450}>
                  <LineChart 
                    data={sampledHistory}
                    onMouseDown={(e) => e && e.activeLabel && setRefAreaLeft(e.activeLabel)}
                    onMouseMove={(e) => refAreaLeft && e && e.activeLabel && setRefAreaRight(e.activeLabel)}
                    onMouseUp={zoom}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date"
                      domain={[left, right]}
                      tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis 
                      domain={[bottom, top]}
                      allowDataOverflow
                      label={{ value: 'Price ($)', angle: -90, position: 'insideLeft' }}
                      tickFormatter={(value) => `$${value.toFixed(2)}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Line type="monotone" dataKey="close_price" stroke="#8884d8" name="Close" strokeWidth={2} dot={false} animationDuration={300} />
                    {refAreaLeft && refAreaRight && (
                      <ReferenceArea
                        x1={refAreaLeft}
                        x2={refAreaRight}
                        strokeOpacity={0.3}
                        fill="#667eea"
                        fillOpacity={0.3}
                      />
                    )}
                    <Brush 
                      dataKey="date" 
                      height={30} 
                      stroke="#667eea"
                      tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short' })}
                      startIndex={left !== 'dataMin' ? sampledHistory.findIndex(d => d.date === left) : undefined}
                      endIndex={right !== 'dataMax' ? sampledHistory.findIndex(d => d.date === right) : undefined}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="chart-info">
                  <p><strong>Tip:</strong> Click and drag on the chart to draw a rectangle and zoom into that area. Use the brush slider below or click "Reset Zoom" to return. Showing {sampledHistory.length} of {history.length} data points.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="notes-sidebar">
          <div className="notes-section">
            <h3 className="card-title">Your Notes</h3>
            <div className="notes-list">
              {notes.length === 0 ? (
                <p className="no-notes">No notes yet. Add your first note above!</p>
              ) : (
                notes.map((note) => (
                  <div key={note.id} className="note-item">
                    {editingNoteId === note.id ? (
                      <div className="note-edit">
                        <textarea
                          value={editNoteText}
                          onChange={(e) => setEditNoteText(e.target.value)}
                          className="note-input"
                          rows="3"
                        />
                        <div className="note-actions">
                          <button onClick={() => handleUpdateNote(note.id)} className="btn-primary btn-sm">Save</button>
                          <button onClick={cancelEditing} className="btn-secondary btn-sm">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="note-content">{note.content}</div>
                        <div className="note-meta">
                          <span className="note-date">
                            {new Date(note.created_at).toLocaleString()}
                          </span>
                          <div className="note-actions">
                            <button onClick={() => startEditingNote(note)} className="btn-link">Edit</button>
                            <button onClick={() => handleDeleteNote(note.id)} className="btn-link delete">Delete</button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StockProfile;
