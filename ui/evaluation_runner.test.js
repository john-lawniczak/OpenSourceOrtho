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
