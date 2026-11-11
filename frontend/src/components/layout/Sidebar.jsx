import React from 'react';
import { LineChart, BrainCircuit, Lightbulb, ActivitySquare, ShieldAlert } from 'lucide-react';

const tabs = [
  { id: 'terminal', label: 'Terminal', icon: LineChart, desc: 'Price Chart & Indicators' },
  { id: 'sentiment', label: 'Sentiment', icon: BrainCircuit, desc: 'FinBERT NLP Analysis' },
  { id: 'forecast', label: 'ML Forecast', icon: Lightbulb, desc: 'XGBoost & Bi-LSTM' },
  { id: 'backtest', label: 'Backtesting', icon: ActivitySquare, desc: 'Strategy Simulator' },
  { id: 'risk', label: 'Risk Analytics', icon: ShieldAlert, desc: 'Portfolio Metrics' }
];

const Sidebar = ({ activeTab, setActiveTab }) => {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-700 flex flex-col shrink-0">
      <div className="p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Modules</p>
        <nav className="space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                  isActive 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? 'text-emerald-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                <div className="flex flex-col items-start text-left">
                  <span className="font-medium text-sm">{tab.label}</span>
                  <span className={`text-[10px] ${isActive ? 'text-emerald-500/70' : 'text-slate-600'}`}>{tab.desc}</span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>
      
      <div className="mt-auto p-4 border-t border-slate-800">
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400">System Status</span>
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse"></span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Data Feed</span>
              <span className="text-emerald-400 font-medium">Connected</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">ML Engine</span>
              <span className="text-emerald-400 font-medium">Online</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
