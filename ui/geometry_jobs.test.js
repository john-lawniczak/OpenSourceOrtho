import test from 'node:test';
import assert from 'node:assert/strict';
import { geometryJob } from './geometry_jobs.js';

test('abort during creation cancels the resulting server job', async t => {
  const calls = [];
  let created;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push([url, options]);
    if (url === '/api/geometry-jobs') return new Promise(resolve => { created = () => resolve({ok:true, json:async()=>({ok:true,job_id:'late'})}); });
    return {ok:true,json:async()=>({ok:true})};
  });
  const controller = new AbortController();
  const promise = geometryJob('evaluate', {}, {signal:controller.signal});
  controller.abort(); created();
  await assert.rejects(promise, {name:'AbortError'});
  assert.ok(calls.some(([url, opts])=>url.endsWith('/cancel') && JSON.parse(opts.body).job_id === 'late'));
  assert.equal(calls.filter(([url])=>url.endsWith('/late')).length, 0);
});

test('completed job returns engine response and releases server storage', async t => {
  const calls=[];
  let cleanupConsumed = false;
  t.mock.method(globalThis, 'fetch', async url => {
    calls.push(url);
    return {ok:true,json:async()=> {
      if (url.endsWith('/cancel')) cleanupConsumed = true;
      return url.endsWith('/geometry-jobs') ? {ok:true,job_id:'done'} :
        {ok:true,status:'complete',result:{ok:true,frames:[]}};
    }};
  });
  assert.deepEqual(await geometryJob('evaluate', {}), {ok:true,frames:[]});
  assert.ok(calls.includes('/api/geometry-jobs/cancel'));
  assert.equal(cleanupConsumed, true);
});

test('transient worker saturation is retried without dropping a scan operation', async t => {
  let attempts=0;
  t.mock.method(globalThis, 'fetch', async url => ({ok:true,json:async()=> {
    if (url === '/api/geometry-jobs') return ++attempts === 1
      ? {ok:false,retryable:true,errors:['busy']} : {ok:true,job_id:'retry'};
    return {ok:true,status:'complete',result:{ok:true}};
  }}));
  assert.deepEqual(await geometryJob('segment', {}), {ok:true});
  assert.equal(attempts, 2);
});
