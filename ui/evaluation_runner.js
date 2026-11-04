// Scheduling invalidates older requests immediately, including the debounce gap.
export function createEvaluationRunner({ getPayload, evaluate, onResult, onError, onPending, cacheKey, delay = 150 }) {
  let revision = 0;
  let timer;
  let active;
  const cache = new Map();
  async function run(token) {
    try {
      const payload = getPayload();
      const key = cacheKey?.(payload);
      let request = key ? cache.get(key) : null;
      if (!request) {
        const controller = new AbortController();
        active = { key, controller };
        request = Promise.resolve(evaluate(payload, { signal: controller.signal }));
        active.request = request;
        if (key) {
          cache.set(key, request);
          if (cache.size > 4) cache.delete(cache.keys().next().value);
          request.catch(() => { if (cache.get(key) === request) cache.delete(key); });
        }
      }
      const result = await request;
      if (active?.request === request) active = null;
      if (key && result?.ok === false && cache.get(key) === request) cache.delete(key);
      if (token === revision) onResult(result);
    } catch (error) {
      if (token === revision) onError(error);
    }
  }
  function schedule() {
    const token = ++revision;
    clearTimeout(timer);
    const key = cacheKey?.(getPayload());
    if (active && (!key || active.key !== key)) {
      active.controller.abort();
      if (active.key) cache.delete(active.key);
      active = null;
    }
    onPending();
    timer = setTimeout(() => run(token), delay);
  }
  schedule.prime = (payload, result) => {
    const key = cacheKey?.(payload);
    if (key) cache.set(key, Promise.resolve(result));
    if (cache.size > 4) cache.delete(cache.keys().next().value);
  };
  return schedule;
}
