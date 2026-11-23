import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Header from './components/Header.jsx';
import StatsStrip from './components/StatsStrip.jsx';
import FilterSidebar from './components/FilterSidebar.jsx';
import JobCard from './components/JobCard.jsx';
import JobDetailPane from './components/JobDetailPane.jsx';
import TrackerBoard from './components/TrackerBoard.jsx';
import SyncTelemetryDrawer from './components/SyncTelemetryDrawer.jsx';
import LiveHarvestModal from './components/LiveHarvestModal.jsx';
import {
  fetchJobs,
  fetchFilters,
  fetchSyncStatus,
  updateJobTracking,
  triggerSync,
  verifyJobLiveness,
  markJobExpired,
} from './api/client.js';
import { ChevronLeft, ChevronRight, SlidersHorizontal, ArrowUpDown } from 'lucide-react';

export default function App() {
  const queryClient = useQueryClient();

  // -------------------------------------------------------------
  // Read initial filter state from URL Search Params
  // -------------------------------------------------------------
  const getInitialStateFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    return {
      q: params.get('q') || '',
      category: params.get('category') || null,
      country: params.get('country') || null,
      location: params.get('location') || null,
      company: params.get('company') || null,
      source: params.get('source') || null,
      min_exp: params.get('min_exp') ? Number(params.get('min_exp')) : null,
      max_exp: params.get('max_exp') ? Number(params.get('max_exp')) : null,
      remote_only: params.get('remote_only') === 'true',
      india_only: params.get('india_only') === 'true',
      active_only: params.get('active_only') !== 'false',
      sort: params.get('sort') || 'newest',
      page: params.get('page') ? Number(params.get('page')) : 1,
      tab: params.get('tab') || 'discover',
    };
  };

  const initial = useMemo(getInitialStateFromUrl, []);

  // UI States
  const [activeTab, setActiveTab] = useState(initial.tab);
  const [searchQuery, setSearchQuery] = useState(initial.q);
  const [debouncedSearch, setDebouncedSearch] = useState(initial.q);
  const [selectedCategory, setSelectedCategory] = useState(initial.category);
  const [selectedCountry, setSelectedCountry] = useState(initial.country);
  const [selectedCity, setSelectedCity] = useState(initial.location);
  const [selectedCompany, setSelectedCompany] = useState(initial.company);
  const [selectedSource, setSelectedSource] = useState(initial.source);
  const [selectedExp, setSelectedExp] = useState(
    initial.min_exp !== null || initial.max_exp !== null
      ? { min: initial.min_exp, max: initial.max_exp }
      : null
  );
  const [remoteOnly, setRemoteOnly] = useState(initial.remote_only);
  const [indiaOnly, setIndiaOnly] = useState(initial.india_only);
  const [activeOnly, setActiveOnly] = useState(initial.active_only);
  const [sortBy, setSortBy] = useState(initial.sort);
  const [page, setPage] = useState(initial.page);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(false);
  const [isHarvestModalOpen, setIsHarvestModalOpen] = useState(false);

  // Live URL Verification state
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Synchronize state with URL parameters
  useEffect(() => {
    const params = new URLSearchParams();
    if (activeTab !== 'discover') params.set('tab', activeTab);
    if (debouncedSearch) params.set('q', debouncedSearch);
    if (selectedCategory) params.set('category', selectedCategory);
    if (selectedCountry) params.set('country', selectedCountry);
    if (selectedCity) params.set('location', selectedCity);
    if (selectedCompany) params.set('company', selectedCompany);
    if (selectedSource) params.set('source', selectedSource);
    if (selectedExp?.min !== undefined && selectedExp?.min !== null)
      params.set('min_exp', selectedExp.min);
    if (selectedExp?.max !== undefined && selectedExp?.max !== null)
      params.set('max_exp', selectedExp.max);
    if (remoteOnly) params.set('remote_only', 'true');
    if (indiaOnly) params.set('india_only', 'true');
    if (!activeOnly) params.set('active_only', 'false');
    if (sortBy !== 'newest') params.set('sort', sortBy);
    if (page > 1) params.set('page', page);

    const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
  }, [
    activeTab,
    debouncedSearch,
    selectedCategory,
    selectedCountry,
    selectedCity,
    selectedCompany,
    selectedSource,
    selectedExp,
    remoteOnly,
    indiaOnly,
    activeOnly,
    sortBy,
    page,
  ]);

  // -------------------------------------------------------------
  // Data Queries
  // -------------------------------------------------------------
  const { data: filtersData, refetch: refetchFilters } = useQuery({
    queryKey: ['filters', selectedCountry],
    queryFn: () => fetchFilters(selectedCountry),
  });

  const queryParams = useMemo(() => {
    const p = {
      page,
      page_size: 20,
      sort: sortBy,
    };
    if (debouncedSearch) p.q = debouncedSearch;
    if (selectedCategory) p.category = selectedCategory;
    if (selectedCountry) p.country = selectedCountry;
    if (selectedCity) p.location = selectedCity;
    if (selectedCompany) p.company = selectedCompany;
    if (selectedSource) p.source = selectedSource;
    if (selectedExp?.min !== undefined && selectedExp?.min !== null) p.min_exp = selectedExp.min;
    if (selectedExp?.max !== undefined && selectedExp?.max !== null) p.max_exp = selectedExp.max;
    if (remoteOnly) p.remote_only = true;
    if (indiaOnly) p.india_only = true;
    if (activeOnly) p.active_only = true;
    return p;
  }, [
    debouncedSearch,
    selectedCategory,
    selectedCountry,
    selectedCity,
    selectedCompany,
    selectedSource,
    selectedExp,
    remoteOnly,
    indiaOnly,
    activeOnly,
    sortBy,
    page,
  ]);

  const {
    data: jobsData,
    isLoading: isJobsLoading,
    isFetching: isJobsFetching,
  } = useQuery({
    queryKey: ['jobs', queryParams],
    queryFn: () => fetchJobs(queryParams),
  });

  // Query for tracked applications (used by Tracker view and Header badge)
  const { data: trackedJobsData, refetch: refetchTracked } = useQuery({
    queryKey: ['tracked_jobs'],
    queryFn: () => fetchJobs({ saved_only: true, page_size: 100 }),
  });

  // Telemetry status query
  const { data: syncStatus, refetch: refetchTelemetry } = useQuery({
    queryKey: ['sync_status'],
    queryFn: fetchSyncStatus,
    refetchInterval: isTelemetryOpen ? 3000 : false,
  });

  const isSyncing = Boolean(syncStatus?.is_running);

  // Automatic background refresh check on app load / refresh:
  // If no sync has occurred within the last hour, run a silent background sync automatically
  useEffect(() => {
    if (syncStatus && !syncStatus.is_running) {
      const lastRun = syncStatus.last_started_at ? new Date(syncStatus.last_started_at).getTime() : 0;
      const oneHourAgo = Date.now() - 60 * 60 * 1000;
      if (lastRun < oneHourAgo) {
        triggerSync({ mode: 'fast' })
          .then(() => {
            queryClient.invalidateQueries({ queryKey: ['sync_status'] });
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['filters'] });
          })
          .catch(() => {});
      }
    }
  }, [syncStatus, queryClient]);

  // Auto-select first job if none selected
  const jobs = jobsData?.jobs || [];
  const selectedJob = useMemo(() => {
    if (!jobs.length) return null;
    return jobs.find((j) => j.id === selectedJobId) || jobs[0];
  }, [jobs, selectedJobId]);

  useEffect(() => {
    if (jobs.length > 0 && !selectedJobId) {
      setSelectedJobId(jobs[0].id);
    }
  }, [jobs, selectedJobId]);

  // -------------------------------------------------------------
  // Keyboard Navigation (j / k / ArrowDown / ArrowUp)
  // -------------------------------------------------------------
  useEffect(() => {
    if (activeTab !== 'discover' || !jobs.length) return;

    function handleKeyDown(e) {
      if (['input', 'textarea', 'select'].includes(document.activeElement?.tagName?.toLowerCase())) {
        return;
      }
      const currentIndex = jobs.findIndex((j) => j.id === selectedJob?.id);
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = Math.min(currentIndex + 1, jobs.length - 1);
        setSelectedJobId(jobs[nextIndex].id);
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = Math.max(currentIndex - 1, 0);
        setSelectedJobId(jobs[prevIndex].id);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, jobs, selectedJob]);

  // -------------------------------------------------------------
  // Mutations: Tracking & Sync
  // -------------------------------------------------------------
  const trackingMutation = useMutation({
    mutationFn: ({ jobId, payload }) => updateJobTracking(jobId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['tracked_jobs'] });
      queryClient.invalidateQueries({ queryKey: ['filters'] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: (mode) => triggerSync(mode),
    onSuccess: () => {
      refetchTelemetry();
      setIsTelemetryOpen(true);
    },
  });

  const handleToggleSave = (job) => {
    const nextSaved = !job.is_saved;
    trackingMutation.mutate({
      jobId: job.id,
      payload: {
        is_saved: nextSaved,
        application_status: nextSaved && job.application_status === 'none' ? 'saved' : job.application_status,
      },
    });
  };

  const handleUpdateTracking = (jobId, payload) => {
    trackingMutation.mutate({ jobId, payload });
  };

  const handleVerifyLiveness = async (jobId) => {
    setIsVerifying(true);
    setVerificationResult(null);
    try {
      const res = await verifyJobLiveness(jobId);
      setVerificationResult(res);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['filters'] });
    } catch (err) {
      setVerificationResult({ job_id: jobId, is_active: true, message: `Check failed: ${err.message}` });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleMarkExpired = async (jobId) => {
    try {
      await markJobExpired(jobId);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['filters'] });
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetFilters = () => {
    setSelectedCategory(null);
    setSelectedCountry(null);
    setSelectedCity(null);
    setSelectedCompany(null);
    setSelectedSource(null);
    setSelectedExp(null);
    setRemoteOnly(false);
    setIndiaOnly(false);
    setActiveOnly(true);
    setSearchQuery('');
    setPage(1);
  };

  const activeFilterCount =
    (selectedCategory ? 1 : 0) +
    (selectedCountry ? 1 : 0) +
    (selectedCity ? 1 : 0) +
    (selectedCompany ? 1 : 0) +
    (selectedSource ? 1 : 0) +
    (selectedExp ? 1 : 0) +
    (remoteOnly ? 1 : 0) +
    (indiaOnly ? 1 : 0) +
    (!activeOnly ? 1 : 0) +
    (debouncedSearch ? 1 : 0);

  const trackedCount = (filtersData?.kpis?.saved_jobs || 0) + (filtersData?.kpis?.applied_jobs || 0);

  return (
    <div className="min-h-screen bg-[#F7F7F5] flex flex-col font-sans">
      {/* 1. Sticky Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onOpenTelemetry={() => setIsTelemetryOpen(true)}
        onOpenLiveHarvest={() => setIsHarvestModalOpen(true)}
        onTriggerSync={(mode) => syncMutation.mutate(mode)}
        isSyncing={isSyncing}
        trackedCount={trackedCount}
        indiaOnly={indiaOnly}
        onToggleIndia={() => {
          const nextVal = !indiaOnly;
          setIndiaOnly(nextVal);
          if (nextVal) {
            setSelectedCountry('India');
          } else if (selectedCountry === 'India') {
            setSelectedCountry(null);
          }
          setPage(1);
        }}
      />

      {/* 2. Compact KPI Metric Strip */}
      <StatsStrip
        kpis={filtersData?.kpis}
        isLoading={!filtersData}
        indiaOnly={indiaOnly}
        onToggleIndia={() => {
          const nextVal = !indiaOnly;
          setIndiaOnly(nextVal);
          if (nextVal) {
            setSelectedCountry('India');
          } else if (selectedCountry === 'India') {
            setSelectedCountry(null);
          }
          setPage(1);
        }}
      />

      {/* 3. Main Views */}
      {activeTab === 'discover' ? (
        <div className="flex-1 flex w-full">
          {/* Left Filter Rail (252px) */}
          <FilterSidebar
            filtersData={filtersData}
            selectedCategory={selectedCategory}
            onSelectCategory={(cat) => {
              setSelectedCategory(cat);
              setPage(1);
            }}
            selectedCountry={selectedCountry}
            onSelectCountry={(c) => {
              setSelectedCountry(c);
              setSelectedCity(null);
              if (c && c !== 'India') {
                setIndiaOnly(false);
              } else if (c === 'India') {
                setIndiaOnly(true);
              }
              setPage(1);
            }}
            selectedCity={selectedCity}
            onSelectCity={(city) => {
              setSelectedCity(city);
              setPage(1);
            }}
            selectedCompany={selectedCompany}
            onSelectCompany={(comp) => {
              setSelectedCompany(comp);
              setPage(1);
            }}
            selectedSource={selectedSource}
            onSelectSource={(src) => {
              setSelectedSource(src);
              setPage(1);
            }}
            selectedExp={selectedExp}
            onSelectExp={(exp) => {
              setSelectedExp(exp);
              setPage(1);
            }}
            remoteOnly={remoteOnly}
            onToggleRemote={(rem) => {
              setRemoteOnly(rem);
              setPage(1);
            }}
            indiaOnly={indiaOnly}
            onToggleIndia={(ind) => {
              setIndiaOnly(ind);
              if (ind) {
                setSelectedCountry('India');
              } else if (selectedCountry === 'India') {
                setSelectedCountry(null);
              }
              setPage(1);
            }}
            activeOnly={activeOnly}
            onToggleActive={(act) => {
              setActiveOnly(act);
              setPage(1);
            }}
            onResetFilters={handleResetFilters}
            activeFilterCount={activeFilterCount}
          />

          {/* Middle Feed Column */}
          <main className="flex-1 min-w-0 border-r border-neutral-200 bg-white">
            {/* Feed Control Bar: Sort & Result Count */}
            <div className="h-10 px-4 border-b border-neutral-200 flex items-center justify-between text-xs bg-white sticky top-[97px] z-10">
              <span className="font-mono text-neutral-500 text-[11px] tabular-nums">
                {isJobsLoading ? (
                  'Loading openings...'
                ) : (
                  <>
                    Showing{' '}
                    <span className="font-semibold text-neutral-900">
                      {jobsData?.total ? (page - 1) * 20 + 1 : 0}–
                      {Math.min(page * 20, jobsData?.total || 0)}
                    </span>{' '}
                    of{' '}
                    <span className="font-semibold text-neutral-900">
                      {jobsData?.total?.toLocaleString() || 0}
                    </span>{' '}
                    roles
                  </>
                )}
              </span>

              {/* Sort Selector */}
              <div className="flex items-center gap-1.5">
                <ArrowUpDown className="w-3 h-3 text-neutral-400" />
                <span className="text-neutral-500 text-[11px]">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => {
                    setSortBy(e.target.value);
                    setPage(1);
                  }}
                  className="bg-transparent text-neutral-900 font-medium text-xs focus:outline-none cursor-pointer"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="exp_asc">Experience (Low to High)</option>
                  <option value="salary_desc">Compensation (High to Low)</option>
                </select>
              </div>
            </div>

            {/* Job Cards Stream */}
            <div className="divide-y divide-neutral-100">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSelected={job.id === selectedJob?.id}
                  onSelect={() => {
                    setSelectedJobId(job.id);
                    setVerificationResult(null);
                  }}
                  onToggleSave={handleToggleSave}
                />
              ))}

              {!isJobsLoading && jobs.length === 0 && (
                <div className="p-16 text-center text-xs text-neutral-500 space-y-2">
                  <p className="font-semibold text-neutral-700 text-sm">No openings match your criteria</p>
                  <p className="text-neutral-400">
                    Try clearing some filters or searching for a broader term.
                  </p>
                  {activeFilterCount > 0 && (
                    <button
                      onClick={handleResetFilters}
                      className="mt-3 px-3 py-1.5 bg-[#111827] text-white rounded-md text-xs font-medium"
                    >
                      Clear All Filters
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            {jobsData?.total_pages > 1 && (
              <div className="p-4 border-t border-neutral-200 flex items-center justify-between text-xs bg-white">
                <button
                  onClick={() => setPage(Math.max(page - 1, 1))}
                  disabled={page <= 1 || isJobsFetching}
                  className="px-3 py-1.5 rounded border border-neutral-200 text-neutral-700 font-medium disabled:opacity-40 flex items-center gap-1 hover:bg-neutral-50 transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>

                <span className="font-mono text-neutral-500 text-[11px] tabular-nums">
                  Page {page} of {jobsData.total_pages}
                </span>

                <button
                  onClick={() => setPage(Math.min(page + 1, jobsData.total_pages))}
                  disabled={page >= jobsData.total_pages || isJobsFetching}
                  className="px-3 py-1.5 rounded border border-neutral-200 text-neutral-700 font-medium disabled:opacity-40 flex items-center gap-1 hover:bg-neutral-50 transition-colors"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </main>

          {/* Right Sticky Reading Pane */}
          <div className="w-[440px] shrink-0 hidden lg:block">
            <JobDetailPane
              job={selectedJob}
              onToggleSave={handleToggleSave}
              onUpdateTracking={handleUpdateTracking}
              isTrackingPending={trackingMutation.isPending}
              onVerifyLiveness={handleVerifyLiveness}
              onMarkExpired={handleMarkExpired}
              isVerifying={isVerifying}
              verificationResult={verificationResult}
            />
          </div>
        </div>
      ) : (
        /* My Tracker Kanban Board View */
        <main className="flex-1">
          <TrackerBoard
            jobs={trackedJobsData?.jobs || []}
            onUpdateTracking={handleUpdateTracking}
            onSelectJob={(job) => {
              setSelectedJobId(job.id);
              setActiveTab('discover');
            }}
            isLoading={!trackedJobsData}
          />
        </main>
      )}

      {/* 4. Slide-Over Sync Telemetry Drawer */}
      <SyncTelemetryDrawer
        isOpen={isTelemetryOpen}
        onClose={() => setIsTelemetryOpen(false)}
        syncStatus={syncStatus}
        onRefreshTelemetry={refetchTelemetry}
        onTriggerSync={(mode) => syncMutation.mutate(mode)}
      />

      {/* 5. Live Dynamic Job Harvest Modal */}
      <LiveHarvestModal
        isOpen={isHarvestModalOpen}
        onClose={() => setIsHarvestModalOpen(false)}
        onStartHarvest={(payload) => syncMutation.mutate(payload)}
        isSyncing={isSyncing}
      />
    </div>
  );
}
