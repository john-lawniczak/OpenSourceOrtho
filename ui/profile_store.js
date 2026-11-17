import { activeProfileId, validProfileId } from "./profile_context.js";

async function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("orthoplan-profiles", 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore("profiles", { keyPath: "id" });
      request.result.createObjectStore("workspaces", { keyPath: "id" });
      request.transaction.objectStore("profiles").add({ id: "default", name: "My profile", createdAt: new Date().toISOString() });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function transaction(stores, mode, action) {
  const db = await database();
  return new Promise((resolve, reject) => {
    let tx;
    try { tx = db.transaction(stores, mode); } catch (error) { db.close(); reject(error); return; }
    let result, error;
    const fail = reason => { error = reason; tx.abort(); };
    tx.oncomplete = () => { db.close(); resolve(result); };
    tx.onerror = tx.onabort = () => { db.close(); reject(error || tx.error || new Error("Profile storage failed.")); };
    try { action(tx, value => { result = value; }, fail); } catch (reason) { fail(reason); }
  });
}
export const listProfiles = () => transaction(["profiles"], "readonly", (tx, done) => {
  const request = tx.objectStore("profiles").getAll(); request.onsuccess = () => done(request.result);
});
export function createProfile(name) {
  name = name.trim();
  if (!name || name.length > 60) throw new Error("Enter a profile name of 1–60 characters.");
  const profile = { id: crypto.randomUUID(), name, createdAt: new Date().toISOString() };
  return transaction(["profiles"], "readwrite", (tx, done, fail) => {
    const store = tx.objectStore("profiles"), request = store.getAll();
    request.onsuccess = () => {
      if (request.result.some(p => p.name.toLocaleLowerCase() === name.toLocaleLowerCase())) return fail(new Error("That profile name is already in use."));
      store.add(profile); done(profile);
    };
  });
}
export function renameProfile(id, name) {
  name = name.trim();
  if (!validProfileId(id) || !name || name.length > 60) throw new Error("Enter a profile name of 1–60 characters.");
  return transaction(["profiles"], "readwrite", (tx, done, fail) => {
    const store = tx.objectStore("profiles"), request = store.getAll();
    request.onsuccess = () => {
      const profile = request.result.find(p => p.id === id);
      if (!profile || request.result.some(p => p.id !== id && p.name.toLocaleLowerCase() === name.toLocaleLowerCase())) return fail(new Error("Profile missing or name already used."));
      store.put({ ...profile, name }); done();
    };
  });
}
export const loadWorkspace = () => transaction(["workspaces"], "readonly", (tx, done) => {
  const request = tx.objectStore("workspaces").get(activeProfileId); request.onsuccess = () => done(request.result || null);
});
export function saveWorkspace(data, expectedRevision) {
  return transaction(["workspaces", "profiles"], "readwrite", (tx, done, fail) => {
    const profiles = tx.objectStore("profiles"), exists = profiles.get(activeProfileId);
    exists.onsuccess = () => {
      if (!exists.result) return fail(new Error("This profile no longer exists."));
      const store = tx.objectStore("workspaces"), request = store.get(activeProfileId);
      request.onsuccess = () => {
        if ((request.result?.revision || null) !== expectedRevision) return fail(new Error("Progress changed in another tab. Reload before saving; this tab has not overwritten it."));
        const record = { id: activeProfileId, revision: crypto.randomUUID(), savedAt: new Date().toISOString(), data };
        store.put(record); done(record);
      };
    };
  });
}
