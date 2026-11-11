import { createScanComparison } from "./scan_comparison_viewer.js";

// Both arches occupy a shared display scene; placement is not a bite registration.
export function createHistoryViewer(host, options = {}) {
  return createScanComparison(host, { ...options, defaultZoom: 1.25 * 1.25 });
}
