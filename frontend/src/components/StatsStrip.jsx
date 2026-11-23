import React from 'react';
import { Database, Layers, Globe, Bookmark, Clock } from 'lucide-react';

export default function StatsStrip({ kpis, isLoading, indiaOnly, onToggleIndia }) {
  const total = kpis?.total_jobs ?? 0;
  const active = kpis?.active_jobs ?? total;
  const india = kpis?.india_jobs ?? 0;
  const activeSources = kpis?.active_sources ?? 0;
  const remote = kpis?.remote_jobs ?? 0;
  const tracked = (kpis?.saved_jobs ?? 0) + (kpis?.applied_jobs ?? 0);
  const lastSync = kpis?.last_synced_at;

  const formatLastSync = (isoStr) => {
    if (!isoStr) return 'Not yet synced';
    try {
      const date = new Date(isoStr);
      const diffMinutes = Math.floor((new Date() - date) / 60000);
      if (diffMinutes < 1) return 'Just now';
      if (diffMinutes < 60) return `${diffMinutes}m ago`;
      const diffHours = Math.floor(diffMinutes / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return 'Recently';
    }
  };

  return (
    <div className="bg-white border-b border-neutral-200 px-6 py-2.5 flex items-center justify-between text-xs overflow-x-auto gap-6">
      <div className="flex items-center gap-6">
        {/* Total & Active Jobs */}
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-neutral-500">Active Live:</span>
          <span className="font-mono font-semibold text-emerald-700 tabular-nums">
            {isLoading ? '...' : active.toLocaleString()} roles
          </span>
        </div>

        {/* India Roles Clickable Pill */}
        <button
          type="button"
          onClick={onToggleIndia}
          title="Click to filter India roles"
          className={`flex items-center gap-1.5 px-2 py-0.5 rounded border transition-all cursor-pointer ${
            indiaOnly
              ? 'bg-orange-50 border-[#F26825] text-[#F26825] font-semibold'
              : 'border-neutral-200 hover:border-neutral-300 text-neutral-700 bg-white'
          }`}
        >
          <span>🇮🇳</span>
          <span className="text-neutral-500">India:</span>
          <span className="font-mono font-semibold text-[#F26825] tabular-nums">
            {isLoading ? '...' : india.toLocaleString()}
          </span>
        </button>

        {/* Active Ingestion Sources */}
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-neutral-500">Sources:</span>
          <span className="font-mono font-medium text-[#111827] tabular-nums">
            {isLoading ? '...' : activeSources} boards
          </span>
        </div>

        {/* Remote Openings */}
        <div className="flex items-center gap-2">
          <Globe className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-neutral-500">Remote:</span>
          <span className="font-mono font-medium text-[#111827] tabular-nums">
            {isLoading ? '...' : remote.toLocaleString()} roles
          </span>
        </div>

        {/* Tracked Applications */}
        <div className="flex items-center gap-2">
          <Bookmark className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-neutral-500">Tracked:</span>
          <span className="font-mono font-medium text-[#111827] tabular-nums">
            {isLoading ? '...' : tracked} saved/applied
          </span>
        </div>
      </div>

      {/* Last Synced */}
      <div className="flex items-center gap-1.5 text-neutral-500 font-mono text-[11px] shrink-0">
        <Clock className="w-3 h-3 text-neutral-400" />
        <span>Last synced: {formatLastSync(lastSync)}</span>
      </div>
    </div>
  );
}
