import React from 'react';
import { Bookmark, MapPin, Briefcase, DollarSign, Clock, Check } from 'lucide-react';
import { SOURCE_COLORS, formatSourceName } from './FilterSidebar.jsx';

const STATUS_CONFIG = {
  saved: { label: 'Saved', color: 'bg-neutral-100 text-neutral-700 border-neutral-300' },
  applied: { label: 'Applied', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  interview: { label: 'Interview', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  offer: { label: 'Offer', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  rejected: { label: 'Rejected', color: 'bg-red-50 text-red-700 border-red-200' },
};

export default function JobCard({ job, isSelected, onSelect, onToggleSave }) {
  const companyInitial = job.company?.charAt(0)?.toUpperCase() || '?';

  // Format salary
  const formatSalary = () => {
    if (!job.salary_min && !job.salary_max) return null;
    const curr = job.currency || '$';
    const isUSD = curr === 'USD' || curr === '$';
    const isINR = curr === 'INR' || curr === '₹';

    if (job.salary_min && job.salary_max) {
      if (isINR) {
        return `₹${(job.salary_min / 100000).toFixed(1)}L - ${(job.salary_max / 100000).toFixed(1)}L`;
      }
      return `${curr}${Math.round(job.salary_min / 1000)}k - ${curr}${Math.round(job.salary_max / 1000)}k`;
    }
    const val = job.salary_min || job.salary_max;
    if (isINR) return `₹${(val / 100000).toFixed(1)}L`;
    return `${curr}${Math.round(val / 1000)}k`;
  };

  // Format experience
  const formatExp = () => {
    if (job.min_exp !== null && job.max_exp !== null) {
      return `${job.min_exp}–${job.max_exp} yrs`;
    }
    if (job.min_exp !== null) {
      return `${job.min_exp}+ yrs`;
    }
    return null;
  };

  // Relative posted date
  const formatPostedAt = () => {
    if (!job.posted_at) return null;
    try {
      const diffHours = Math.floor((new Date() - new Date(job.posted_at)) / 3600000);
      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 30) return `${diffDays}d ago`;
      return new Date(job.posted_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return null;
    }
  };

  const statusBadge = job.application_status && job.application_status !== 'none'
    ? STATUS_CONFIG[job.application_status]
    : null;

  return (
    <div
      onClick={onSelect}
      className={`p-3.5 sm:p-4 border-b border-neutral-200 transition-colors cursor-pointer text-xs active:bg-orange-50/50 ${
        isSelected
          ? 'border-l-2 border-l-[#F26825] bg-[#FFFBF7]'
          : 'border-l-2 border-l-transparent bg-white hover:bg-[#FAFAF9]'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Monogram + Title Info */}
        <div className="flex items-start gap-2.5 sm:gap-3 flex-1 min-w-0">
          <div className="w-8 h-8 rounded bg-neutral-100 border border-neutral-200 text-[#111827] font-semibold text-xs flex items-center justify-center shrink-0">
            {companyInitial}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-[#111827] truncate leading-tight">
              {job.title}
            </h3>
            <p className="text-neutral-600 font-medium text-xs truncate mt-0.5">
              {job.company}
            </p>
          </div>
        </div>

        {/* Bookmark Action */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleSave(job);
          }}
          className="text-neutral-400 hover:text-[#111827] p-1.5 -mr-1.5 transition-colors touch-manipulation"
          title={job.is_saved ? 'Remove bookmark' : 'Bookmark job'}
          aria-label={job.is_saved ? 'Remove bookmark' : 'Bookmark job'}
        >
          <Bookmark
            className={`w-4 h-4 ${job.is_saved ? 'fill-[#F26825] text-[#F26825]' : ''}`}
          />
        </button>
      </div>

      {/* Location, Category, Remote, Country & Active Badges */}
      <div className="flex flex-wrap items-center gap-1.5 mt-2.5 text-neutral-500">
        <span className="flex items-center gap-1 text-[11px] truncate max-w-[180px]">
          <MapPin className="w-3 h-3 text-neutral-400 shrink-0" />
          <span>{job.city || job.location || 'Unspecified'}</span>
        </span>

        {job.country === 'India' && (
          <span className="bg-orange-50 text-[#F26825] font-semibold text-[10px] px-1.5 py-0.2 rounded border border-orange-200 flex items-center gap-1">
            <span>🇮🇳</span>
            <span>India</span>
          </span>
        )}

        {job.is_remote && (
          <span className="bg-emerald-50 text-emerald-800 text-[10px] font-medium px-1.5 py-0.2 rounded border border-emerald-200">
            Remote
          </span>
        )}

        <span className="bg-neutral-100 text-neutral-600 text-[10px] font-medium px-1.5 py-0.2 rounded border border-neutral-200">
          {job.category}
        </span>

        {job.is_active ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Live</span>
          </span>
        ) : (
          <span className="text-[10px] font-medium text-neutral-500 bg-neutral-100 px-1.5 py-0.2 rounded border border-neutral-200">
            Expired
          </span>
        )}

        {statusBadge && (
          <span className={`text-[10px] font-medium px-1.5 py-0.2 rounded border ${statusBadge.color}`}>
            {statusBadge.label}
          </span>
        )}
      </div>

      {/* Meta Footer: Experience, Salary, Date & Merged Sources */}
      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-neutral-100">
        <div className="flex items-center gap-3 font-mono text-[11px] text-neutral-600 tabular-nums">
          {formatExp() && <span>{formatExp()}</span>}
          {formatSalary() && (
            <span className="text-neutral-900 font-medium">{formatSalary()}</span>
          )}
          {formatPostedAt() && (
            <span className="text-neutral-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatPostedAt()}
            </span>
          )}
        </div>

        {/* Merged Multi-Source Badges */}
        <div className="flex items-center gap-1">
          {job.sources?.map((s) => {
            const dotColor = SOURCE_COLORS[s.source_name.toLowerCase()] || '#6B7280';
            return (
              <span
                key={s.id}
                className="inline-flex items-center gap-1 bg-white border border-neutral-200 text-neutral-700 text-[10px] font-medium px-1.5 py-0.5 rounded"
                title={`Available on ${formatSourceName(s.source_name)}`}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ backgroundColor: dotColor }}
                />
                <span className="truncate">{formatSourceName(s.source_name)}</span>
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
