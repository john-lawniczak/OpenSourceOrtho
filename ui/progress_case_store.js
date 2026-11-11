// Explicit local saves include original bytes so fitting can be repeated after restart.
async function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("ortho-two-visit-cases", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("cases", { keyPath: "name" });
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
}
export async function caseStore(operation, value) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction("cases", operation === "put" ? "readwrite" : "readonly");
    const request = transaction.objectStore("cases")[operation](value);
    transaction.oncomplete = () => { resolve(request.result); db.close(); };
    transaction.onerror = () => { reject(transaction.error); db.close(); };
    transaction.onabort = () => { reject(transaction.error || new Error("Case save cancelled")); db.close(); };
  });
}
