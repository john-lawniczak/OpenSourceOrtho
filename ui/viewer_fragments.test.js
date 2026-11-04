import test from 'node:test';
import assert from 'node:assert/strict';
import { createFragmentLoader } from './viewer_fragments.js';

test('fragment loading deduplicates requests and rejects stale scan responses', async () => {
  const original = globalThis.fetch;
  const pending = [];
  globalThis.fetch = () => new Promise(resolve => pending.push(resolve));
  const store = createFragmentLoader(bytes => ({ bytes, dispose() {} }), () => {});
  try {
    const old = store.load([{ tooth: '11', url: '/old' }]);
    const duplicate = store.load([{ tooth: '11', url: '/old' }]);
    assert.equal(duplicate, old);
    assert.equal(pending.length, 1);
    const next = store.load([{ tooth: '12', url: '/new' }]);
    pending[0]({ ok: true, arrayBuffer: async () => 'old' });
    pending[1]({ ok: true, arrayBuffer: async () => 'new' });
    assert.equal(await old, false);
    assert.equal(await next, true);
    assert.deepEqual([...store.cache.keys()], ['12']);
    store.clear();
    assert.equal(store.cache.size, 0);
  } finally { globalThis.fetch = original; }
});

test('a partial failed load is disposed and can be retried with the same URLs', async (t) => {
  const disposed = [];
  let fail = true;
  t.mock.method(globalThis, 'fetch', async url => ({ ok: !(fail && url === '/12'), arrayBuffer: async () => url }));
  const store = createFragmentLoader(bytes => ({ bytes, dispose() { disposed.push(bytes); } }), () => {});
  const items = [{ tooth: '11', url: '/11' }, { tooth: '12', url: '/12' }];
  assert.equal(await store.load(items), false);
  assert.equal(store.cache.size, 0);
  assert.deepEqual(disposed, ['/11']);
  assert.match(store.error, /could not be loaded/);
  fail = false;
  assert.equal(await store.load(items), true);
  assert.equal(store.cache.size, 2);
  assert.equal(store.error, '');
});
