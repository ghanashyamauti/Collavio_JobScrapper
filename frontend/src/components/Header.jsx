import React, { useState, useEffect, useRef } from 'react';
import { Search, RefreshCw, ChevronDown, Bookmark, Sparkles } from 'lucide-react';

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
  const [syncDropdownOpen, setSyncDropdownOpen] = useState(false);
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
    <header className="sticky top-0 z-30 h-14 bg-white border-b border-neutral-200 px-4 sm:px-6 flex items-center justify-between">
      {/* Brand & Mode Switcher */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <img
            src="/collavio_favicon.svg"
            alt="Collavio Logo"
            className="w-7 h-7 object-contain"
          />
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-tight text-[#0F172A]">
              Collavio <span className="text-[#F26825]">Jobs</span>
            </span>
            <span className="hidden sm:inline-block text-[10px] font-mono uppercase bg-orange-50 text-[#F26825] px-1.5 py-0.5 rounded tracking-wider border border-orange-200 font-semibold">
              Readiness
            </span>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <nav className="flex items-center space-x-1 border-l border-neutral-200 pl-6">
          <button
            onClick={() => setActiveTab('discover')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === 'discover'
                ? 'bg-[#0F172A] text-white shadow-sm'
                : 'text-neutral-600 hover:text-[#0F172A] hover:bg-neutral-100'
            }`}
          >
            Discover Feed
          </button>
          <button
            onClick={() => setActiveTab('tracker')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'tracker'
                ? 'bg-[#0F172A] text-white shadow-sm'
                : 'text-neutral-600 hover:text-[#0F172A] hover:bg-neutral-100'
            }`}
          >
            <span>My Tracker</span>
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

      {/* Global Command Search & Quick India Switcher */}
      <div className="flex-1 max-w-lg mx-4 hidden md:flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles, companies, or cities worldwide (e.g. Software Developer, Pune, Stripe, Tokyo)..."
            className="w-full bg-[#F8FAFC] border border-neutral-200 rounded-lg pl-8 pr-10 py-1.5 text-xs text-[#0F172A] placeholder-neutral-400 focus:outline-none focus:border-[#F26825] focus:bg-white transition-colors"
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
            <kbd className="text-[10px] font-mono text-neutral-400 bg-neutral-200 px-1 py-0.5 rounded border border-neutral-300">
              /
            </kbd>
          </div>
        </div>

        {/* India Roles Quick Toggle Button */}
        <button
          type="button"
          onClick={onToggleIndia}
          title="Toggle India Roles"
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-xs font-semibold shrink-0 transition-all cursor-pointer ${
            indiaOnly
              ? 'bg-orange-500 text-white border-orange-500 shadow-sm'
              : 'bg-white text-neutral-700 border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
          }`}
        >
          <span>🇮🇳</span>
          <span>India</span>
        </button>
      </div>

      {/* Right Utility Cluster: Live Harvest, Telemetry & Ingestion Actions */}
      <div className="flex items-center gap-2">
        {/* Live Dynamic Harvest Button */}
        <button
          onClick={onOpenLiveHarvest}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#F26825] bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100/70 transition-colors shadow-sm"
          title="Open Custom Dynamic Job Harvester"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#F26825]" />
          <span className="hidden sm:inline">Live Harvest</span>
        </button>

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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#F26825] hover:bg-[#D95B1E] rounded-l-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-white' : 'text-white'}`} />
              <span>{isSyncing ? 'Syncing...' : 'Quick Sync'}</span>
            </button>
            <button
              onClick={() => setSyncDropdownOpen(!syncDropdownOpen)}
              disabled={isSyncing}
              className="px-1.5 py-1.5 text-white bg-[#F26825] hover:bg-[#D95B1E] rounded-r-lg border-l border-orange-400 transition-colors disabled:opacity-50"
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
                className="w-full text-left px-3 py-2 hover:bg-orange-50/50 flex flex-col"
              >
                <span className="font-medium text-[#0F172A]">Quick Sync (APIs & Direct ATS)</span>
                <span className="text-[11px] text-neutral-500">Greenhouse, Lever, Ashby, Himalayas, Remotive (~10s)</span>
              </button>
              <div className="border-t border-neutral-100 my-1" />
              <button
                onClick={() => {
                  setSyncDropdownOpen(false);
                  onTriggerSync('full');
                }}
                className="w-full text-left px-3 py-2 hover:bg-orange-50/50 flex flex-col"
              >
                <span className="font-medium text-[#0F172A]">Full Deep Sync (Include JobSpy)</span>
                <span className="text-[11px] text-neutral-500">LinkedIn, Naukri, Indeed, Glassdoor + ATS (~60s)</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
