import assert from "node:assert/strict";
import { test } from "node:test";

function makeIndexedDbStub() {
  const data = new Map();
  return {
    open() {
      const request = {};
      queueMicrotask(() => {
        request.result = {
          createObjectStore() {},
          transaction() {
            const tx = {
              objectStore() {
                return {
                  put(value, key) {
                    data.set(key, value);
                    queueMicrotask(() => tx.oncomplete?.());
                  },
                  get(key) {
                    const getRequest = {};
                    queueMicrotask(() => {
                      getRequest.result = data.get(key);
                      getRequest.onsuccess?.();
                      tx.oncomplete?.();
                    });
                    return getRequest;
                  },
                  delete(key) {
                    data.delete(key);
                    queueMicrotask(() => tx.oncomplete?.());
                  },
                };
              },
            };
            return tx;
          },
          close() {},
        };
        request.onupgradeneeded?.();
        request.onsuccess?.();
      });
      return request;
    },
  };
}

test("uploaded STL files can be saved, restored, and cleared", async () => {
  globalThis.window = { indexedDB: makeIndexedDbStub() };
  const { clearUploadedFiles, restoreUploadedFiles, saveUploadedFiles } = await import("./storage.js");
  const files = [
    { name: "upper.stl", size: 12 },
    { name: "lower.stl", size: 34 },
  ];

  await saveUploadedFiles(files);
  assert.deepEqual(await restoreUploadedFiles(), files);

  await clearUploadedFiles();
  assert.deepEqual(await restoreUploadedFiles(), []);
});

test("upload storage reports unavailable IndexedDB clearly", async () => {
  globalThis.window = {};
  const { saveUploadedFiles } = await import("./storage.js");

  await assert.rejects(
    () => saveUploadedFiles([{ name: "upper.stl" }]),
    /IndexedDB is not available/,
  );
});

function makeLocalStorageStub() {
  const data = new Map();
  return {
    setItem(key, value) { data.set(key, String(value)); },
    getItem(key) { return data.has(key) ? data.get(key) : null; },
    removeItem(key) { data.delete(key); },
  };
}

test("segmentation review persists per plan id and round-trips", async () => {
  globalThis.localStorage = makeLocalStorageStub();
  const { saveSegmentationReview, restoreSegmentationReview, clearSegmentationReview } =
    await import("./storage.js");

  const review = { missingTeeth: "15", edits: { a1: { tooth: "14", included: true } }, applied: null };
  saveSegmentationReview("case-1", review);
  assert.deepEqual(restoreSegmentationReview("case-1"), review);
  // Keyed by plan id: a different case is independent.
  assert.equal(restoreSegmentationReview("case-2"), null);

  clearSegmentationReview("case-1");
  assert.equal(restoreSegmentationReview("case-1"), null);
});

test("segmentation review save/restore is a no-op without a plan id or storage", async () => {
  globalThis.localStorage = makeLocalStorageStub();
  const { saveSegmentationReview, restoreSegmentationReview } = await import("./storage.js");
  saveSegmentationReview("", { missingTeeth: "15" });
  assert.equal(restoreSegmentationReview(""), null);

  delete globalThis.localStorage;
  assert.equal(restoreSegmentationReview("case-3"), null);
});
