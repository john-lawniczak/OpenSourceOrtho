import { parseStlGeometry } from "./stl.js";
export const el = id => document.getElementById(id);
export async function scanFile(file, index) {
  if (!file) throw new Error("Choose both endpoint scans.");
  const bytes = await file.arrayBuffer();
  const geometry = parseStlGeometry(bytes); geometry.dispose();
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return { bytes, filename: file.name, sha256: Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2,"0")).join(""),
    label: index ? "Later visit" : "Baseline", date: "" };
}
export function orientation(index) { return JSON.parse(el(`orientation${index}`).value); }
export async function upload(scan) {
  const response = await fetch("/api/upload/scan", { method: "POST", headers: { "Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(scan.filename) }, body: scan.bytes });
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error(result.errors?.join("; ") || "Scan upload failed");
  return { reference: result.url, filename: scan.filename, rotation: scan.rotation };
}
export async function correctionFile(file) { return file ? JSON.parse(await file.text()) : null; }
