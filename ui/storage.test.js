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
