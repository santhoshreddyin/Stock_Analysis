/**
 * News Summary Component
 * Displays news articles and summaries for a stock
 */

import React, { useEffect, useState } from 'react';
import { stockAPI } from '../services/api';
import './NewsSummary.css';

const NewsSummary = ({ symbol }) => {
  const [articles, setArticles] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('articles');

  useEffect(() => {
    if (symbol) {
      fetchNewsData();
    }
  }, [symbol]);

  const fetchNewsData = async () => {
    try {
      setLoading(true);
      
      // Fetch both articles and summaries
      const [articlesData, summariesData] = await Promise.all([
        stockAPI.getNewsArticles(symbol),
        stockAPI.getNewsSummaries(symbol)
      ]);
      
      setArticles(articlesData);
      setSummaries(summariesData);
      setError(null);
    } catch (err) {
      setError('Failed to load news data: ' + err.message);
      console.error('Error fetching news data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (score) => {
    if (!score) return '#6b7280';
    if (score > 0.3) return '#10b981';
    if (score < -0.3) return '#ef4444';
    return '#f59e0b';
  };

  const getSentimentLabel = (score) => {
    if (!score) return 'Neutral';
    if (score > 0.3) return 'Positive';
    if (score < -0.3) return 'Negative';
    return 'Neutral';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (loading) {
    return <div className="news-loading">Loading news data...</div>;
  }

  if (error) {
    return <div className="news-error">{error}</div>;
  }

  return (
    <div className="news-summary">
      <div className="news-header">
        <h2>News Analysis for {symbol}</h2>
        <button onClick={fetchNewsData} className="refresh-button">
          Refresh
        </button>
      </div>

      <div className="news-tabs">
        <button
          className={`tab-button ${activeTab === 'articles' ? 'active' : ''}`}
          onClick={() => setActiveTab('articles')}
        >
          Articles ({articles.length})
        </button>
        <button
          className={`tab-button ${activeTab === 'summaries' ? 'active' : ''}`}
          onClick={() => setActiveTab('summaries')}
        >
          Summaries ({summaries.length})
        </button>
      </div>

      {activeTab === 'articles' && (
        <div className="articles-list">
          {articles.length === 0 ? (
            <div className="empty-state">
              <p>No news articles available</p>
              <p className="hint">The News Analyst will collect articles here</p>
            </div>
          ) : (
            articles.map(article => (
              <div key={article.id} className="article-card">
                <div className="article-header">
                  <h3>{article.title}</h3>
                  <span 
                    className="sentiment-badge"
                    style={{ 
                      backgroundColor: getSentimentColor(article.sentiment_score),
                      color: 'white'
                    }}
                  >
                    {getSentimentLabel(article.sentiment_score)}
                  </span>
                </div>
                
                <div className="article-meta">
                  <span className="source">{article.source}</span>
                  {article.author && <span className="author">by {article.author}</span>}
                  <span className="date">{formatDate(article.published_date)}</span>
                </div>

                <p className="article-content">
                  {article.content.length > 300 
                    ? article.content.substring(0, 300) + '...' 
                    : article.content}
                </p>

                {article.url && (
                  <a 
                    href={article.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="read-more"
                  >
                    Read Full Article →
                  </a>
                )}

                {article.sentiment_score !== null && (
                  <div className="sentiment-score">
                    Sentiment Score: {article.sentiment_score.toFixed(2)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'summaries' && (
        <div className="summaries-list">
          {summaries.length === 0 ? (
            <div className="empty-state">
              <p>No summaries available</p>
              <p className="hint">The News Analyst will generate summaries here</p>
            </div>
          ) : (
            summaries.map(summary => (
              <div key={summary.id} className="summary-card">
                <div className="summary-header">
                  <h3>
                    {summary.period.charAt(0).toUpperCase() + summary.period.slice(1)} Summary
                  </h3>
                  <span className="summary-date">{formatDate(summary.summary_date)}</span>
                </div>

                {summary.sentiment_trend && (
                  <div 
                    className="sentiment-trend"
                    style={{ 
                      backgroundColor: getSentimentColor(summary.overall_sentiment_score),
                      color: 'white'
                    }}
                  >
                    Trend: {summary.sentiment_trend.toUpperCase()}
                  </div>
                )}

                <p className="summary-text">{summary.summary_text}</p>

                {summary.key_events && summary.key_events.length > 0 && (
                  <div className="key-events">
                    <h4>Key Events:</h4>
                    <ul>
                      {summary.key_events.map((event, idx) => (
                        <li key={idx}>
                          {typeof event === 'string' ? event : event.event || JSON.stringify(event)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="summary-meta">
                  <span>Based on {summary.article_count} articles</span>
                  {summary.overall_sentiment_score !== null && (
                    <span>Overall Sentiment: {summary.overall_sentiment_score.toFixed(2)}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default NewsSummary;
