import React, { useState } from 'react';
import { X, Search, RotateCcw } from 'lucide-react';

const SOURCE_COLORS = {
  linkedin: '#0A66C2',
  naukri: '#275DF5',
  indeed: '#2164F3',
  glassdoor: '#0CAA41',
  greenhouse: '#00B268',
  lever: '#4C44EC',
  ashby: '#FF5722',
  himalayas: '#6366F1',
  themuse: '#00A389',
  remotive: '#10B981',
  remoteok: '#FF4742',
  arbeitnow: '#8B5CF6',
  jobicy: '#EC4899',
  weworkremotely: '#F59E0B',
  adzuna: '#22C55E',
  jooble: '#F97316',
  jsearch: '#3B82F6',
};

const EXP_TIERS = [
  { label: 'Any', min: null, max: null },
  { label: '0–1y', min: 0, max: 1 },
  { label: '1–3y', min: 1, max: 3 },
  { label: '3–6y', min: 3, max: 6 },
  { label: '6+y', min: 6, max: null },
];

export default function FilterSidebar({
  filtersData,
  selectedCategory,
  onSelectCategory,
  selectedCountry,
  onSelectCountry,
  selectedCity,
  onSelectCity,
  selectedCompany,
  onSelectCompany,
  selectedSource,
  onSelectSource,
  selectedExp,
  onSelectExp,
  remoteOnly,
  onToggleRemote,
  indiaOnly,
  onToggleIndia,
  activeOnly,
  onToggleActive,
  onResetFilters,
  activeFilterCount,
}) {
  const [citySearch, setCitySearch] = useState('');
  const [compSearch, setCompSearch] = useState('');

  const categories = filtersData?.categories || [];
  const rawCountries = filtersData?.countries || [];

  // Standard countries list with flags
  const baseCountries = [
    { name: 'India', flag: '🇮🇳' },
    { name: 'Remote / Worldwide', flag: '🌐' },
    { name: 'United States', flag: '🇺🇸' },
    { name: 'United Kingdom', flag: '🇬🇧' },
    { name: 'Germany', flag: '🇩🇪' },
  ];

  const countryCounts = {};
  rawCountries.forEach((c) => {
    countryCounts[c.name] = c.count;
  });

  const displayCountries = baseCountries.map((bc) => ({
    ...bc,
    count: countryCounts[bc.name] || 0,
  }));

  rawCountries.forEach((c) => {
    if (
      c.name &&
      !displayCountries.some((dc) => dc.name.toLowerCase() === c.name.toLowerCase())
    ) {
      displayCountries.push({ name: c.name, flag: '🌍', count: c.count });
    }
  });

  const cities = (filtersData?.cities || []).filter((c) =>
    c.name.toLowerCase().includes(citySearch.toLowerCase())
  );
  const companies = (filtersData?.companies || []).filter((c) =>
    c.name.toLowerCase().includes(compSearch.toLowerCase())
  );
  const sources = filtersData?.sources || [];

  return (
    <aside className="w-[252px] shrink-0 bg-white border-r border-neutral-200 h-[calc(100vh-56px-41px)] sticky top-[97px] overflow-y-auto p-4 flex flex-col justify-between text-xs">
      <div className="space-y-6">
        {/* Header & Reset Button */}
        <div className="flex items-center justify-between pb-2 border-b border-neutral-100">
          <span className="font-semibold text-neutral-900 tracking-tight text-xs uppercase text-neutral-400">
            Filters
          </span>
          {activeFilterCount > 0 && (
            <button
              onClick={onResetFilters}
              className="text-[#F26825] hover:text-[#D95B1E] flex items-center gap-1 font-semibold transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset all</span>
            </button>
          )}
        </div>

        {/* Quick Toggles */}
        <div className="space-y-2">
          {/* India Roles Quick Toggle */}
          <div className="flex items-center justify-between p-2 rounded-md bg-orange-50/70 border border-orange-100">
            <div className="flex items-center gap-1.5">
              <span className="text-sm">🇮🇳</span>
              <span className="font-semibold text-neutral-900 text-[11px]">India Roles</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={indiaOnly}
              onClick={() => onToggleIndia(!indiaOnly)}
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                indiaOnly ? 'bg-[#F26825]' : 'bg-neutral-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  indiaOnly ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Remote Only Toggle */}
          <div className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-neutral-50 transition-colors">
            <span className="font-medium text-neutral-800">Remote Only</span>
            <button
              type="button"
              role="switch"
              aria-checked={remoteOnly}
              onClick={() => onToggleRemote(!remoteOnly)}
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                remoteOnly ? 'bg-[#111827]' : 'bg-neutral-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  remoteOnly ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Active Jobs Only (Hide Expired) */}
          <div className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-neutral-50 transition-colors">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${activeOnly ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-300'}`} />
              <span className="font-medium text-neutral-800">Active Jobs Only</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={activeOnly}
              onClick={() => onToggleActive(!activeOnly)}
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                activeOnly ? 'bg-emerald-600' : 'bg-neutral-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  activeOnly ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Experience Chips */}
        <div>
          <span className="font-medium text-neutral-800 block mb-2">Experience</span>
          <div className="grid grid-cols-3 gap-1">
            {EXP_TIERS.map((tier) => {
              const isSelected =
                selectedExp?.min === tier.min && selectedExp?.max === tier.max;
              return (
                <button
                  key={tier.label}
                  onClick={() => onSelectExp(isSelected ? null : tier)}
                  className={`px-2 py-1 text-[11px] rounded font-medium border text-center transition-colors ${
                    isSelected
                      ? 'bg-[#111827] text-white border-[#111827]'
                      : 'bg-white text-neutral-600 border-neutral-200 hover:bg-neutral-50'
                  }`}
                >
                  {tier.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Country & Region */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">Country</span>
            {selectedCountry && (
              <button
                onClick={() => onSelectCountry(null)}
                className="text-[10px] text-[#F26825] hover:underline font-medium"
              >
                Clear
              </button>
            )}
          </div>
          <div className="space-y-0.5 max-h-40 overflow-y-auto pr-1">
            {displayCountries.map((c) => {
              const isSelected = selectedCountry === c.name;
              return (
                <button
                  key={c.name}
                  onClick={() => onSelectCountry(isSelected ? null : c.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-neutral-900 font-semibold text-white'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <div className="flex items-center gap-1.5 truncate pr-1">
                    <span>{c.flag || '🌍'}</span>
                    <span className="truncate">{c.name}</span>
                  </div>
                  {c.count > 0 && (
                    <span
                      className={`font-mono text-[10px] tabular-nums ${
                        isSelected ? 'text-white/80' : 'text-neutral-400'
                      }`}
                    >
                      {c.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Department / Category */}
        <div>
          <span className="font-medium text-neutral-800 block mb-2">Category</span>
          <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
            {categories.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <button
                  key={cat.name}
                  onClick={() => onSelectCategory(isSelected ? null : cat.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-neutral-100 font-semibold text-[#111827]'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <span className="truncate pr-1">{cat.name}</span>
                  <span className="font-mono text-[10px] text-neutral-400 tabular-nums">
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Location / City */}
        <div>
          <span className="font-medium text-neutral-800 block mb-2">Location & City</span>
          <div className="relative mb-2">
            <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={citySearch}
              onChange={(e) => setCitySearch(e.target.value)}
              placeholder="Search cities..."
              className="w-full bg-[#F7F7F5] border border-neutral-200 rounded px-2 pl-6 py-1 text-[11px] focus:outline-none focus:border-neutral-400"
            />
          </div>
          <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1">
            {cities.map((city) => {
              const isSelected = selectedCity === city.name;
              return (
                <button
                  key={city.name}
                  onClick={() => onSelectCity(isSelected ? null : city.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-neutral-100 font-semibold text-[#111827]'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <span className="truncate pr-1">{city.name}</span>
                  <span className="font-mono text-[10px] text-neutral-400 tabular-nums">
                    {city.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Company */}
        <div>
          <span className="font-medium text-neutral-800 block mb-2">Company</span>
          <div className="relative mb-2">
            <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={compSearch}
              onChange={(e) => setCompSearch(e.target.value)}
              placeholder="Search companies..."
              className="w-full bg-[#F7F7F5] border border-neutral-200 rounded px-2 pl-6 py-1 text-[11px] focus:outline-none focus:border-neutral-400"
            />
          </div>
          <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1">
            {companies.map((comp) => {
              const isSelected = selectedCompany === comp.name;
              return (
                <button
                  key={comp.name}
                  onClick={() => onSelectCompany(isSelected ? null : comp.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-neutral-100 font-semibold text-[#111827]'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <span className="truncate pr-1">{comp.name}</span>
                  <span className="font-mono text-[10px] text-neutral-400 tabular-nums">
                    {comp.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Platform Source */}
        <div>
          <span className="font-medium text-neutral-800 block mb-2">Platform Source</span>
          <div className="space-y-0.5 max-h-40 overflow-y-auto pr-1">
            {sources.map((src) => {
              const isSelected = selectedSource === src.name;
              const dotColor = SOURCE_COLORS[src.name.toLowerCase()] || '#6B7280';
              return (
                <button
                  key={src.name}
                  onClick={() => onSelectSource(isSelected ? null : src.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-neutral-100 font-semibold text-[#111827]'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate pr-1">
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: dotColor }}
                    />
                    <span className="capitalize truncate">{src.name}</span>
                  </div>
                  <span className="font-mono text-[10px] text-neutral-400 tabular-nums">
                    {src.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
