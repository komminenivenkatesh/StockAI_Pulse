import React, { useState } from 'react';
import { Play, Settings2, SlidersHorizontal, Loader2, Calendar } from 'lucide-react';

const StrategyControls = ({ ticker = 'AAPL', onRunBacktest, loading }) => {
  const [strategy, setStrategy] = useState('MACD_CROSSOVER');
  const [fastPeriod, setFastPeriod] = useState(12);
  const [slowPeriod, setSlowPeriod] = useState(26);
  const [signalSmoothing, setSignalSmoothing] = useState(9);
  const [sentThreshold, setSentThreshold] = useState(0.15);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [oversold, setOversold] = useState(30);
  const [overbought, setOverbought] = useState(70);
  const [bbPeriod, setBbPeriod] = useState(20);
  const [bbStdDev, setBbStdDev] = useState(2.0);

  const [period, setPeriod] = useState('1y');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commission, setCommission] = useState(0.1);
  const [slippage, setSlippage] = useState(0.05);

  const isIndian = ticker?.toUpperCase().endsWith('.NS') || ticker?.toUpperCase().endsWith('.BO');
  const currencySymbol = isIndian ? '₹' : '$';

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading) return;

    const params = {};
    if (strategy === 'MACD_CROSSOVER') {
      params.fast = Number(fastPeriod);
      params.slow = Number(slowPeriod);
      params.signal = Number(signalSmoothing);
    } else if (strategy === 'SMA_CROSSOVER') {
      params.fast_period = Number(fastPeriod);
      params.slow_period = Number(slowPeriod);
    } else if (strategy === 'SENTIMENT_ENHANCED') {
      params.fast_period = Number(fastPeriod);
      params.slow_period = Number(slowPeriod);
      params.sentiment_threshold = Number(sentThreshold);
    } else if (strategy === 'RSI_MOMENTUM') {
      params.period = Number(rsiPeriod);
      params.oversold = Number(oversold);
      params.overbought = Number(overbought);
    } else if (strategy === 'BOLLINGER_BREAKOUT') {
      params.period = Number(bbPeriod);
      params.std_dev = Number(bbStdDev);
    }

    onRunBacktest({
      ticker,
      strategy,
      params,
      initial_capital: Number(initialCapital),
      commission_pct: Number(commission) / 100,
      slippage_pct: Number(slippage) / 100,
      period,
      interval: '1d',
    });
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl flex flex-col shadow-xl h-full">
      <div className="px-5 py-4 border-b border-slate-700 bg-slate-800/30 flex items-center space-x-2">
        <Settings2 className="w-5 h-5 text-indigo-400" />
        <h3 className="text-white font-semibold">Strategy Parameters</h3>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
        <div className="p-5 flex-1 overflow-y-auto space-y-5 custom-scrollbar">
          {/* Strategy Selection */}
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Algorithm</label>
            <select
              value={strategy}
              onChange={(e) => {
                const s = e.target.value;
                setStrategy(s);
                if (s === 'SMA_CROSSOVER') {
                  setFastPeriod(20);
                  setSlowPeriod(50);
                } else if (s === 'MACD_CROSSOVER') {
                  setFastPeriod(12);
                  setSlowPeriod(26);
                  setSignalSmoothing(9);
                }
              }}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              <option value="MACD_CROSSOVER">MACD Crossover</option>
              <option value="SMA_CROSSOVER">SMA Crossover (Fast/Slow)</option>
              <option value="SENTIMENT_ENHANCED">Sentiment-Enhanced MACD</option>
              <option value="RSI_MOMENTUM">RSI Momentum Builder</option>
              <option value="BOLLINGER_BREAKOUT">Bollinger Breakout</option>
            </select>
          </div>

          {/* Dynamic Strategy Inputs */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center">
              <SlidersHorizontal className="w-3 h-3 mr-1" /> Dynamic Inputs
            </h4>

            {(strategy === 'MACD_CROSSOVER' || strategy === 'SMA_CROSSOVER' || strategy === 'SENTIMENT_ENHANCED') && (
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Fast Period</label>
                  <input
                    type="number"
                    value={fastPeriod}
                    onChange={(e) => setFastPeriod(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Slow Period</label>
                  <input
                    type="number"
                    value={slowPeriod}
                    onChange={(e) => setSlowPeriod(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            )}

            {strategy === 'MACD_CROSSOVER' && (
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Signal Smoothing</label>
                <input
                  type="number"
                  value={signalSmoothing}
                  onChange={(e) => setSignalSmoothing(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {strategy === 'SENTIMENT_ENHANCED' && (
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Sentiment Threshold</label>
                <input
                  type="number"
                  step="0.05"
                  value={sentThreshold}
                  onChange={(e) => setSentThreshold(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {strategy === 'RSI_MOMENTUM' && (
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">RSI Period</label>
                  <input
                    type="number"
                    value={rsiPeriod}
                    onChange={(e) => setRsiPeriod(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Oversold (Buy)</label>
                    <input
                      type="number"
                      value={oversold}
                      onChange={(e) => setOversold(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Overbought (Sell)</label>
                    <input
                      type="number"
                      value={overbought}
                      onChange={(e) => setOverbought(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {strategy === 'BOLLINGER_BREAKOUT' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Period</label>
                  <input
                    type="number"
                    value={bbPeriod}
                    onChange={(e) => setBbPeriod(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Std Dev</label>
                  <input
                    type="number"
                    step="0.1"
                    value={bbStdDev}
                    onChange={(e) => setBbStdDev(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Simulation Settings */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center">
              <Calendar className="w-3 h-3 mr-1" /> Simulation Settings
            </h4>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Historical Lookback</label>
                <div className="grid grid-cols-3 gap-2">
                  {['6mo', '1y', '2y'].map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPeriod(p)}
                      className={`py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                        period === p
                          ? 'bg-indigo-600/20 text-indigo-400 border-indigo-500/50'
                          : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-white'
                      }`}
                    >
                      {p.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Capital ({currencySymbol})</label>
                  <input
                    type="number"
                    value={initialCapital}
                    onChange={(e) => setInitialCapital(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Commission (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={commission}
                    onChange={(e) => setCommission(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Slippage (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={slippage}
                  onChange={(e) => setSlippage(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="p-5 border-t border-slate-700 bg-slate-800/30">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg flex items-center justify-center space-x-2 transition-colors shadow-[0_0_15px_rgba(79,70,229,0.3)] cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Running Simulation...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Backtest ({ticker})</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default StrategyControls;