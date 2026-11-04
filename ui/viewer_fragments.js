// Load a complete set atomically; a failed fragment must not leave a partial
// tooth set that looks reviewed. New requests invalidate and dispose old loads.
export function createFragmentLoader(parse, orient) {
  const cache = new Map();
  let revision = 0, key = "", pending = null, error = "";
  function clear() {
    revision++;
    for (const geometry of cache.values()) geometry.dispose();
    cache.clear();
    key = "";
    pending = null;
    error = "";
  }
  function load(items = []) {
    const nextKey = items.map(item => `${item.tooth}:${item.url}`).sort().join("|");
    if (nextKey === key) return pending || Promise.resolve(false);
    clear();
    key = nextKey;
    const token = revision;
    pending = Promise.all(items.map(async item => {
      let geometry;
      try {
        if (!item.tooth || !item.url) throw new Error("Invalid tooth fragment");
        const response = await fetch(item.url);
        if (!response.ok) throw new Error("Tooth fragment unavailable");
        const bytes = await response.arrayBuffer();
        if (token !== revision) return null;
        geometry = parse(bytes);
        orient(geometry);
        return [String(item.tooth), geometry];
      } catch { geometry?.dispose(); return null; }
    })).then(results => {
      if (token !== revision || results.some(item => !item)) {
        for (const item of results) item?.[1].dispose();
        if (token === revision) {
          key = ""; // An ordinary subsequent render can retry a transient failure.
          error = "Tooth surfaces could not be loaded. Re-select a tooth to retry.";
        }
        return false;
      }
      for (const [tooth, geometry] of results) cache.set(tooth, geometry);
      return results.length > 0;
    }).finally(() => { if (token === revision) pending = null; });
    return pending;
  }
  return { cache, load, clear, get error() { return error; } };
}
