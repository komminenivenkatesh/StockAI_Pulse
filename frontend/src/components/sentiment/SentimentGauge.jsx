import React, { useState, useEffect } from 'react';
import { RefreshCw, Activity, Brain } from 'lucide-react';
import { api } from '../../api/client';

const SentimentGauge = ({ ticker = 'AAPL', score: initialScore = null }) => {
  const [currentScore, setCurrentScore] = useState(initialScore !== null ? initialScore : 0.42);
  const [signal, setSignal] = useState('Bullish');
  const [probs, setProbs] = useState({ pos: 68.5, neu: 20.0, neg: 11.5 });
  const [loading, setLoading] = useState(false);

  const loadSentiment = async () => {
    setLoading(true);
    try {
      const res = await api.fetchSentiment(ticker, 7);
      if (res && res.data) {
        const s = Number(res.data.current_score || 0);
        setCurrentScore(s);
        setSignal(res.data.signal || (s >= 0.15 ? 'Bullish' : s <= -0.15 ? 'Bearish' : 'Neutral'));

        if (res.data.headline_scores && res.data.headline_scores.length > 0) {
          const avgPos = res.data.headline_scores.reduce((acc, h) => acc + (h.positive || 0), 0) / res.data.headline_scores.length;
          const avgNeu = res.data.headline_scores.reduce((acc, h) => acc + (h.neutral || 0), 0) / res.data.headline_scores.length;
          const avgNeg = res.data.headline_scores.reduce((acc, h) => acc + (h.negative || 0), 0) / res.data.headline_scores.length;
          setProbs({
            pos: Math.round(avgPos * 1000) / 10,
            neu: Math.round(avgNeu * 1000) / 10,
            neg: Math.round(avgNeg * 1000) / 10,
          });
        } else {
          // Neutral baseline if no news
          setProbs({ pos: 33.3, neu: 33.4, neg: 33.3 });
        }
      }
    } catch (err) {
      console.warn('Could not fetch sentiment score:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialScore === null) {
      loadSentiment();
    }
  }, [ticker, initialScore]);

  const score = currentScore;
  const normalizedScore = (score + 1) / 2; // 0 to 1
  const rotation = Math.max(-90, Math.min(90, normalizedScore * 180 - 90)); // -90 to 90 degrees

  let sentimentStatus = signal;
  let colorClass = 'text-slate-400';
  let bgClass = 'bg-slate-500';

  if (sentimentStatus.toLowerCase() === 'bullish' || score >= 0.15) {
    sentimentStatus = 'Bullish';
    colorClass = 'text-emerald-400';
    bgClass = 'bg-emerald-500';
  } else if (sentimentStatus.toLowerCase() === 'bearish' || score <= -0.15) {
    sentimentStatus = 'Bearish';
    colorClass = 'text-red-400';
    bgClass = 'bg-red-500';
  } else {
    sentimentStatus = 'Neutral';
    colorClass = 'text-amber-400';
    bgClass = 'bg-amber-500';
  }

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 flex flex-col items-center justify-between shadow-xl h-full">
      <div className="w-full flex justify-between items-center mb-4">
        <div className="flex items-center space-x-2">
          <Brain className="w-4 h-4 text-indigo-400" />
          <h3 className="text-slate-300 text-xs font-semibold uppercase tracking-wider">
            FinBERT Compound • {ticker}
          </h3>
        </div>
        <button
          onClick={loadSentiment}
          disabled={loading}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Refresh Sentiment Score"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
        </button>
      </div>

      <div className="relative w-48 h-24 overflow-hidden my-4">
        {/* Gauge Background */}
        <div className="absolute w-48 h-48 rounded-full border-[20px] border-slate-800" />

        {/* Color Gradient Arc (Simulated with segments) */}
        <div className="absolute w-48 h-48 rounded-full border-[20px] border-transparent border-t-red-500 border-l-red-500 rotate-45 opacity-50" />
        <div className="absolute w-48 h-48 rounded-full border-[20px] border-transparent border-t-emerald-500 border-r-emerald-500 -rotate-45 opacity-50" />

        {/* Needle */}
        <div
          className="absolute bottom-0 left-1/2 w-1 h-20 bg-white origin-bottom rounded-t-full shadow-[0_0_10px_rgba(255,255,255,0.5)] transition-transform duration-1000 ease-out"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        />
        {/* Needle Base */}
        <div className="absolute bottom-0 left-1/2 w-6 h-6 bg-white rounded-full -translate-x-1/2 translate-y-1/2 shadow-lg" />
      </div>

      <div className="text-center my-2">
        <div className={`text-3xl font-bold ${colorClass} mb-1 font-mono`}>
          {score > 0 ? '+' : ''}{score.toFixed(2)}
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest ${bgClass} text-white inline-block`}>
          {sentimentStatus}
        </div>
      </div>

      <div className="w-full space-y-3 mt-4 pt-4 border-t border-slate-800">
        <div className="flex flex-col space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-emerald-400 font-medium">P(Positive)</span>
            <span className="text-slate-300 font-mono">{probs.pos.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${probs.pos}%` }} />
          </div>
        </div>

        <div className="flex flex-col space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400 font-medium">P(Neutral)</span>
            <span className="text-slate-300 font-mono">{probs.neu.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-slate-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${probs.neu}%` }} />
          </div>
        </div>

        <div className="flex flex-col space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-red-400 font-medium">P(Negative)</span>
            <span className="text-slate-300 font-mono">{probs.neg.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-red-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${probs.neg}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SentimentGauge;
