import axios from 'axios';

const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Retry logic with exponential backoff for startup race condition
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const requestWithRetry = async (requestFn, retries = 3, delay = 2000) => {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await requestFn();
      return response.data;
    } catch (error) {
      const isNetworkError = error.code === 'ECONNREFUSED' || 
                             error.code === 'ERR_NETWORK' ||
                             error.message?.includes('Network Error');
      
      if (isNetworkError && attempt < retries) {
        console.warn(`API request failed (attempt ${attempt + 1}/${retries + 1}), retrying in ${delay}ms...`);
        await sleep(delay);
        delay *= 1.5; // exponential backoff
        continue;
      }
      
      console.warn('API request failed:', error.message);
      return null;
    }
  }
  return null;
};

export const api = {
  searchSymbols: async (query, limit = 8) => {
    try {
      const res = await apiClient.get('/market/search', { params: { q: query, limit } });
      return res.data;
    } catch (e) {
      console.warn('searchSymbols failed:', e);
      return { data: [] };
    }
  },

  fetchMarketData: (ticker, period = '1y', interval = '1d', include_indicators = true) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/market/data/${encodeURIComponent(ticker)}`, {
          params: { period, interval, include_indicators }
        });
        return res;
      }
    );
  },

  fetchLiveData: (ticker) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/market/data/${encodeURIComponent(ticker)}`, {
          params: { period: '1d', interval: '5m', include_indicators: false }
        });
        return res;
      }
    );
  },

  fetchIndicators: (ticker, period = '1y', interval = '1d') => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/market/indicators/${encodeURIComponent(ticker)}`, {
          params: { period, interval }
        });
        return res;
      }
    );
  },

  fetchSentiment: (ticker, lookback_days = 7) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/sentiment/analyze/${encodeURIComponent(ticker)}`, {
          params: { lookback_days }
        });
        return res;
      }
    );
  },

  analyzeHeadlines: (headlines) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.post(`/sentiment/analyze/headlines`, { headlines });
        return res;
      }
    );
  },

  runBacktest: ({ ticker, strategy = 'SMA_CROSSOVER', params = {}, period = '1y', interval = '1d', initial_capital = 10000, commission_pct = 0.001, slippage_pct = 0.0005 }) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.post(`/backtest/run`, {
          ticker,
          strategy,
          params,
          period,
          interval,
          initial_capital,
          commission_pct,
          slippage_pct
        });
        return res;
      }
    );
  },

  fetchStrategies: () => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/backtest/strategies`);
        return res;
      }
    );
  },

  fetchForecast: (ticker, days = 5) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.get(`/forecast/predict/${encodeURIComponent(ticker)}`, {
          params: { days }
        });
        return res;
      }
    );
  },

  trainForecastModel: ({ ticker, period = '2y', task = 'classification', forecast_horizon = 1 }) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.post(`/forecast/train`, {
          ticker,
          period,
          task,
          forecast_horizon
        });
        return res;
      }
    );
  },

  evaluateRisk: (returns, risk_free_rate = 0.02) => {
    return requestWithRetry(
      async () => {
        const res = await apiClient.post(`/risk/evaluate`, {
          returns,
          risk_free_rate
        });
        return res;
      }
    );
  }
};
