import React, { useState, useEffect, useRef } from 'react';
import { X, Search, RotateCcw } from 'lucide-react';

export const SOURCE_COLORS = {
  linkedin: '#0A66C2',
  naukri: '#275DF5',
  indeed: '#2164F3',
  glassdoor: '#0CAA41',
  greenhouse: '#00B268',
  lever: '#4C44EC',
  ashby: '#FF5722',
  smartrecruiters: '#10B981',
  workable: '#0070CD',
  workday: '#E06522',
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

export const SOURCE_FORMAT_MAP = {
  linkedin: 'LinkedIn',
  naukri: 'Naukri',
  indeed: 'Indeed',
  glassdoor: 'Glassdoor',
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  ashby: 'Ashby',
  smartrecruiters: 'SmartRecruiters',
  workable: 'Workable',
  workday: 'Workday',
  arbeitnow: 'Arbeitnow',
  himalayas: 'Himalayas',
  remotive: 'Remotive',
  remoteok: 'Remote OK',
  jobicy: 'Jobicy',
  weworkremotely: 'We Work Remotely',
  themuse: 'The Muse',
  adzuna: 'Adzuna',
  jooble: 'Jooble',
  jsearch: 'JSearch',
};

export const formatSourceName = (source) => {
  if (!source) return '';
  const key = source.toLowerCase().trim();
  if (SOURCE_FORMAT_MAP[key]) return SOURCE_FORMAT_MAP[key];
  return key
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
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
  onClose,
  isMobile = false,
}) {
  const [countrySearch, setCountrySearch] = useState('');
  const [showAllCountries, setShowAllCountries] = useState(false);
  const [citySearch, setCitySearch] = useState('');
  const [compSearch, setCompSearch] = useState('');

  // Experience Slider State (-1 represents 'Any')
  const initialSliderVal = selectedExp?.exact !== undefined ? Number(selectedExp.exact) : -1;
  const [sliderVal, setSliderVal] = useState(initialSliderVal);
  const debounceTimerRef = useRef(null);

  useEffect(() => {
    setSliderVal(selectedExp?.exact !== undefined ? Number(selectedExp.exact) : -1);
  }, [selectedExp]);

  const handleSliderChange = (newVal) => {
    setSliderVal(newVal);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      commitSliderValue(newVal);
    }, 200);
  };

  const commitSliderValue = (val) => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    if (val < 0) {
      onSelectExp(null);
    } else {
      onSelectExp({
        min: null,
        max: null,
        exact: val,
        isCustom: true,
        label: val >= 15 ? '15+ yrs' : `${val} yr${val === 1 ? '' : 's'}`,
      });
    }
  };

  const categories = filtersData?.categories || [];

  const COUNTRY_FLAG_MAP = {
    india: '🇮🇳',
    'united states': '🇺🇸',
    'remote / worldwide': '🌐',
    remote: '🌐',
    'united kingdom': '🇬🇧',
    germany: '🇩🇪',
    canada: '🇨🇦',
    singapore: '🇸🇬',
    australia: '🇦🇺',
    ireland: '🇮🇪',
    france: '🇫🇷',
    netherlands: '🇳🇱',
    spain: '🇪🇸',
    poland: '🇵🇱',
    'united arab emirates': '🇦🇪',
    uae: '🇦🇪',
    israel: '🇮🇱',
    brazil: '🇧🇷',
    switzerland: '🇨🇭',
    sweden: '🇸🇪',
    japan: '🇯🇵',
    mexico: '🇲🇽',
    philippines: '🇵🇭',
    italy: '🇮🇹',
    portugal: '🇵🇹',
    austria: '🇦🇹',
    belgium: '🇧🇪',
    denmark: '🇩🇰',
    finland: '🇫🇮',
    norway: '🇳🇴',
    estonia: '🇪🇪',
    czechia: '🇨🇿',
    'czech republic': '🇨🇿',
    romania: '🇷🇴',
    hungary: '🇭🇺',
    colombia: '🇨🇴',
    argentina: '🇦🇷',
    chile: '🇨🇱',
    'new zealand': '🇳🇿',
    'south africa': '🇿🇦',
    global: '🌍',
  };

  const getCountryFlag = (name) => {
    if (!name) return '🌍';
    return COUNTRY_FLAG_MAP[name.trim().toLowerCase()] || '🌍';
  };

  // Directly fetch countries from the API / database response - zero hardcoded list
  const allCountries = (filtersData?.countries || []).map((c) => ({
    name: c.name,
    count: c.count,
    flag: getCountryFlag(c.name),
  }));

  const filteredCountries = allCountries.filter((c) =>
    c.name.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const displayedCountries = showAllCountries || countrySearch
    ? filteredCountries
    : filteredCountries.slice(0, 10);

  const cities = (filtersData?.cities || []).filter((c) =>
    c.name.toLowerCase().includes(citySearch.toLowerCase())
  );
  const companies = (filtersData?.companies || []).filter((c) =>
    c.name.toLowerCase().includes(compSearch.toLowerCase())
  );
  const sources = filtersData?.sources || [];

  const containerClasses = isMobile
    ? "w-full bg-white h-full overflow-y-auto p-4 flex flex-col justify-between text-xs"
    : "hidden lg:flex w-[252px] shrink-0 bg-white border-r border-neutral-200 h-full overflow-y-auto p-4 flex-col justify-between text-xs";

  return (
    <aside className={containerClasses}>
      <div className="space-y-6">
        {/* Header & Reset Button */}
        <div className="flex items-center justify-between pb-2 border-b border-neutral-100">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-900 tracking-tight text-xs uppercase text-neutral-400">
              Filters
            </span>
            {activeFilterCount > 0 && (
              <span className="bg-[#F26825] text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full font-mono">
                {activeFilterCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {activeFilterCount > 0 && (
              <button
                onClick={onResetFilters}
                className="text-[#F26825] hover:text-[#D95B1E] flex items-center gap-1 font-semibold transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset all</span>
              </button>
            )}
            {isMobile && onClose && (
              <button
                onClick={onClose}
                className="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 ml-1"
                aria-label="Close filters"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
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
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${indiaOnly ? 'bg-[#F26825]' : 'bg-neutral-200'
                }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${indiaOnly ? 'translate-x-4' : 'translate-x-0'
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
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${remoteOnly ? 'bg-[#111827]' : 'bg-neutral-200'
                }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${remoteOnly ? 'translate-x-4' : 'translate-x-0'
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
              className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${activeOnly ? 'bg-emerald-600' : 'bg-neutral-200'
                }`}
            >
              <span
                className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${activeOnly ? 'translate-x-4' : 'translate-x-0'
                  }`}
              />
            </button>
          </div>
        </div>

        {/* Single-Thumb Experience Line Slider */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">Experience</span>
            <div className="flex items-center gap-1.5">
              <span className={`font-mono text-xs tabular-nums ${sliderVal < 0 ? 'text-neutral-500' : 'text-[#F26825] font-semibold'}`}>
                {sliderVal < 0
                  ? 'Any'
                  : sliderVal === 0
                  ? 'Fresher (0 yrs)'
                  : sliderVal >= 15
                  ? '15+ yrs'
                  : `${sliderVal} yr${sliderVal === 1 ? '' : 's'}`}
              </span>
              {sliderVal >= 0 && (
                <button
                  type="button"
                  onClick={() => {
                    commitSliderValue(-1);
                    setSliderVal(-1);
                  }}
                  className="text-[10px] text-[#F26825] hover:underline font-semibold ml-0.5 cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          <div className="pt-1 pb-2">
            {/* Range input with dynamic progress fill */}
            <div className="relative flex items-center">
              <input
                type="range"
                min="-1"
                max="15"
                step="1"
                value={sliderVal}
                onChange={(e) => handleSliderChange(Number(e.target.value))}
                onPointerUp={() => commitSliderValue(sliderVal)}
                onTouchEnd={() => commitSliderValue(sliderVal)}
                className="w-full h-[3px] rounded-lg appearance-none cursor-pointer focus:outline-none accent-[#F26825] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-[#F26825] [&::-webkit-slider-thumb]:shadow-xs [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110"
                style={{
                  background:
                    sliderVal >= 0
                      ? `linear-gradient(to right, #F26825 0%, #F26825 ${((sliderVal + 1) / 16) * 100}%, #E5E7EB ${((sliderVal + 1) / 16) * 100}%, #E5E7EB 100%)`
                      : '#E5E7EB',
                }}
              />
            </div>

            {/* Tick graduation labels */}
            <div className="flex justify-between text-[10px] text-neutral-400 font-mono mt-1.5 px-0.5 select-none">
              <span
                onClick={() => { setSliderVal(-1); commitSliderValue(-1); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === -1 ? 'text-[#F26825] font-bold' : ''}`}
              >
                Any
              </span>
              <span
                onClick={() => { setSliderVal(0); commitSliderValue(0); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === 0 ? 'text-[#F26825] font-bold' : ''}`}
              >
                0
              </span>
              <span
                onClick={() => { setSliderVal(3); commitSliderValue(3); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === 3 ? 'text-[#F26825] font-bold' : ''}`}
              >
                3
              </span>
              <span
                onClick={() => { setSliderVal(6); commitSliderValue(6); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === 6 ? 'text-[#F26825] font-bold' : ''}`}
              >
                6
              </span>
              <span
                onClick={() => { setSliderVal(10); commitSliderValue(10); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === 10 ? 'text-[#F26825] font-bold' : ''}`}
              >
                10
              </span>
              <span
                onClick={() => { setSliderVal(15); commitSliderValue(15); }}
                className={`cursor-pointer hover:text-neutral-700 ${sliderVal === 15 ? 'text-[#F26825] font-bold' : ''}`}
              >
                15+
              </span>
            </div>
          </div>
        </div>

        {/* Country & Region */}
        {allCountries.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-neutral-800">
                {selectedExp ? `Countries (${selectedExp.label})` : 'Country'}
              </span>
              {selectedCountry && (
                <button
                  onClick={() => onSelectCountry(null)}
                  className="text-[10px] text-[#F26825] hover:underline font-medium"
                >
                  Clear
                </button>
              )}
            </div>

            {allCountries.length > 6 && (
              <div className="relative mb-1.5">
                <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  placeholder="Filter countries..."
                  className="w-full bg-[#F7F7F5] border border-neutral-200 rounded px-2 pl-6 py-1 text-[11px] focus:outline-none focus:border-neutral-400"
                />
              </div>
            )}

            <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
              {displayedCountries.length === 0 ? (
                <div className="py-2 text-center text-[11px] text-neutral-400">
                  No countries match "{countrySearch}"
                </div>
              ) : (
                displayedCountries.map((c) => {
                  const isSelected = selectedCountry === c.name;
                  return (
                    <button
                      key={c.name}
                      onClick={() => onSelectCountry(isSelected ? null : c.name)}
                      className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${isSelected
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
                          className={`font-mono text-[10px] tabular-nums ${isSelected ? 'text-white/80' : 'text-neutral-400'
                            }`}
                        >
                          {c.count}
                        </span>
                      )}
                    </button>
                  );
                })
              )}
            </div>

            {filteredCountries.length > 10 && !countrySearch && (
              <button
                onClick={() => setShowAllCountries(!showAllCountries)}
                className="w-full text-center py-1 text-[10px] font-semibold text-[#F26825] hover:text-[#D95B1E] transition-colors mt-1"
              >
                {showAllCountries ? 'Show fewer countries' : `Show all ${filteredCountries.length} countries`}
              </button>
            )}
          </div>
        )}

        {/* Location & City (Placed next to Country; dynamically shows only cities of the selected country) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">
              {selectedCountry ? `Cities in ${selectedCountry}` : 'Location & City'}
            </span>
            {selectedCity && (
              <button
                onClick={() => onSelectCity(null)}
                className="text-[10px] text-[#F26825] hover:underline font-medium"
              >
                Clear
              </button>
            )}
          </div>
          {selectedCity && cities.length > 0 && !cities.some(c => c.name.toLowerCase() === selectedCity.toLowerCase()) && (
            <div className="mb-2 px-2 py-1 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 flex items-center justify-between">
              <span className="truncate">No matching roles in "{selectedCity}"</span>
              <button onClick={() => onSelectCity(null)} className="font-semibold underline ml-1 hover:text-amber-950 shrink-0">Clear</button>
            </div>
          )}
          <div className="relative mb-2">
            <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={citySearch}
              onChange={(e) => setCitySearch(e.target.value)}
              placeholder={selectedCountry ? `Search cities in ${selectedCountry}...` : "Search any world city..."}
              className="w-full bg-[#F7F7F5] border border-neutral-200 rounded px-2 pl-6 py-1 text-[11px] focus:outline-none focus:border-neutral-400"
            />
          </div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
            {cities.length === 0 ? (
              <div className="py-2 text-center text-[11px] text-neutral-400">
                {citySearch ? `No cities match "${citySearch}"` : 'No cities listed yet'}
              </div>
            ) : (
              cities.map((city) => {
                const isSelected = selectedCity === city.name;
                return (
                  <button
                    key={city.name}
                    onClick={() => onSelectCity(isSelected ? null : city.name)}
                    className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${isSelected
                        ? 'bg-neutral-900 font-semibold text-white'
                        : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                      }`}
                  >
                    <span className="truncate pr-1">{city.name}</span>
                    <span
                      className={`font-mono text-[10px] tabular-nums ${isSelected ? 'text-white/80' : 'text-neutral-400'
                        }`}
                    >
                      {city.count}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Department / Category */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">Category</span>
            {selectedCategory && (
              <button
                onClick={() => onSelectCategory(null)}
                className="text-[10px] text-[#F26825] hover:underline font-medium"
              >
                Clear
              </button>
            )}
          </div>
          <div className="space-y-0.5 max-h-52 overflow-y-auto pr-1">
            {categories.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <button
                  key={cat.name}
                  onClick={() => onSelectCategory(isSelected ? null : cat.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${isSelected
                      ? 'bg-neutral-900 font-semibold text-white'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                    }`}
                >
                  <span className="truncate pr-1">{cat.name}</span>
                  <span
                    className={`font-mono text-[10px] tabular-nums ${isSelected ? 'text-white/80' : 'text-neutral-400'
                      }`}
                  >
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Company */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">
              {selectedCountry ? `Companies in ${selectedCountry}` : 'Company'}
            </span>
            {selectedCompany && (
              <button
                onClick={() => onSelectCompany(null)}
                className="text-[10px] text-[#F26825] hover:underline font-medium"
              >
                Clear
              </button>
            )}
          </div>
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
          <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
            {companies.map((comp) => {
              const isSelected = selectedCompany === comp.name;
              return (
                <button
                  key={comp.name}
                  onClick={() => onSelectCompany(isSelected ? null : comp.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${isSelected
                      ? 'bg-neutral-900 font-semibold text-white'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                    }`}
                >
                  <span className="truncate pr-1">{comp.name}</span>
                  <span
                    className={`font-mono text-[10px] tabular-nums ${isSelected ? 'text-white/80' : 'text-neutral-400'
                      }`}
                  >
                    {comp.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Platform Source */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-neutral-800">Platform Source</span>
            {selectedSource && (
              <button
                onClick={() => onSelectSource(null)}
                className="text-[10px] text-[#F26825] hover:underline font-medium"
              >
                Clear
              </button>
            )}
          </div>
          <div className="space-y-0.5 max-h-40 overflow-y-auto pr-1">
            {sources.map((src) => {
              const isSelected = selectedSource === src.name;
              const dotColor = SOURCE_COLORS[src.name.toLowerCase()] || '#6B7280';
              return (
                <button
                  key={src.name}
                  onClick={() => onSelectSource(isSelected ? null : src.name)}
                  className={`w-full flex items-center justify-between px-2 py-1 rounded text-left transition-colors ${isSelected
                      ? 'bg-neutral-900 font-semibold text-white'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                    }`}
                >
                  <div className="flex items-center gap-2 truncate pr-1">
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: dotColor }}
                    />
                    <span className="truncate">{formatSourceName(src.name)}</span>
                  </div>
                  <span
                    className={`font-mono text-[10px] tabular-nums ${isSelected ? 'text-white/80' : 'text-neutral-400'
                      }`}
                  >
                    {src.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      {isMobile && onClose && (
        <div className="sticky bottom-0 pt-4 mt-6 bg-white border-t border-neutral-100">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-[#F26825] hover:bg-[#D95B1E] text-white font-semibold rounded-lg shadow-sm text-xs transition-colors flex items-center justify-center gap-1.5"
          >
            <span>Apply Filters & View Roles</span>
          </button>
        </div>
      )}
    </aside>
  );
}
