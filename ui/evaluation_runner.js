// Scheduling invalidates older requests immediately, including the debounce gap.
export function createEvaluationRunner({ getPayload, evaluate, onResult, onError, onPending, delay = 150 }) {
  let revision = 0;
  let timer;
  async function run(token) {
    try {
      const result = await evaluate(getPayload());
      if (token === revision) onResult(result);
    } catch (error) {
      if (token === revision) onError(error);
    }
  }
  return function schedule() {
    const token = ++revision;
    clearTimeout(timer);
    onPending();
    timer = setTimeout(() => run(token), delay);
  };
}
