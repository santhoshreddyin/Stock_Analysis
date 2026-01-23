/**
 * API Service for Stock Analysis Backend
 * Handles all HTTP requests to FastAPI backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service methods
export const stockAPI = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/api/health');
    return response.data;
  },

  // Get all stocks with optional filters
  getStocks: async (params = {}) => {
    const response = await api.get('/api/stocks', { params });
    return response.data;
  },

  // Get stock detail by symbol
  getStockDetail: async (symbol) => {
    const response = await api.get(`/api/stocks/${symbol}`);
    return response.data;
  },

  // Get key parameters
  getKeyParameters: async () => {
    const response = await api.get('/api/key-parameters');
    return response.data;
  },

  // Get stock history
  getStockHistory: async (symbol, limit = 30) => {
    const response = await api.get(`/api/stocks/${symbol}/history`, {
      params: { limit },
    });
    return response.data;
  },

  // Get all sectors
  getSectors: async () => {
    const response = await api.get('/api/sectors');
    return response.data;
  },

  // News and Graph APIs

  // Get news articles
  getNewsArticles: async (symbol = null, source = null, limit = 20) => {
    const response = await api.get('/api/news', {
      params: { symbol, source, limit },
    });
    return response.data;
  },

  // Search news with semantic search
  searchNews: async (query, symbol = null, limit = 10) => {
    const response = await api.post('/api/news/search', {
      query,
      symbol,
      limit,
    });
    return response.data;
  },

  // Get news summaries
  getNewsSummaries: async (symbol, period = 'daily', limit = 5) => {
    const response = await api.get(`/api/news/summary/${symbol}`, {
      params: { period, limit },
    });
    return response.data;
  },

  // Get graph data for visualization
  getGraphData: async (symbol = null, entity_type = null, limit = 100) => {
    const response = await api.get('/api/graph', {
      params: { symbol, entity_type, limit },
    });
    return response.data;
  },
};

export default api;
