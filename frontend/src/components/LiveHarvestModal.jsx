import React, { useState } from 'react';
import { X, Sparkles, Search, MapPin, Globe, RefreshCw, Check } from 'lucide-react';

const SUGGESTED_QUERIES = [
  'Software Developer',
  'Software Engineer',
  'Full Stack Developer',
  'Backend Developer',
  'Frontend Developer',
  'DevOps Engineer',
  'Data Scientist',
  'Product Manager',
];

const SUGGESTED_LOCATIONS = [
  'Pune',
  'Mumbai',
  'Bengaluru',
  'Hyderabad',
  'Delhi NCR',
  'Remote',
  'London',
  'New York',
  'San Francisco',
  'Berlin',
  'Singapore',
  'Tokyo',
];

export default function LiveHarvestModal({
  isOpen,
  onClose,
  onStartHarvest,
  isSyncing,
}) {
  const [queryInput, setQueryInput] = useState('');
  const [selectedQueries, setSelectedQueries] = useState(['Software Engineer']);
  const [locationInput, setLocationInput] = useState('');
  const [selectedLocations, setSelectedLocations] = useState(['Bengaluru', 'Remote']);
  const [country, setCountry] = useState('India');
  const [selectedSources, setSelectedSources] = useState(['linkedin', 'naukri', 'indeed', 'greenhouse', 'public_feeds']);

  if (!isOpen) return null;

  const handleAddQuery = (q) => {
    const val = q.trim();
    if (val && !selectedQueries.includes(val)) {
      setSelectedQueries([...selectedQueries, val]);
      setQueryInput('');
    }
  };

  const handleRemoveQuery = (q) => {
    setSelectedQueries(selectedQueries.filter((item) => item !== q));
  };

  const handleAddLocation = (loc) => {
    const val = loc.trim();
    if (val && !selectedLocations.includes(val)) {
      setSelectedLocations([...selectedLocations, val]);
      setLocationInput('');
    }
  };

  const handleRemoveLocation = (loc) => {
    setSelectedLocations(selectedLocations.filter((item) => item !== loc));
  };

  const toggleSource = (src) => {
    if (selectedSources.includes(src)) {
      if (selectedSources.length > 1) {
        setSelectedSources(selectedSources.filter((s) => s !== src));
      }
    } else {
      setSelectedSources([...selectedSources, src]);
    }
  };

  const handleRun = () => {
    onStartHarvest({
      mode: 'full',
      queries: selectedQueries.length > 0 ? selectedQueries : ['Software Engineer'],
      locations: selectedLocations.length > 0 ? selectedLocations : ['India', 'Remote'],
      country,
      sources: selectedSources,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-neutral-900/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="min-h-full flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl max-w-lg w-full border border-neutral-200 shadow-2xl p-6 text-xs text-[#0F172A] space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-neutral-100">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-orange-50 border border-orange-200 flex items-center justify-center text-[#F26825]">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-neutral-900">Live Dynamic Job Harvest</h3>
                <p className="text-[11px] text-neutral-500">
                  Search live career boards in real-time with custom roles & locations
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-700 p-1 rounded-md hover:bg-neutral-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Role / Keywords */}
          <div className="space-y-2">
            <label className="font-semibold text-neutral-800 block text-xs">
              Target Roles / Keywords
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddQuery(queryInput);
                    }
                  }}
                  placeholder="Type role title & press Enter (e.g. Golang Developer)..."
                  className="w-full bg-[#F8FAFC] border border-neutral-200 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-[#F26825] focus:bg-white"
                />
              </div>
              <button
                type="button"
                onClick={() => handleAddQuery(queryInput)}
                className="px-3 py-1.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-medium rounded-lg text-xs"
              >
                Add
              </button>
            </div>

            {/* Active Query Badges */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {selectedQueries.map((q) => (
                <span
                  key={q}
                  className="inline-flex items-center gap-1 bg-orange-50 border border-orange-200 text-[#F26825] px-2 py-0.5 rounded-md font-medium text-[11px]"
                >
                  <span>{q}</span>
                  <button
                    onClick={() => handleRemoveQuery(q)}
                    className="hover:text-red-600 p-0.5"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ))}
            </div>

            {/* Suggestions */}
            <div className="flex flex-wrap items-center gap-1 text-[11px] text-neutral-400 pt-1">
              <span className="text-neutral-500">Popular:</span>
              {SUGGESTED_QUERIES.slice(0, 5).map((sq) => (
                <button
                  key={sq}
                  type="button"
                  onClick={() => handleAddQuery(sq)}
                  className="px-1.5 py-0.5 rounded bg-neutral-100 hover:bg-neutral-200 text-neutral-600 text-[10px]"
                >
                  + {sq}
                </button>
              ))}
            </div>
          </div>

          {/* Locations */}
          <div className="space-y-2">
            <label className="font-semibold text-neutral-800 block text-xs">
              Target Locations
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <MapPin className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  value={locationInput}
                  onChange={(e) => setLocationInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddLocation(locationInput);
                    }
                  }}
                  placeholder="Type city or 'Remote' & press Enter..."
                  className="w-full bg-[#F8FAFC] border border-neutral-200 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-[#F26825] focus:bg-white"
                />
              </div>
              <button
                type="button"
                onClick={() => handleAddLocation(locationInput)}
                className="px-3 py-1.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-medium rounded-lg text-xs"
              >
                Add
              </button>
            </div>

            {/* Active Location Badges */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {selectedLocations.map((loc) => (
                <span
                  key={loc}
                  className="inline-flex items-center gap-1 bg-neutral-100 border border-neutral-300 text-neutral-800 px-2 py-0.5 rounded-md font-medium text-[11px]"
                >
                  <span>{loc}</span>
                  <button
                    onClick={() => handleRemoveLocation(loc)}
                    className="hover:text-red-600 p-0.5"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ))}
            </div>

            {/* Suggestions */}
            <div className="flex flex-wrap items-center gap-1 text-[11px] text-neutral-400 pt-1">
              <span className="text-neutral-500">Popular:</span>
              {SUGGESTED_LOCATIONS.map((sl) => (
                <button
                  key={sl}
                  type="button"
                  onClick={() => handleAddLocation(sl)}
                  className="px-1.5 py-0.5 rounded bg-neutral-100 hover:bg-neutral-200 text-neutral-600 text-[10px]"
                >
                  + {sl}
                </button>
              ))}
            </div>
          </div>

          {/* Country Focus */}
          <div>
            <label className="font-semibold text-neutral-800 block text-xs mb-1.5">
              Country Priority
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'India', label: '🇮🇳 India', desc: 'Naukri, Indeed India & India ATS' },
                { id: 'Remote', label: '🌐 Remote Worldwide', desc: 'Global remote postings' },
                { id: 'United States', label: '🇺🇸 United States', desc: 'US tech & global hubs' },
              ].map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setCountry(c.id)}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    country === c.id
                      ? 'border-[#F26825] bg-orange-50/50 shadow-sm'
                      : 'border-neutral-200 bg-white hover:bg-neutral-50'
                  }`}
                >
                  <span className="font-semibold block text-xs text-neutral-900">{c.label}</span>
                  <span className="text-[10px] text-neutral-500 leading-tight block mt-0.5">
                    {c.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-3 border-t border-neutral-100 flex items-center justify-between">
            <span className="text-[11px] text-neutral-500">
              Harvested jobs stream live directly into Neon PostgreSQL.
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs text-neutral-600 hover:text-neutral-900 font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRun}
                disabled={isSyncing}
                className="px-4 py-2 bg-[#F26825] hover:bg-[#D95B1E] text-white font-semibold text-xs rounded-lg transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Ingestion Active...' : 'Harvest Live Roles Now'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
