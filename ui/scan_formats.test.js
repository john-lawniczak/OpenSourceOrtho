import assert from "node:assert/strict";
import test from "node:test";

import { inferArchFromName } from "./core.js";
import {
  SCAN_ACCEPT,
  SCAN_EXTENSIONS,
  buildViewerScanSources,
  isBrowserParsableScan,
  isSupportedScanName,
  looksLikePointCloud,
  scanUploadContentType,
} from "./scan_formats.js";

test("every format a consumer scanner exports is accepted", () => {
  for (const name of [
    "upper.stl", "upper.PLY", "arch.obj", "cloud.asc", "cloud.xyz", "cloud.pts",
    "model.3mf", "scan.gltf", "scan.glb", "textured.fbx",
  ]) {
    assert.equal(isSupportedScanName(name), true, name);
  }
  assert.equal(isSupportedScanName("notes.txt"), false);
  assert.equal(isSupportedScanName("archive.stl.zip"), false);
  assert.equal(isSupportedScanName(""), false);
  assert.equal(isSupportedScanName(undefined), false);
});

test("accept attribute lists every supported extension", () => {
  assert.equal(SCAN_ACCEPT.split(",").length, SCAN_EXTENSIONS.length);
  assert.ok(SCAN_ACCEPT.includes(".3mf"));
});

test("only the engine's canonical shapes are parsed in the browser", () => {
  assert.equal(isBrowserParsableScan("upper.stl"), true);
  assert.equal(isBrowserParsableScan("cloud.xyz"), true);
  assert.equal(isBrowserParsableScan("upper.ply"), false);
  assert.equal(isBrowserParsableScan("scan.glb"), false);
});

test("upload content type is per format, with a safe default", () => {
  assert.equal(scanUploadContentType("upper.stl"), "model/stl");
  assert.equal(scanUploadContentType("scan.glb"), "model/gltf-binary");
  assert.equal(scanUploadContentType("upper.ply"), "application/octet-stream");
});

test("non-STL uploads render from the engine's canonical copy, not the local file", () => {
  const ply = { name: "upper.ply" };
  const sources = buildViewerScanSources(
    [ply],
    [{ name: "upper.ply", url: "/api/mesh/abc", arch: "maxillary", asset: { id: "abc" } }],
    inferArchFromName,
  );

  assert.equal(sources.length, 1);
  assert.equal(sources[0].file, null, "a PLY the browser cannot parse must not be read locally");
  assert.equal(sources[0].url, "/api/mesh/abc");
  assert.equal(sources[0].arch, "maxillary");
});

test("an STL still renders from the local file, before any round trip", () => {
  const file = { name: "upper.stl" };
  const [source] = buildViewerScanSources([file], [], inferArchFromName);

  assert.equal(source.file, file);
  assert.equal(source.url, null);
  assert.equal(source.arch, "maxillary", "arch falls back to the filename when unregistered");
});

test("an unregistered non-STL file is dropped rather than rendered empty", () => {
  assert.deepEqual(buildViewerScanSources([{ name: "upper.ply" }], [], inferArchFromName), []);
});

test("with no picked files the registered sources are used as-is", () => {
  const registered = [{ name: "lower.obj", url: "/api/mesh/x", arch: "mandibular" }];
  assert.equal(buildViewerScanSources([], registered), registered);
});

test("point-cloud bytes are told apart from STL bytes", () => {
  const xyz = new TextEncoder().encode("0 0 0\n1 0 0\n0 1 0\n").buffer;
  assert.equal(looksLikePointCloud(xyz), true);

  const asciiStl = new TextEncoder().encode(
    "solid t\n facet normal 0 0 1\n  outer loop\n   vertex 0 0 0\n",
  ).buffer;
  assert.equal(looksLikePointCloud(asciiStl), false);

  const binaryStl = new Uint8Array(84 + 50).buffer;
  assert.equal(looksLikePointCloud(binaryStl), false);
});

test("arch is inferred from the u/l suffix on any scan extension", () => {
  assert.equal(inferArchFromName("case-u.ply"), "maxillary");
  assert.equal(inferArchFromName("case_l.3mf"), "mandibular");
  assert.equal(inferArchFromName("case-u.stl"), "maxillary");
});
