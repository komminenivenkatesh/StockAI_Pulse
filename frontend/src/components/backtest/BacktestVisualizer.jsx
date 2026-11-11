import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import { TrendingUp, Award, Activity, BarChart2, Layers } from 'lucide-react';

const MetricCard = ({ title, value, positive, subtitle }) => (
  <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3 flex flex-col justify-between">
    <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">{title}</span>
    <div className="flex items-baseline space-x-1 my-1">
      <span
        className={`text-lg font-bold font-mono ${
          positive === undefined
            ? 'text-white'
            : positive
            ? 'text-emerald-400'
            : 'text-red-400'
        }`}
      >
        {value}
      </span>
    </div>
    {subtitle && <span className="text-[10px] text-slate-500">{subtitle}</span>}
  </div>
);

const BacktestVisualizer = ({ data, loading }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  const metrics = data?.metrics || {};
  const equityCurve = data?.equity_curve || [];
  const trades = data?.trades || [];
  const ticker = data?.ticker || '';
  const isINR = ticker.toUpperCase().endsWith('.NS') || ticker.toUpperCase().endsWith('.BO');
  const cur = isINR ? '₹' : '$';

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
      },
    });

    chartRef.current = chart;

    const strategySeries = chart.addLineSeries({
      color: '#10b981',
      lineWidth: 2,
      title: 'Strategy',
    });

    const benchmarkSeries = chart.addLineSeries({
      color: '#64748b',
      lineWidth: 2,
      lineStyle: 2,
      title: 'Buy & Hold',
    });

    if (equityCurve.length > 0) {
      const sData = equityCurve.map((pt) => ({
        time: pt.timestamp.split('T')[0],
        value: Number(pt.equity),
      }));

      const bData = equityCurve.map((pt) => ({
        time: pt.timestamp.split('T')[0],
        value: Number(pt.benchmark),
      }));

      strategySeries.setData(sData);
      benchmarkSeries.setData(bData);
      chart.timeScale().fitContent();
    } else {
      // Default demo equity curve
      const data1 = [];
      const data2 = [];
      let val1 = 10000;
      let val2 = 10000;
      const now = new Date();

      for (let i = 0; i < 100; i++) {
        const time = new Date(now.getTime() - (100 - i) * 24 * 60 * 60 * 1000)
          .toISOString()
          .split('T')[0];
        val1 = val1 * (1 + (Math.random() - 0.46) * 0.04);
        val2 = val2 * (1 + (Math.random() - 0.5) * 0.035);
        data1.push({ time, value: Math.round(val1) });
        data2.push({ time, value: Math.round(val2) });
      }

      strategySeries.setData(data1);
      benchmarkSeries.setData(data2);
      chart.timeScale().fitContent();
    }

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [equityCurve]);

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl flex flex-col shadow-xl h-full overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30">
        <div className="flex items-center space-x-3">
          <Layers className="w-5 h-5 text-indigo-400" />
          <h3 className="text-white font-semibold">
            {data?.ticker ? `${data.ticker} • ` : ''}Equity Curve: Strategy vs Benchmark
          </h3>
        </div>
        <div className="flex space-x-4 text-xs">
          <div className="flex items-center">
            <span className="w-3 h-3 bg-emerald-500 rounded-sm mr-2"></span>
            <span className="text-slate-300">Strategy</span>
          </div>
          <div className="flex items-center">
            <span className="w-3 h-3 bg-slate-500 rounded-sm mr-2 border border-dashed border-slate-400"></span>
            <span className="text-slate-300">Buy & Hold Benchmark</span>
          </div>
        </div>
      </div>

      {/* Metrics Summary Strip */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4 bg-slate-900/60 border-b border-slate-800">
          <MetricCard
            title="Total ROI"
            value={`${((metrics.total_roi || 0) * 100).toFixed(2)}%`}
            positive={(metrics.total_roi || 0) >= 0}
            subtitle="Strategy return"
          />
          <MetricCard
            title="Win Rate"
            value={`${((metrics.win_rate || 0) * 100).toFixed(1)}%`}
            positive={(metrics.win_rate || 0) >= 0.5}
            subtitle={`${metrics.winning_trades || 0}W / ${metrics.losing_trades || 0}L`}
          />
          <MetricCard
            title="Sharpe Ratio"
            value={(metrics.sharpe_ratio || 0).toFixed(2)}
            positive={(metrics.sharpe_ratio || 0) >= 1.0}
            subtitle="Risk-adjusted return"
          />
          <MetricCard
            title="Max Drawdown"
            value={`${((metrics.max_drawdown || 0) * 100).toFixed(2)}%`}
            positive={false}
            subtitle="Peak to trough drop"
          />
          <MetricCard
            title="Total Trades"
            value={metrics.total_trades || 0}
            subtitle={`Profit Factor: ${(metrics.profit_factor || 0).toFixed(2)}`}
          />
        </div>
      )}

      {/* Equity Curve Chart */}
      <div className="h-64 p-2 relative">
        <div ref={chartContainerRef} className="absolute inset-2" />
      </div>

      {/* Executed Trades Table */}
      <div className="flex-1 flex flex-col border-t border-slate-700 min-h-0">
        <div className="p-3 bg-slate-800/50 border-b border-slate-700 flex justify-between items-center">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Recent Executed Trades ({trades.length})
          </h4>
          {trades.length > 0 && (
            <span className="text-[11px] text-slate-500">
              Showing all trade entries and exits
            </span>
          )}
        </div>

        <div className="flex-1 overflow-auto custom-scrollbar p-0">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs text-slate-500 bg-slate-900 sticky top-0">
              <tr>
                <th className="px-4 py-3 font-medium">Side</th>
                <th className="px-4 py-3 font-medium">Entry Time</th>
                <th className="px-4 py-3 font-medium">Exit Time</th>
                <th className="px-4 py-3 font-medium text-right">Entry ({cur})</th>
                <th className="px-4 py-3 font-medium text-right">Exit ({cur})</th>
                <th className="px-4 py-3 font-medium text-right">PnL ({cur})</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {trades.length > 0 ? (
                trades.map((t, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-4 py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          t.side === 'BUY'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {t.side}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-400">
                      {t.entry_time?.split('T')[0] || t.entry_time}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-400">
                      {t.exit_time?.split('T')[0] || t.exit_time}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {cur}{Number(t.entry_price || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {cur}{Number(t.exit_price || 0).toFixed(2)}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right font-mono font-medium ${
                        Number(t.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {Number(t.pnl || 0) >= 0 ? '+' : ''}{cur}{Number(t.pnl || 0).toFixed(2)}
                      <span className="text-xs opacity-70 ml-1">
                        ({Number(t.return_pct || 0) >= 0 ? '+' : ''}
                        {(Number(t.return_pct || 0) * 100).toFixed(2)}%)
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500 text-xs">
                    {loading
                      ? 'Simulating historical trades across data...'
                      : 'Click "Run Backtest" to simulate this strategy over historical data.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BacktestVisualizer;
