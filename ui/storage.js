const DB_NAME = "opensource-ortho";
const DB_VERSION = 1;
const STORE = "uploads";
const UPLOAD_KEY = "current-stl-files";

function openDb() {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      reject(new Error("IndexedDB is not available"));
      return;
    }
    const request = window.indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore(mode, callback) {
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const store = tx.objectStore(STORE);
      let result;
      try {
        result = callback(store);
      } catch (error) {
        reject(error);
        return;
      }
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error("IndexedDB transaction aborted"));
    });
  } finally {
    db.close();
  }
}

export async function saveUploadedFiles(files) {
  await withStore("readwrite", (store) => {
    store.put(Array.from(files), UPLOAD_KEY);
  });
}

export async function restoreUploadedFiles() {
  return withStore("readonly", (store) => new Promise((resolve, reject) => {
    const request = store.get(UPLOAD_KEY);
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  }));
}

export async function clearUploadedFiles() {
  await withStore("readwrite", (store) => {
    store.delete(UPLOAD_KEY);
  });
}
