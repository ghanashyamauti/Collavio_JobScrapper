import React, { useEffect } from 'react';
import { X, RefreshCw, CheckCircle2, AlertCircle, Clock, Key, ShieldCheck } from 'lucide-react';

export default function SyncTelemetryDrawer({
  isOpen,
  onClose,
  syncStatus,
  onRefreshTelemetry,
  onTriggerSync,
}) {
  // Auto-poll telemetry every 3 seconds if collector is running
  useEffect(() => {
    let interval;
    if (isOpen && syncStatus?.is_running) {
      interval = setInterval(() => {
        onRefreshTelemetry();
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [isOpen, syncStatus?.is_running, onRefreshTelemetry]);

  if (!isOpen) return null;

  const runs = syncStatus?.recent_runs || [];
  const isRunning = syncStatus?.is_running;
  const activeCollector = syncStatus?.active_collector;

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900/20 backdrop-blur-[1px] transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white border-l border-neutral-200 shadow-xl flex flex-col justify-between text-xs">
          {/* Header */}
          <div className="p-5 border-b border-neutral-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  isRunning ? 'bg-amber-500 animate-pulse' : 'bg-emerald-600'
                }`}
              />
              <h2 className="font-bold text-sm text-[#111827] tracking-tight">
                Collector Telemetry & Sync Runs
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* Live Status Card */}
            <div className="p-4 rounded-lg border border-neutral-200 bg-[#F9F9F8]">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-neutral-900 text-xs">Ingestion Engine</span>
                <span
                  className={`font-mono text-[10px] px-2 py-0.5 rounded font-medium border ${
                    isRunning
                      ? 'bg-amber-50 text-amber-800 border-amber-200'
                      : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  }`}
                >
                  {isRunning ? 'RUNNING' : 'IDLE'}
                </span>
              </div>
              <p className="text-neutral-600 leading-relaxed text-[11px]">
                {isRunning
                  ? `Active Collector: "${activeCollector}". Normalizing incoming job streams and applying 3-tier deduplication.`
                  : 'All background pipelines are quiet. Built-in scheduler runs automatically every 6 hours.'}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => onTriggerSync('fast')}
                  disabled={isRunning}
                  className="bg-[#111827] text-white hover:bg-neutral-800 disabled:opacity-50 px-3 py-1.5 rounded font-medium text-xs transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3 h-3 ${isRunning ? 'animate-spin' : ''}`} />
                  <span>{isRunning ? 'Ingestion in progress' : 'Trigger Quick Sync'}</span>
                </button>
                <button
                  onClick={onRefreshTelemetry}
                  className="bg-white border border-neutral-200 text-neutral-700 hover:bg-neutral-50 px-2.5 py-1.5 rounded font-medium text-xs transition-colors"
                >
                  Refresh
                </button>
              </div>
            </div>

            {/* Optional Free-Tier APIs Status */}
            <div>
              <span className="font-semibold text-neutral-900 text-xs block mb-2 uppercase tracking-wider text-neutral-400">
                Optional Pre-Wired APIs
              </span>
              <div className="space-y-2">
                <div className="p-2.5 rounded border border-neutral-200 bg-white flex items-center justify-between">
                  <div>
                    <span className="font-medium text-neutral-900 block">Adzuna Global API</span>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      ADZUNA_APP_ID / KEY
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded">
                    Auto-Activates via .env
                  </span>
                </div>

                <div className="p-2.5 rounded border border-neutral-200 bg-white flex items-center justify-between">
                  <div>
                    <span className="font-medium text-neutral-900 block">Jooble REST API</span>
                    <span className="text-[10px] text-neutral-500 font-mono">JOOBLE_API_KEY</span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded">
                    Auto-Activates via .env
                  </span>
                </div>

                <div className="p-2.5 rounded border border-neutral-200 bg-white flex items-center justify-between">
                  <div>
                    <span className="font-medium text-neutral-900 block">JSearch (RapidAPI)</span>
                    <span className="text-[10px] text-neutral-500 font-mono">RAPIDAPI_JSEARCH_KEY</span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded">
                    Auto-Activates via .env
                  </span>
                </div>
              </div>
            </div>

            {/* Recent Scrape Runs Table */}
            <div>
              <span className="font-semibold text-neutral-900 text-xs block mb-2 uppercase tracking-wider text-neutral-400">
                Recent Ingestion Runs
              </span>
              <div className="border border-neutral-200 rounded-lg overflow-hidden">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="bg-neutral-50 border-b border-neutral-200 text-neutral-500 font-medium font-mono">
                      <th className="p-2">Collector</th>
                      <th className="p-2">Status</th>
                      <th className="p-2 text-right">Found</th>
                      <th className="p-2 text-right">New</th>
                      <th className="p-2 text-right">Merged</th>
                      <th className="p-2 text-right">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {runs.map((r) => (
                      <tr key={r.id} className="hover:bg-neutral-50/50">
                        <td className="p-2 font-medium text-neutral-900 capitalize">
                          {r.source}
                        </td>
                        <td className="p-2">
                          <span
                            className={`inline-block px-1.5 py-0.2 rounded font-mono text-[9px] uppercase font-semibold ${
                              r.status === 'success'
                                ? 'bg-emerald-50 text-emerald-700'
                                : r.status === 'running'
                                ? 'bg-amber-50 text-amber-700'
                                : 'bg-red-50 text-red-700'
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="p-2 text-right font-mono tabular-nums text-neutral-600">
                          {r.jobs_found}
                        </td>
                        <td className="p-2 text-right font-mono tabular-nums text-emerald-600 font-medium">
                          {r.new_jobs}
                        </td>
                        <td className="p-2 text-right font-mono tabular-nums text-neutral-500">
                          {r.duplicates_merged}
                        </td>
                        <td className="p-2 text-right font-mono text-neutral-400">
                          {formatDate(r.started_at)}
                        </td>
                      </tr>
                    ))}
                    {runs.length === 0 && (
                      <tr>
                        <td colSpan={6} className="p-4 text-center text-neutral-400 font-mono">
                          No ingestion runs logged yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-neutral-200 bg-neutral-50 text-neutral-500 text-[11px] flex items-center justify-between">
            <span>JobPulse Engine v1.0</span>
            <span className="font-mono">psycopg3 + FastAPI</span>
          </div>
        </div>
      </div>
    </div>
  );
}
