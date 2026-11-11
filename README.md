# StockAI Pulse (AlgoScan) 📈🤖
### AI-Powered Quantitative Trading Terminal & Institutional Sentiment Engine

**StockAI Pulse (AlgoScan)** is an end-to-end predictive algorithmic trading, machine learning directional forecasting, and financial sentiment analysis terminal. It combines natural language processing (NLP) via financial domain transformers with quantitative time-series backtesting, technical indicator calculation, institutional risk analytics, and real-time interactive charting.

---

## 🌟 Key Highlights & Core Capabilities

- **🌐 Multi-Market & Global Asset Coverage**: Native out-of-the-box support for:
  - **Indian Equities (NSE & BSE)**: `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`, `IRFC.NS`, `INFY.NS`, `IREDA.NS`, `IOC.NS`, `TATAMOTORS.NS`, etc., with automatic currency detection (₹ INR).
  - **US Equities**: `AAPL`, `NVDA`, `TSLA`, `MSFT`, `GOOGL`, `AMZN`, etc. ($ USD).
  - **Cryptocurrency**: `BTC/USDT`, `ETH/USDT`, `SOL/USDT` via real-time market feeds.
- **🔍 Smart Universal Ticker & Company Search**: Zero-latency search bar featuring real-time fuzzy matching across companies and symbols, keyboard navigation, and asset filtering chips (*All / Stocks / Crypto*).
- **🛡️ Domain Reputation Scoring & Fake News Protection (Whitelisting & Tiering)**:
  To protect traders and quantitative models against market manipulation and clickbait/fake news, AlgoScan implements a 3-tier domain reputation engine:
  - **Tier 1 (High Trust — Weight: 1.0)**: Official regulatory disclosures (SEC EDGAR filings, BSE/NSE corporate announcements), established business wires (Reuters, Bloomberg, Wall Street Journal, Financial Times, Moneycontrol, Livemint, The Economic Times, Business Standard, Financial Express, CNBC-TV18, NDTV Profit).
  - **Tier 2 (Secondary Media — Weight: 0.65)**: Mainstream national outlets & financial aggregators (Yahoo Finance, Google News, MarketWatch, Benzinga, Investing.com, The Hindu, Times of India, Hindustan Times, Zee Business).
  - **Tier 3 (Unverified / High Risk — Weight: 0.25)**: Unregistered blogs, forums, and retail-trader social feeds (LinkedIn, scanx, Reddit, Twitter/X, forums). Heavily down-weighted (75% discount) and flagged with caution badges to safeguard sentiment scoring from speculative manipulation.
- **🧠 Transformer NLP Sentiment Engine**: Powered by **FinBERT** (`ProsusAI/finbert`), calculating sentence-level polarity distributions, time-decayed exponential rolling sentiment, and discrete trading signals (*Bullish / Bearish / Neutral*).
- **🔮 Machine Learning Directional Forecasting**:
  - Gradient Boosted Trees (**XGBoost**) and Bidirectional LSTM neural networks (**PyTorch**).
  - Strict temporal train/validation splitting (`shift(1)`) to eliminate lookahead bias.
  - Interactive on-the-fly model retraining and feature importance factor analysis (RSI Momentum, MACD Divergence, Bollinger Band %, Volume Volatility).
- **📊 Quantitative Backtesting & Strategy Simulator**:
  - 5 customizable quantitative algorithms: `SMA_CROSSOVER`, `MACD_CROSSOVER`, `RSI_MOMENTUM`, `SENTIMENT_ENHANCED`, and `BOLLINGER_BREAKOUT`.
  - Realistic transaction cost simulation (slippage and commission models).
  - Dual equity curve comparison (*Strategy vs Buy & Hold Benchmark*).
  - Complete executed trade log with entry/exit timestamps, prices, and net PnL.
- **🛡️ Institutional Risk Scorecard**:
  Calculates critical risk-adjusted performance metrics: **Cumulative ROI**, **Annualized ROI**, **Sharpe Ratio**, **Sortino Ratio (Downside Risk)**, **Max Drawdown (MDD)**, **Win Rate**, and **Profit Factor**.
- **📈 Interactive Trading Terminal**:
  Powered by TradingView Lightweight Charts with candlestick charts, volume histograms, dynamic Moving Average overlays (SMA 20, SMA 50, EMA 12), timeframes (`1D`, `1W`, `1M`, `6M`, `1Y`, `LIVE`), settings overlay modal, and full-screen trading mode.

---

## 🏛️ Architecture & Tech Stack

| Layer | Technologies |
|---|---|
| **Backend & API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn, AsyncIO, HTTPX |
| **NLP & Sentiment** | Hugging Face Transformers, FinBERT (`ProsusAI/finbert`), Google News RSS, Yahoo Finance, NewsAPI, Alpha Vantage |
| **Market Data** | Yahoo Finance (`yfinance`), CCXT (Binance), NumPy, Pandas |
| **Machine Learning** | XGBoost, PyTorch (Bi-LSTM), Scikit-Learn, Model Registry |
| **Backtesting & Risk** | VectorBT, Pandas, Custom Event Simulation Engine |
| **Frontend UI** | React 18, Vite, Tailwind CSS, TradingView Lightweight Charts, Lucide Icons |
| **DevOps & Containers**| Docker, Docker Compose, Nginx, Redis |

---

## 📁 Repository Structure

