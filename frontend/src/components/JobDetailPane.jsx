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
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  ArrowLeft,
  X,
} from 'lucide-react';
import { fetchJobDetail } from '../api/client.js';
import { formatSourceName } from './FilterSidebar.jsx';

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
  onVerifyLiveness,
  onMarkExpired,
  isVerifying = false,
  verificationResult = null,
  onClose = null,
}) {
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [liveDesc, setLiveDesc] = useState(job?.description || null);
  const [isLoadingDesc, setIsLoadingDesc] = useState(false);
  const [isJobExpired, setIsJobExpired] = useState(job ? !job.is_active : false);

  useEffect(() => {
    if (job) {
      setNotes(job.notes || '');
      setShowNotes(Boolean(job.notes));
      setLiveDesc(job.description || null);
      setIsJobExpired(!job.is_active);

      // On-demand fetch if description is not yet populated
      if (!job.description) {
        setIsLoadingDesc(true);
        fetchJobDetail(job.id)
          .then((res) => {
            if (res.status === 'expired' || res.is_active === false) {
              setIsJobExpired(true);
              onMarkExpired?.(job.id);
            } else if (res.description) {
              setLiveDesc(res.description);
            }
          })
          .catch((err) => {
            console.warn('[JobDetail] On-demand fetch error:', err);
          })
          .finally(() => {
            setIsLoadingDesc(false);
          });
      }
    }
  }, [job?.id]);

  if (!job) {
    return (
      <div className="h-full bg-white border-l border-neutral-200 flex flex-col items-center justify-center p-8 text-center text-neutral-400 text-xs">
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

  const renderCleanDescription = (raw) => {
    if (!raw) {
      return (
        <p className="text-neutral-400 italic">No description provided by the source board.</p>
      );
    }

    // Step 1: Decode HTML entities (&lt; -> <, &amp; -> &, &#39; -> ', etc.)
    let content = raw;
    try {
      const textarea = document.createElement('textarea');
      textarea.innerHTML = content;
      content = textarea.value;
      if (content.includes('&lt;') || content.includes('&gt;')) {
        textarea.innerHTML = content;
        content = textarea.value;
      }
    } catch {
      content = content
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'");
    }

    // Step 2: Convert HTML tags into structured text if HTML tags present
    if (/<[a-z][\s\S]*>/i.test(content)) {
      try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(content, 'text/html');

        doc.querySelectorAll('li').forEach((li) => {
          li.textContent = `• ${li.textContent.trim()}\n`;
        });

        doc.querySelectorAll('p, div, h1, h2, h3, h4, h5, h6, ul, ol').forEach((el) => {
          el.insertAdjacentText('afterend', '\n\n');
        });

        doc.querySelectorAll('br').forEach((br) => {
          br.replaceWith('\n');
        });

        content = doc.body.textContent || content;
      } catch {
        content = content
          .replace(/<li[^>]*>/gi, '• ')
          .replace(/<\/li>/gi, '\n')
          .replace(/<\/p>|<\/div>|<br\s*\/?>/gi, '\n\n')
          .replace(/<[^>]+>/g, '');
      }
    }

    // Step 3: Split into clean paragraphs and formatted sections
    const blocks = content
      .split(/\n{2,}/)
      .map((b) => b.trim())
      .filter(Boolean);

    return (
      <div className="space-y-3.5 leading-relaxed text-xs text-neutral-700">
        {blocks.map((block, idx) => {
          // Bullet point lists
          if (block.includes('• ') || block.startsWith('- ') || block.startsWith('* ')) {
            const lines = block.split(/\n+/).map((l) => l.trim()).filter(Boolean);
            return (
              <ul key={idx} className="space-y-1.5 pl-1 my-2">
                {lines.map((line, lIdx) => {
                  const itemText = line.replace(/^[•\-\*]\s*/, '').trim();
                  return (
                    <li key={lIdx} className="flex items-start gap-2">
                      <span className="text-[#F26825] font-bold shrink-0 mt-0.5">•</span>
                      <span className="flex-1 leading-relaxed text-neutral-700">{itemText}</span>
                    </li>
                  );
                })}
              </ul>
            );
          }

          // Section headings
          const isHeading =
            block.length < 80 &&
            (block.endsWith(':') ||
              /^(about|who we are|what you|responsibilities|requirements|qualifications|benefits|perks|preferred|minimum|the role|our values|what we offer|role overview)/i.test(block));

          if (isHeading) {
            return (
              <h4
                key={idx}
                className="font-bold text-neutral-900 text-xs pt-2.5 pb-0.5 tracking-tight border-b border-neutral-100 uppercase tracking-wide"
              >
                {block.replace(/^(\*\*|#+)\s*/, '').replace(/\*\*$/, '')}
              </h4>
            );
          }

          return (
            <p key={idx} className="text-neutral-700 leading-relaxed">
              {block}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="h-full bg-white border-l border-neutral-200 overflow-y-auto p-4 sm:p-6 flex flex-col justify-between text-xs">
      <div className="space-y-6">
        {/* Mobile Back / Close Navigation Bar */}
        {onClose && (
          <div className="flex items-center justify-between pb-3 -mt-1 border-b border-neutral-100 lg:hidden">
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 text-xs font-semibold text-[#0F172A] hover:text-[#F26825] px-2.5 py-1.5 rounded-lg bg-neutral-100 hover:bg-orange-50 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to openings</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
              aria-label="Close pane"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

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
              className="p-1.5 rounded-lg border border-neutral-200 text-neutral-600 hover:text-[#F26825] hover:bg-neutral-50 transition-colors shrink-0"
              title={job.is_saved ? 'Remove bookmark' : 'Bookmark job'}
            >
              <Bookmark
                className={`w-4 h-4 ${job.is_saved ? 'fill-[#F26825] text-[#F26825]' : ''}`}
              />
            </button>
          </div>

          {/* Badges strip */}
          <div className="flex flex-wrap items-center gap-1.5 mt-3">
            <span className="inline-flex items-center gap-1 text-neutral-600 bg-neutral-100 px-2 py-0.5 rounded text-[11px] font-medium border border-neutral-200">
              <MapPin className="w-3 h-3 text-neutral-400" />
              {job.city || job.location || 'Unspecified'}
            </span>

            {job.country === 'India' && (
              <span className="bg-orange-50 text-[#F26825] font-semibold text-[11px] px-2 py-0.5 rounded border border-orange-200 flex items-center gap-1">
                <span>🇮🇳</span>
                <span>India Role</span>
              </span>
            )}

            {job.is_remote && (
              <span className="bg-emerald-50 text-emerald-800 text-[11px] font-medium px-2 py-0.5 rounded border border-emerald-200">
                Remote
              </span>
            )}

            <span className="bg-neutral-100 text-neutral-700 text-[11px] font-medium px-2 py-0.5 rounded border border-neutral-200">
              {job.category}
            </span>

            {job.is_active ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Live on Source</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded border border-neutral-200">
                <AlertTriangle className="w-3 h-3 text-amber-500" />
                <span>Closed / Expired</span>
              </span>
            )}
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

        {/* Direct Apply & Live Verification Cluster */}
        <div className="space-y-2.5">
          {primarySource && (
            <a
              href={primarySource.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-[#F26825] text-white hover:bg-[#D95B1E] rounded-lg py-2.5 px-4 font-semibold flex items-center justify-center gap-2 text-xs transition-colors shadow-sm"
            >
              <span>Apply on {formatSourceName(primarySource.source_name)}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}

          {/* Liveness Check Actions */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onVerifyLiveness(job.id)}
              disabled={isVerifying}
              className="flex-1 py-1.5 px-3 rounded-md border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 font-medium text-[11px] transition-colors flex items-center justify-center gap-1.5"
            >
              <RefreshCw className={`w-3 h-3 ${isVerifying ? 'animate-spin text-[#F26825]' : 'text-neutral-500'}`} />
              <span>{isVerifying ? 'Checking URL...' : 'Verify Live Link'}</span>
            </button>

            {job.is_active && (
              <button
                type="button"
                onClick={() => onMarkExpired(job.id)}
                title="Mark this job as closed/expired"
                className="py-1.5 px-2.5 rounded-md border border-neutral-200 bg-white hover:bg-red-50 hover:text-red-600 hover:border-red-200 text-neutral-500 font-medium text-[11px] transition-colors"
              >
                Mark Closed
              </button>
            )}
          </div>

          {/* Verification Feedback Pill */}
          {verificationResult && verificationResult.job_id === job.id && (
            <div
              className={`p-2 rounded-md text-[11px] font-medium border flex items-center gap-1.5 ${
                verificationResult.is_active
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-red-50 text-red-800 border-red-200'
              }`}
            >
              {verificationResult.is_active ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-red-600 shrink-0" />
              )}
              <span>{verificationResult.message}</span>
            </div>
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
                    <span>{formatSourceName(s.source_name)}</span>
                    <ExternalLink className="w-3 h-3 text-neutral-400" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Full Editorial Description */}
        <div className="pt-4 border-t border-neutral-200 pb-16 lg:pb-0">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-neutral-900 text-xs uppercase tracking-wider text-neutral-400">
              Job Description
            </h3>
            {isLoadingDesc && (
              <span className="flex items-center gap-1.5 text-[10px] text-[#F26825] font-medium animate-pulse">
                <RefreshCw className="w-3 h-3 animate-spin" />
                <span>Loading live details...</span>
              </span>
            )}
          </div>

          {isJobExpired ? (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              <span>This role has been closed by the employer on their career portal.</span>
            </div>
          ) : isLoadingDesc ? (
            <div className="space-y-2.5 animate-pulse py-2">
              <div className="h-3.5 bg-neutral-200 rounded w-3/4"></div>
              <div className="h-3 bg-neutral-100 rounded w-full"></div>
              <div className="h-3 bg-neutral-100 rounded w-5/6"></div>
              <div className="h-3 bg-neutral-100 rounded w-4/6"></div>
              <div className="h-3 bg-neutral-100 rounded w-2/3"></div>
            </div>
          ) : (
            <div className="max-w-prose leading-relaxed text-neutral-800 text-xs font-sans">
              {renderCleanDescription(liveDesc || job.description)}
            </div>
          )}
        </div>
      </div>

      {/* Mobile Sticky Quick Apply Bar */}
      {onClose && (
        <div className="sticky bottom-0 -mx-4 -mb-4 sm:-mx-6 sm:-mb-6 p-3 bg-white/95 backdrop-blur-md border-t border-neutral-200 mt-6 lg:hidden flex items-center gap-2 z-10 shadow-lg">
          <button
            onClick={() => onToggleSave(job)}
            className="p-2.5 rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-50 shrink-0"
            aria-label="Save Job"
          >
            <Bookmark className={`w-4 h-4 ${job.is_saved ? 'fill-[#F26825] text-[#F26825]' : ''}`} />
          </button>
          <a
            href={primarySource?.apply_url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#F26825] hover:bg-[#D95B1E] text-white font-semibold rounded-lg text-xs transition-colors shadow-sm"
          >
            <span>Apply on {primarySource?.source_name ? primarySource.source_name.toUpperCase() : 'Company Board'}</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}
    </div>
  );
}
