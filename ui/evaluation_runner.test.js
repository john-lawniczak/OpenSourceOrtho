import test from "node:test";
import assert from "node:assert/strict";
import { createEvaluationRunner } from "./evaluation_runner.js";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const flush = async () => { await Promise.resolve(); await Promise.resolve(); };

test("an edit invalidates an in-flight evaluation before the next request starts", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const requests = [deferred(), deferred()];
  const results = [], errors = [], pending = [];
  let index = 0;
  const schedule = createEvaluationRunner({ getPayload: () => ({}), evaluate: () => requests[index++].promise,
    onResult: (value) => results.push(value), onError: (error) => errors.push(error), onPending: () => pending.push(true) });
  schedule();
  t.mock.timers.tick(150);
  schedule(); // second request still debouncing; first response must already be obsolete
  requests[0].resolve("old");
  await flush();
  assert.deepEqual(results, []);
  t.mock.timers.tick(150);
  requests[1].resolve("new");
  await flush();
  assert.deepEqual(results, ["new"]);
  assert.deepEqual(errors, []);
  assert.equal(pending.length, 2);
});

test("stale errors cannot erase newer results; current errors are surfaced", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const requests = [deferred(), deferred(), deferred()];
  const results = [], errors = [];
  let index = 0;
  const schedule = createEvaluationRunner({ getPayload: () => ({}), evaluate: () => requests[index++].promise,
    onResult: (value) => results.push(value), onError: (error) => errors.push(error.message), onPending() {} });
  schedule(); t.mock.timers.tick(150);
  schedule(); t.mock.timers.tick(150);
  requests[1].resolve("new"); await flush();
  requests[0].reject(new Error("old")); await flush();
  assert.deepEqual(results, ["new"]);
  assert.deepEqual(errors, []);
  schedule(); t.mock.timers.tick(150);
  requests[2].reject(new Error("offline")); await flush();
  assert.deepEqual(errors, ["offline"]);
});

test("UI-only updates share evaluations while plan edits get fresh results", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const first = deferred();
  let payload = { stage: 1 }, calls = 0;
  const results = [];
  const schedule = createEvaluationRunner({ getPayload: () => payload, cacheKey: JSON.stringify,
    evaluate: () => { calls++; return calls === 1 ? first.promise : Promise.resolve('edited'); },
    onResult: value => results.push(value), onError() {}, onPending() {} });
  schedule(); t.mock.timers.tick(150);
  schedule(); t.mock.timers.tick(150);
  assert.equal(calls, 1);
  first.resolve('initial'); await flush();
  assert.deepEqual(results, ['initial']);
  schedule(); t.mock.timers.tick(150); await flush();
  assert.equal(calls, 1);
  payload = { stage: 2 };
  schedule(); t.mock.timers.tick(150); await flush();
  assert.equal(calls, 2);
  assert.equal(results.at(-1), 'edited');
});

test("applying an already evaluated preview does not repeat the engine request", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let calls = 0;
  const results = [];
  const schedule = createEvaluationRunner({ getPayload: () => ({ stage: 2 }), cacheKey: JSON.stringify,
    evaluate: async () => { calls++; }, onPending() {}, onError() {}, onResult: result => results.push(result) });
  schedule.prime({ stage: 2 }, 'preview checks');
  schedule(); t.mock.timers.tick(150); await flush();
  assert.equal(calls, 0);
  assert.deepEqual(results, ['preview checks']);
});

test("an unsuccessful evaluation is retried instead of cached permanently", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let calls = 0;
  const results = [];
  const schedule = createEvaluationRunner({ getPayload: () => ({}), cacheKey: JSON.stringify,
    evaluate: async () => ++calls === 1 ? { ok: false, errors: ['temporary failure'] } : { ok: true },
    onPending() {}, onError() {}, onResult: result => results.push(result) });
  schedule(); t.mock.timers.tick(150); await flush();
  schedule(); t.mock.timers.tick(150); await flush();
  assert.equal(calls, 2);
  assert.equal(results.at(-1).ok, true);
});

test('plan edits abort obsolete geometry workers', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let payload = {revision: 1};
  const signals = [];
  const schedule = createEvaluationRunner({getPayload:()=>payload, cacheKey:JSON.stringify,
    evaluate: (_payload, {signal}) => { signals.push(signal); return new Promise(()=>{}); },
    onResult(){}, onError(){}, onPending(){}});
  schedule(); t.mock.timers.tick(150);
  schedule(); assert.equal(signals[0].aborted, false);
  payload = {revision:2}; schedule();
  assert.equal(signals[0].aborted, true);
});
