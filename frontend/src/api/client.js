const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchJobs(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== false) {
      query.set(key, value);
    }
  });

  const res = await fetch(`${API_BASE_URL}/api/jobs?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch jobs: ${res.statusText}`);
  return res.json();
}

export async function fetchJobById(jobId) {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job #${jobId}`);
  return res.json();
}

export async function updateJobTracking(jobId, payload) {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/track`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update job tracking: ${res.statusText}`);
  return res.json();
}

export async function fetchFilters() {
  const res = await fetch(`${API_BASE_URL}/api/filters`);
  if (!res.ok) throw new Error(`Failed to fetch filter facets: ${res.statusText}`);
  return res.json();
}

export async function fetchSyncStatus() {
  const res = await fetch(`${API_BASE_URL}/api/sync/status`);
  if (!res.ok) throw new Error(`Failed to fetch sync status: ${res.statusText}`);
  return res.json();
}

export async function triggerSync(mode = 'fast') {
  const res = await fetch(`${API_BASE_URL}/api/sync?mode=${mode}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to trigger sync: ${res.statusText}`);
  return res.json();
}