```
StockAI_Pulse/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint & lifespan
│   │   ├── config.py                # Pydantic Settings & environment configuration
│   │   ├── dependencies.py          # Dependency injection
│   │   ├── api/
│   │   │   ├── router.py            # API router aggregating all v1 endpoints
│   │   │   └── v1/
│   │   │       ├── sentiment.py     # /api/v1/sentiment/* (FinBERT + Tiering)
│   │   │       ├── market.py        # /api/v1/market/* (OHLCV, Search, Indicators)
│   │   │       ├── forecast.py      # /api/v1/forecast/* (XGBoost training & prediction)
│   │   │       ├── backtest.py      # /api/v1/backtest/* (Strategy execution)
│   │   │       └── risk.py          # /api/v1/risk/* (Portfolio risk metrics)
│   │   ├── core/
│   │   │   ├── sentiment/           # News fetchers, FinBERT analyzer, Tiered aggregator
│   │   │   ├── market/              # Data fetcher, technical indicators, feature engineering
│   │   │   ├── ml/                  # Forecasters, evaluation, Model Registry
│   │   │   ├── backtest/            # Trading strategies, BacktestEngine, reporting
│   │   │   └── risk/                # Quantitative risk metrics
│   │   ├── models/                  # Pydantic DTOs for requests & responses
│   │   └── utils/                   # Structured logging, error handlers, LRU caching
│   ├── tests/                       # Pytest test suite
│   ├── Dockerfile                   # Backend Docker container specification
│   ├── pyproject.toml               # Poetry/pip project metadata
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Environment configuration template
├── frontend/
│   ├── src/
│   │   ├── api/client.js            # Axios client with automatic retry logic
│   │   ├── components/
│   │   │   ├── charts/PriceChart.jsx # TradingView Lightweight Chart + Overlays
│   │   │   ├── sentiment/           # SentimentGauge, NewsFeed with Trust Badges
│   │   │   ├── backtest/            # Dynamic StrategyControls, BacktestVisualizer
│   │   │   ├── risk/                # RiskScorecard
│   │   │   ├── forecast/            # Directional ForecastCard & Feature Weights
│   │   │   └── layout/              # Universal Search Navbar, Sidebar Navigation
│   │   ├── App.jsx                  # Main dashboard controller
│   │   └── index.css                # Institutional dark theme styling
│   ├── nginx.conf                   # Reverse proxy configuration
│   ├── Dockerfile                   # Frontend Docker container specification
│   ├── vite.config.js               # Vite bundler configuration
│   ├── tailwind.config.js           # Tailwind typography & dark theme tokens
│   └── package.json                 # Node dependencies
├── docker-compose.yml               # Multi-container orchestration
├── run.py                           # Cross-platform single-command runner
├── start.bat                        # Windows 1-click launcher
├── start.sh                         # Linux/macOS launcher
├── package.json                     # Root scripts
├── .gitignore                       # Git exclusion rules
└── README.md                        # Documentation
```

---

## ⚡ Quick Start Guide

### Prerequisites
- **Python**: Version 3.10 or 3.11
- **Node.js**: Version 18 or higher (with `npm`)
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/komminenivenkatesh/StockAI_Pulse.git
cd StockAI_Pulse
```

### 2. Single-Command Launch (Recommended)
You can launch both the **FastAPI Backend** and the **React Frontend** together using the included runner:

#### Windows / macOS / Linux:
```bash
python run.py
```

#### Windows Double-Click:
Double-click `start.bat` or run:
```cmd
start.bat
```

#### macOS / Linux:
```bash
chmod +x start.sh
./start.sh
```

The application will automatically start:
- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Manual Development Setup

If you prefer to run services in separate terminals:

### Terminal 1: Backend Setup
```bash
cd backend
python -m venv .venv

# Activate virtual environment:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# Start backend with auto-reload:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🐳 Docker Deployment

To launch the full containerized stack (FastAPI Backend + React Nginx Frontend + Redis Cache):

```bash
docker compose up --build -d
```

- **Frontend**: [http://localhost](http://localhost)
- **API Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

To stop containers:
```bash
docker compose down
```

---

## 📡 REST API Reference

Interactive OpenAPI documentation is available live at `http://localhost:8000/docs`.

### 📰 Sentiment & News Intelligence
- `GET /api/v1/sentiment/analyze/{ticker}`: Real-time news scraping with domain reputation tiering (Tier 1/2/3), FinBERT sentiment scoring, and weighted confidence.
- `POST /api/v1/sentiment/analyze/headlines`: Batch score user-provided financial headlines.

### 📊 Market Data & Indicators
- `GET /api/v1/market/search?q={query}`: Fuzzy symbol and company name lookup.
- `GET /api/v1/market/data/{ticker}`: Standardized OHLCV candlestick data with optional technical indicator calculations.
- `GET /api/v1/market/indicators/{ticker}`: Standalone computation of 10+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP).

### 🔮 Machine Learning Directional Forecast
- `POST /api/v1/forecast/train`: Retrain the XGBoost directional forecasting model on historical bars.
- `GET /api/v1/forecast/predict/{ticker}`: Real-time directional prediction (Up/Down/Sideways) with feature importance weights.

### 📈 Backtesting & Quantitative Risk
- `POST /api/v1/backtest/run`: Run historical simulation with configurable parameters, commission, and slippage.
- `GET /api/v1/backtest/strategies`: Catalog of supported strategies and default parameter schemas.
- `POST /api/v1/risk/evaluate`: Institutional portfolio risk evaluation (Sharpe, Sortino, Drawdown, Profit Factor, Win Rate).

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.
