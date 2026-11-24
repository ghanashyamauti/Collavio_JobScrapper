import React, { useState, useEffect, useRef } from 'react';
import { Search, RefreshCw, ChevronDown, Sparkles, X, Database, Activity } from 'lucide-react';

export default function Header({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  onOpenTelemetry,
  onOpenLiveHarvest,
  onTriggerSync,
  isSyncing,
  trackedCount = 0,
  indiaOnly = false,
  onToggleIndia,
}) {
  const [toolsMenuOpen, setToolsMenuOpen] = useState(false);
  const searchInputRef = useRef(null);

  // Global keyboard shortcut: pressing '/' focuses search
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-neutral-200 shrink-0">
      <div className="h-14 px-3 sm:px-6 flex items-center justify-between gap-2 sm:gap-4">
        {/* Brand & Mode Switcher */}
        <div className="flex items-center gap-3 sm:gap-6 shrink-0">
          <div className="flex items-center gap-2">
            <img
              src="/collavio_favicon.svg"
              alt="Collavio Logo"
              className="w-6 h-6 sm:w-7 sm:h-7 object-contain"
            />
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm sm:text-base tracking-tight text-[#0F172A]">
                Collavio <span className="text-[#F26825]">Jobs</span>
              </span>
              <span className="hidden lg:inline-block text-[10px] font-mono uppercase bg-orange-50 text-[#F26825] px-1.5 py-0.5 rounded tracking-wider border border-orange-200 font-semibold">
                Live
              </span>
            </div>
          </div>

          {/* View Switcher Tabs */}
          <nav className="flex items-center space-x-1 border-l border-neutral-200 pl-2.5 sm:pl-4">
            <button
              onClick={() => setActiveTab('discover')}
              className={`px-2.5 py-1 sm:px-3 sm:py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'discover'
                  ? 'bg-[#0F172A] text-white shadow-sm'
                  : 'text-neutral-600 hover:text-[#0F172A] hover:bg-neutral-100'
              }`}
            >
              Feed
            </button>
            <button
              onClick={() => setActiveTab('tracker')}
              className={`px-2.5 py-1 sm:px-3 sm:py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'tracker'
                  ? 'bg-[#0F172A] text-white shadow-sm'
                  : 'text-neutral-600 hover:text-[#0F172A] hover:bg-neutral-100'
              }`}
            >
              <span>Tracker</span>
              {trackedCount > 0 && (
                <span
                  className={`tabular-nums text-[10px] px-1.5 py-0.2 rounded-full font-mono font-medium ${
                    activeTab === 'tracker'
                      ? 'bg-[#F26825] text-white'
                      : 'bg-orange-100 text-[#F26825]'
                  }`}
                >
                  {trackedCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Desktop Search Bar (hidden on mobile, visible md+) */}
        <div className="flex-1 max-w-xl mx-2 sm:mx-4 hidden md:flex items-center">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search roles, companies, or cities worldwide..."
              className="w-full bg-[#F8FAFC] border border-neutral-200 rounded-lg pl-8 pr-12 py-1.5 text-xs text-[#0F172A] placeholder-neutral-400 focus:outline-none focus:border-[#F26825] focus:bg-white transition-colors"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    searchInputRef.current?.focus();
                  }}
                  className="p-0.5 rounded hover:bg-neutral-200 text-neutral-400 hover:text-neutral-700 transition-colors"
                  title="Clear search"
                >
                  <X className="w-3 h-3" />
                </button>
              ) : (
                <kbd className="text-[10px] font-mono text-neutral-400 bg-neutral-200 px-1 py-0.5 rounded border border-neutral-300">
                  /
                </kbd>
              )}
            </div>
          </div>
        </div>

        {/* Right Utility Cluster: Consolidated Discreet Data & Ingestion Tools */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="relative">
            <button
              onClick={() => setToolsMenuOpen(!toolsMenuOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-neutral-700 bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 rounded-lg transition-colors cursor-pointer"
              title="Data & Ingestion Tools"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isSyncing ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
                }`}
              />
              <span className="hidden sm:inline font-semibold text-[11px] text-neutral-800">
                {isSyncing ? 'Syncing...' : 'Data Tools'}
              </span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {/* Ingestion & Diagnostics Dropdown */}
            {toolsMenuOpen && (
              <div
                className="absolute right-0 mt-1.5 w-64 bg-white border border-neutral-200 rounded-xl shadow-xl py-1.5 z-50 text-xs"
                onMouseLeave={() => setToolsMenuOpen(false)}
              >
                <div className="px-3 py-1.5 text-[10px] font-semibold text-neutral-400 uppercase tracking-wider border-b border-neutral-100 flex items-center justify-between">
                  <span>Data Controls</span>
                  <span className="font-mono text-emerald-600 font-bold lowercase">auto-sync active</span>
                </div>

                <button
                  onClick={() => {
                    setToolsMenuOpen(false);
                    onTriggerSync('fast');
                  }}
                  disabled={isSyncing}
                  className="w-full text-left px-3 py-2 hover:bg-orange-50/60 flex items-center gap-2.5 transition-colors disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-[#F26825] shrink-0 ${isSyncing ? 'animate-spin' : ''}`} />
                  <div>
                    <div className="font-semibold text-[#0F172A] text-xs">Run Quick Sync</div>
                    <div className="text-[10px] text-neutral-400">Direct ATS & lightweight feeds (~10s)</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setToolsMenuOpen(false);
                    onTriggerSync('full');
                  }}
                  disabled={isSyncing}
                  className="w-full text-left px-3 py-2 hover:bg-orange-50/60 flex items-center gap-2.5 transition-colors disabled:opacity-50 cursor-pointer"
                >
                  <Database className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <div>
                    <div className="font-semibold text-[#0F172A] text-xs">Run Deep Sync</div>
                    <div className="text-[10px] text-neutral-400">Enterprise Workday + JobSpy boards (~60s)</div>
                  </div>
                </button>

                <div className="border-t border-neutral-100 my-1" />

                <button
                  onClick={() => {
                    setToolsMenuOpen(false);
                    onOpenLiveHarvest();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-orange-50/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  <div>
                    <div className="font-semibold text-[#0F172A] text-xs">Live Harvester</div>
                    <div className="text-[10px] text-neutral-400">Scrape custom employer boards on demand</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setToolsMenuOpen(false);
                    onOpenTelemetry();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-orange-50/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Activity className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-semibold text-[#0F172A] text-xs">Telemetry & Logs</div>
                    <div className="text-[10px] text-neutral-400">Inspect ingestion metrics & real-time logs</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Search Row (visible on screens < md) */}
      <div className="px-3 py-2 md:hidden flex items-center gap-2 border-t border-neutral-100 bg-[#FAFAF9]">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles, companies, or cities..."
            className="w-full bg-white border border-neutral-200 rounded-lg pl-8 pr-8 py-1.5 text-xs text-[#0F172A] placeholder-neutral-400 focus:outline-none focus:border-[#F26825]"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-neutral-400 hover:text-neutral-700"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
