import React, { useState, useEffect, useRef } from 'react';
import { Search, SlidersHorizontal, RefreshCw, Activity, ChevronDown, CheckCircle2, Bookmark } from 'lucide-react';

export default function Header({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  onOpenTelemetry,
  onTriggerSync,
  isSyncing,
  trackedCount = 0,
}) {
  const [syncDropdownOpen, setSyncDropdownOpen] = useState(false);
  const searchInputRef = useRef(null);

  // Global keyboard shortcut: pressing '/' focuses the search input
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
    <header className="sticky top-0 z-30 h-14 bg-white border-b border-neutral-200 px-4 sm:px-6 flex items-center justify-between">
      {/* Brand & Mode Switcher */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-[#111827] flex items-center justify-center text-white text-xs font-bold tracking-tight">
            P
          </div>
          <span className="font-semibold text-base tracking-tight text-[#111827]">JobPulse</span>
          <span className="hidden sm:inline-block text-[10px] font-mono uppercase bg-neutral-100 text-neutral-600 px-1.5 py-0.5 rounded tracking-wider border border-neutral-200">
            Unified
          </span>
        </div>

        {/* View Switcher Tabs */}
        <nav className="flex items-center space-x-1 border-l border-neutral-200 pl-6">
          <button
            onClick={() => setActiveTab('discover')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === 'discover'
                ? 'bg-[#111827] text-white'
                : 'text-neutral-600 hover:text-[#111827] hover:bg-neutral-100'
            }`}
          >
            Discover Feed
          </button>
          <button
            onClick={() => setActiveTab('tracker')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'tracker'
                ? 'bg-[#111827] text-white'
                : 'text-neutral-600 hover:text-[#111827] hover:bg-neutral-100'
            }`}
          >
            <span>My Tracker</span>
            {trackedCount > 0 && (
              <span
                className={`tabular-nums text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  activeTab === 'tracker'
                    ? 'bg-neutral-700 text-white'
                    : 'bg-neutral-200 text-neutral-800'
                }`}
              >
                {trackedCount}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Global Command Search */}
      <div className="flex-1 max-w-md mx-4 hidden md:block">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles, keywords, or skills..."
            className="w-full bg-[#F7F7F5] border border-neutral-200 rounded-lg pl-8 pr-10 py-1.5 text-xs text-[#111827] placeholder-neutral-400 focus:outline-none focus:border-neutral-400 focus:bg-white transition-colors"
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
            <kbd className="text-[10px] font-mono text-neutral-400 bg-neutral-200 px-1 py-0.5 rounded border border-neutral-300">
              /
            </kbd>
          </div>
        </div>
      </div>

      {/* Right Utility Cluster: Telemetry & Ingestion Actions */}
      <div className="flex items-center gap-2">
        {/* Sync Telemetry Drawer Trigger */}
        <button
          onClick={onOpenTelemetry}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
          title="Open Sync Telemetry & Log Drawer"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isSyncing ? 'bg-amber-500 animate-pulse' : 'bg-emerald-600'
            }`}
          />
          <span className="hidden sm:inline">Telemetry</span>
        </button>

        {/* Sync Action Cluster */}
        <div className="relative">
          <div className="inline-flex rounded-lg border border-neutral-200 shadow-none">
            <button
              onClick={() => onTriggerSync('fast')}
              disabled={isSyncing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#111827] bg-white hover:bg-neutral-50 rounded-l-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-amber-600' : 'text-neutral-500'}`} />
              <span>{isSyncing ? 'Syncing...' : 'Quick Sync'}</span>
            </button>
            <button
              onClick={() => setSyncDropdownOpen(!syncDropdownOpen)}
              disabled={isSyncing}
              className="px-1.5 py-1.5 text-neutral-500 bg-white hover:bg-neutral-50 rounded-r-lg border-l border-neutral-200 transition-colors disabled:opacity-50"
            >
              <ChevronDown className="w-3 h-3" />
            </button>
          </div>

          {/* Sync Mode Dropdown Menu */}
          {syncDropdownOpen && (
            <div
              className="absolute right-0 mt-1 w-64 bg-white border border-neutral-200 rounded-lg shadow-lg py-1 z-40 text-xs"
              onMouseLeave={() => setSyncDropdownOpen(false)}
            >
              <button
                onClick={() => {
                  setSyncDropdownOpen(false);
                  onTriggerSync('fast');
                }}
                className="w-full text-left px-3 py-2 hover:bg-neutral-50 flex flex-col"
              >
                <span className="font-medium text-[#111827]">Quick Sync (APIs & Direct ATS)</span>
                <span className="text-[11px] text-neutral-500">Greenhouse, Lever, Ashby, Himalayas, Muse (~10s)</span>
              </button>
              <div className="border-t border-neutral-100 my-1" />
              <button
                onClick={() => {
                  setSyncDropdownOpen(false);
                  onTriggerSync('full');
                }}
                className="w-full text-left px-3 py-2 hover:bg-neutral-50 flex flex-col"
              >
                <span className="font-medium text-[#111827]">Full Deep Sync (Include JobSpy)</span>
                <span className="text-[11px] text-neutral-500">LinkedIn, Naukri, Indeed, Glassdoor + ATS (~60s)</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
