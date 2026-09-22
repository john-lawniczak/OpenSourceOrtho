// Scan-file formats the app accepts, and how the viewer gets geometry for one.
//
// Consumer scanners (Revopoint POP and friends) export whichever format the user
// picked in the scanner software, so intake accepts all of them. Parsing lives in
// the Python engine - one implementation, not two - and the engine stores every
// registered scan in a canonical form: binary STL for a mesh, plain-text XYZ for
// a point cloud. The browser therefore only ever parses those two shapes, and
// reads geometry for anything else from `/api/mesh/<id>`.
//
// Pure: no `THREE`, no `document`, no `fetch`, no `state`. Geometry parsing
// lives next door in scan_geometry.js, which is the only piece that needs a
// renderer.

// Keep in sync with SCAN_SUFFIXES in orthoplan/io/mesh_formats/__init__.py.
export const SCAN_EXTENSIONS = [
  ".stl", ".ply", ".obj", ".asc", ".xyz", ".pts", ".3mf", ".gltf", ".glb", ".fbx",
];

export const SCAN_ACCEPT = SCAN_EXTENSIONS.join(",");

// "STL, PLY, OBJ, ASC, XYZ, PTS, 3MF, GLTF, GLB or FBX"
export const SCAN_FORMATS_LABEL = (() => {
  const names = SCAN_EXTENSIONS.map((ext) => ext.slice(1).toUpperCase());
  return `${names.slice(0, -1).join(", ")} or ${names[names.length - 1]}`;
})();

const CONTENT_TYPES = { ".stl": "model/stl", ".gltf": "model/gltf+json", ".glb": "model/gltf-binary" };
// The two canonical shapes the engine serves back, and the only ones parsed here.
const BROWSER_PARSABLE = [".stl", ".xyz"];

export function scanExtension(name = "") {
  const text = String(name).toLowerCase();
  const dot = text.lastIndexOf(".");
  return dot < 0 ? "" : text.slice(dot);
}

export function isSupportedScanName(name) {
  return SCAN_EXTENSIONS.includes(scanExtension(name));
}

// True when the browser can render the file the user picked without waiting for
// the engine to canonicalize it.
export function isBrowserParsableScan(name) {
  return BROWSER_PARSABLE.includes(scanExtension(name));
}

export function scanUploadContentType(name) {
  return CONTENT_TYPES[scanExtension(name)] || "application/octet-stream";
}

// Pair each picked file with its registered asset, and decide where the viewer
// reads its bytes from: the local file when the browser can parse that format,
// otherwise the engine's canonical copy. A file that is neither parsable locally
// nor registered has no geometry to show and is dropped.
export function buildViewerScanSources(files = [], registered = [], inferArch = () => null) {
  if (!files.length) return registered;
  const byName = new Map(registered.map((source) => [source.name, source]));
  return files
    .map((file) => {
      const match = byName.get(file.name);
      const local = isBrowserParsableScan(file.name);
      return {
        name: file.name,
        file: local ? file : null,
        url: match?.url || null,
        arch: match?.arch || inferArch(file.name) || null,
        asset: match?.asset || null,
      };
    })
    .filter((source) => source.file || source.url);
}

// A canonical point cloud is ASCII "x y z" rows; canonical mesh bytes are STL,
// which is either binary (not decodable as text) or starts with "solid".
export function looksLikePointCloud(buffer) {
  const head = new Uint8Array(buffer, 0, Math.min(buffer.byteLength, 512));
  let text = "";
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(head);
  } catch {
    return false;
  }
  const lines = text.split(/\r?\n/).slice(0, -1).filter((line) => line.trim());
  if (!lines.length) return false;
  return lines.every((line) => {
    const parts = line.trim().split(/[\s,]+/);
    return parts.length >= 3 && parts.slice(0, 3).every((part) => Number.isFinite(Number(part)));
  });
}
