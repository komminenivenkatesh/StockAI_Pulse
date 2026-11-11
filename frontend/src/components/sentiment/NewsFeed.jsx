import React, { useState, useEffect } from 'react';
import { ExternalLink, Clock, RefreshCw, Newspaper, ShieldCheck, AlertTriangle, Filter, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';

const getSentimentBadge = (sentiment, conf) => {
  let colors = '';
  switch (sentiment?.toLowerCase()) {
    case 'positive':
      colors = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      break;
    case 'negative':
      colors = 'bg-red-500/20 text-red-400 border-red-500/30';
      break;
    case 'neutral':
    default:
      colors = 'bg-slate-700/50 text-slate-300 border-slate-600';
      break;
  }
  return (
    <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold flex items-center space-x-1 ${colors}`}>
      <span>{sentiment}</span>
      <span className="opacity-70">|</span>
      <span>{conf}%</span>
    </span>
  );
};

const getTrustBadge = (tier) => {
  if (tier === 1) {
    return (
      <span
        className="px-2 py-0.5 rounded border text-[10px] font-semibold flex items-center space-x-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
        title="Tier 1 (High Trust): Official disclosures & leading business wires (Weight 1.0)"
      >
        <ShieldCheck className="w-3 h-3" />
        <span>Tier 1 (High Trust)</span>
      </span>
    );
  } else if (tier === 2) {
    return (
      <span
        className="px-2 py-0.5 rounded border text-[10px] font-semibold flex items-center space-x-1 bg-sky-500/10 text-sky-400 border-sky-500/30"
        title="Tier 2 (Secondary Media): General aggregators & national outlets (Weight 0.65)"
      >
        <Newspaper className="w-3 h-3" />
        <span>Tier 2 (Secondary)</span>
      </span>
    );
  } else {
    return (
      <span
        className="px-2 py-0.5 rounded border text-[10px] font-semibold flex items-center space-x-1 bg-amber-500/10 text-amber-400 border-amber-500/30"
        title="Tier 3 (Unverified): Blogs, forums or retail feeds. Heavily down-weighted (0.25) by AI to prevent fake news manipulation."
      >
        <AlertTriangle className="w-3 h-3" />
        <span>Tier 3 (Unverified)</span>
      </span>
    );
  }
};

const NewsFeed = ({ ticker = 'AAPL' }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tierFilter, setTierFilter] = useState('ALL'); // ALL, TIER1, TIER1_2

  const loadNews = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.fetchSentiment(ticker, 14);
      if (res && res.data && res.data.headline_scores && res.data.headline_scores.length > 0) {
        const liveItems = res.data.headline_scores.map((h, idx) => {
          const maxProb = Math.max(h.positive || 0, h.negative || 0, h.neutral || 0);
          return {
            id: idx + 1,
            title: h.headline,
            source: h.source || 'Financial Media',
            source_tier: h.source_tier || 1,
            trust_label: h.trust_label || 'Tier 1: High Trust',
            tier_weight: h.tier_weight || 1.0,
            url: h.url || '',
            sentiment: (h.label || 'neutral').charAt(0).toUpperCase() + (h.label || 'neutral').slice(1),
            conf: Math.round(maxProb * 100),
          };
        });
        setItems(liveItems);
      } else {
        setItems([]);
      }
    } catch (err) {
      console.warn('Could not fetch live sentiment headlines:', err);
      setError('Unable to load headlines for ' + ticker);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNews();
  }, [ticker]);

  const filteredItems = items.filter((item) => {
    if (tierFilter === 'TIER1') return item.source_tier === 1;
    if (tierFilter === 'TIER1_2') return item.source_tier <= 2;
    return true;
  });

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl flex flex-col shadow-xl overflow-hidden h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex flex-wrap justify-between items-center bg-slate-800/30 gap-2">
        <div className="flex items-center space-x-2">
          <Newspaper className="w-4 h-4 text-emerald-400" />
          <h3 className="text-white font-semibold flex items-center space-x-2">
            <span>Verified Headlines Feed — {ticker}</span>
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </h3>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs text-slate-400 flex items-center">
            <span>FinBERT NLP ({filteredItems.length} articles)</span>
          </span>
          <button
            onClick={loadNews}
            disabled={loading}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Refresh Headlines"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Domain Reputation & Whitelist Filter Bar */}
      <div className="px-6 py-2.5 bg-slate-950/40 border-b border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 font-medium">Reputation Filter:</span>
          {[
            { id: 'ALL', label: 'All Sources' },
            { id: 'TIER1', label: 'Tier 1 Only (Verified)' },
            { id: 'TIER1_2', label: 'Tier 1 & 2' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setTierFilter(tab.id)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors ${
                tierFilter === tab.id
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="hidden md:flex items-center space-x-1.5 text-[11px] text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Fake News Protection: Tier 3 Down-weighted to 0.25</span>
        </div>
      </div>

      {/* Feed Content */}
      <div className="overflow-y-auto flex-1 p-4 space-y-3 custom-scrollbar">
        {loading && items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-3 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
            <p className="text-sm">Fetching and scoring live headlines via FinBERT...</p>
          </div>
        ) : filteredItems.length > 0 ? (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className={`p-4 rounded-lg bg-slate-800/50 border transition-colors group ${
                item.source_tier === 3
                  ? 'border-amber-500/30 hover:border-amber-500/60'
                  : 'border-slate-700/50 hover:border-slate-600'
              }`}
            >
              <div className="flex flex-wrap justify-between items-start gap-2 mb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold text-indigo-300">{item.source}</span>
                  {getTrustBadge(item.source_tier)}
                  <span className="text-slate-500 text-xs flex items-center">
                    <Clock className="w-3 h-3 mr-1" /> {item.time}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  {getSentimentBadge(item.sentiment, item.conf)}
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                      title="Open full verified article"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
              <p className="text-sm text-slate-200 leading-snug group-hover:text-white transition-colors">
                {item.title}
              </p>
              {item.source_tier === 3 && (
                <div className="mt-2 text-[10px] text-amber-400/80 flex items-center space-x-1">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  <span>Unverified source: AI algorithms down-weight this headline by 75% to prevent speculative manipulation.</span>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-48 p-6 text-center space-y-3">
            <Newspaper className="w-8 h-8 text-slate-500" />
            <div>
              <p className="text-sm font-semibold text-slate-300">
                No recent live headlines available for {ticker} under selected filter.
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Try switching the filter to "All Sources" or search major tickers like RELIANCE, TCS, IRFC, HDFCBANK, NVDA, or AAPL.
              </p>
            </div>
            <button
              onClick={loadNews}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition-colors border border-slate-700 cursor-pointer"
            >
              Retry Live Fetch
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsFeed;
