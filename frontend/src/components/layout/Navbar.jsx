import React, { useState, useEffect, useRef } from 'react';
import { Activity, Search, Clock, Globe, TrendingUp, X, Loader2 } from 'lucide-react';
import { api } from '../../api/client';

const POPULAR_SUGGESTIONS = [
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries Ltd', exchange: 'NSE', type: 'Stock' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services', exchange: 'NSE', type: 'Stock' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank Ltd', exchange: 'NSE', type: 'Stock' },
  { symbol: 'INFY.NS', name: 'Infosys Limited', exchange: 'NSE', type: 'Stock' },
  { symbol: 'IRFC.NS', name: 'Indian Railway Finance Corporation', exchange: 'NSE', type: 'Stock' },
  { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'BTC/USDT', name: 'Bitcoin', exchange: 'CRYPTO', type: 'Crypto' },
];

const Navbar = ({ selectedTicker, setSelectedTicker, selectedTimeframe, setSelectedTimeframe }) => {
  const [searchInput, setSearchInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [filterTab, setFilterTab] = useState('ALL');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const searchContainerRef = useRef(null);

  // Debounced search
  useEffect(() => {
    const query = searchInput.trim();
    if (!query) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const res = await api.searchSymbols(query, 10);
        if (res && res.data) {
          setSuggestions(res.data);
        }
      } catch (err) {
        console.warn('Search failed:', err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (symbol) => {
    setSelectedTicker(symbol.toUpperCase());
    setSearchInput('');
    setIsOpen(false);
    setHighlightedIndex(-1);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const visibleList = getFilteredList();
    if (highlightedIndex >= 0 && highlightedIndex < visibleList.length) {
      handleSelect(visibleList[highlightedIndex].symbol);
    } else if (visibleList.length > 0) {
      handleSelect(visibleList[0].symbol);
    } else if (searchInput.trim()) {
      handleSelect(searchInput.trim().toUpperCase());
    }
  };

  const handleKeyDown = (e) => {
    const visibleList = getFilteredList();
    if (!isOpen || visibleList.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < visibleList.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : visibleList.length - 1));
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const getFilteredList = () => {
    const list = searchInput.trim() ? suggestions : POPULAR_SUGGESTIONS;
    if (filterTab === 'STOCKS') {
      return list.filter((i) => i.type?.toLowerCase() === 'stock');
    }
    if (filterTab === 'CRYPTO') {
      return list.filter((i) => i.type?.toLowerCase() === 'crypto' || i.exchange === 'CRYPTO');
    }
    return list;
  };

  const visibleList = getFilteredList();

  const getExchangeBadgeStyle = (exchange) => {
    switch (exchange) {
      case 'NSE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'BSE':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'NASDAQ':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'NYSE':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'CRYPTO':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600/40';
    }
  };

  return (
    <nav className="h-16 border-b border-slate-700 bg-slate-900 flex items-center justify-between px-6 text-white shrink-0 z-50 relative">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <Activity className="h-6 w-6 text-emerald-400 animate-pulse" />
          <div className="flex flex-col">
            <span className="font-bold text-lg leading-tight tracking-wider">AlgoScan</span>
            <span className="text-xs text-slate-400">AI Quant Terminal</span>
          </div>
        </div>
        <div className="h-6 w-px bg-slate-700 mx-4" />
        <div className="flex items-center space-x-2 text-xs">
          <Globe className="h-4 w-4 text-emerald-400" />
          <span className="text-slate-300">Market Open</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">14ms latency</span>
        </div>
      </div>

      {/* Center Search with Live Dropdown */}
      <div ref={searchContainerRef} className="flex flex-1 items-center justify-center relative max-w-lg mx-6">
        <form onSubmit={handleSearchSubmit} className="relative w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search stock or company (e.g. indian, tata, reliance, irfc)..."
            className="w-full bg-slate-800/90 border border-slate-700/80 rounded-full py-2 pl-10 pr-28 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-all shadow-inner"
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
          />

          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center space-x-2">
            {loading && <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />}
            {searchInput && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  setSuggestions([]);
                }}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
            <div className="flex items-center space-x-1 pointer-events-none">
              <span className="text-[10px] text-slate-400 bg-slate-700/60 px-1.5 py-0.5 rounded border border-slate-600/40">Active:</span>
              <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">{selectedTicker}</span>
            </div>
          </div>
        </form>

        {/* Search Results Dropdown (Groww / Zerodha style) */}
        {isOpen && (
          <div className="absolute left-0 right-0 top-full mt-2 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in duration-150">
            {/* Filter Chips Bar */}
            <div className="flex items-center space-x-2 px-4 py-2.5 border-b border-slate-800 bg-slate-950/40">
              {['ALL', 'STOCKS', 'CRYPTO'].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setFilterTab(tab)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                    filterTab === tab
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                      : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-slate-200'
                  }`}
                >
                  {tab === 'ALL' ? 'All' : tab === 'STOCKS' ? 'Stocks' : 'Crypto'}
                </button>
              ))}
              <span className="text-[11px] text-slate-500 ml-auto">
                {searchInput.trim() ? `${visibleList.length} results` : 'Popular Stocks'}
              </span>
            </div>

            {/* List of Suggestions */}
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60 custom-scrollbar">
              {visibleList.length > 0 ? (
                visibleList.map((item, idx) => {
                  const isHighlighted = idx === highlightedIndex;
                  return (
                    <div
                      key={`${item.symbol}-${idx}`}
                      onClick={() => handleSelect(item.symbol)}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                      className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-colors ${
                        isHighlighted ? 'bg-slate-800/90' : 'hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center space-x-3 min-w-0 pr-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                          <TrendingUp className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="text-sm font-semibold text-slate-100 truncate">
                            {item.name}
                          </span>
                          <div className="flex items-center space-x-2 text-xs text-slate-400 mt-0.5">
                            <span>{item.type || 'Stock'}</span>
                            <span className="text-slate-600">•</span>
                            <span className="font-mono text-emerald-400/90 font-medium">{item.symbol}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center shrink-0">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold border uppercase tracking-wider ${getExchangeBadgeStyle(item.exchange)}`}>
                          {item.exchange || 'STOCK'}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-8 text-center text-slate-400 text-sm">
                  {loading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                      <span>Searching markets...</span>
                    </div>
                  ) : (
                    <div>
                      <p className="font-medium text-slate-300">No matching assets found for "{searchInput}"</p>
                      <p className="text-xs text-slate-500 mt-1">Press Enter to force-search this ticker directly.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-1 bg-slate-800 rounded-lg p-1 border border-slate-700">
          {['1D', '1W', '1M', '6M', '1Y', 'LIVE'].map((tf) => (
            <button
              key={tf}
              onClick={() => setSelectedTimeframe(tf)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors flex items-center space-x-1 ${
                selectedTimeframe === tf
                  ? tf === 'LIVE' 
                    ? 'bg-emerald-500/20 text-emerald-400 shadow-sm border border-emerald-500/50'
                    : 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tf === 'LIVE' && <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>}
              <span>{tf}</span>
            </button>
          ))}
        </div>
        <Clock className="h-5 w-5 text-slate-400" />
      </div>
    </nav>
  );
};

export default Navbar;
