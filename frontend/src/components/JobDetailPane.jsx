import React, { useState, useEffect } from 'react';
import {
  ExternalLink,
  MapPin,
  Briefcase,
  DollarSign,
  Bookmark,
  Calendar,
  Layers,
  FileText,
  ChevronDown,
  CheckCircle2,
} from 'lucide-react';

const STATUS_OPTIONS = [
  { value: 'none', label: 'Not Tracked' },
  { value: 'saved', label: 'Saved' },
  { value: 'applied', label: 'Applied' },
  { value: 'interview', label: 'Interviewing' },
  { value: 'offer', label: 'Offer Received' },
  { value: 'rejected', label: 'Rejected' },
];

export default function JobDetailPane({
  job,
  onToggleSave,
  onUpdateTracking,
  isTrackingPending,
}) {
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);

  useEffect(() => {
    if (job) {
      setNotes(job.notes || '');
      setShowNotes(Boolean(job.notes));
    }
  }, [job?.id]);

  if (!job) {
    return (
      <div className="h-[calc(100vh-97px)] sticky top-[97px] bg-white border-l border-neutral-200 flex flex-col items-center justify-center p-8 text-center text-neutral-400 text-xs">
        <FileText className="w-10 h-10 mb-3 text-neutral-300 stroke-[1.5]" />
        <h4 className="font-semibold text-neutral-700 text-sm mb-1">No Job Selected</h4>
        <p className="max-w-xs text-neutral-500 leading-relaxed">
          Select an opening from the list to inspect full requirements, manage tracking stages, and access direct apply links.
        </p>
      </div>
    );
  }

  const formatSalary = () => {
    if (!job.salary_min && !job.salary_max) return 'Not disclosed';
    const curr = job.currency || '$';
    const isINR = curr === 'INR' || curr === '₹';
    if (job.salary_min && job.salary_max) {
      if (isINR) {
        return `₹${(job.salary_min / 100000).toFixed(1)}L – ${(job.salary_max / 100000).toFixed(1)}L / yr`;
      }
      return `${curr}${Math.round(job.salary_min / 1000)}k – ${curr}${Math.round(job.salary_max / 1000)}k / yr`;
    }
    const val = job.salary_min || job.salary_max;
    if (isINR) return `₹${(val / 100000).toFixed(1)}L / yr`;
    return `${curr}${Math.round(val / 1000)}k / yr`;
  };

  const formatExp = () => {
    if (job.min_exp !== null && job.max_exp !== null) {
      return `${job.min_exp} – ${job.max_exp} years`;
    }
    if (job.min_exp !== null) {
      return `${job.min_exp}+ years`;
    }
    return 'Not specified';
  };

  const formatPostedAt = () => {
    if (!job.posted_at) return 'Recently';
    try {
      return new Date(job.posted_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'Recently';
    }
  };

  const primarySource = job.sources?.[0];
  const siblingSources = job.sources?.slice(1) || [];

  return (
    <div className="h-[calc(100vh-97px)] sticky top-[97px] bg-white border-l border-neutral-200 overflow-y-auto p-6 flex flex-col justify-between text-xs">
      <div className="space-y-6">
        {/* Top Header */}
        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                {job.company}
              </span>
              <h1 className="text-lg font-bold text-[#111827] tracking-tight leading-snug">
                {job.title}
              </h1>
            </div>

            <button
              onClick={() => onToggleSave(job)}
              className="p-1.5 rounded-lg border border-neutral-200 text-neutral-600 hover:text-[#111827] hover:bg-neutral-50 transition-colors shrink-0"
              title={job.is_saved ? 'Remove bookmark' : 'Bookmark job'}
            >
              <Bookmark
                className={`w-4 h-4 ${job.is_saved ? 'fill-[#111827] text-[#111827]' : ''}`}
              />
            </button>
          </div>

          {/* Badges strip */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className="inline-flex items-center gap-1 text-neutral-600 bg-neutral-100 px-2 py-0.5 rounded text-[11px] font-medium border border-neutral-200">
              <MapPin className="w-3 h-3 text-neutral-400" />
              {job.city || job.location || 'Unspecified'}
            </span>
            {job.is_remote && (
              <span className="bg-emerald-50 text-emerald-800 text-[11px] font-medium px-2 py-0.5 rounded border border-emerald-200">
                Remote
              </span>
            )}
            <span className="bg-neutral-100 text-neutral-700 text-[11px] font-medium px-2 py-0.5 rounded border border-neutral-200">
              {job.category}
            </span>
          </div>
        </div>

        {/* Key Metadata Grid */}
        <div className="grid grid-cols-2 gap-3 p-3.5 bg-[#F9F9F8] rounded-lg border border-neutral-200">
          <div>
            <span className="text-[11px] text-neutral-500 block mb-0.5">Experience</span>
            <span className="font-mono text-neutral-900 font-medium">{formatExp()}</span>
          </div>
          <div>
            <span className="text-[11px] text-neutral-500 block mb-0.5">Compensation</span>
            <span className="font-mono text-neutral-900 font-medium">{formatSalary()}</span>
          </div>
          <div>
            <span className="text-[11px] text-neutral-500 block mb-0.5">Employment Type</span>
            <span className="font-medium text-neutral-900">{job.job_type || 'Full-time'}</span>
          </div>
          <div>
            <span className="text-[11px] text-neutral-500 block mb-0.5">Date Posted</span>
            <span className="font-mono text-neutral-900">{formatPostedAt()}</span>
          </div>
        </div>

        {/* Application Tracking Console */}
        <div className="p-3.5 bg-white rounded-lg border border-neutral-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-neutral-900 text-xs">Application Pipeline</span>
            <span className="text-[10px] font-mono text-neutral-400 uppercase">
              {job.application_status !== 'none' ? 'Tracked' : 'Not Tracked'}
            </span>
          </div>

          <div className="flex flex-wrap gap-1">
            {STATUS_OPTIONS.map((opt) => {
              const active = job.application_status === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => onUpdateTracking(job.id, { application_status: opt.value })}
                  disabled={isTrackingPending}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                    active
                      ? 'bg-[#111827] text-white'
                      : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          {/* Personal Notes */}
          <div>
            <button
              onClick={() => setShowNotes(!showNotes)}
              className="text-neutral-500 hover:text-neutral-900 text-[11px] flex items-center gap-1 font-medium mt-1"
            >
              <span>Personal Notes</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${showNotes ? 'rotate-180' : ''}`} />
            </button>

            {showNotes && (
              <div className="mt-2">
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  onBlur={() => {
                    if (notes !== (job.notes || '')) {
                      onUpdateTracking(job.id, { notes });
                    }
                  }}
                  placeholder="Referral name, interview rounds, salary expectations, follow-up dates..."
                  rows={3}
                  className="w-full bg-[#F7F7F5] border border-neutral-200 rounded-md p-2 text-xs text-[#111827] placeholder-neutral-400 focus:outline-none focus:border-neutral-400 focus:bg-white transition-colors"
                />
              </div>
            )}
          </div>
        </div>

        {/* Direct Apply Multi-Platform Cluster */}
        <div className="space-y-2">
          {primarySource && (
            <a
              href={primarySource.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-[#111827] text-white hover:bg-neutral-800 rounded-lg py-2.5 px-4 font-medium flex items-center justify-center gap-2 text-xs transition-colors"
            >
              <span>Apply on {primarySource.source_name.toUpperCase()}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}

          {siblingSources.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-medium text-neutral-500 block">
                Also found on {siblingSources.length} other {siblingSources.length === 1 ? 'board' : 'boards'}:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {siblingSources.map((s) => (
                  <a
                    key={s.id}
                    href={s.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 font-medium text-[11px] transition-colors"
                  >
                    <span className="capitalize">{s.source_name}</span>
                    <ExternalLink className="w-3 h-3 text-neutral-400" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Full Editorial Description */}
        <div className="pt-4 border-t border-neutral-200">
          <h3 className="font-semibold text-neutral-900 text-xs mb-3 uppercase tracking-wider text-neutral-400">
            Job Description
          </h3>
          <div className="max-w-prose leading-relaxed text-neutral-800 text-xs whitespace-pre-line space-y-3 font-sans">
            {job.description || 'No description provided by the source board.'}
          </div>
        </div>
      </div>
    </div>
  );
}
