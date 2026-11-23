import React from 'react';
import { ExternalLink, Trash2, ArrowRight, MessageSquare, Briefcase } from 'lucide-react';

const STAGES = [
  { id: 'saved', label: 'Saved', color: 'border-neutral-300 bg-neutral-100 text-neutral-800' },
  { id: 'applied', label: 'Applied', color: 'border-blue-300 bg-blue-50 text-blue-800' },
  { id: 'interview', label: 'Interview', color: 'border-amber-300 bg-amber-50 text-amber-800' },
  { id: 'offer', label: 'Offer Received', color: 'border-emerald-300 bg-emerald-50 text-emerald-800' },
  { id: 'rejected', label: 'Rejected', color: 'border-red-300 bg-red-50 text-red-800' },
];

export default function TrackerBoard({
  jobs = [],
  onUpdateTracking,
  onSelectJob,
  isLoading,
}) {
  const getJobsByStage = (stageId) => {
    return jobs.filter((j) => j.application_status === stageId);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center text-xs text-neutral-500 font-mono">
        Loading tracker pipeline...
      </div>
    );
  }

  const totalTracked = jobs.filter((j) => j.application_status && j.application_status !== 'none').length;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-base font-bold text-[#111827] tracking-tight">
            Application Pipeline
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Organize, track, and monitor every stage of your job applications with custom notes.
          </p>
        </div>
        <span className="font-mono text-xs bg-neutral-100 border border-neutral-200 px-2.5 py-1 rounded text-neutral-700">
          {totalTracked} Active Applications
        </span>
      </div>

      {/* Kanban Columns */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 items-start">
        {STAGES.map((stage) => {
          const stageJobs = getJobsByStage(stage.id);
          return (
            <div
              key={stage.id}
              className="bg-[#FFFFFF] border border-neutral-200 rounded-lg p-3 min-h-[500px] flex flex-col justify-between"
            >
              <div>
                {/* Column Header */}
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-100">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-[#111827]">{stage.label}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-600 font-medium border border-neutral-200">
                      {stageJobs.length}
                    </span>
                  </div>
                </div>

                {/* Cards List */}
                <div className="space-y-2.5">
                  {stageJobs.map((job) => (
                    <div
                      key={job.id}
                      onClick={() => onSelectJob(job)}
                      className="p-3 bg-white border border-neutral-200 rounded-md hover:border-neutral-300 transition-shadow cursor-pointer text-xs space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <span className="text-[10px] uppercase font-semibold text-neutral-400 block truncate">
                            {job.company}
                          </span>
                          <h4 className="font-semibold text-[#111827] text-xs leading-snug truncate">
                            {job.title}
                          </h4>
                        </div>
                      </div>

                      {/* City / Remote badge */}
                      <div className="flex items-center gap-1.5 text-[10px] text-neutral-500">
                        <span>{job.city || job.location || 'Remote'}</span>
                        {job.is_remote && (
                          <span className="bg-emerald-50 text-emerald-800 px-1 rounded text-[9px] font-medium border border-emerald-200">
                            Remote
                          </span>
                        )}
                      </div>

                      {/* Notes Preview */}
                      {job.notes && (
                        <div className="bg-[#F9F9F8] p-1.5 rounded border border-neutral-100 text-[11px] text-neutral-600 flex items-start gap-1">
                          <MessageSquare className="w-3 h-3 text-neutral-400 shrink-0 mt-0.5" />
                          <p className="line-clamp-2 italic">{job.notes}</p>
                        </div>
                      )}

                      {/* Controls Footer */}
                      <div className="flex items-center justify-between pt-2 border-t border-neutral-100">
                        {/* Stage Selector */}
                        <select
                          value={job.application_status}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) =>
                            onUpdateTracking(job.id, { application_status: e.target.value })
                          }
                          className="bg-[#F7F7F5] border border-neutral-200 text-neutral-700 text-[10px] rounded px-1.5 py-0.5 font-medium focus:outline-none"
                        >
                          {STAGES.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                          <option value="none">Untrack</option>
                        </select>

                        {/* Direct Apply Link */}
                        {job.sources?.[0] && (
                          <a
                            href={job.sources[0].apply_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-neutral-500 hover:text-[#111827] p-1 transition-colors"
                            title={`Apply on ${job.sources[0].source_name}`}
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}

                  {stageJobs.length === 0 && (
                    <div className="py-8 text-center text-neutral-400 text-[11px]">
                      No roles in {stage.label.toLowerCase()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
