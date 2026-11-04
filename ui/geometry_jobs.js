// A cancelled browser request must also stop the CPU worker on the local server.
export async function geometryJob(operation, payload, { signal } = {}) {
  let jobId;
  const cancel = () => {
    if (jobId) void fetch('/api/geometry-jobs/cancel', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId }), keepalive: true,
    }).catch(() => {});
  };
  const check = async response => {
    const result = await response.json();
    if (!response.ok || result.ok === false) throw new Error((result.errors || ['Geometry request failed']).join('; '));
    return result;
  };
  signal?.throwIfAborted();
  globalThis.addEventListener?.("pagehide", cancel);
  signal?.addEventListener('abort', cancel, { once: true });
  try {
    // Do not abort creation: we need the returned ID to cancel a job created
    // while the user changes inputs. No mesh data or credentials enter the URL.
    let job;
    const admissionDeadline = Date.now() + 15000;
    do {
      signal?.throwIfAborted();
      const response = await fetch('/api/geometry-jobs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation, payload }),
      });
      job = await response.json();
      if (response.ok && job.retryable && Date.now() < admissionDeadline) {
        await new Promise(resolve => setTimeout(resolve, 250));
        continue;
      }
      if (!response.ok || job.ok === false) throw new Error((job.errors || ['Geometry request failed']).join('; '));
      break;
    } while (true);
    if (!job.job_id) throw new Error("Geometry server did not return a job ID");
    jobId = job.job_id;
    if (signal?.aborted) { cancel(); signal.throwIfAborted(); }
    const deadline = Date.now() + 135000;
    while (Date.now() < deadline) {
      signal?.throwIfAborted();
      const status = await check(await fetch(`/api/geometry-jobs/${jobId}`, { signal }));
      if (status.status === 'complete') return status.result;
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw new Error('Geometry request timed out');
  } catch (error) {
    cancel();
    throw error;
  } finally {
    signal?.removeEventListener('abort', cancel);
    globalThis.removeEventListener?.('pagehide', cancel);
    cancel(); // Release completed result files too.
  }
}
