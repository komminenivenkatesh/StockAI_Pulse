import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Maximize2, Minimize2, Settings, BarChart2, Wifi, AlertCircle, X, Check } from 'lucide-react';
import { api } from '../../api/client';

// Map timeframe to period/interval for API
const getTimeframeParams = (timeframe) => {
  switch (timeframe) {
    case '1D':   return { period: '5d',  interval: '15m' };
    case '1W':   return { period: '1mo', interval: '1h' };
    case '1M':   return { period: '3mo', interval: '1d' };
    case '6M':   return { period: '6mo', interval: '1d' };
    case '1Y':   return { period: '1y',  interval: '1d' };
    case 'LIVE': return { period: '1d',  interval: '2m' };
    default:     return { period: '1y',  interval: '1d' };
  }
};

const PriceChart = ({ ticker, timeframe }) => {
  const chartWrapperRef = useRef(null);
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const sma20SeriesRef = useRef(null);
  const sma50SeriesRef = useRef(null);
  const ema12SeriesRef = useRef(null);

  const [showMAs, setShowMAs] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const [currencySymbol, setCurrencySymbol] = useState('$');
  const [error, setError] = useState(null);
  const [isLive, setIsLive] = useState(false);

  // Fullscreen listener
  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      if (chartRef.current && chartContainerRef.current) {
        setTimeout(() => {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
          });
          chartRef.current.timeScale().fitContent();
        }, 100);
      }
    };
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  const toggleFullscreen = () => {
    if (!chartWrapperRef.current) return;
    if (!document.fullscreenElement) {
      chartWrapperRef.current.requestFullscreen().catch(err => console.warn(err));
    } else {
      document.exitFullscreen().catch(err => console.warn(err));
    }
  };

  // Toggle MA visibility
  useEffect(() => {
    if (sma20SeriesRef.current) sma20SeriesRef.current.applyOptions({ visible: showMAs });
    if (sma50SeriesRef.current) sma50SeriesRef.current.applyOptions({ visible: showMAs });
    if (ema12SeriesRef.current) ema12SeriesRef.current.applyOptions({ visible: showMAs });
  }, [showMAs]);

  // Toggle Volume visibility
  const toggleVolume = () => {
    const next = !showVolume;
    setShowVolume(next);
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.applyOptions({ visible: next });
    }
  };

  // Toggle Gridlines
  const toggleGrid = () => {
    const next = !showGrid;
    setShowGrid(next);
    if (chartRef.current) {
      chartRef.current.applyOptions({
        grid: {
          vertLines: { color: next ? '#1e293b' : 'transparent' },
          horzLines: { color: next ? '#1e293b' : 'transparent' },
        },
      });
    }
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: showGrid ? '#1e293b' : 'transparent' },
        horzLines: { color: showGrid ? '#1e293b' : 'transparent' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#64748b', style: 3 },
        horzLine: { color: '#64748b', style: 3 },
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    candleSeriesRef.current = candlestickSeries;

    // Moving average overlays
    const sma20 = chart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 1.5,
      title: 'SMA 20',
      visible: showMAs,
    });
    const sma50 = chart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 1.5,
      title: 'SMA 50',
      visible: showMAs,
    });
    const ema12 = chart.addLineSeries({
      color: '#a855f7',
      lineWidth: 1.5,
      title: 'EMA 12',
      visible: showMAs,
    });

    sma20SeriesRef.current = sma20;
    sma50SeriesRef.current = sma50;
    ema12SeriesRef.current = ema12;

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: showVolume,
    });
    volumeSeriesRef.current = volumeSeries;

    let isMounted = true;

    async function loadChartData() {
      try {
        setError(null);
        const { period, interval } = getTimeframeParams(timeframe);
        const res = await api.fetchMarketData(ticker, period, interval, true);
        if (res && res.data && res.data.ohlcv && res.data.ohlcv.length > 0 && isMounted) {
          const isIntraday = interval.includes('m') || interval.includes('h');
          
          const candleData = res.data.ohlcv.map(b => ({
            time: isIntraday 
              ? Math.floor(new Date(b.timestamp).getTime() / 1000)
              : b.timestamp.split('T')[0],
            open: Number(b.open),
            high: Number(b.high),
            low: Number(b.low),
            close: Number(b.close)
          }));
          const volData = res.data.ohlcv.map(b => ({
            time: isIntraday
              ? Math.floor(new Date(b.timestamp).getTime() / 1000)
              : b.timestamp.split('T')[0],
            value: Number(b.volume),
            color: b.close >= b.open ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)'
          }));
          candlestickSeries.setData(candleData);
          volumeSeries.setData(volData);

          // Populate Moving Averages
          if (res.data.indicators && res.data.indicators.length > 0) {
            const s20Data = [];
            const s50Data = [];
            const e12Data = [];
            res.data.indicators.forEach(ind => {
              const time = isIntraday
                ? Math.floor(new Date(ind.timestamp).getTime() / 1000)
                : ind.timestamp.split('T')[0];
              if (ind.sma_20 != null) s20Data.push({ time, value: Number(ind.sma_20) });
              if (ind.sma_50 != null) s50Data.push({ time, value: Number(ind.sma_50) });
              if (ind.ema_12 != null) e12Data.push({ time, value: Number(ind.ema_12) });
            });
            sma20.setData(s20Data);
            sma50.setData(s50Data);
            ema12.setData(e12Data);
          }

          chart.timeScale().fitContent();

          // Update price info
          const latest = res.data.ohlcv[res.data.ohlcv.length - 1];
          const prev = res.data.ohlcv.length > 1 ? res.data.ohlcv[res.data.ohlcv.length - 2] : latest;
          const curr = (res.meta?.currency === 'INR' || ticker?.toUpperCase().endsWith('.NS') || ticker?.toUpperCase().endsWith('.BO')) ? '₹' : '$';
          setCurrencySymbol(curr);
          setLastPrice(Number(latest.close).toFixed(2));
          setPriceChange(((Number(latest.close) - Number(prev.close)) / Number(prev.close) * 100).toFixed(2));
          return;
        } else if (isMounted) {
          candlestickSeries.setData([]);
          volumeSeries.setData([]);
          sma20.setData([]);
          sma50.setData([]);
          ema12.setData([]);
          setLastPrice(null);
          setPriceChange(null);
          setError(`No price data returned for "${ticker}".`);
        }
      } catch (e) {
        console.warn('API fetchMarketData failed:', e);
        if (isMounted) {
          candlestickSeries.setData([]);
          volumeSeries.setData([]);
          sma20.setData([]);
          sma50.setData([]);
          ema12.setData([]);
          setLastPrice(null);
          setPriceChange(null);
          setError(`Could not find symbol "${ticker}". Please verify the ticker or exchange.`);
        }
      }
    }

    loadChartData();

    // LIVE mode: auto-refresh every 5 seconds
    let liveInterval = null;
    if (timeframe === 'LIVE') {
      setIsLive(true);
      liveInterval = setInterval(() => {
        if (isMounted) loadChartData();
      }, 5000);
    } else {
      setIsLive(false);
    }

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      isMounted = false;
      if (liveInterval) clearInterval(liveInterval);
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [ticker, timeframe]);

  return (
    <div 
      ref={chartWrapperRef}
      className={`h-full w-full flex flex-col bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-xl ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      }`}
    >
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between bg-slate-800/50">
        <div className="flex items-center space-x-3">
          <h2 className="text-lg font-bold text-white">{ticker}</h2>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            isLive ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-slate-700 text-slate-300'
          }`}>
            {isLive ? '● LIVE' : timeframe}
          </span>
          {lastPrice && (
            <span className="text-white font-semibold text-lg">{currencySymbol}{lastPrice}</span>
          )}
          {priceChange && (
            <span className={`text-sm font-medium ${Number(priceChange) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {Number(priceChange) >= 0 ? '+' : ''}{priceChange}%
            </span>
          )}
          {isLive && (
            <span className="flex items-center space-x-1 text-xs text-emerald-400">
              <Wifi className="w-3 h-3" />
              <span>1m candles • auto-refresh 5s</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2 relative">
          {/* Moving Averages Button */}
          <button 
            onClick={() => setShowMAs(!showMAs)}
            className={`flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer ${
              showMAs 
                ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 shadow-sm' 
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-slate-200'
            }`}
            title="Toggle Moving Averages overlay"
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>MAs (20, 50, 12)</span>
          </button>

          {/* Settings Button & Popover */}
          <div className="relative">
            <button 
              onClick={() => setShowSettings(!showSettings)}
              className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                showSettings 
                  ? 'bg-slate-700 text-white border-slate-600' 
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'
              }`}
              title="Chart display settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {showSettings && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-xl shadow-2xl p-3 z-30 space-y-2 animate-in fade-in duration-100">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-semibold text-slate-300">
                  <span>Chart Overlays</span>
                  <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer p-1.5 rounded hover:bg-slate-800">
                  <span>Moving Averages</span>
                  <input 
                    type="checkbox" 
                    checked={showMAs} 
                    onChange={() => setShowMAs(!showMAs)}
                    className="rounded accent-emerald-500 cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer p-1.5 rounded hover:bg-slate-800">
                  <span>Volume Histogram</span>
                  <input 
                    type="checkbox" 
                    checked={showVolume} 
                    onChange={toggleVolume}
                    className="rounded accent-emerald-500 cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer p-1.5 rounded hover:bg-slate-800">
                  <span>Gridlines</span>
                  <input 
                    type="checkbox" 
                    checked={showGrid} 
                    onChange={toggleGrid}
                    className="rounded accent-emerald-500 cursor-pointer"
                  />
                </label>
              </div>
            )}
          </div>

          {/* Fullscreen Button */}
          <button 
            onClick={toggleFullscreen}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 rounded-lg transition-colors cursor-pointer"
            title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="flex-1 relative w-full h-full min-h-[300px]">
        <div ref={chartContainerRef} className="w-full h-full" />
        {error && (
          <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center z-10">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center mb-3">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="text-white font-semibold text-base mb-1">Symbol Not Found</h3>
            <p className="text-slate-400 text-sm max-w-md mb-4">{error}</p>
            <div className="text-xs text-slate-500 bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2">
              Try searching a valid ticker like: <span className="text-emerald-400 font-mono">RELIANCE</span>, <span className="text-emerald-400 font-mono">TCS</span>, <span className="text-emerald-400 font-mono">INFY</span>, <span className="text-emerald-400 font-mono">AAPL</span>, or <span className="text-emerald-400 font-mono">BTC/USDT</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PriceChart;