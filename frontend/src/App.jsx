import React, { useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import PriceChart from './components/charts/PriceChart';
import SentimentGauge from './components/sentiment/SentimentGauge';
import NewsFeed from './components/sentiment/NewsFeed';
import RiskScorecard from './components/risk/RiskScorecard';
import ForecastCard from './components/forecast/ForecastCard';
import StrategyControls from './components/backtest/StrategyControls';
import BacktestVisualizer from './components/backtest/BacktestVisualizer';
import { api } from './api/client';

const App = () => {
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1Y');
  const [activeTab, setActiveTab] = useState('terminal');

  const [backtestResult, setBacktestResult] = useState(null);
  const [backtestLoading, setBacktestLoading] = useState(false);

  const handleRunBacktest = async (payload) => {
    setBacktestLoading(true);
    try {
      const res = await api.runBacktest(payload);
      if (res && res.data) {
        setBacktestResult(res.data);
      }
    } catch (e) {
      console.warn('Backtest failed:', e);
    } finally {
      setBacktestLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'terminal':
        return (
          <div className="flex-1 p-6 h-full">
            <PriceChart ticker={selectedTicker} timeframe={selectedTimeframe} />
          </div>
        );
      case 'sentiment':
        return (
          <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
            <div className="lg:col-span-1 h-full">
              <SentimentGauge ticker={selectedTicker} />
            </div>
            <div className="lg:col-span-2 h-full">
              <NewsFeed ticker={selectedTicker} />
            </div>

          </div>
        );
      case 'forecast':
        return (
          <div className="flex-1 p-6 max-w-4xl mx-auto w-full h-full">
            <ForecastCard ticker={selectedTicker} />
          </div>
        );
      case 'backtest':
        return (
          <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
            <div className="lg:col-span-1 h-full">
              <StrategyControls
                ticker={selectedTicker}
                onRunBacktest={handleRunBacktest}
                loading={backtestLoading}
              />
            </div>
            <div className="lg:col-span-3 h-full">
              <BacktestVisualizer
                data={backtestResult}
                loading={backtestLoading}
              />
            </div>
          </div>
        );
      case 'risk':
        return (
          <div className="flex-1 p-6 h-full">
            <RiskScorecard ticker={selectedTicker} />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#020617] text-slate-300 font-sans overflow-hidden">
      <Navbar 
        selectedTicker={selectedTicker} 
        setSelectedTicker={setSelectedTicker}
        selectedTimeframe={selectedTimeframe}
        setSelectedTimeframe={setSelectedTimeframe}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 relative overflow-auto bg-gradient-to-br from-[#020617] to-slate-900">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default App;
