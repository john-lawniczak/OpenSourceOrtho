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

// Keep only note metadata in memory, not every saved scan's STL and face labels.
export async function listEditNotes() {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("edits", "readonly"), entries = [];
    const request = tx.objectStore("edits").openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      const record = cursor.value;
      if (record.saved_at && record.name.startsWith("boundary-")) entries.push({
        title: `${record.scan?.filename || "Personal scan"} · ${record.scan?.arch || "Unknown arch"}`,
        notes: record.notes || "", saved_at: record.saved_at, review_status: record.review_status || "draft",
        href: `./region-review.html?edit=${encodeURIComponent(record.name)}`,
      });
      cursor.continue();
    };
    tx.oncomplete = () => { db.close(); resolve(entries); };
    tx.onerror = tx.onabort = () => { db.close(); reject(tx.error || new Error("Could not read browser paintings.")); };
  });
}

// Compare and write in one transaction so concurrent editors cannot overwrite
// each other's saved labels or notes between a read and a separate write.
export async function saveEditRevision(record, expectedRevision) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("edits", "readwrite"), store = tx.objectStore("edits");
    let conflict = false;
    const read = store.get(record.name);
    read.onsuccess = () => {
      if ((read.result?.revision || read.result?.saved_at || null) !== expectedRevision) { conflict = true; tx.abort(); }
      else store.put(record);
    };
    tx.oncomplete = () => { db.close(); resolve(record); };
    tx.onerror = tx.onabort = () => {
      db.close(); reject(new Error(conflict ? "A newer painting was saved in another editor. Reopen the scan before saving." : "Browser painting save failed."));
    };
  });
}
