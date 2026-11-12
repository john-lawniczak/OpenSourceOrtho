// Explicit local saves include original bytes so fitting can be repeated after restart.
async function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("ortho-two-visit-cases", 2);
    request.onupgradeneeded = () => {
      for (const name of ["cases","edits"]) if (!request.result.objectStoreNames.contains(name)) request.result.createObjectStore(name, {keyPath:"name"});
    };
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
}
export async function caseStore(operation, value, store = "cases") {
  const db = await database();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, ["put","delete"].includes(operation) ? "readwrite" : "readonly");
    const request = transaction.objectStore(store)[operation](value);
    transaction.oncomplete = () => { resolve(request.result); db.close(); };
    transaction.onerror = () => { reject(transaction.error); db.close(); };
    transaction.onabort = () => { reject(transaction.error || new Error("Case save cancelled")); db.close(); };
  });
}
